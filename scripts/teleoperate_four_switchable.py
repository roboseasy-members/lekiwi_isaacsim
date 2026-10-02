#!/usr/bin/env python3
"""One keyboard + one SO-101 leader, switch among four LeKiwi robots.

`--record` turns on a second, independent mode built for capturing real
manual teleop sessions on video: Blue 1 is locked as the only manually
driven robot (T/F is disabled), the other three putter around on their own
at low speed, and four fixed recording cameras (top / Blue 1 base-follow /
Blue 1 gripper / basket-side) capture to their own PNG sequences + a shared
per-frame log, independent of whatever the interactive viewport is showing.
Recording start/stop is triggered from another terminal via
record_start.sh / record_stop.sh (POSIX signals), not from inside this
process's own keyboard loop, so it doesn't compete with driving input.

Nothing here fakes a grasp: there is no auto-approach, no arm keyframing, no
ball teleport, and no forced attachment. Picking a ball up only ever happens
through the real leader-arm joints and PhysX friction, exactly as in the
plain (non---record) mode.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import math
import os
import queue
import random
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import zmq


PROJECT_ROOT = Path(__file__).resolve().parent
BUNDLE_SCRIPTS = (
    PROJECT_ROOT / "teleop_bundle/lekiwi_test_room_bundle/scripts"
)
sys.path.insert(0, str(BUNDLE_SCRIPTS))
from lekiwi_protocol import LeaderMessage, decode_leader_message
import lekiwi_ik
import task_recording_presets as task_presets


ROBOTS = {
    "Blue 1": "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_01",
    "Blue 2": "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_02",
    "Red 1": "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_01",
    "Red 2": "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_02",
}
MANUAL_ROBOT = "Blue 1"

WHEEL_JOINTS = ("left_wheel_joint", "back_wheel_joint", "right_wheel_joint")
ARM_JOINTS = {
    "shoulder_pan.pos": "shoulder_pan",
    "shoulder_lift.pos": "shoulder_lift",
    "elbow_flex.pos": "elbow_flex",
    "wrist_flex.pos": "wrist_flex",
    "wrist_roll.pos": "wrist_roll",
    "gripper.pos": "gripper",
}

ARM_MAX_STEP_DEG = {
    "shoulder_pan.pos": 4.0,
    "shoulder_lift.pos": 4.0,
    "elbow_flex.pos": 8.0,
    "wrist_flex.pos": 8.0,
    "wrist_roll.pos": 8.0,
}

# Stiffness/damping/max_force while nothing is driving the arm yet. A first
# version used zero stiffness (damping only): with no spring term there is
# no restoring force at all, so gravity just keeps rotating the joint at a
# roughly constant terminal velocity -- measured over an 8 s headless run,
# shoulder_lift never stopped drooping (2 deg -> 28 deg and still climbing,
# heading for a joint-limit hard stop, not a settle). A soft spring toward
# an actual "hanging" target gives it a real equilibrium so it settles
# within a couple of seconds instead of drifting indefinitely -- confirmed
# by the same measurement: shoulder_lift/elbow_flex both plateau by ~t=5s.
ARM_RELAXED_DRIVE = (3.0, 2.0, 3.0)
ARM_RELAXED_TARGET_DEG = {
    "shoulder_pan.pos": 0.0,
    "shoulder_lift.pos": 45.0,
    "elbow_flex.pos": 20.0,
    "wrist_flex.pos": 10.0,
    "wrist_roll.pos": 0.0,
    "gripper.pos": 0.0,
}

# When a robot starts actually receiving leader commands (first connect,
# reconnect after a stale gap, or switching the active robot while the
# leader is already streaming), its arm target is blended from wherever the
# joint *physically* is right now to the leader's reported pose over this
# many seconds, instead of snapping the drive target straight to the
# leader's raw value on the very first message (the old
# `state.get(key, requested)` default did exactly that: with no prior
# `state` entry it returns `requested` itself, so the first call clamps
# nothing).
CONNECT_BLEND_SECONDS = 0.6

OVERALL_VIEW_CAMERA = "/World/Arena/SpectatorCamera"

# Background robots (every robot except MANUAL_ROBOT) drive their base with
# a small random walk so they look alive instead of frozen; their arms are
# left alone (relaxed, since they never receive leader data).
BACKGROUND_LINEAR_SPEED = (0.05, 0.12)   # m/s, sampled per action -- "저속"
BACKGROUND_ROTATE_DEG = (15.0, 50.0)     # deg/s, sampled per action
BACKGROUND_ACTION_SECONDS = (1.0, 2.5)
BACKGROUND_TEAM_MARGIN = 0.15            # m clearance from the net/centre line
BACKGROUND_WALL_MARGIN = 0.25            # m clearance from the outer walls
# Measured base+wheel footprint width is ~0.356 m (see ARENA_NET_REVISION.md
# section 6); this is a centre-to-centre keep-out distance, so it already
# gives roughly a half-body gap on each side once two robots are this far
# apart.
ROBOT_CLEARANCE = 0.42
# 공 무작위 재배치 폭 (N 키). 시연 데이터가 한 자리에만 몰리지 않게 한다 (2026-10-01)
BALL_SCATTER_X = 0.12
BALL_SCATTER_Y = 0.12
# 공 콜라이더는 내접 정육면체라 실제로는 z≈0.022 m 에 안착한다(create_net_arena PHYSICS PASS 실측).
# 그 높이에 바로 놓아야 튀지 않고 '이상적인 정렬 상태' 가 그대로 재현된다.
# --grasp-demo 로 놓을 때 공 중심 높이. 공의 **콜라이더(속 정육면체) 반높이**가 곧 안정 높이다
# — 보이는 구(반지름 40 mm)가 아니다. 2026-10-01 콜라이더를 46.2 → 60.0 mm 로 키우면서
# 안정 높이가 21.3 → 28.7 mm 가 됐다(sim_ball_rest_check.py 실측). 예전 값 23 mm 로 놓으면
# 공이 바닥에 박힌 채 시작해 턱이 그 위를 지나간다.
BALL_DEMO_Z = 0.029               # --grasp-demo 로 놓을 때 공 중심 높이
BALL_PARK_X = 1.45                # 쓰지 않는 공을 치워 둘 자리(코트 가장자리)
BALL_PARK_Y0 = -0.85

# --auto-base (2026-10-01, 베이스 전용 자율주행). 경로 계획·추종 파라미터.
AUTO_GRID_RES = 0.02              # 점유격자 해상도 m/셀 (3x2 m 코트 → 약 160x110)
AUTO_GRID_Z_MAX = 0.35            # 이 높이 위에만 있는 것은 베이스가 지나갈 수 있다
AUTO_SAFETY_MARGIN = 0.04         # 발자국 내접반경에 더할 여유
AUTO_ROBOT_OBSTACLE_R = 0.26      # 재계획 시 다른 로봇을 이 반경 원으로 찍는다
AUTO_BASE_SPEED = 0.60            # m/s
AUTO_BASE_ROT_DEG = 90.0          # deg/s 상한
AUTO_GOAL_TOL = 0.06              # m, 최종 웨이포인트 도착 판정
AUTO_GOAL_SNAP = 0.30             # m, 목표가 장애물 안이면 이 반경에서 빈 칸으로 당긴다
AUTO_FACE_TOL_DEG = 20.0          # 목표를 바라보는 각도 허용치(베이스만 쓰므로 느슨하게)
AUTO_FACE_MAX_S = 3.0             # 방향 맞추기 최대 시간. 베이스 각 감쇠가 커서 90 deg/s 를 줘도
                                  # 실제로는 10~20 deg/s 밖에 안 돈다(2026-10-01 실측) → 무한 대기 금지
# 2026-10-01 sim_grasp_pose.py 쓸기 결과: 베이스 중심~공 0.28 m 에서 팔이 가장 잘 닿는다
# (0.20/0.24 는 shoulder_lift 가 100° 한계에 걸리고, 0.32 이상은 멀어 못 닿는다).
# 실물 정렬값(베이스 바깥 0.075 + 반경 0.13 + 공 반지름 0.04 ≈ 0.245 m)과도 가깝다.
AUTO_BALL_STANDOFF = 0.28         # 공 중심에서 이만큼 떨어져 선다
# 정지 지점은 라이다 안전정지(gap 0.10 m)보다 멀어야 한다. 베이스 바깥 반경 0.18 을 더해
# 네트/바구니 면에서 0.28 m 이상 떨어지도록 잡는다 — 더 가까이 잡으면 스스로 멈춰 도착을 못 한다.
AUTO_NET_STANDOFF = 0.34          # 네트선(x=0)에서 이만큼 앞에 선다
AUTO_NET_Y_LIMIT = 0.80           # 네트 앞 정지 지점의 |y| 상한
AUTO_BASKET_STANDOFF = 0.40       # 바구니 중심에서 네트 반대쪽으로 이만큼 떨어져 선다
AUTO_BASKET_LANE = 0.14           # 같은 바구니로 두 대가 몰릴 때 서로 비키는 가로 간격
AUTO_REPLAN_SECONDS = 1.5         # 주행 중 재계획 주기(공이 굴러가거나 로봇이 막을 수 있다)
AUTO_STATE_TIMEOUT = 45.0         # 한 주행 상태의 상한(초, 시뮬 시간)
AUTO_PICK_PAUSE = 1.0             # '집는 척' 멈춰 서 있는 시간
AUTO_DROP_PAUSE = 0.8             # 놓기 전 멈춰 서 있는 시간
# 라이다 (실물: 베이스 제일 아래, 바닥 2 cm). 항법에서는 **안전 정지와 회피**에만 쓴다.
# 실물에서 배운 규칙: 앞이 막히면 기능과 무관하게 먼저 멈춘다 (2026-09-23 바구니 충돌).
AUTO_LIDAR_RAYS = 120
AUTO_LIDAR_STOP_GAP = 0.10        # 베이스 바깥 기준 이 거리 안이면 전진 금지
AUTO_LIDAR_SLOW_GAP = 0.25        # 이 거리 안이면 감속
AUTO_LIDAR_FRONT_DEG = 35.0       # 전방 판정 반각
AUTO_LIDAR_MIN_POINTS = 2         # 잡음 1점으로는 멈추지 않는다
AUTO_BASE_EDGE_R = 0.18           # 라이다(베이스 중심) → 베이스 바깥 반경 (실물 0.13, 심 발자국 기준)
AUTO_LIDAR_PERIOD = 0.1           # s, 실물 라이다와 같은 10 Hz (매 틱 쏘면 레이캐스트가 루프를 잡아먹는다)
AUTO_STATUS_PERIOD = 5.0          # s, 상태 요약 출력 주기
BASKET_KEEPOUT_MARGIN = 0.15
COLLISION_LOOKAHEAD_SECONDS = 0.3

# ---------------------------------------------------------------------- #
# AI autonomous-grasp-attempt mode (--ai-mode). This is a scripted
# perception + finite-state-machine + numerical-IK controller, NOT a
# trained policy: no SmolVLA/ACT/X-VLA checkpoint compatible with this
# robot/camera/action-space exists locally as of 2026-09-11 (see
# research/2026-09-10_v1/recommended_architecture.md). Ball positions come
# from the simulator's own ground-truth prim transforms, not from camera
# perception -- every state-transition log line below is prefixed
# "[AI]" and states are printed on every change specifically so this is
# never confused with either a learned policy or a human demonstration in
# any recording/log taken from this mode.
# ---------------------------------------------------------------------- #
# 2026-10-01: 고정 파지 자세(SIM_GRASP_POSE_DEG)는 공이 베이스 중심에서 0.28 m 앞에 있을 때
# 맞춰져 있다 → 베이스 정지 거리를 그 값과 똑같이 둔다(sim_grasp_pose.py 쓸기 결과).
AI_STANDOFF_DIST = 0.28          # m, base stops this far from the ball before the arm phase
AI_POS_TOLERANCE = 0.06          # m, base position tolerance to end APPROACH
AI_HEADING_TOLERANCE_DEG = 18.0  # deg, base heading tolerance to end APPROACH
AI_BASE_LINEAR_SPEED = 0.14      # m/s cap while approaching
AI_BASE_ROT_GAIN = 2.0           # deg/s commanded per deg of heading error
AI_BASE_ROT_SPEED_CAP = 60.0     # deg/s
AI_ARM_POS_TOLERANCE = 0.03      # m, live gripper-to-target tolerance to advance the arm state
AI_ARM_UNREACHABLE_ERROR = 0.05  # m, IK residual above this treated as "not reachable from here"
AI_GRASP_HOVER_HEIGHT = 0.07     # m above ball centre for the pre-grasp hover point
# 2026-10-01 사용자 지시: 공을 **가로로** 잡는다. 지금까지는 턱이 세로로 선 채 위에서 내려와
# 공(속 정육면체)의 모서리에 걸려 22회 시도에서 들어올림 0회였다. wrist_roll 을 90° 돌려
# 턱이 수평이 되게 하면 정육면체의 마주 보는 두 옆면을 잡는다.
AI_GRASP_WRIST_ROLL_DEG = 90.0
AI_GRASP_JAW_TOL = 0.045         # m, 턱 중 가까운 쪽이 공에서 이 거리 안이면 닫아도 된다
AI_ARM_RATE_DEG_PER_S = 90.0     # deg/s, 고정 자세로 갈 때의 관절 속도 제한
AI_JAW_REFINE_PERIOD = 0.35      # s, 턱 오프셋 재측정 주기(매 틱 갱신하면 목표가 달아나 발산한다)
AI_DESCEND_MAX_S = 8.0           # s, 이 안에 턱이 공에 닿지 못하면 실패
# 정렬이 끝나면 공은 베이스 기준 (앞 0.28 m, 중앙, 높이 0.04 m) 에 고정된다 → IK 로 매 틱 쫓지 않고
# 이 자세 하나를 재생한다. sim_grasp_pose.py 로 구함(턱중앙-공 2.0 cm). 실물 poses/grasp.json 과 같은 개념.
SIM_GRASP_POSE_DEG = {
    "shoulder_pan.pos": 86.13,
    "shoulder_lift.pos": 90.85,
    "elbow_flex.pos": -28.87,
    "wrist_flex.pos": -9.18,
    "wrist_roll.pos": 90.00,
}
AI_LIFT_DELTA_Z = 0.14           # m, how far to lift after closing
AI_BLUE1_DEFER_RADIUS = 0.35     # m, balls this close to Blue 1 are left for the user
BALL_RADIUS_M = 0.040            # m (NEXT_CHAT_HANDOFF.md section 7)
AI_LIFTED_HEIGHT_THRESHOLD = BALL_RADIUS_M + 0.03  # m, ball centre Z counted as "lifted"
AI_CARRY_DISTANCE = 0.06         # m, gripper-to-ball distance counted as "still in hand"
AI_MAX_CONSECUTIVE_FAILS = 3     # same-ball retries before a cooldown
AI_FAIL_COOLDOWN_SECONDS = 8.0
AI_STATE_TIMEOUT_SECONDS = {
    # CLOSE was 3.0s until a headless measurement (2026-09-11, after fixing
    # the ai_set_gripper "done" bug -- see its docstring) showed the
    # deliberately weak/compliant gripper drive (stiffness 8.0, damping
    # 2.0, max_force 0.45 -- NOT changed here, per standing instruction not
    # to touch gripper drive values) only reaches ~50% closed_fraction in
    # 3s. 8s comfortably covers a full close at that measured rate.
    "APPROACH": 15.0, "ARM_UP": 6.0, "DESCEND": 5.0, "CLOSE": 8.0,
    # All in SIMULATED seconds (update_ai_robots is fed timeline time).
    "LIFT": 6.0, "VERIFY": 1.5, "PLACE": 5.0, "RETREAT": 15.0,
    "CARRY": 40.0, "PASS_REACH": 12.0, "PASS_RELEASE": 8.0,
}
# After a successful lift on a net arena the robot carries the ball to the
# net and sets it down on the opponent's side ("pass"): base stops this far
# from the net (x=0), gripper reaches this far past the net at this height
# (net top is 0.30 m; ball hangs ~0.03-0.04 m below the gripper frame).
AI_PASS_STANDOFF_X = 0.24   # base edge (~0.18 radius) still clears the 0.02 m net collider
AI_PASS_OVER_X = 0.05       # 0.08 left a ~0.055 m IK residual from a 0.26 standoff (headless)
AI_PASS_HEIGHT = 0.40
AI_PASS_BASKET_CLEAR = 0.45   # keep the pass spot this far (in y) from the own basket centre

# Per-task takes (2026-09-11): "blue1_topdown" reuses the manual robot's
# viewport top-down camera prim; "net" is a fixed view across the net that is
# only switched on (render product created) once the manual robot attaches a
# ball during a take; "top" can be limited to the first --record-top-seconds
# of a take. Together these keep a take at ~3 live cameras, which is what the
# PNG writers can sustain without dropping frames (see RECORD_WRITER_THREADS).
RECORD_CAMERA_NAMES = ("top", "blue1_follow", "blue1_gripper", "basket_side", "blue1_topdown", "net",
                       "opponent_basket", "own_basket")
# --record-task markers: written by record_mark.sh into the command file
# (logs/recording_sessions/current.cmd), consumed by the main loop and logged
# to events.csv with the current frame/sim/wall time. Operator annotations
# only -- never treated as a physics verdict. No keyboard shortcuts: the
# user asked for every recording action to be a separate command.
MARKER_NAMES = ("attempt_start", "grasp", "release", "success", "failed")
RECORD_MIN_FREE_DISK_GB = 5.0
# Bounded PNG-write queue: at 4 cameras this holds a few seconds of frames
# (640x360x3 bytes each) before the writer thread must catch up. Bounded so a
# slow disk cannot grow memory without limit -- capture_tick() drops (and
# logs) a frame rather than blocking the control loop when this fills up.
RECORD_QUEUE_MAXSIZE = 512
# PNG encoding (PIL, compress_level=1) measured ~61 ms per 1280x720 frame:
# one writer thread tops out at ~16 frames/s while 4 cameras at 8 fps need
# 32/s, and the first FHD take (rec_20260911_132705_001) dropped 3384 of
# 7404 camera-frames -- almost all from the cameras captured last in the
# tick. PIL releases the GIL inside its encoder, so several writer threads
# really do run in parallel.
RECORD_WRITER_THREADS = 4
RECORD_FINALIZE_TIMEOUT_SECONDS = 15.0

# --data-collect: LeRobot-style per-step training data for Blue 1 only,
# using the LeKiwi asset's OWN base_camera/wrist_camera prims (confirmed to
# exist and render via a headless probe, 2026-09-11) instead of an
# externally-placed cinematic camera -- these are the two that would still
# exist on a real robot, per the requirement to prefer real-hardware-
# reproducible observation cameras over sim-only viewpoints. Always used
# together with --record's own shared start/stop signal (SIGUSR1/SIGUSR2)
# so one take produces both the demo video and the training episode from
# the same session; --data-collect without --record is rejected in
# parse_args() rather than silently degrading into a video-less mode nobody
# asked for.
DATASET_CAMERAS = (("base_camera", "base_link"), ("wrist_camera", "gripper_link"))
DATASET_FINALIZE_TIMEOUT_SECONDS = 15.0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", default=str(PROJECT_ROOT / "lekiwi_arena_3p0x2p0_4robots.usd")
    )
    parser.add_argument("--endpoint", default="tcp://127.0.0.1:5557")
    parser.add_argument("--fps", type=float, default=60.0)
    parser.add_argument("--linear-speed", type=float, default=0.35)
    parser.add_argument("--rotation-speed", type=float, default=75.0)
    parser.add_argument("--leader-timeout", type=float, default=0.5)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--run-seconds", type=float, default=0.0)

    parser.add_argument(
        "--ai-mode", action="store_true",
        help="Replace the low-speed random background wander (every robot "
             "except the active/manual one) with a SEARCH/APPROACH/ARM_UP/"
             "DESCEND/CLOSE/LIFT/VERIFY/PLACE/RETREAT grasp-attempt state "
             "machine driven by simulator ground-truth ball positions and "
             "a numerical IK solver (lekiwi_ik.py). This is a scripted "
             "baseline, not a trained policy -- see the module docstring "
             "and NEXT_CHAT_HANDOFF.md section 16. Manually selecting a "
             "robot (T/F, or the fixed Blue-1-manual assignment under "
             "--record) always overrides AI control for that robot "
             "immediately.",
    )
    parser.add_argument(
        "--auto-base", action="store_true",
        help="베이스 전용 자율주행 루프 (2026-10-01). 팔·그리퍼는 건드리지 않는다. "
             "경기 로직: 가장 가까운 공 탐색 → 격자 A* 경로로 그 공 앞까지 주행 → "
             "집기는 '했다 치고'(기존 scripted attach 로 공을 붙인다) → 공 색에 따라 "
             "네트/바구니 앞까지 주행 → 놓기 → 반복. 경로 계획·추종은 sim_nav.py. "
             "--ai-mode(팔 IK 파지 시도)와 동시에 쓰지 않는다.",
    )
    parser.add_argument(
        "--render-width", type=int, default=2560,
        help="뷰포트 렌더 해상도 가로. 기본 2560 은 영상 녹화용 — 데이터 수집 때는 --low-render 를 쓰면 1280 으로 내려간다.",
    )
    parser.add_argument(
        "--render-height", type=int, default=1440,
        help="뷰포트 렌더 해상도 세로.",
    )
    parser.add_argument(
        "--low-render", action="store_true",
        help="GPU 부담 줄이기 (2026-10-01): 렌더 1280x720 + 반사/AO/translucency 끔. "
             "데이터 수집·텔레옵처럼 화질이 중요하지 않을 때 쓴다.",
    )
    parser.add_argument(
        "--grasp-demo", action="store_true",
        help="시연 수집용 (2026-10-01 사용자 지시). 정렬을 하지 않고 **공을 수동 로봇 바로 앞**"
             "(베이스 기준 정면 GRASP_DEMO_DIST m, 바닥)에 갖다 놓는다. 에피소드를 넘길 때마다"
             "(→ 키) --demo-colors 순서로 색을 바꿔 다음 공을 놓는다. 팔만 사람이 조작한다.",
    )
    parser.add_argument(
        "--demo-colors", default="red,yellow,blue",
        help="--grasp-demo 에서 돌아가며 놓을 공 색 순서.",
    )
    parser.add_argument(
        "--demo-dist", type=float, default=0.28,
        help="--grasp-demo: 베이스 중심에서 공까지 거리 m. 기본 0.28 = 항법 정렬이 노리는 "
             "**이상적인 정렬 위치**(AUTO_BALL_STANDOFF)와 같은 값이다. 좌우 오차는 0.",
    )
    parser.add_argument(
        "--align-demo", action="store_true",
        help="시연 데이터 수집용 (2026-10-01). --auto-base 와 함께 쓴다. 수동 로봇(기본 Blue 1)까지 "
             "항법이 **정렬만** 해 준다: 가장 가까운 공 앞 AUTO_BALL_STANDOFF 까지 가서 멈추고, "
             "집기·배달은 하지 않는다(팔은 사람이 리더암으로). N 키로 공을 흩으면 다시 정렬한다. "
             "추론 때와 같은 알고리즘으로 시작 자세를 만들기 위한 모드 — 수동 주행으로 정렬하면 "
             "학습 데이터의 시작 상태가 배포 때와 달라진다.",
    )
    parser.add_argument(
        "--auto-base-robots", default="all",
        help="--auto-base 대상: 'all'(기본) 또는 라벨 쉼표 목록(예: 'Red 1,Red 2'). "
             "수동 선택된 로봇은 어느 경우에도 제외된다.",
    )
    parser.add_argument(
        "--debug-press-g", default="",
        help="Headless test hook only: comma-separated wall-clock seconds after "
             "the loop starts at which to simulate a G key press on the active "
             "robot (there is no keyboard in --headless).",
    )
    parser.add_argument(
        "--ai-prefer-color", default="white",
        help="--ai-mode ball choice: prefer balls whose arena:ballColor matches "
             "this (nearest such ball first; any other ball only if none is "
             "available). Empty string = nearest ball regardless of colour.",
    )
    parser.add_argument(
        "--record", action="store_true",
        help="Recording mode: lock Blue 1 as the only manual robot, run the "
             "other three as low-speed random wanderers, and enable the "
             "four-camera recording subsystem (start/stop via SIGUSR1/"
             "SIGUSR2 -- see record_start.sh / record_stop.sh).",
    )
    parser.add_argument("--record-fps", type=float, default=15.0,
                         help="Target capture rate for the 4 recording cameras "
                              "(independent of --fps, the control-loop rate).")
    parser.add_argument("--record-width", type=int, default=640)
    parser.add_argument("--record-height", type=int, default=360)
    parser.add_argument(
        "--record-cameras", default="top,blue1_follow,blue1_gripper,basket_side",
        help="Comma-separated subset of top,blue1_follow,blue1_gripper,basket_side,"
             "blue1_topdown,net to actually render/capture -- fewer cameras costs "
             "less per frame on an 8GB GPU (real achieved fps was ~6.25fps at 4 "
             "cameras/640x360 in a logged GUI+--ai-mode session, well under the "
             "--record-fps target; see NEXT_CHAT_HANDOFF.md section 16). "
             "'net' only starts rendering once Blue 1 attaches a ball during a "
             "take; see --record-top-seconds for 'top'. e.g. --record-cameras top,blue1_gripper",
    )
    # --- Single-camera task recording (2026-09-11) ---------------------
    # A task/view pair selects ONE recording camera preset and the output
    # label (logs/task_recordings/<task>/<view>/<timestamp>_takeNNN/). It
    # implies --record with exactly that camera, so nothing else is rendered
    # or saved. Task names never trigger automatic grasping or scoring.
    parser.add_argument("--record-task", default="",
                        help="Task label for single-camera recording; see --list-record-tasks.")
    parser.add_argument("--record-view", default="",
                        help="Camera view for --record-task (net, robot_top, gripper, arena, "
                             "opponent_basket, own_basket).")
    parser.add_argument("--list-record-tasks", action="store_true",
                        help="Print the supported task/view combinations and exit.")
    parser.add_argument("--record-outdir", default=str(PROJECT_ROOT / "logs/task_recordings"),
                        help="Root folder for --record-task takes.")
    parser.add_argument("--preview-views", default="",
                        help="Headless check: render one still per camera view preset into "
                             "this directory and exit (no recording).")
    parser.add_argument(
        "--record-top-seconds", type=float, default=0.0,
        help="If > 0, the 'top' camera is captured only for this many wall-clock "
             "seconds after each record start, then switched off (its render "
             "product is destroyed) so the GPU/PNG budget goes to the remaining "
             "cameras. 0 = keep 'top' for the whole take.",
    )
    parser.add_argument(
        "--record-dir", default=str(PROJECT_ROOT / "logs/recording_sessions")
    )
    parser.add_argument(
        "--data-collect", action="store_true",
        help="Also write a LeRobot-style per-step training episode for "
             "Blue 1 (images from the robot's own base_camera/wrist_camera, "
             "joint state, gripper, base state, applied action, raw leader "
             "input, timestamps, episode metadata) every time --record "
             "starts/stops a session. Requires --record.",
    )
    parser.add_argument(
        "--dataset-dir", default=str(PROJECT_ROOT / "logs/datasets"),
        help="Output directory for --data-collect episodes.",
    )
    parser.add_argument(
        "--scripted-attach", action="store_true",
        help="NOT real friction/contact grasping. For ANY robot (manual or "
             "--ai-mode), if the gripper is mostly closed and both jaws "
             "(gripper_link and moving_jaw_so101_v1_link) are within a few "
             "cm of a ball, the ball is kinematically glued to the gripper "
             "frame (offset computed at the moment of contact, per grasp-"
             "frame practice) until the gripper opens again, at which point "
             "it's released back to normal physics. This exists because "
             "real IK-driven contact grasping was not reliable (0/~15 "
             "headless lifts, and the user's own hands-on leader-arm "
             "attempt also failed) -- see NEXT_CHAT_HANDOFF.md section 16. "
             "Every attach/release logs as [ATTACH], and any success/data "
             "coming from this mode must be labeled 'scripted_attach', "
             "never reported as a real grasp.",
    )
    args = parser.parse_args()
    if args.list_record_tasks:
        print(task_presets.format_listing())
        raise SystemExit(0)
    if args.preview_views:
        # Render every preset once: needs the full recording camera rig.
        args.record = True
        args.headless = True
        args.record_cameras = ",".join(v["camera"] for v in task_presets.VIEWS.values())
    if args.record_task or args.record_view:
        if not (args.record_task and args.record_view):
            raise SystemExit("--record-task and --record-view must be given together.\n"
                             + task_presets.format_listing())
        ok, message = task_presets.validate(args.record_task, args.record_view)
        if not ok:
            raise SystemExit(f"{message}\n\n{task_presets.format_listing()}")
        args.record = True
        args.record_cameras = task_presets.VIEWS[args.record_view]["camera"]
        args.record_dir = str(Path(args.record_outdir) / args.record_task / args.record_view)
    if args.data_collect and not args.record:
        raise SystemExit("--data-collect requires --record (shared start/stop signal "
                          "and camera-rig session lifecycle).")
    selected_cameras = [n.strip() for n in args.record_cameras.split(",") if n.strip()]
    invalid = [n for n in selected_cameras if n not in RECORD_CAMERA_NAMES]
    if invalid or not selected_cameras:
        raise SystemExit(f"--record-cameras: invalid/empty selection {selected_cameras!r}; "
                          f"choose from {RECORD_CAMERA_NAMES}")
    args.record_cameras = selected_cameras
    return args


def find_joint(stage: Any, robot_path: str, joint_name: str):
    exact = stage.GetPrimAtPath(f"{robot_path}/joints/{joint_name}")
    if exact.IsValid():
        return exact
    matches = [
        prim
        for prim in stage.Traverse()
        if str(prim.GetPath()).startswith(robot_path)
        and prim.GetTypeName() == "PhysicsRevoluteJoint"
        and prim.GetName() == joint_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one joint '{joint_name}' below {robot_path}; got {len(matches)}"
        )
    return matches[0]


def configure_drive(prim, UsdPhysics, stiffness, damping, max_force):
    drive = UsdPhysics.DriveAPI.Get(prim, "angular")
    if not drive:
        drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
    drive.CreateTypeAttr("force")
    drive.CreateStiffnessAttr(float(stiffness))
    drive.CreateDampingAttr(float(damping))
    drive.CreateMaxForceAttr(float(max_force))
    return drive


def joint_limits(prim, UsdPhysics):
    joint = UsdPhysics.RevoluteJoint(prim)
    lower = joint.GetLowerLimitAttr().Get()
    upper = joint.GetUpperLimitAttr().Get()
    if lower is None or upper is None or float(lower) >= float(upper):
        return None
    return float(lower), float(upper)


def receive_latest(subscriber):
    newest = None
    while True:
        try:
            payload = subscriber.recv(flags=zmq.NOBLOCK)
        except zmq.Again:
            return newest
        try:
            newest = decode_leader_message(payload)
        except ValueError as exc:
            print(f"[WARN] Invalid leader message: {exc}", flush=True)


def main():
    args = parse_args()
    stage_path = Path(args.stage).expanduser().resolve()
    if not stage_path.is_file():
        raise FileNotFoundError(stage_path)

    os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"
    os.environ["ROS_DOMAIN_ID"] = "72"
    original_argv = sys.argv
    sys.argv = [sys.argv[0]]
    from isaacsim import SimulationApp

    # 2026-10-01: 기본 2560x1440 은 영상 녹화용 값이라 8 GB GPU 에서 데이터 수집까지 겹치면
    # GPU 95% 로 포화돼 조작이 끊긴다(실측). --low-render 로 렌더 해상도와 품질을 낮춘다.
    render_w, render_h = (args.render_width, args.render_height)
    if args.low_render:
        render_w, render_h = 1280, 720
    app = SimulationApp(
        {
            "headless": args.headless,
            "open_usd": str(stage_path),
            "create_new_stage": False,
            # width/height = viewport RENDER resolution (/app/renderer/resolution),
            # window_* = OS window size. 2560x1440 (2026-09-11) so a screen
            # recording of the viewport is true 1440p instead of upscaled 720p;
            # the laptop panel is 2560x1600. Headless runs ignore the window size.
            "width": render_w,
            "height": render_h,
            "window_width": render_w,
            "window_height": render_h,
            "renderer": "RaytracedLighting",
        }
    )
    sys.argv = original_argv

    import carb
    import omni.appwindow
    import omni.timeline
    import omni.usd
    from pxr import Gf, PhysxSchema, Usd, UsdGeom, UsdPhysics

    if args.low_render:
        # 2026-10-01: 8 GB GPU 에서 데이터 수집 중 GPU 95% 포화로 조작이 끊겼다.
        # 화질이 필요 없는 수집·텔레옵에서 반사/AO/투과/서브샘플을 끄고 해상도를 낮춘다.
        _s = carb.settings.get_settings()
        for key, value in (
            ("/rtx/reflections/enabled", False),
            ("/rtx/ambientOcclusion/enabled", False),
            ("/rtx/translucency/enabled", False),
            ("/rtx/directLighting/sampledLighting/enabled", False),
            ("/rtx/post/dlss/execMode", 0),          # 0 = 성능 우선
            ("/rtx/pathtracing/totalSpp", 1),
            ("/app/renderer/resolution/width", render_w),
            ("/app/renderer/resolution/height", render_h),
        ):
            try:
                _s.set(key, value)
            except Exception:  # noqa: BLE001 — 설정 키가 없는 빌드면 그냥 넘어간다
                pass
        print(f"[RENDER] 저부하 모드: {render_w}x{render_h}, 반사·AO·투과 끔", flush=True)

    if args.record or args.ai_mode:
        import omni.replicator.core as rep
        import imageio.v3 as iio

    context = omni.usd.get_context()
    deadline = time.monotonic() + 120.0
    stage = None
    while app.is_running() and time.monotonic() < deadline:
        app.update()
        stage = context.get_stage()
        if stage is not None and all(
            stage.GetPrimAtPath(path).IsValid() for path in ROBOTS.values()
        ):
            break
    if stage is None:
        raise RuntimeError("Stage did not load")

    arena_size = stage.GetPrimAtPath("/World/Arena").GetAttribute(
        "arena:interiorSizeMeters"
    ).Get()
    ball_material = UsdPhysics.MaterialAPI(
        stage.GetPrimAtPath("/World/Arena/Materials/BallPhysics")
    )
    ball_body = PhysxSchema.PhysxRigidBodyAPI(
        stage.GetPrimAtPath("/World/Arena/Balls/Ball_01")
    )
    ball_geom = UsdGeom.Sphere(
        stage.GetPrimAtPath("/World/Arena/Balls/Ball_01/Visual")
    )
    print(f"Stage: {stage_path}", flush=True)
    if args.record:
        print("[KEYS] Enter=녹화 시작/정지, →=에피소드 넘기기"
              + (" + 다음 색 공 배치" if args.grasp_demo else " + 공 재배치")
              + ", N=공 재배치, B=공 원위치, Q=전체 정지", flush=True)
    print(
        "Arena/Ball: "
        f"{float(arena_size[0]):.1f}x{float(arena_size[1]):.1f} m, "
        f"diameter={2.0 * float(ball_geom.GetRadiusAttr().Get()):.3f} m, "
        f"friction={ball_material.GetStaticFrictionAttr().Get()}/"
        f"{ball_material.GetDynamicFrictionAttr().Get()}, "
        f"restitution={ball_material.GetRestitutionAttr().Get()}, "
        f"damping={ball_body.GetLinearDampingAttr().Get()}/"
        f"{ball_body.GetAngularDampingAttr().Get()}",
        flush=True,
    )

    # Minimal ball reset for repeated grasp trials: no such feature existed
    # before this change, and re-launching the whole process after every
    # dropped/knocked-away ball is not viable for a manual pick-up test
    # session. Captured before timeline.play() below, so these are the
    # authored spawn positions, not wherever physics has since settled them.
    ball_controls = {}
    for ball_prim in stage.GetPrimAtPath("/World/Arena/Balls").GetChildren():
        # 2026-09-10: balls are now an Xform (translate + rigid body) with a
        # separate round Visual sphere and a faceted Collider mesh, so the
        # ball prim itself is no longer a UsdGeom.Sphere -- identify it by
        # its arena:ballColor marker attribute instead.
        if not ball_prim.HasAttribute("arena:ballColor"):
            continue
        translate_attr = ball_prim.GetAttribute("xformOp:translate")
        rigid = UsdPhysics.RigidBodyAPI(ball_prim)
        ball_controls[str(ball_prim.GetPath())] = {
            "translate_attr": translate_attr,
            "initial_translate": translate_attr.Get(),
            "velocity": rigid.CreateVelocityAttr(),
            "angular": rigid.CreateAngularVelocityAttr(),
            "rigid_api": rigid,
            "kinematic_attr": rigid.CreateKinematicEnabledAttr(),
            "color": str(ball_prim.GetAttribute("arena:ballColor").Get() or "").lower(),
            # Every collider under the ball (the invisible cube mesh). While
            # --scripted-attach has the ball glued to a gripper it is
            # kinematic, i.e. infinitely massive to PhysX -- if that collider
            # then overlaps a jaw or the floor, the *robot* is what gets shoved,
            # hard enough to tip the base. Collision is switched off for the
            # duration of a hold and restored on release.
            "collision_attrs": [
                UsdPhysics.CollisionAPI(p).CreateCollisionEnabledAttr()
                for p in Usd.PrimRange(ball_prim) if p.HasAPI(UsdPhysics.CollisionAPI)
            ],
        }

    def reset_balls(scatter=False):
        """공을 처음 자리로 되돌린다. scatter=True 면 같은 자리 근처로 **무작위**로 흩어 놓는다.

        2026-10-01: 심에서 시연 데이터를 모을 때 10 에피소드를 똑같은 배치로 찍으면 정렬 오차에
        약한 정책이 된다 → 에피소드마다 공을 조금씩 옮긴다(좌우 ±BALL_SCATTER_Y, 앞뒤 ±BALL_SCATTER_X).
        """
        for path, control in ball_controls.items():
            # If --scripted-attach currently has this ball glued to a
            # robot's gripper, release it first -- otherwise
            # update_scripted_attach() would just snap it straight back to
            # the gripper on the very next tick, making B look like a no-op.
            owner = ball_attached_to.get(path)
            if owner is not None:
                release_ball(owner)
            home = control["initial_translate"]
            if scatter:
                jx = random.uniform(-BALL_SCATTER_X, BALL_SCATTER_X)
                jy = random.uniform(-BALL_SCATTER_Y, BALL_SCATTER_Y)
                # 코트 안(벽에서 0.12 m)과 네트(|x| >= 0.18 m) 밖으로 벗어나지 않게 자른다
                nx = max(-1.38, min(1.38, float(home[0]) + jx))
                if abs(nx) < 0.18:
                    nx = math.copysign(0.18, home[0] if home[0] != 0 else 1.0)
                ny = max(-0.88, min(0.88, float(home[1]) + jy))
                target = Gf.Vec3d(nx, ny, float(home[2]))
            else:
                target = home
            control["translate_attr"].Set(target)
            control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        print(f"BALLS RESET: {len(ball_controls)} ball(s) "
              f"{'scattered near' if scatter else 'returned to'} spawn positions", flush=True)

    demo_state = {"i": 0}

    def place_demo_ball(label=None, advance=True):
        """--grasp-demo: 수동 로봇 정면 --demo-dist 지점에 다음 색 공을 갖다 놓는다.

        정렬을 생략하고 '정렬이 끝난 상태' 를 그대로 만든다(사용자 지시 2026-10-01).
        나머지 공은 코트 밖 대기 위치로 치워 화면과 라이다를 깨끗하게 둔다.

        advance=False 는 '다시 찍기'(왼쪽 화살표)용 — 색 순서를 넘기지 않고 같은 색을 다시 놓는다.
        """
        order = [c.strip().lower() for c in args.demo_colors.split(",") if c.strip()]
        if not order:
            return None
        if advance:
            color = order[demo_state["i"] % len(order)]
            demo_state["i"] += 1
        else:
            color = order[(demo_state["i"] - 1) % len(order)] if demo_state["i"] else order[0]
        # 쥐고 있는 공은 먼저 놓는다 — 안 그러면 아래 탐색에서 걸러져 재배치가 조용히 실패한다
        # (reset_balls 와 같은 이유).
        for owner in list(ball_attached_to.values()):
            if owner is not None:
                release_ball(owner)
        target_label = label or MANUAL_ROBOT
        control = robot_controls.get(target_label)
        if control is None:
            return None
        xf = UsdGeom.Xformable(control["base_prim"]).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        o = xf.ExtractTranslation()
        f = xf.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
        yaw = math.atan2(f[1], f[0])
        px = float(o[0]) + math.cos(yaw) * args.demo_dist
        py = float(o[1]) + math.sin(yaw) * args.demo_dist
        chosen = None
        for path, bc in ball_controls.items():
            if bc.get("color") == color and path not in ball_attached_to:
                chosen = (path, bc)
                break
        if chosen is None:
            print(f"[DEMO] {color} 공을 못 찾았다", flush=True)
            return None
        path, bc = chosen
        bc["translate_attr"].Set(Gf.Vec3d(px, py, BALL_DEMO_Z))
        bc["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        bc["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        # 다른 공은 멀리 치운다(겹쳐 보이면 학습 영상이 지저분하다)
        park = 0
        for other, obc in ball_controls.items():
            if other == path or other in ball_attached_to:
                continue
            obc["translate_attr"].Set(Gf.Vec3d(BALL_PARK_X, BALL_PARK_Y0 + park * 0.10, BALL_DEMO_Z))
            obc["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            obc["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            park += 1
        print(f"[DEMO] {target_label} 앞 {args.demo_dist:.2f} m 에 {color} 공 배치 "
              f"({px:+.2f},{py:+.2f})  — 에피소드 {demo_state['i']}", flush=True)
        return path

    robot_controls = {}
    for label, robot_path in ROBOTS.items():
        base_prim = stage.GetPrimAtPath(f"{robot_path}/base_footprint")
        if not base_prim.IsValid() or not base_prim.HasAPI(UsdPhysics.RigidBodyAPI):
            raise RuntimeError(f"Invalid base rigid body: {robot_path}/base_footprint")
        rigid = UsdPhysics.RigidBodyAPI(base_prim)

        for joint_name in WHEEL_JOINTS:
            configure_drive(
                find_joint(stage, robot_path, joint_name),
                UsdPhysics,
                0.0,
                0.0,
                0.0,
            )

        arm_prims = {
            key: find_joint(stage, robot_path, name)
            for key, name in ARM_JOINTS.items()
        }
        arm_drives = {}
        operating_values = {}
        for key, prim in arm_prims.items():
            if key == "gripper.pos":
                # A compliant grip avoids pinching the rigid foam-ball
                # approximation hard enough to eject it sideways. Unchanged
                # from before -- normal grasp force is not part of this
                # change.
                values = (8.0, 2.0, 0.45)
            elif key in {"shoulder_pan.pos", "shoulder_lift.pos"}:
                values = (25.0, 3.2, 32.0)
            else:
                values = (25.0, 1.8, 20.0)
            operating_values[key] = values
            # Start relaxed (see ARM_RELAXED_DRIVE); activate_arm_drives()
            # restores `values` once this robot actually starts receiving
            # leader commands.
            drive = configure_drive(prim, UsdPhysics, *ARM_RELAXED_DRIVE)
            drive.CreateTargetPositionAttr().Set(ARM_RELAXED_TARGET_DEG[key])
            arm_drives[key] = drive

        gripper_frame_link = stage.GetPrimAtPath(f"{robot_path}/gripper_frame_link")
        robot_controls[label] = {
            "robot_path": robot_path,
            "base_prim": base_prim,
            "gripper_frame_link": gripper_frame_link if gripper_frame_link.IsValid() else None,
            "velocity": rigid.CreateVelocityAttr(),
            "angular": rigid.CreateAngularVelocityAttr(),
            "arm_drives": arm_drives,
            "arm_joint_prims": arm_prims,
            "arm_operating_values": operating_values,
            "gripper_limits": joint_limits(arm_prims["gripper.pos"], UsdPhysics),
            "last_targets": {},
            "blend_until": 0.0,
            "blend_from": {},
        }

    def base_world_xy(label):
        t = UsdGeom.Xformable(
            robot_controls[label]["base_prim"]
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        return float(t[0]), float(t[1])

    def gripper_world_pos(label):
        link = robot_controls[label]["gripper_frame_link"]
        if link is None:
            return None
        return UsdGeom.Xformable(link).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        ).ExtractTranslation()

    # Territory is derived from each robot's actual spawn position, not from
    # its prim path containing "TeamRed"/"TeamBlue": whichever side of the
    # centre line (X=0) a robot starts on is the side it must stay on. This
    # also gives a robot-agnostic "facing" direction for the recording
    # cameras: every LeKiwi spawn in this project's arenas has its arm
    # reaching toward the centre (away from its own back wall), confirmed by
    # reading both the plain and net-A stages, so "facing" is just the sign
    # opposite the robot's own spawn X.
    for label in ROBOTS:
        sx, _sy = base_world_xy(label)
        sign = 1.0 if sx > 0 else -1.0
        robot_controls[label]["team_sign"] = sign
        robot_controls[label]["facing_sign"] = -sign

    # ------------------------------------------------------------------ #
    # Per-robot top-down tracking cameras (2026-09-10). One real USD camera
    # per robot, always present (not just for --record), so the interactive
    # viewport can switch to whichever robot is selected. This is cheap on
    # an 8GB GPU: switching the viewport's camera_path does not add a render
    # product or a second render -- the viewport still renders exactly one
    # camera at a time, same as before. All four are still kept updated
    # every frame (plain transform math, no rendering) so whichever one the
    # viewport is pointed at is never a stale frame behind.
    #
    # facing_sign (above) only encodes each robot's *spawn* side and does
    # not change; the base can rotate freely during teleop (Z/X keys), so
    # the forward direction used here is read from the base's actual
    # current transform every call, not from facing_sign.
    # ------------------------------------------------------------------ #
    # A first pass at 0.62m/24mm was rendered and inspected: the arm's idle
    # pose stretches out almost horizontally and filled the whole frame,
    # cropping out the base and most of the workspace ball beside it (see
    # ARENA_BUILD_GUIDE.md). Raised height and widened focal length below
    # to comfortably fit the robot body + outstretched arm + a workspace
    # ball beside it; tilt ratio (back offset : look-ahead) kept about the
    # same so it stays a similarly "high, mostly-overhead" angle.
    TOPDOWN_HEIGHT = 0.85        # camera height above the floor
    TOPDOWN_BACK_OFFSET = 0.08   # pulled back slightly behind the base centre
    TOPDOWN_LOOK_AHEAD = 0.45    # look-at point this far in front of the base
    TOPDOWN_LOOK_HEIGHT = 0.03   # look-at point height (near the gripper's work height)

    def _topdown_look_at(eye, target, up_hint=Gf.Vec3d(0, 0, 1)):
        forward = (target - eye).GetNormalized()
        right = Gf.Cross(forward, up_hint).GetNormalized()
        true_up = Gf.Cross(right, forward)
        m = Gf.Matrix4d(1.0)
        m.SetRow(0, Gf.Vec4d(right[0], right[1], right[2], 0.0))
        m.SetRow(1, Gf.Vec4d(true_up[0], true_up[1], true_up[2], 0.0))
        m.SetRow(2, Gf.Vec4d(-forward[0], -forward[1], -forward[2], 0.0))
        m.SetRow(3, Gf.Vec4d(eye[0], eye[1], eye[2], 1.0))
        return m

    topdown_cameras = {}
    for label, robot_path in ROBOTS.items():
        cam_path = f"/World/Arena/TopdownCam_{label.replace(' ', '')}"
        cam = UsdGeom.Camera.Define(stage, cam_path)
        cam.CreateFocalLengthAttr(16.0)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.05, 100.0))
        topdown_cameras[label] = {
            "path": cam_path,
            "op": UsdGeom.Xformable(cam).AddTransformOp(),
        }

    def update_topdown_camera(label, op=None, back=TOPDOWN_BACK_OFFSET,
                              ahead=TOPDOWN_LOOK_AHEAD, height=TOPDOWN_HEIGHT):
        """Track the base's current position and yaw only -- never the arm,
        never base roll/pitch. Default is near-vertical (small back/ahead
        offsets relative to the 0.62m height); if a raised arm turns out to
        block the gripper/ball view for a given pose, narrow the gap between
        TOPDOWN_BACK_OFFSET and TOPDOWN_LOOK_AHEAD to tilt it further from
        vertical rather than raising the height (which would shrink the
        robot in frame). `op`/offsets let the --record 'robot_top' camera
        reuse this tracking with its own framing without touching the
        interactive viewport camera."""
        base_prim = robot_controls[label]["base_prim"]
        transform = UsdGeom.Xformable(base_prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        center = transform.ExtractTranslation()
        # Local +X is this asset's forward axis (create_net_arena.py: "local
        # +X faces the net"); project to the XY plane so a tilted base
        # (there shouldn't be one on a flat floor, but be defensive) doesn't
        # roll the camera.
        forward = transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
        forward = Gf.Vec3d(forward[0], forward[1], 0.0)
        length = forward.GetLength()
        forward = forward / length if length > 1e-6 else Gf.Vec3d(1.0, 0.0, 0.0)
        eye = Gf.Vec3d(center[0] - forward[0] * back,
                        center[1] - forward[1] * back,
                        height)
        target = Gf.Vec3d(center[0] + forward[0] * ahead,
                           center[1] + forward[1] * ahead,
                           TOPDOWN_LOOK_HEIGHT)
        (op if op is not None else topdown_cameras[label]["op"]).Set(_topdown_look_at(eye, target))

    # ------------------------------------------------------------------ #
    # --ai-mode diagnostic snapshots: one PNG per robot the first time it
    # enters a given AI state (see ai_set_state's call site below), reusing
    # that robot's own always-present topdown camera (no new camera prim).
    # This exists to answer "does an autonomous attempt actually look like
    # it's reaching for the ball" without needing a GUI session -- not a
    # recording feature, just a few still frames per run.
    # ------------------------------------------------------------------ #
    ai_snapshot_dir = PROJECT_ROOT / "screenshots" / "ai_grasp_snapshots"

    ai_snapshot_pending = []

    def ai_capture_snapshot(label, tag):
        """Queue one still from this robot's topdown camera. The render
        product is created here and read back by ai_flush_snapshots() on a
        later tick (right after app.update()), then destroyed. Keeping one
        product per robot alive for the whole run cost up to three extra
        960x540 renders per tick and dragged the headless loop to a few Hz;
        reading back on the same tick as creation returns nothing."""
        if not args.ai_mode:
            return
        product = rep.create.render_product(topdown_cameras[label]["path"], (960, 540))
        annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        annotator.attach([product])
        ai_snapshot_pending.append([label, tag, product, annotator, 0])

    def ai_flush_snapshots():
        if not ai_snapshot_pending:
            return
        ai_snapshot_dir.mkdir(parents=True, exist_ok=True)
        remaining = []
        for entry in ai_snapshot_pending:
            label, tag, product, annotator, age = entry
            data = annotator.get_data()
            ok = data is not None and getattr(data, "size", 0) > 0
            if not ok and age < 3:
                entry[4] = age + 1
                remaining.append(entry)
                continue
            if ok:
                safe_label = label.replace(" ", "")
                out_path = ai_snapshot_dir / f"{safe_label}_{tag}_{time.strftime('%H%M%S')}.png"
                iio.imwrite(out_path, data[..., :3].copy())
                print(f"[AI][SNAPSHOT] {label} {tag} -> {out_path}", flush=True)
            annotator.detach([product])
            product.destroy()
        ai_snapshot_pending[:] = remaining

    def basket_keepout_boxes():
        boxes = []
        for goal in ("TeamRed_Goal", "TeamBlue_Goal"):
            prim = stage.GetPrimAtPath(f"/World/Arena/Baskets/{goal}")
            if not prim.IsValid():
                continue
            attr = prim.GetAttribute("arena:basketCenter")
            center = attr.Get() if attr.IsValid() else None
            if center is None:
                continue
            half = 0.34 / 2.0 + BASKET_KEEPOUT_MARGIN
            cx, cy = float(center[0]), float(center[1])
            boxes.append((cx - half, cx + half, cy - half, cy + half))
        return boxes

    basket_keepouts = basket_keepout_boxes()
    if not basket_keepouts:
        print("[WARN] No basket prims found on this stage; background robots "
              "only avoid each other, the net/centre line and the outer walls.",
              flush=True)

    def blocked(label, next_x, next_y):
        for (x0, x1, y0, y1) in basket_keepouts:
            if x0 <= next_x <= x1 and y0 <= next_y <= y1:
                return True
        for other in ROBOTS:
            if other == label:
                continue
            ox, oy = base_world_xy(other)
            if math.hypot(next_x - ox, next_y - oy) < ROBOT_CLEARANCE:
                return True
        return False

    zmq_context = zmq.Context()
    subscriber = zmq_context.socket(zmq.SUB)
    subscriber.setsockopt(zmq.SUBSCRIBE, b"")
    subscriber.setsockopt(zmq.CONFLATE, 1)
    subscriber.setsockopt(zmq.LINGER, 0)
    subscriber.connect(args.endpoint)

    labels = list(ROBOTS)
    active_index = labels.index(MANUAL_ROBOT) if args.record else 0
    pressed_keys = set()
    stop_requested = False
    movement_paused = False
    current_speed = args.linear_speed
    current_rotation = args.rotation_speed
    active_drives_ready = set()
    # "topdown" (default): viewport follows the selected robot's top-down
    # camera. "overview" : viewport shows the fixed whole-arena
    # SpectatorCamera instead, toggled with V. Always None in --headless
    # (no viewport exists to switch); switch_viewport_camera() below guards
    # on that.
    camera_view_mode = "topdown"
    viewport_api = None

    def activate_arm_drives(label):
        """Restore full stiffness/damping/max_force once `label` actually
        starts receiving leader commands. Before this the arm sits relaxed
        (ARM_RELAXED_DRIVE) and gravity settles it into a natural pose."""
        if label in active_drives_ready:
            return
        control = robot_controls[label]
        for key, drive in control["arm_drives"].items():
            drive.CreateStiffnessAttr(control["arm_operating_values"][key][0])
            drive.CreateDampingAttr(control["arm_operating_values"][key][1])
            drive.CreateMaxForceAttr(control["arm_operating_values"][key][2])
        active_drives_ready.add(label)

    def start_connect_blend(label):
        """Record where this robot's arm actually is right now so apply_arm()
        can ease from there to the leader's pose instead of snapping to it.
        Called on first connect, on reconnect after a stale gap, and when
        switching the active robot while the leader is already streaming."""
        control = robot_controls[label]
        now = time.monotonic()
        control["blend_until"] = now + CONNECT_BLEND_SECONDS
        blend_from = {}
        for key, joint_prim in control["arm_joint_prims"].items():
            attr = joint_prim.GetAttribute("state:angular:physics:position")
            actual = attr.Get() if attr.IsValid() else None
            if actual is None:
                actual = control["last_targets"].get(key, ARM_RELAXED_TARGET_DEG[key])
            blend_from[key] = float(actual)
        control["blend_from"] = blend_from
        control["last_targets"] = {}

    app_window = None if args.headless else omni.appwindow.get_default_app_window()
    input_interface = None
    keyboard = None
    keyboard_subscription = None

    motion_keys = {
        carb.input.KeyboardInput.W,
        carb.input.KeyboardInput.A,
        carb.input.KeyboardInput.S,
        carb.input.KeyboardInput.D,
        carb.input.KeyboardInput.Z,
        carb.input.KeyboardInput.X,
    }
    def zero_all_bases():
        for control in robot_controls.values():
            control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))

    def select_robot(index):
        nonlocal active_index
        active_index = index
        pressed_keys.clear()
        zero_all_bases()
        if leader_announced:
            # Leader is already streaming (we switched robots mid-session);
            # firm up this robot's arm and blend into the leader's pose
            # immediately instead of waiting for a "first message" event
            # that already happened for a different robot and won't fire
            # again.
            activate_arm_drives(labels[active_index])
            start_connect_blend(labels[active_index])
        switch_viewport_camera(labels[active_index])
        if args.ai_mode:
            # Atomic hand-off: the instant a robot becomes the manual one,
            # its AI grasp attempt (if any) is abandoned -- claim released,
            # state reset -- so no AI base/arm command can land on it after
            # this point. update_ai_robots() re-arms AI control for whatever
            # robot this index just displaced, the next time it runs.
            ai_on_manual_select(labels[active_index])
        print(f"ACTIVE ROBOT: {labels[active_index]}", flush=True)

    # fn(name, detail) sinks for operator/teleop events (markers, ball reset,
    # all-stop, attach/release). The --record subsystem registers one that
    # writes events.csv; without recording the list stays empty.
    event_sinks = []

    def emit_event(name, detail=""):
        for sink in event_sinks:
            sink(name, detail)

    def on_keyboard(event, *_):
        nonlocal stop_requested, current_speed, current_rotation, movement_paused, camera_view_mode
        key = event.input
        if event.type == carb.input.KeyboardEventType.KEY_PRESS:
            if key == carb.input.KeyboardInput.T:
                if args.record:
                    print("Recording mode: Blue 1 is the only manual robot; T/F is disabled.",
                          flush=True)
                else:
                    select_robot((active_index + 1) % len(labels))
            elif key == carb.input.KeyboardInput.F:
                if args.record:
                    print("Recording mode: Blue 1 is the only manual robot; T/F is disabled.",
                          flush=True)
                else:
                    select_robot((active_index - 1) % len(labels))
            elif key in motion_keys:
                if not movement_paused:
                    pressed_keys.add(key)
            elif key == carb.input.KeyboardInput.Q:
                pressed_keys.clear()
                movement_paused = True
                zero_all_bases()
                emit_event("all_stop")
                print("ALL BASES STOPPED (including background wander). "
                      "Press R to resume.", flush=True)
            elif key == carb.input.KeyboardInput.R:
                if movement_paused:
                    movement_paused = False
                    emit_event("resume")
                    print("Background wander resumed.", flush=True)
            elif key == carb.input.KeyboardInput.ENTER:
                # 2026-10-01: 녹화는 원래 SIGUSR1/명령파일로만 시작했다 → 키보드에서 바로 쓰도록 추가.
                # Enter = 녹화 시작(첫 에피소드), 다시 누르면 정지.
                if recording is not None:
                    recording["pending_commands"].append(
                        "stop" if recording["active"] else "start")
                    print(f"[REC] {'정지' if recording['active'] else '시작'} 요청", flush=True)
            elif key == carb.input.KeyboardInput.RIGHT:
                # 2026-10-01 사용자 지시: 에피소드는 시간 제한 없이(999 s) 두고 → 키로 넘긴다.
                # 실물 lekiwi-record 의 오른쪽 화살표와 같은 조작.
                if recording is not None:
                    recording["pending_commands"].append("next_episode")
                    print("[REC] 다음 에피소드로", flush=True)
            elif key == carb.input.KeyboardInput.LEFT:
                # 2026-10-01 사용자 지시: 왼쪽 화살표 = 지금 에피소드를 버리고 **같은 색으로 다시 찍기**.
                if recording is not None:
                    recording["pending_commands"].append("redo_episode")
                    print("[REC] 이 에피소드 버리고 다시 찍기", flush=True)
            elif key == carb.input.KeyboardInput.N:
                # 2026-10-01: 시연 수집용 — 공을 처음 자리 근처로 무작위로 흩어 놓는다
                reset_balls(scatter=True)
                emit_event("balls_scatter")
                if args.auto_base and auto_nav is not None:
                    for lb in auto_nav["labels"]:
                        auto_nav["claims"].pop(auto_nav["state"][lb].get("ball"), None)
                        auto_nav["state"][lb]["ball"] = None
                        auto_nav["state"][lb]["state"] = "SEARCH"
                    print("[AUTO] 공 재배치 → 전원 재정렬", flush=True)
            elif key == carb.input.KeyboardInput.B:
                reset_balls()
                emit_event("ball_reset")
            elif key == carb.input.KeyboardInput.G:
                manual_attach_toggle(labels[active_index])
            elif key == carb.input.KeyboardInput.K and args.data_collect:
                mark_last_episode_outcome("success")
            elif key == carb.input.KeyboardInput.L and args.data_collect:
                mark_last_episode_outcome("failure")
            elif key == carb.input.KeyboardInput.J and args.data_collect:
                mark_last_episode_outcome("aborted")
            elif key == carb.input.KeyboardInput.V:
                camera_view_mode = "overview" if camera_view_mode == "topdown" else "topdown"
                switch_viewport_camera(labels[active_index])
                print(f"VIEW: {camera_view_mode}", flush=True)
            elif key == carb.input.KeyboardInput.RIGHT_BRACKET:
                current_speed = min(1.0, current_speed * 1.25)
                current_rotation = min(300.0, current_rotation * 1.25)
                print(f"SPEED: {current_speed:.3f} m/s, {current_rotation:.1f} deg/s")
            elif key == carb.input.KeyboardInput.LEFT_BRACKET:
                current_speed = max(0.05, current_speed / 1.25)
                current_rotation = max(5.0, current_rotation / 1.25)
                print(f"SPEED: {current_speed:.3f} m/s, {current_rotation:.1f} deg/s")
            elif key == carb.input.KeyboardInput.ESCAPE:
                stop_requested = True
        elif event.type == carb.input.KeyboardEventType.KEY_RELEASE:
            pressed_keys.discard(key)
        return True

    if not args.headless:
        if app_window is None:
            raise RuntimeError("Could not get Isaac Sim app window")
        keyboard = app_window.get_keyboard()
        input_interface = carb.input.acquire_input_interface()
        keyboard_subscription = input_interface.subscribe_to_keyboard_events(
            keyboard, on_keyboard
        )
        # 2026-09-10: superseded this project's older "T/F never changes the
        # camera" decision (NEXT_CHAT_HANDOFF.md section 10) on explicit
        # user request -- the viewport now follows the selected robot's
        # top-down camera by default, switching whenever T/F changes the
        # active robot. V toggles back to this fixed whole-arena
        # SpectatorCamera view. This is completely separate from --record's
        # own capture cameras below: this only affects what the interactive
        # viewport shows.
        from omni.kit.viewport.utility import get_active_viewport

        viewport_api = get_active_viewport()

    def switch_viewport_camera(label):
        if viewport_api is None:
            return
        viewport_api.camera_path = (
            OVERALL_VIEW_CAMERA if camera_view_mode == "overview" else topdown_cameras[label]["path"]
        )

    if not args.headless:
        switch_viewport_camera(labels[active_index])

    def apply_base_commands():
        zero_all_bases()
        if movement_paused:
            return
        x = current_speed * (
            int(carb.input.KeyboardInput.W in pressed_keys)
            - int(carb.input.KeyboardInput.S in pressed_keys)
        )
        y = current_speed * (
            int(carb.input.KeyboardInput.A in pressed_keys)
            - int(carb.input.KeyboardInput.D in pressed_keys)
        )
        yaw = current_rotation * (
            int(carb.input.KeyboardInput.Z in pressed_keys)
            - int(carb.input.KeyboardInput.X in pressed_keys)
        )
        control = robot_controls[labels[active_index]]
        transform = UsdGeom.Xformable(
            control["base_prim"]
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        world = transform.TransformDir(Gf.Vec3d(x, y, 0.0))
        control["velocity"].Set(Gf.Vec3f(world[0], world[1], 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, yaw))

    def team_half(label):
        sign = robot_controls[label]["team_sign"]
        x_half = float(arena_size[0]) / 2.0 - BACKGROUND_WALL_MARGIN
        y_half = float(arena_size[1]) / 2.0 - BACKGROUND_WALL_MARGIN
        if sign > 0:
            return BACKGROUND_TEAM_MARGIN, x_half, -y_half, y_half
        return -x_half, -BACKGROUND_TEAM_MARGIN, -y_half, y_half

    background_state = {
        label: {"until": 0.0, "vx": 0.0, "vy": 0.0, "wz": 0.0} for label in ROBOTS
    }

    def update_background_robots(now):
        """Random base-only wander for every robot except the manually
        driven one: rotate in place or creep forward/back, never crossing
        into the other team's half, through the outer walls, into a basket
        footprint, or within ROBOT_CLEARANCE of another robot's current
        position. Called after apply_base_commands() so its
        zero_all_bases() doesn't wipe this."""
        if movement_paused:
            return
        for label in ROBOTS:
            if label == labels[active_index]:
                continue
            control = robot_controls[label]
            state = background_state[label]
            x, y = base_world_xy(label)
            x_lo, x_hi, y_lo, y_hi = team_half(label)
            if not (x_lo <= x <= x_hi and y_lo <= y <= y_hi):
                # Strayed out of its safe half (e.g. nudged by a collision):
                # steer back toward the centre of it, ignoring the timer.
                cx, cy = (x_lo + x_hi) / 2.0, 0.0
                dx, dy = cx - x, cy - y
                dist = math.hypot(dx, dy) or 1.0
                speed = 0.10
                control["velocity"].Set(Gf.Vec3f(dx / dist * speed, dy / dist * speed, 0.0))
                control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                state["until"] = 0.0
                continue
            if now >= state["until"]:
                action = random.choice(("forward", "back", "rotate_left", "rotate_right", "pause"))
                state["until"] = now + random.uniform(*BACKGROUND_ACTION_SECONDS)
                speed = random.uniform(*BACKGROUND_LINEAR_SPEED)
                turn = random.uniform(*BACKGROUND_ROTATE_DEG)
                if action == "forward":
                    state["vx"], state["vy"], state["wz"] = speed, 0.0, 0.0
                elif action == "back":
                    state["vx"], state["vy"], state["wz"] = -speed, 0.0, 0.0
                elif action == "rotate_left":
                    state["vx"], state["vy"], state["wz"] = 0.0, 0.0, turn
                elif action == "rotate_right":
                    state["vx"], state["vy"], state["wz"] = 0.0, 0.0, -turn
                else:
                    state["vx"], state["vy"], state["wz"] = 0.0, 0.0, 0.0
            transform = UsdGeom.Xformable(
                control["base_prim"]
            ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            world = transform.TransformDir(Gf.Vec3d(state["vx"], state["vy"], 0.0))
            wx, wy = float(world[0]), float(world[1])
            next_x = x + wx * COLLISION_LOOKAHEAD_SECONDS
            next_y = y + wy * COLLISION_LOOKAHEAD_SECONDS
            if (wx != 0.0 or wy != 0.0) and blocked(label, next_x, next_y):
                # Don't drive into it; stop and try a different random
                # action soon instead of pushing against the obstacle.
                control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                state["until"] = now  # re-roll next tick
                continue
            control["velocity"].Set(Gf.Vec3f(wx, wy, 0.0))
            control["angular"].Set(Gf.Vec3f(0.0, 0.0, state["wz"]))

    # ------------------------------------------------------------------ #
    # --auto-base (2026-10-01): 베이스 전용 자율주행. 팔은 건드리지 않는다.
    #   SEARCH → GO_BALL → PICK(흉내) → GO_DELIVER → DROP → SEARCH
    # 경로는 격자 A*(sim_nav.plan), 추종은 홀로노믹 추종기(sim_nav.HoloFollower).
    # 정적 장애물(벽·네트·바구니)은 스테이지 콜라이더에서 한 번 굽고, 다른 로봇은
    # 재계획할 때마다 임시로 찍는다. 공은 장애물이 아니다(목표물이자 밟고 지나가도 됨).
    # ------------------------------------------------------------------ #
    auto_nav = None
    if args.auto_base:
        import sim_nav  # noqa: PLC0415  (Isaac/USD 환경에서만 필요)

        if args.auto_base_robots.strip().lower() == "all":
            auto_labels = list(ROBOTS)
        else:
            auto_labels = [s.strip() for s in args.auto_base_robots.split(",") if s.strip()]
            unknown = [s for s in auto_labels if s not in ROBOTS]
            if unknown:
                raise SystemExit(f"--auto-base-robots: 모르는 라벨 {unknown}; 가능한 값 {list(ROBOTS)}")
        base_grid = sim_nav.build_occupancy(stage, res=AUTO_GRID_RES, z_max=AUTO_GRID_Z_MAX)
        any_robot = next(iter(ROBOTS.values()))
        fp = sim_nav.compute_footprint(stage, any_robot)
        plan_radius = fp["inscribed_radius"] + AUTO_SAFETY_MARGIN
        occ_ratio = float((base_grid.data > 0).mean())
        print(f"[AUTO] 점유격자 {base_grid.shape[1]}x{base_grid.shape[0]} @ {AUTO_GRID_RES} m "
              f"(원점 {base_grid.x_min:+.2f},{base_grid.y_min:+.2f}, 점유 {occ_ratio*100:.1f}%) | "
              f"로봇 발자국 {fp['size'][0]:.3f}x{fp['size'][1]:.3f} m, 내접 r={fp['inscribed_radius']:.3f}, "
              f"계획 반경 {plan_radius:.3f} m | 대상 {auto_labels}", flush=True)
        import sim_lidar  # noqa: PLC0415

        # 공은 장애물이 아니라 목표물이다 — 실물에서도 scan_blob_filter 가 공 크기 덩어리를 지운다.
        # 안 지우면 공 앞 0.28 m 에서 안전 정지가 걸려 집으러 갈 수가 없다(2026-10-01 실측).
        auto_lidar = sim_lidar.RaycastLidar(n_rays=AUTO_LIDAR_RAYS, fov_deg=360.0,
                                            ignore_prefixes=("/World/Arena/Balls",))
        print(f"[AUTO] 라이다: 바닥 {sim_lidar.LIDAR_Z*100:.0f} cm, {AUTO_LIDAR_RAYS}빔/360°, "
              f"정지 gap {AUTO_LIDAR_STOP_GAP} m (실물 배치와 동일)", flush=True)
        auto_nav = {
            "lidar": auto_lidar,
            "grid": base_grid,
            "fp": fp,
            "radius": plan_radius,
            "labels": auto_labels,
            "state": {label: {"state": "SEARCH", "ball": None, "since": 0.0,
                              "follower": sim_nav.HoloFollower(
                                  max_vx=AUTO_BASE_SPEED, max_wz=math.radians(AUTO_BASE_ROT_DEG),
                                  goal_tol=AUTO_GOAL_TOL, slow_radius=0.15),
                              "replan_at": 0.0, "goal": None, "fails": 0, "blocked_at": 0.0}
                      for label in ROBOTS},
            "stats": {label: {"picked": 0, "delivered": 0, "noplan": 0} for label in ROBOTS},
            "claims": {},     # ball path -> label
            "debug_label": auto_labels[1] if len(auto_labels) > 1 else auto_labels[0],
        }

    def auto_goal_for_color(label, color):
        """공 색 → 목적지 앞 정지 지점(월드 x,y)과 바라볼 점.

        노랑 = 우리 바구니, 그 외 = 네트 너머로 넘기기(네트 앞). 실물 규칙과 같다.
        """
        sign = robot_controls[label]["team_sign"]        # +1 / -1 진영
        if color == "yellow":
            for goal in ("TeamRed_Goal", "TeamBlue_Goal"):
                prim = stage.GetPrimAtPath(f"/World/Arena/Baskets/{goal}")
                attr = prim.GetAttribute("arena:basketCenter") if prim.IsValid() else None
                center = attr.Get() if attr and attr.IsValid() else None
                if center is None:
                    continue
                cx, cy = float(center[0]), float(center[1])
                if (cx >= 0) == (sign > 0):              # 우리 진영 바구니
                    # 같은 팀 두 대가 같은 바구니로 가므로 플레이어 번호로 접근 차선을 벌린다
                    lane = AUTO_BASKET_LANE * (1 if label.strip().endswith("2") else -1)
                    stand = (cx + math.copysign(AUTO_BASKET_STANDOFF, sign), cy + lane)
                    return stand, (cx, cy)
        # 네트: x=0 전 구간. 현재 y 를 유지한 채 네트 앞 AUTO_NET_STANDOFF 지점
        x, y = base_world_xy(label)
        y = max(-AUTO_NET_Y_LIMIT, min(AUTO_NET_Y_LIMIT, y))
        return (math.copysign(AUTO_NET_STANDOFF, sign), y), (0.0, y)

    def auto_base_yaw(label):
        xf = UsdGeom.Xformable(robot_controls[label]["base_prim"]).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default())
        f = xf.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
        return math.atan2(f[1], f[0])

    def auto_standoff_ahead(label, ball_xy, dist=None):
        """현재 heading 을 유지한 채 공이 **정면** dist 에 오게 되는 베이스 위치."""
        d = AUTO_BALL_STANDOFF if dist is None else dist
        yaw = auto_base_yaw(label)
        return (ball_xy[0] - math.cos(yaw) * d, ball_xy[1] - math.sin(yaw) * d)

    def auto_plan_to(label, goal_xy, face_xy):
        """다른 로봇을 임시 장애물로 찍은 격자에서 경로를 만들어 추종기에 넣는다."""
        g = auto_nav["grid"].copy()
        for other in ROBOTS:
            if other == label:
                continue
            ox, oy = base_world_xy(other)
            g.stamp_disc(ox, oy, AUTO_ROBOT_OBSTACLE_R)
        x, y = base_world_xy(label)
        path = sim_nav.plan(g, (x, y), goal_xy, auto_nav["radius"], goal_snap=AUTO_GOAL_SNAP)
        st = auto_nav["state"][label]
        if path is None:
            st["fails"] += 1
            auto_nav["stats"][label]["noplan"] += 1
            return False
        st["fails"] = 0
        st["goal"] = goal_xy
        f = st["follower"]
        # 주행 중에는 heading 을 고정한다(옴니 베이스라 게걸음으로 간다). 회전과 직진을 동시에 주면
        # 베이스가 제자리에서 떨며 목표에 수렴하지 못했다(2026-10-01 헤드리스 실측).
        f.yaw_mode = "hold"
        f.face_xy = face_xy
        f.set_path(path)
        return True

    def auto_set_state(label, new, now):
        st = auto_nav["state"][label]
        if st["state"] != new:
            print(f"[AUTO] {label}: {st['state']} -> {new}", flush=True)
        st["state"] = new
        st["since"] = now
        st["face_since"] = None

    def auto_drive(label, now):
        """추종기 한 스텝 → 베이스 속도 적용. 도착했으면 True."""
        st = auto_nav["state"][label]
        f = st["follower"]
        x, y = base_world_xy(label)
        xf = UsdGeom.Xformable(robot_controls[label]["base_prim"]).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default())
        fwd = xf.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
        yaw = math.atan2(fwd[1], fwd[0])
        vx, vy, wz = f.step(x, y, yaw)
        # --- 안전 먼저: 라이다로 **진행 방향**이 막혔으면 속도를 줄이거나 멈춘다 ---
        # 2026-10-01 실측: 몸체 정면만 보면 게걸음(옴니)으로 옆으로 갈 때 엉뚱한 방향을 보고
        # 멈춰 목적지 0.3 m 앞에서 영영 못 간다. 실제 가는 쪽을 봐야 한다.
        speed_cmd = math.hypot(vx, vy)
        if speed_cmd > 1e-3:
            scan = st.get("scan")
            if scan is None or (now - st.get("scan_at", -1.0)) >= AUTO_LIDAR_PERIOD:
                scan = auto_nav["lidar"].scan(x, y, yaw)
                st["scan"], st["scan_at"] = scan, now
            travel = math.atan2(vy, vx)            # 몸체 기준 진행 방향
            half = math.radians(AUTO_LIDAR_FRONT_DEG)
            vals = [r for a, r in zip(scan.angles, scan.ranges)
                    if abs(math.atan2(math.sin(a - travel), math.cos(a - travel))) <= half
                    and math.isfinite(r)]
            if len(vals) >= AUTO_LIDAR_MIN_POINTS:
                gap = min(vals) - AUTO_BASE_EDGE_R
                if gap <= AUTO_LIDAR_STOP_GAP:
                    st["blocked_at"] = now
                    vx = vy = 0.0
                elif gap < AUTO_LIDAR_SLOW_GAP:
                    scale = max(0.25, gap / AUTO_LIDAR_SLOW_GAP)
                    vx, vy = vx * scale, vy * scale
        control = robot_controls[label]
        world = xf.TransformDir(Gf.Vec3d(vx, vy, 0.0))
        control["velocity"].Set(Gf.Vec3f(float(world[0]), float(world[1]), 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, float(math.degrees(wz))))
        if label == auto_nav.get("debug_label") and now - auto_nav.get("dbg_at", 0.0) >= 1.0:
            auto_nav["dbg_at"] = now
            tgt = f.path[f.idx] if not f.done else None
            print(f"[AUTO][DBG] {label} pos=({x:+.2f},{y:+.2f}) yaw={math.degrees(yaw):+.0f}° "
                  f"idx={f.idx}/{len(f.path)} wp={tgt} cmd vx={vx:+.3f} vy={vy:+.3f} wz={math.degrees(wz):+.0f}",
                  flush=True)
        if not f.done:
            return False
        # 위치는 도착. 바라보는 각도까지 맞아야 '도착' 으로 본다(집는 척·놓기 전 정렬)
        if f.face_xy is not None:
            want = math.atan2(f.face_xy[1] - y, f.face_xy[0] - x)
            err = math.degrees(math.atan2(math.sin(want - yaw), math.cos(want - yaw)))
            if st.get("face_since") is None:
                st["face_since"] = now
            if abs(err) > AUTO_FACE_TOL_DEG and (now - st["face_since"]) < AUTO_FACE_MAX_S:
                rate = max(-AUTO_BASE_ROT_DEG, min(AUTO_BASE_ROT_DEG, err * 2.0))
                control["angular"].Set(Gf.Vec3f(0.0, 0.0, float(rate)))
                return False
        st["face_since"] = None
        control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        return True

    def auto_pick_ball(label):
        """우리 진영에서 가장 가까운, 아직 아무도 안 찍은 공. 없으면 None."""
        x, y = base_world_xy(label)
        sign = robot_controls[label]["team_sign"]
        best, best_d = None, math.inf
        for path in ball_controls:
            if path in ball_attached_to or auto_nav["claims"].get(path) not in (None, label):
                continue
            bx, by, _bz = ball_world_xyz(path)
            if (bx >= 0) != (sign > 0):          # 네트 너머 공은 가져오지 않는다
                continue
            d = math.hypot(bx - x, by - y)
            if d < best_d:
                best, best_d = path, d
        return best

    def update_auto_base(raw_now):
        """--auto-base 본체. 수동 로봇과 Q(정지) 중에는 아무 명령도 내지 않는다.

        시계: timeline.get_current_time() 은 이 스테이지에서 약 1 초마다 **되감긴다**(실측
        2026-10-01: 0.2→0.9→0.2…). 그대로 쓰면 상태 타임아웃·대기 시간이 영영 성립하지 않으므로
        한 틱의 증가분만 받아 단조 증가하는 자체 시계를 만든다."""
        if movement_paused:
            return
        prev = auto_nav.get("raw_prev")
        dt = (raw_now - prev) if prev is not None else 0.0
        if dt <= 0.0 or dt > 0.5:          # 되감김·일시정지 → 명목 프레임 간격으로 대체
            dt = 1.0 / float(args.fps)
        auto_nav["raw_prev"] = raw_now
        auto_nav["clock"] = now = auto_nav.get("clock", 0.0) + dt
        for label in auto_nav["labels"]:
            if label == labels[active_index] and not args.align_demo:
                st = auto_nav["state"][label]
                if st["state"] != "MANUAL":
                    ball = st["ball"]
                    if ball is not None:
                        auto_nav["claims"].pop(ball, None)
                    st["ball"] = None
                    auto_set_state(label, "MANUAL", now)
                continue
            st = auto_nav["state"][label]
            if st["state"] == "MANUAL":
                auto_set_state(label, "SEARCH", now)

            wall_now = time.monotonic()
            if wall_now - auto_nav.get("status_at", 0.0) >= AUTO_STATUS_PERIOD:
                auto_nav["status_at"] = wall_now
                parts = []
                for lb in auto_nav["labels"]:
                    s_ = auto_nav["state"][lb]
                    px, py = base_world_xy(lb)
                    stt = auto_nav["stats"][lb]
                    parts.append(f"{lb}:{s_['state']}@({px:+.2f},{py:+.2f}) "
                                 f"pick={stt['picked']} drop={stt['delivered']} noplan={stt['noplan']}")
                print(f"[AUTO][STATUS] sim={now:.1f}s | " + " | ".join(parts), flush=True)

            if st["state"] == "SEARCH":
                ball = auto_pick_ball(label)
                if ball is None:
                    control = robot_controls[label]
                    control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                    control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                    continue
                st["ball"] = ball
                auto_nav["claims"][ball] = label
                bx, by, _bz = ball_world_xyz(ball)
                # 2026-10-01: 회전으로 공을 정면에 두려 하면 안 된다 — 베이스 각 감쇠가 커서
                # 90 deg/s 를 줘도 실제로는 10~20 deg/s 라 제시간에 못 돈다(실측). 옴니 베이스이므로
                # **현재 heading 을 유지한 채 옆걸음**으로 "공이 정면 AUTO_BALL_STANDOFF" 가 되는
                # 지점으로 간다. 도착하면 공은 정의상 정면에 있다 → 고정 파지 자세가 그대로 맞는다.
                stand = auto_standoff_ahead(label, (bx, by))
                if auto_plan_to(label, stand, None):
                    st["replan_at"] = now + AUTO_REPLAN_SECONDS
                    auto_set_state(label, "GO_BALL", now)
                else:
                    auto_nav["claims"].pop(ball, None)
                    st["ball"] = None
                continue

            if st["state"] == "GO_BALL":
                ball = st["ball"]
                if ball is None or ball in ball_attached_to:
                    auto_set_state(label, "SEARCH", now)
                    continue
                bx, by, _bz = ball_world_xyz(ball)
                if now >= st["replan_at"]:        # 공이 굴러갔거나 다른 로봇이 막았을 수 있다
                    auto_plan_to(label, auto_standoff_ahead(label, (bx, by)), None)
                    st["replan_at"] = now + AUTO_REPLAN_SECONDS
                arrived = auto_drive(label, now)
                if arrived or (now - st["since"]) > AUTO_STATE_TIMEOUT:
                    px, py = base_world_xy(label)
                    print(f"[AUTO] {label}: GO_BALL {'도착' if arrived else '시간초과'} "
                          f"{now - st['since']:.1f}s, 공까지 {math.hypot(bx-px, by-py):.3f} m", flush=True)
                    px, py = base_world_xy(label)
                    yaw = auto_base_yaw(label)
                    rel_x = (bx - px) * math.cos(yaw) + (by - py) * math.sin(yaw)
                    rel_y = -(bx - px) * math.sin(yaw) + (by - py) * math.cos(yaw)
                    print(f"[AUTO] {label}: 정렬 결과 — 공이 베이스 기준 앞 {rel_x:+.3f} m, "
                          f"옆 {rel_y:+.3f} m (목표: 앞 {AUTO_BALL_STANDOFF:.2f}, 옆 0.00)", flush=True)
                    auto_set_state(label, "HOLD" if args.align_demo else "PICK", now)
                continue

            if st["state"] == "HOLD":
                # 정렬 끝. 팔 조작은 사람이 한다 — 베이스만 멈춰 세운다.
                control = robot_controls[label]
                control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                continue

            if st["state"] == "PICK":
                # "집었다 치고": 팔을 쓰지 않고 공을 그리퍼 프레임에 붙인다(기존 scripted attach).
                ball = st["ball"]
                if ball is None or ball in ball_attached_to:
                    auto_set_state(label, "SEARCH", now)
                    continue
                if (now - st["since"]) < AUTO_PICK_PAUSE:
                    continue                      # 멈춰 선 채 '집는 동작' 시간을 둔다
                attach_ball(label, ball)
                # attach_ball 은 attach_mode 를 "auto" 로 둔다 → update_scripted_attach 가
                # "그리퍼가 안 닫혔다" 며 즉시 되돌려 놓는다. 베이스 모드는 팔을 쓰지 않으므로
                # 수동 부착과 같은 취급으로 바꿔 자동 해제를 면제한다 (2026-10-01 실측).
                attach_mode[label] = "manual"
                auto_nav["stats"][label]["picked"] += 1
                color = ball_controls[ball].get("color", "")
                goal_xy, face_xy = auto_goal_for_color(label, color)
                dest = "basket" if color == "yellow" else "net"
                print(f"[AUTO] {label}: 집은 척 완료 {ball} (색 {color or '?'}) → {dest} "
                      f"{goal_xy[0]:+.2f},{goal_xy[1]:+.2f}", flush=True)
                if auto_plan_to(label, goal_xy, face_xy):
                    st["replan_at"] = now + AUTO_REPLAN_SECONDS
                    auto_set_state(label, "GO_DELIVER", now)
                else:
                    auto_set_state(label, "DROP", now)
                continue

            if st["state"] == "GO_DELIVER":
                if now >= st["replan_at"] and st["goal"] is not None:
                    auto_plan_to(label, st["goal"], st["follower"].face_xy)
                    st["replan_at"] = now + AUTO_REPLAN_SECONDS
                arrived = auto_drive(label, now)
                if arrived or (now - st["since"]) > AUTO_STATE_TIMEOUT:
                    px, py = base_world_xy(label)
                    gx, gy = st["goal"] if st["goal"] else (px, py)
                    print(f"[AUTO] {label}: GO_DELIVER {'도착' if arrived else '시간초과'} "
                          f"{now - st['since']:.1f}s, 목적지까지 {math.hypot(gx-px, gy-py):.3f} m", flush=True)
                    auto_set_state(label, "DROP", now)
                continue

            if st["state"] == "DROP":
                if (now - st["since"]) < AUTO_DROP_PAUSE:
                    continue
                ball = attached_ball[label]
                if ball is not None:
                    release_ball(label)
                    auto_nav["stats"][label]["delivered"] += 1
                if st["ball"] is not None:
                    auto_nav["claims"].pop(st["ball"], None)
                st["ball"] = None
                auto_set_state(label, "SEARCH", now)

    # ------------------------------------------------------------------ #
    # --ai-mode: scripted ball-search + IK grasp-attempt state machine.
    # See the AI_* constants' comment block near the top of this file and
    # lekiwi_ik.py's module docstring. Ball positions are read live every
    # tick from each ball's own simulated prim transform (simulator ground
    # truth, not camera perception) so a moved/knocked ball is picked up on
    # the very next control tick, not just once at claim time.
    # ------------------------------------------------------------------ #
    ai_clock = [0.0]        # 단조 증가 시뮬 시계(위 주석 참고)
    ai_state = {
        label: {"state": "SEARCH", "target_ball": None, "entered_at": 0.0,
                "seed_deg": dict(lekiwi_ik.NEUTRAL_DEG), "scratch": {},
                "outcome": None}
        for label in ROBOTS
    }
    ai_ball_claims: dict[str, str] = {}          # ball prim path -> owning robot label
    ai_ball_fail_counts: dict[tuple, int] = {}    # (label, ball path) -> consecutive fails
    ai_ball_cooldowns: dict[str, float] = {}      # ball path -> monotonic time it's excluded until
    ai_stats = {label: {"attempts": 0, "successes": 0, "scripted_successes": 0, "fails": 0, "passes": 0}
                for label in ROBOTS}
    net_present = stage.GetPrimAtPath("/World/Arena/Net").IsValid()

    def own_basket_center(label):
        sign = robot_controls[label]["team_sign"]
        for goal in ("TeamRed_Goal", "TeamBlue_Goal"):
            prim = stage.GetPrimAtPath(f"/World/Arena/Baskets/{goal}")
            attr = prim.GetAttribute("arena:basketCenter") if prim.IsValid() else None
            center = attr.Get() if attr is not None and attr.IsValid() else None
            if center is not None and (float(center[0]) < 0) == (sign < 0):
                return float(center[0]), float(center[1])
        return None

    def ai_still_holding(label, ball):
        if ball is None or ball not in ball_controls:
            return False
        if args.scripted_attach:
            return attached_ball[label] == ball
        gp = gripper_world_pos(label)
        if gp is None:
            return False
        bx, by, bz = ball_world_xyz(ball)
        return math.dist((bx, by, bz), (float(gp[0]), float(gp[1]), float(gp[2]))) < AI_CARRY_DISTANCE
    # Measured control-tick period, so AI rate limits are deg/s instead of
    # deg/tick (see ai_set_gripper). Clamped: a hitch never turns into a jump.
    ai_tick_dt = [1.0 / 60.0]
    ai_last_tick = [None]

    def ball_world_xyz(path):
        prim = stage.GetPrimAtPath(path)
        t = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        ).ExtractTranslation()
        return float(t[0]), float(t[1]), float(t[2])

    def ai_set_state(label, new_state, now):
        st = ai_state[label]
        if st["state"] != new_state:
            print(f"[AI] {label}: {st['state']} -> {new_state}"
                  + (f" (ball={st['target_ball']})" if st["target_ball"] else ""),
                  flush=True)
            if new_state in ("SEARCH", "APPROACH", "ARM_UP"):
                ai_state[label]["jaw_off"] = None      # 시도마다 다시 잰다
                ai_state[label]["jaw_target"] = None
                ai_state[label]["jaw_refined_at"] = -9.9
            if new_state in ("ARM_UP", "DESCEND", "CLOSE", "LIFT", "VERIFY", "PASS_REACH", "PASS_RELEASE"):
                ai_capture_snapshot(label, new_state)
        st["state"] = new_state
        st["entered_at"] = now
        st["scratch"] = {}
        if new_state == "SEARCH":
            st["seed_deg"] = dict(lekiwi_ik.NEUTRAL_DEG)

    def ai_release_claim(label):
        st = ai_state[label]
        if st["target_ball"] is not None:
            if ai_ball_claims.get(st["target_ball"]) == label:
                del ai_ball_claims[st["target_ball"]]
            st["target_ball"] = None

    def ai_on_manual_select(label):
        """Called from select_robot(): the robot the user just took manual
        control of immediately drops any AI claim/state so no AI base or
        arm command can be issued for it again until it stops being the
        active robot."""
        st = ai_state[label]
        if st["state"] != "MANUAL":
            ai_release_claim(label)
            ai_set_state(label, "MANUAL", timeline.get_current_time())

    def ai_pick_ball(label, now):
        x_lo, x_hi, y_lo, y_hi = team_half(label)
        bxr, byr = base_world_xy(label)
        # Defer to whoever the user is *currently* driving, not a hardcoded
        # "Blue 1": under --record MANUAL_ROBOT and labels[active_index] are
        # the same robot for the whole session (T/F disabled), but --ai-mode
        # also works standalone (no --record) where T/F can move the manual
        # slot to any robot.
        manual_label = labels[active_index]
        blue1_xy = base_world_xy(manual_label) if manual_label != label else None
        prefer = args.ai_prefer_color.strip().lower()
        best_path, best_dist = None, None            # nearest ball of the preferred colour
        other_path, other_dist = None, None          # nearest ball of any other colour
        for path in ball_controls:
            owner = ai_ball_claims.get(path)
            if owner is not None and owner != label:
                continue
            if now < ai_ball_cooldowns.get(path, 0.0):
                continue
            bx, by, bz = ball_world_xyz(path)
            if not (x_lo <= bx <= x_hi and y_lo <= by <= y_hi):
                continue  # stay on this robot's own team half, like background wander
            if blue1_xy is not None and math.hypot(bx - blue1_xy[0], by - blue1_xy[1]) < AI_BLUE1_DEFER_RADIUS:
                continue  # defer to Blue 1's own workspace
            d = math.hypot(bx - bxr, by - byr)
            if prefer and ball_controls[path]["color"] == prefer:
                if best_path is None or d < best_dist:
                    best_path, best_dist = path, d
            elif other_path is None or d < other_dist:
                other_path, other_dist = path, d
        return best_path if best_path is not None else other_path

    def ai_local_target(label, world_xyz):
        transform = UsdGeom.Xformable(
            robot_controls[label]["base_prim"]
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        p = transform.GetInverse().Transform(Gf.Vec3d(*world_xyz))
        return float(p[0]), float(p[1]), float(p[2])

    def ai_apply_fixed_pose(label, pose_deg):
        """미리 구해 둔 관절 자세를 그대로 명령한다(IK 없음). 속도 제한은 ai_drive_arm 과 같은
        last_targets 경로를 재사용해 급격한 점프를 막는다."""
        control = robot_controls[label]
        activate_arm_drives(label)
        for key, value in pose_deg.items():
            drive = control["arm_drives"].get(key)
            if drive is None:
                continue
            if key in control["last_targets"]:
                prev = control["last_targets"][key]
            else:
                attr = control["arm_joint_prims"][key].GetAttribute("state:angular:physics:position")
                actual = attr.Get() if attr.IsValid() else None
                prev = float(actual) if actual is not None else float(value)
            step = AI_ARM_RATE_DEG_PER_S * ai_tick_dt[0]
            nxt = max(prev - step, min(prev + step, float(value)))
            drive.GetTargetPositionAttr().Set(nxt)
            control["last_targets"][key] = nxt

    def ai_jaw_target(label, ball_xyz):
        """턱 중앙이 공에 오도록 IK 목표(= gripper_frame_link 가 가야 할 점)를 보정한다.

        IK 는 위치만 풀고 방향은 제어하지 않아(lekiwi_ik.py) gripper_frame_link → 턱 오프셋이
        자세마다 다르다. 2026-09-11 실측: frame 이 공에서 0.03 m 일 때 턱은 0.09~0.12 m 떨어져
        있었다. 그래서 고정 오프셋을 쓰지 않고 **매 틱 실측**해 그만큼 목표를 당긴다.
        """
        st = ai_state[label]
        off = st.get("jaw_off")
        if off is None:
            # **시도당 한 번만** 잰다. 매 틱 다시 재면 팔이 움직일 때 오프셋도 같이 변해
            # 목표가 계속 달아나고 DESCEND 에서 수렴하지 못한다(2026-10-01 실측).
            jaws = jaw_world_positions(label)
            xf = gripper_frame_transform(label)
            if jaws is None or xf is None:
                return ball_xyz
            fx, fy, fz = xf.ExtractTranslation()
            mid = [(float(jaws[0][i]) + float(jaws[1][i])) / 2.0 for i in range(3)]
            off = (mid[0] - fx, mid[1] - fy, mid[2] - fz)       # frame → 턱 중앙
            st["jaw_off"] = off
            print(f"[AI] {label}: 턱 오프셋 측정 ({off[0]:+.3f},{off[1]:+.3f},{off[2]:+.3f}) m", flush=True)
        return (ball_xyz[0] - off[0], ball_xyz[1] - off[1], ball_xyz[2] - off[2])

    def ai_drive_arm(label, target_world_xyz, tolerance, wrist_roll_deg=None):
        """One IK solve + rate-limited apply toward a world-frame target.
        Returns (reached, ik_residual_error_m) where `reached` compares the
        *live measured* gripper_frame_link world position against the
        target -- physics feedback, not just trusting the IK solution."""
        control = robot_controls[label]
        activate_arm_drives(label)
        st = ai_state[label]
        local_target = ai_local_target(label, target_world_xyz)
        sol, err = lekiwi_ik.solve_ik(local_target, st["seed_deg"])
        if err > AI_ARM_UNREACHABLE_ERROR:
            # Warm-starting from the previous attempt's (lifted/placed) pose
            # can leave damped-least-squares stuck against a joint limit
            # with a large residual even for a target the neutral seed
            # solves fine -- seen headlessly as ARM_UP failing with ~0.23 m
            # residual on every attempt after the first success.
            sol2, err2 = lekiwi_ik.solve_ik(local_target, dict(lekiwi_ik.NEUTRAL_DEG))
            if err2 < err:
                sol, err = sol2, err2
        st["seed_deg"] = sol
        for key, joint_key in (
            ("shoulder_pan.pos", "shoulder_pan"), ("shoulder_lift.pos", "shoulder_lift"),
            ("elbow_flex.pos", "elbow_flex"), ("wrist_flex.pos", "wrist_flex"),
            ("wrist_roll.pos", "wrist_roll"),
        ):
            # 가로 파지: IK 가 푼 wrist_roll 대신 지정 각도를 쓴다(그리퍼 턱 방향만 바꾼다 —
            # 손목 롤은 손끝 위치에 거의 영향을 주지 않으므로 IK 해를 깨지 않는다).
            if key == "wrist_roll.pos" and wrist_roll_deg is not None:
                sol = dict(sol)
                sol["wrist_roll"] = float(wrist_roll_deg)
            drive = control["arm_drives"][key]
            # Same fix as ai_set_gripper(): default to the live physical
            # angle, not the solved target itself, on the first call for
            # this joint -- otherwise the first IK solve snaps the drive
            # target straight there with no rate limiting.
            if key in control["last_targets"]:
                prev = control["last_targets"][key]
            else:
                attr = control["arm_joint_prims"][key].GetAttribute("state:angular:physics:position")
                actual = attr.Get() if attr.IsValid() else None
                prev = float(actual) if actual is not None else sol[joint_key]
            step = ARM_MAX_STEP_DEG[key] * 60.0 * ai_tick_dt[0]  # per-tick limit -> deg/s
            target = prev + max(-step, min(step, sol[joint_key] - prev))
            control["last_targets"][key] = target
            drive.CreateTargetPositionAttr().Set(target)
        gp = gripper_world_pos(label)
        if gp is None:
            return False, err, None
        dist = math.dist((float(gp[0]), float(gp[1]), float(gp[2])), target_world_xyz)
        return dist <= tolerance, err, dist

    def ai_set_gripper(label, percent):
        """Drives gripper.pos toward `percent` (0=open/100=closed, matching
        the same limits[0]->limits[1] convention apply_arm() already uses
        for the leader's own gripper percent -- not a new convention).
        Returns True once the rate-limited target has converged to the
        commanded percent.

        BUG FIXED 2026-09-11: the first version defaulted `prev` (when
        "gripper.pos" had no prior last_targets entry) to `target` itself --
        the exact same mistake this file's apply_arm() docstring already
        warns about ("with no prior state entry it returns requested
        itself, so the first call clamps nothing"). That made the very
        first ai_set_gripper() call in a CLOSE state jump the commanded
        drive target straight to fully-closed and report done=True on the
        same tick, before the physical joint had moved at all -- confirmed
        via a headless run where CLOSE->LIFT fired instantly while the
        *actual* joint angle (state:angular:physics:position) was still at
        its idle/open value. This is very likely why 0/~15 headless grasp
        attempts ever closed on a ball: the gripper was never really given
        time to close. Fixed by seeding `prev` from the live physical angle
        on first use, same as start_connect_blend() does for the arm."""
        control = robot_controls[label]
        limits = control["gripper_limits"]
        drive = control["arm_drives"]["gripper.pos"]
        target = limits[0] + (limits[1] - limits[0]) * max(0.0, min(100.0, percent)) / 100.0 \
            if limits is not None else 0.0
        if "gripper.pos" in control["last_targets"]:
            prev = control["last_targets"]["gripper.pos"]
        else:
            attr = control["arm_joint_prims"]["gripper.pos"].GetAttribute("state:angular:physics:position")
            actual = attr.Get() if attr.IsValid() else None
            prev = float(actual) if actual is not None else target
        # 60 deg/s -- the same 1 deg/tick the leader path uses at a nominal
        # 60 Hz loop, but scaled by the *measured* tick period so a slow
        # loop (headless with extra render products ran at ~4-6 Hz, GUI at
        # ~10-20 Hz) doesn't turn a 1.7 s close into a 20 s one and blow
        # the CLOSE timeout (that is exactly what the first --scripted-attach
        # runs showed: closed_fraction crawling linearly to ~0.4 in 8 s).
        step = 60.0 * ai_tick_dt[0]
        val = prev + max(-step, min(step, target - prev))
        control["last_targets"]["gripper.pos"] = val
        drive.CreateTargetPositionAttr().Set(val)
        return abs(val - target) < 0.5

    def ai_retreat_arm(label):
        """Non-IK: ease every arm joint except gripper back toward the same
        ARM_RELAXED_TARGET_DEG idle pose used while an AI robot has no ball
        target. Returns True once within 1 degree of that pose on every
        joint."""
        control = robot_controls[label]
        done = True
        for key in ARM_JOINTS:
            if key == "gripper.pos":
                continue
            drive = control["arm_drives"][key]
            target_deg = ARM_RELAXED_TARGET_DEG[key]
            if key in control["last_targets"]:
                prev = control["last_targets"][key]
            else:
                attr = control["arm_joint_prims"][key].GetAttribute("state:angular:physics:position")
                actual = attr.Get() if attr.IsValid() else None
                prev = float(actual) if actual is not None else target_deg
            step = ARM_MAX_STEP_DEG[key] * 60.0 * ai_tick_dt[0]  # per-tick limit -> deg/s
            val = prev + max(-step, min(step, target_deg - prev))
            control["last_targets"][key] = val
            drive.CreateTargetPositionAttr().Set(val)
            if abs(val - target_deg) > 1.0:
                done = False
        return done

    def ai_drive_base_to(label, target_xy, face_xy=None):
        """Holonomic move-to-point + face-the-target heading control. Both
        the position AND heading tolerance must hold at once before this
        reports "reached" -- earlier versions zeroed angular velocity as
        soon as position alone was satisfied, which could permanently
        freeze the yaw error and stall APPROACH until its timeout (caught
        by the first headless --ai-mode run: every attempt timed out at
        exactly 15s). Rotation keeps correcting even after the base has
        arrived, so a heading-only residual still converges."""
        control = robot_controls[label]
        x, y = base_world_xy(label)
        dx, dy = target_xy[0] - x, target_xy[1] - y
        dist = math.hypot(dx, dy)
        transform = UsdGeom.Xformable(
            control["base_prim"]
        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        forward = transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
        cur_yaw = math.degrees(math.atan2(forward[1], forward[0]))
        # Heading target is the thing we want to *face* (the ball), not the
        # waypoint we drive to. When the ball is closer than the standoff
        # distance the waypoint lies behind the base; facing the waypoint
        # spun the robot 180 deg and left the ball at x~-0.23 in the base
        # frame -> every ARM_UP failed "unreachable" (headless, 2026-09-11).
        fx, fy = (face_xy[0] - x, face_xy[1] - y) if face_xy is not None else (dx, dy)
        want_yaw = math.degrees(math.atan2(fy, fx)) if math.hypot(fx, fy) > 1e-6 else cur_yaw
        yaw_err = (want_yaw - cur_yaw + 180.0) % 360.0 - 180.0
        at_position = dist < AI_POS_TOLERANCE
        at_heading = abs(yaw_err) < AI_HEADING_TOLERANCE_DEG
        if at_position and at_heading:
            control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            return True, dist, yaw_err
        speed = 0.0 if at_position else min(AI_BASE_LINEAR_SPEED, dist)
        vx, vy = (dx / dist * speed, dy / dist * speed) if dist > 1e-6 else (0.0, 0.0)
        next_x, next_y = x + vx * COLLISION_LOOKAHEAD_SECONDS, y + vy * COLLISION_LOOKAHEAD_SECONDS
        yaw_rate = 0.0 if at_heading else max(
            -AI_BASE_ROT_SPEED_CAP, min(AI_BASE_ROT_SPEED_CAP, yaw_err * AI_BASE_ROT_GAIN)
        )
        if (vx != 0.0 or vy != 0.0) and blocked(label, next_x, next_y):
            # Don't just freeze: sidestep perpendicular to the travel
            # direction, away from the nearest other robot (holonomic base),
            # so two robots meeting head-on slide past each other instead of
            # both waiting on ROBOT_CLEARANCE until a state timeout.
            nearest, nearest_d = None, None
            for other in ROBOTS:
                if other == label:
                    continue
                ox, oy = base_world_xy(other)
                d_o = math.hypot(ox - x, oy - y)
                if nearest_d is None or d_o < nearest_d:
                    nearest, nearest_d = (ox, oy), d_o
            px, py = -dy / dist, dx / dist  # unit perpendicular
            if nearest is not None and (px * (nearest[0] - x) + py * (nearest[1] - y)) > 0:
                px, py = -px, -py            # flip: move away from that robot
            sx, sy = px * 0.08, py * 0.08
            if not blocked(label, x + sx * COLLISION_LOOKAHEAD_SECONDS, y + sy * COLLISION_LOOKAHEAD_SECONDS):
                control["velocity"].Set(Gf.Vec3f(sx, sy, 0.0))
            else:
                control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
            control["angular"].Set(Gf.Vec3f(0.0, 0.0, yaw_rate))
            return False, dist, yaw_err
        control["velocity"].Set(Gf.Vec3f(vx, vy, 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, yaw_rate))
        return False, dist, yaw_err

    def update_ai_robots(now):
        """--ai-mode counterpart to update_background_robots(): called for
        every robot that is not the current manual one. Global E-stop (Q)
        takes priority over all of this -- apply_base_commands() already
        zeroed every base's velocity this tick, and while movement_paused
        this function does not touch base or arm targets at all, so a
        paused robot simply holds wherever it physically is."""
        # 2026-10-01: timeline.get_current_time() 은 이 스테이지에서 약 1 초마다 되감긴다(실측).
        # 그대로 쓰면 상태 타임아웃·쿨다운이 영영 성립하지 않아 DESCEND 등에서 멈춘다.
        # 증가분만 받아 단조 증가 시계를 만든다(auto-base 와 같은 처리).
        raw_now = now
        prev_raw = ai_last_tick[0]
        dt = (raw_now - prev_raw) if prev_raw is not None else 0.0
        if dt <= 0.0 or dt > 0.5:
            dt = 1.0 / float(args.fps)
        ai_tick_dt[0] = max(1.0 / 240.0, min(0.1, dt))
        ai_last_tick[0] = raw_now
        ai_clock[0] = now = ai_clock[0] + dt
        if movement_paused:
            return
        for label in ROBOTS:
            if label == labels[active_index]:
                st = ai_state[label]
                if st["state"] != "MANUAL":
                    ai_on_manual_select(label)
                continue
            st = ai_state[label]
            if st["state"] == "MANUAL":
                ai_set_state(label, "SEARCH", now)

            state = st["state"]
            timeout = AI_STATE_TIMEOUT_SECONDS.get(state)
            if timeout is not None and now - st["entered_at"] > timeout:
                print(f"[AI] {label}: state {state} timed out after {timeout:.0f}s", flush=True)
                st["outcome"] = "fail"
                ai_set_state(label, "RETREAT", now)
                state = "RETREAT"

            if state == "SEARCH":
                ball = ai_pick_ball(label, now)
                if ball is not None:
                    ai_ball_claims[ball] = label
                    st["target_ball"] = ball
                    ai_stats[label]["attempts"] += 1
                    ai_set_state(label, "APPROACH", now)

            elif state == "APPROACH":
                ball = st["target_ball"]
                if ball is None or ball not in ball_controls or ai_ball_claims.get(ball) != label:
                    ai_set_state(label, "SEARCH", now)
                    continue
                bx, by, _bz = ball_world_xyz(ball)
                rx, ry = base_world_xy(label)
                dx, dy = bx - rx, by - ry
                dn = math.hypot(dx, dy) or 1.0
                standoff = (bx - dx / dn * AI_STANDOFF_DIST, by - dy / dn * AI_STANDOFF_DIST)
                reached, _dist, yaw_err = ai_drive_base_to(label, standoff, face_xy=(bx, by))
                if reached and abs(yaw_err) < AI_HEADING_TOLERANCE_DEG:
                    ai_set_state(label, "ARM_UP", now)

            elif state == "ARM_UP":
                ball = st["target_ball"]
                if ball is None or ball not in ball_controls:
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                    continue
                bx, by, bz = ball_world_xyz(ball)
                reached, err, _dist = ai_drive_arm(label, (bx, by, bz + AI_GRASP_HOVER_HEIGHT), AI_ARM_POS_TOLERANCE)
                if err > AI_ARM_UNREACHABLE_ERROR and now - st["entered_at"] > 1.5:
                    lt = ai_local_target(label, (bx, by, bz))
                    print(f"[AI] {label}: ball unreachable from this stance (IK residual {err:.3f} m, "
                          f"target in base frame x={lt[0]:.3f} y={lt[1]:.3f} z={lt[2]:.3f})",
                          flush=True)
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                elif reached:
                    ai_set_state(label, "DESCEND", now)

            elif state == "DESCEND":
                ball = st["target_ball"]
                if ball is None or ball not in ball_controls:
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                    continue
                # Re-read the ball's live position every tick (not just the
                # position captured when this attempt started) per the
                # requirement to keep tracking a ball that may have moved.
                bx, by, bz = ball_world_xyz(ball)
                # 2026-10-01: sim_grasp_pose.py 가 턱중앙-공 2.0 cm 까지 수렴시킨 방식을 그대로 쓴다 —
                # 물리가 안정된 뒤 (턱중앙 - gripper_frame) 오프셋을 **다시 재서** 목표를 갱신하는
                # 고정점 반복. 매 틱 갱신하면 발산하므로 AI_JAW_REFINE_PERIOD 마다 한 번만 갱신한다.
                if st.get("jaw_target") is None or (now - st.get("jaw_refined_at", -9.9)) >= AI_JAW_REFINE_PERIOD:
                    jaws_now = jaw_world_positions(label)
                    xf_now = gripper_frame_transform(label)
                    if jaws_now is not None and xf_now is not None:
                        fx, fy, fz = xf_now.ExtractTranslation()
                        mid = [(float(jaws_now[0][i]) + float(jaws_now[1][i])) / 2.0 for i in range(3)]
                        off = (mid[0] - float(fx), mid[1] - float(fy), mid[2] - float(fz))
                        st["jaw_target"] = (bx - off[0], by - off[1], bz - off[2])
                    else:
                        st["jaw_target"] = (bx, by, bz)
                    st["jaw_refined_at"] = now
                _r, err, _d = ai_drive_arm(label, st["jaw_target"], AI_ARM_POS_TOLERANCE,
                                           wrist_roll_deg=AI_GRASP_WRIST_ROLL_DEG)
                jaws_now = jaw_world_positions(label)
                dist = (min(math.dist((bx, by, bz), (float(j[0]), float(j[1]), float(j[2])))
                            for j in jaws_now) if jaws_now else 9.9)
                reached = dist < AI_GRASP_JAW_TOL
                if now - st["entered_at"] > AI_DESCEND_MAX_S and not reached:
                    print(f"[AI] {label}: 고정 자세 재생했으나 턱-공 {dist:.3f} m — 실패", flush=True)
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                elif reached:
                    print(f"[AI] {label}: DESCEND reached -- live gripper-ball gap={dist:.4f}m "
                          f"(tolerance={AI_ARM_POS_TOLERANCE:.3f}m, IK residual={err:.4f}m)", flush=True)
                    ai_set_state(label, "CLOSE", now)

            elif state == "CLOSE":
                ball = st["target_ball"]
                if ball is not None and ball in ball_controls:
                    bx, by, bz = ball_world_xyz(ball)
                    if st.get("jaw_target") is not None:
                        ai_drive_arm(label, st["jaw_target"], AI_ARM_POS_TOLERANCE,
                                     wrist_roll_deg=AI_GRASP_WRIST_ROLL_DEG)
                done = ai_set_gripper(label, 100.0)
                # --scripted-attach: the moment the ball is glued on, the
                # close has done its job -- don't sit here waiting for the
                # commanded target to converge (the weak compliant drive may
                # never get there with something between the jaws).
                if args.scripted_attach and attached_ball[label] == ball:
                    ai_set_state(label, "LIFT", now)
                elif done:
                    ai_set_state(label, "LIFT", now)

            elif state == "LIFT":
                if "lift_target" not in st["scratch"]:
                    gp = gripper_world_pos(label)
                    if gp is None:
                        st["outcome"] = "fail"
                        ai_set_state(label, "RETREAT", now)
                        continue
                    st["scratch"]["lift_target"] = (float(gp[0]), float(gp[1]), float(gp[2]) + AI_LIFT_DELTA_Z)
                ai_set_gripper(label, 100.0)
                reached, _err, _dist = ai_drive_arm(label, st["scratch"]["lift_target"], AI_ARM_POS_TOLERANCE)
                if reached:
                    ai_set_state(label, "VERIFY", now)

            elif state == "VERIFY":
                ball = st["target_ball"]
                gp = gripper_world_pos(label)
                lifted = False
                carried = False
                gap = None
                ball_z = None
                if ball is not None and ball in ball_controls and gp is not None:
                    bx, by, bz = ball_world_xyz(ball)
                    ball_z = bz
                    gap = math.dist((bx, by, bz), (float(gp[0]), float(gp[1]), float(gp[2])))
                    carried = gap < AI_CARRY_DISTANCE
                    lifted = bz > AI_LIFTED_HEIGHT_THRESHOLD
                if carried and lifted:
                    scripted = args.scripted_attach and attached_ball[label] == ball
                    print(f"[AI] {label}: LIFT SUCCESS{' (SCRIPTED ATTACH -- not a physics grasp)' if scripted else ''} "
                          f"(ball={ball}) gripper-ball gap={gap:.3f}m ball_z={ball_z:.3f}m", flush=True)
                    st["outcome"] = "success_scripted" if scripted else "success"
                else:
                    print(f"[AI] {label}: grasp not confirmed (carried={carried} lifted={lifted}) "
                          f"gripper-ball gap={gap if gap is None else round(gap,3)}m "
                          f"ball_z={ball_z if ball_z is None else round(ball_z,3)}m "
                          f"(lift threshold={AI_LIFTED_HEIGHT_THRESHOLD:.3f}m, carry threshold={AI_CARRY_DISTANCE:.3f}m)",
                          flush=True)
                    st["outcome"] = "fail"
                if str(st["outcome"]).startswith("success"):
                    # On a net arena: carry it to the net and put it on the
                    # opponent's side (the "pass" the game rules score). No
                    # net -> just set it back down (PLACE).
                    ai_set_state(label, "CARRY" if net_present else "PLACE", now)
                else:
                    ai_set_state(label, "RETREAT", now)

            elif state == "CARRY":
                ball = st["target_ball"]
                ai_set_gripper(label, 100.0)
                if not ai_still_holding(label, ball):
                    print(f"[AI] {label}: lost the ball while carrying", flush=True)
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                    continue
                sign = robot_controls[label]["team_sign"]
                if "pass_y" not in st["scratch"]:
                    # Two pass lanes per team, one on each side of the own
                    # basket (basket keepout at the net spans roughly
                    # |y - basket_y| < 0.32): the centre-side lane and the
                    # wall-side lane. Take the first lane no team-mate is
                    # already carrying toward -- otherwise both red robots
                    # converged on the same spot and the second one sat
                    # blocked (ROBOT_CLEARANCE) until CARRY timed out.
                    basket = own_basket_center(label)
                    _bx0, by0 = base_world_xy(label)
                    if basket is not None:
                        centre_lane = basket[1] - math.copysign(AI_PASS_BASKET_CLEAR, basket[1])
                        wall_lane = math.copysign(0.76, basket[1])
                        # Prefer the lane on the side of the basket the robot
                        # is already on: two team-mates starting in opposite
                        # corners and both heading for the centre lane met
                        # head-on at x~-0.7 and deadlocked on ROBOT_CLEARANCE.
                        on_wall_side = (by0 * basket[1] > 0) and abs(by0) > abs(basket[1]) - 0.10
                        lanes = [wall_lane, centre_lane] if on_wall_side else [centre_lane, wall_lane]
                    else:
                        lanes = [0.0, 0.5, -0.5]
                    taken = [
                        ai_state[o]["scratch"].get("pass_y") for o in ROBOTS
                        if o != label and robot_controls[o]["team_sign"] == sign
                        and ai_state[o]["state"] in ("CARRY", "PASS_REACH", "PASS_RELEASE")
                    ]
                    chosen = lanes[0]
                    for cand in lanes:
                        if all(t is None or abs(t - cand) >= 0.4 for t in taken):
                            chosen = cand
                            break
                    st["scratch"]["pass_y"] = chosen
                    # Route behind the basket first (deep in the own half, at
                    # the lane's y) so the straight-line drive never cuts
                    # through the basket keepout box -- the direct line from
                    # the spawn corners did, and blocked() has no path
                    # planning, so Blue 2 / Red 1 just stalled there.
                    st["scratch"]["carry_leg"] = 0
                pass_y = st["scratch"]["pass_y"]
                if st["scratch"]["carry_leg"] == 0:
                    reached, _dist, _yaw = ai_drive_base_to(
                        label, (sign * 0.70, pass_y), face_xy=(0.0, pass_y)
                    )
                    if reached:
                        st["scratch"]["carry_leg"] = 1
                else:
                    reached, _dist, _yaw = ai_drive_base_to(
                        label, (sign * AI_PASS_STANDOFF_X, pass_y), face_xy=(0.0, pass_y)
                    )
                    if reached:
                        ai_set_state(label, "PASS_REACH", now)

            elif state == "PASS_REACH":
                ball = st["target_ball"]
                ai_set_gripper(label, 100.0)
                if not ai_still_holding(label, ball):
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                    continue
                sign = robot_controls[label]["team_sign"]
                _bx, by0 = base_world_xy(label)
                target = (-sign * AI_PASS_OVER_X, by0, AI_PASS_HEIGHT)
                reached, err, _d = ai_drive_arm(label, target, 0.05)
                if err > 0.08 and now - st["entered_at"] > 2.0:
                    print(f"[AI] {label}: cannot reach over the net from here (IK residual {err:.3f} m)",
                          flush=True)
                    st["outcome"] = "fail"
                    ai_set_state(label, "RETREAT", now)
                elif reached:
                    ai_set_state(label, "PASS_RELEASE", now)

            elif state == "PASS_RELEASE":
                ball = st["target_ball"]
                sign = robot_controls[label]["team_sign"]
                _bx, by0 = base_world_xy(label)
                ai_drive_arm(label, (-sign * AI_PASS_OVER_X, by0, AI_PASS_HEIGHT), 0.04)
                opened = ai_set_gripper(label, 0.0)
                released = (not args.scripted_attach) or attached_ball[label] is None
                if opened and released:
                    bx, by, bz = ball_world_xyz(ball) if ball in ball_controls else (0.0, 0.0, 0.0)
                    if bx * sign < 0:
                        ai_stats[label]["passes"] += 1
                        print(f"[AI] {label}: PASS SUCCESS -- {ball} ({ball_controls[ball]['color']}) "
                              f"now on the other side at x={bx:.3f}"
                              f"{' (scripted attach carry)' if args.scripted_attach else ''}", flush=True)
                    else:
                        print(f"[AI] {label}: released but ball still on own side (x={bx:.3f})", flush=True)
                    ai_set_state(label, "RETREAT", now)

            elif state == "PLACE":
                # Success path only: no verified place-in-basket behaviour
                # exists, so set the ball back down safely near the current
                # position rather than attempting to score it (see
                # NEXT_CHAT_HANDOFF.md section 16).
                if "place_target" not in st["scratch"]:
                    gp = gripper_world_pos(label)
                    if gp is None:
                        ai_set_state(label, "RETREAT", now)
                        continue
                    st["scratch"]["place_target"] = (
                        float(gp[0]), float(gp[1]), max(BALL_RADIUS_M + 0.02, float(gp[2]) - AI_LIFT_DELTA_Z)
                    )
                ai_drive_arm(label, st["scratch"]["place_target"], AI_ARM_POS_TOLERANCE)
                if ai_set_gripper(label, 0.0):
                    ai_set_state(label, "RETREAT", now)

            elif state == "RETREAT":
                ai_set_gripper(label, 0.0)
                arm_home = ai_retreat_arm(label)
                # --scripted-attach: never leave RETREAT while a ball is still
                # glued on -- release happens in update_scripted_attach() once
                # the gripper has physically opened past RELEASE_CLOSED_FRACTION,
                # and finishing early would drag the ball into the next SEARCH.
                still_holding = args.scripted_attach and attached_ball[label] is not None
                if arm_home and not still_holding:
                    outcome = st["outcome"] or "fail"
                    ball = st["target_ball"]
                    if outcome == "fail" and ball is not None:
                        key = (label, ball)
                        ai_ball_fail_counts[key] = ai_ball_fail_counts.get(key, 0) + 1
                        ai_stats[label]["fails"] += 1
                        if ai_ball_fail_counts[key] >= AI_MAX_CONSECUTIVE_FAILS:
                            ai_ball_cooldowns[ball] = now + AI_FAIL_COOLDOWN_SECONDS
                            ai_ball_fail_counts[key] = 0
                            print(f"[AI] {label}: {ball} put on {AI_FAIL_COOLDOWN_SECONDS:.0f}s cooldown "
                                  f"after {AI_MAX_CONSECUTIVE_FAILS} consecutive failed attempts", flush=True)
                    elif outcome == "success":
                        ai_stats[label]["successes"] += 1
                    elif outcome == "success_scripted":
                        ai_stats[label]["scripted_successes"] += 1
                    if str(outcome).startswith("success") and ball is not None:
                        # Just set this one down -- go find a different ball
                        # for a while instead of picking the same one straight
                        # back up (demo reads better, and it stops one robot
                        # camping a single ball).
                        ai_ball_cooldowns[ball] = now + AI_FAIL_COOLDOWN_SECONDS
                    ai_release_claim(label)
                    st["outcome"] = None
                    ai_set_state(label, "SEARCH", now)

    # ------------------------------------------------------------------ #
    # --scripted-attach: NOT real friction/contact grasping. See the CLI
    # help text above. Applies to every robot (manual Blue 1 included, not
    # just --ai-mode), independent of the AI state machine -- CLOSE already
    # drives gripper.pos toward 100% (AI) or the leader's own gripper
    # reading (manual), so this only has to watch for "gripper mostly
    # closed + both jaws near an unclaimed ball" and glue/release
    # accordingly. Per the grasp-frame practice: the gripper->ball offset
    # is always computed fresh at the moment of contact, never hardcoded.
    # ------------------------------------------------------------------ #
    # Measured headlessly (2026-09-11): at the DESCEND->CLOSE transition,
    # gripper_frame_link (the IK target reference point) sits ~0.03m from
    # the ball, but the two actual jaw links (gripper_link /
    # moving_jaw_so101_v1_link) are typically ~0.09-0.12m away -- because
    # the IK is position-only (no orientation control, see lekiwi_ik.py),
    # gripper_frame_link's fixed local offset doesn't reliably point at the
    # jaws' own location. 0.14m covers the observed gap with some margin;
    # tightening this would need orientation-aware IK, not a bigger number.
    ATTACH_JAW_DISTANCE = 0.14                   # m, "close enough" per jaw
    # Measured headlessly (2026-09-11, --scripted-attach diagnostic run):
    # with the gripper's own weak/compliant drive (stiffness 8.0, max_force
    # 0.45 -- not changed), closed_fraction plateaus around 0.40-0.55
    # regardless of whether anything is between the jaws (self-contact
    # between the two jaw tips, not a bug) -- it essentially never reaches
    # a "fully closed" 0.9+. So closed-fraction alone can't tell "gripping
    # something" from "jaws met each other on empty air"; ATTACH_JAW_DISTANCE
    # (both jaws actually near the ball) is what has to do that job.
    ATTACH_CLOSED_FRACTION = 0.35                # gripper must be at least this closed
    RELEASE_CLOSED_FRACTION = 0.20               # opens back below this to release
    attached_ball = {label: None for label in ROBOTS}   # label -> ball path or None
    attach_mode = {label: None for label in ROBOTS}     # "auto" (closed+near) | "manual" (G key)
    MANUAL_ATTACH_RADIUS = 0.25                          # m from gripper_frame_link, G key
    attach_local_offset = {}                              # label -> Gf.Vec3d (in gripper_frame_link's local frame)
    ball_attached_to = {}                                  # ball path -> label (global ownership, prevents double-attach)

    def gripper_frame_transform(label):
        link = robot_controls[label]["gripper_frame_link"]
        if link is None:
            return None
        return UsdGeom.Xformable(link).ComputeLocalToWorldTransform(Usd.TimeCode.Default())

    def jaw_world_positions(label):
        robot_path = robot_controls[label]["robot_path"]
        out = []
        for sub in ("gripper_link", "moving_jaw_so101_v1_link"):
            prim = stage.GetPrimAtPath(f"{robot_path}/{sub}")
            if not prim.IsValid():
                return None
            out.append(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
                Usd.TimeCode.Default()).ExtractTranslation())
        return out

    def gripper_closed_fraction(label):
        control = robot_controls[label]
        limits = control["gripper_limits"]
        prim = control["arm_joint_prims"]["gripper.pos"]
        attr = prim.GetAttribute("state:angular:physics:position")
        angle = attr.Get() if attr.IsValid() else None
        if limits is None or angle is None or limits[1] == limits[0]:
            return 0.0
        return max(0.0, min(1.0, (float(angle) - limits[0]) / (limits[1] - limits[0])))

    _attach_dbg_next = {}

    def find_grabbable_ball(label, debug=False):
        jaws = jaw_world_positions(label)
        if jaws is None:
            return None
        best, best_d = None, None
        # BUG FIXED 2026-09-11: nearest_any_d used to be assigned the (d0, d1)
        # *tuple* on first sight, then later compared as `d < nearest_any_d`
        # (a float vs. a tuple) -- raised TypeError the first time any robot's
        # gripper crossed ATTACH_CLOSED_FRACTION with no ball in range, which
        # silently killed the whole process (no KeyboardInterrupt handler
        # catches it) with no traceback captured. Kept as a scalar now;
        # the tuple to report lives in a separate variable.
        nearest_any, nearest_any_pair, nearest_any_d = None, None, None
        for path in ball_controls:
            if path in ball_attached_to:
                continue
            bx, by, bz = ball_world_xyz(path)
            d0 = math.dist((bx, by, bz), (float(jaws[0][0]), float(jaws[0][1]), float(jaws[0][2])))
            d1 = math.dist((bx, by, bz), (float(jaws[1][0]), float(jaws[1][1]), float(jaws[1][2])))
            d = max(d0, d1)
            if nearest_any_d is None or d < nearest_any_d:
                nearest_any, nearest_any_pair, nearest_any_d = path, (d0, d1), d
            if d0 <= ATTACH_JAW_DISTANCE and d1 <= ATTACH_JAW_DISTANCE:
                if best is None or d < best_d:
                    best, best_d = path, d
        now_dbg = time.monotonic()
        if debug and best is None and nearest_any is not None and now_dbg >= _attach_dbg_next.get(label, 0.0):
            _attach_dbg_next[label] = now_dbg + 2.0
            print(f"[ATTACH][DEBUG] {label}: closed but no ball in range -- nearest "
                  f"{nearest_any} jaw distances={nearest_any_pair[0]:.3f}m/{nearest_any_pair[1]:.3f}m "
                  f"(threshold={ATTACH_JAW_DISTANCE:.3f}m)", flush=True)
        return best

    # Called as fn(label, ball_path) after every successful attach (G key or
    # scripted). The --record subsystem registers one to switch its 'net'
    # camera on; defined here so attach_ball needs no knowledge of recording.
    attach_listeners = []

    def attach_ball(label, ball_path):
        xf = gripper_frame_transform(label)
        if xf is None:
            return
        bx, by, bz = ball_world_xyz(ball_path)
        local = xf.GetInverse().Transform(Gf.Vec3d(bx, by, bz))
        attached_ball[label] = ball_path
        attach_local_offset[label] = local
        ball_attached_to[ball_path] = label
        attach_mode[label] = "auto"
        control = ball_controls[ball_path]
        control["kinematic_attr"].Set(True)
        for attr in control["collision_attrs"]:
            attr.Set(False)
        control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        print(f"[ATTACH] {label}: scripted-attached {ball_path} "
              "(NOT a real physics grasp)", flush=True)
        for listener in attach_listeners:
            listener(label, ball_path)

    def manual_attach_toggle(label):
        """G key: glue the nearest ball (within MANUAL_ATTACH_RADIUS of the
        gripper frame) to this robot's gripper, or release the one it holds.
        No closed-gripper or jaw-distance condition -- the operator decides.
        A ball attached this way is NOT auto-released by opening the gripper;
        only G (or B ball reset) lets go. Scripted, not a physics grasp."""
        if attached_ball[label] is not None:
            release_ball(label)
            return
        gp = gripper_world_pos(label)
        if gp is None:
            print(f"[ATTACH] {label}: no gripper frame on this robot", flush=True)
            return
        gx, gy, gz = float(gp[0]), float(gp[1]), float(gp[2])
        best, best_d = None, None
        for path in ball_controls:
            if path in ball_attached_to:
                continue
            d = math.dist(ball_world_xyz(path), (gx, gy, gz))
            if d <= MANUAL_ATTACH_RADIUS and (best is None or d < best_d):
                best, best_d = path, d
        if best is None:
            print(f"[ATTACH] {label}: G pressed but no ball within {MANUAL_ATTACH_RADIUS:.2f} m "
                  "of the gripper", flush=True)
            return
        attach_ball(label, best)
        attach_mode[label] = "manual"
        print(f"[ATTACH] {label}: held by G key (distance was {best_d:.3f} m) -- press G again to drop",
              flush=True)

    def release_ball(label):
        ball_path = attached_ball[label]
        if ball_path is None:
            return
        attach_mode[label] = None
        control = ball_controls[ball_path]
        for attr in control["collision_attrs"]:
            attr.Set(True)
        control["kinematic_attr"].Set(False)
        control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
        ball_attached_to.pop(ball_path, None)
        attached_ball[label] = None
        attach_local_offset.pop(label, None)
        print(f"[ATTACH] {label}: released {ball_path}", flush=True)
        emit_event("release", f"{label}:{ball_path}")

    def update_scripted_attach():
        # G-key holds must keep following the gripper even without
        # --scripted-attach; the automatic closed+near attach/auto-release
        # rules below stay behind the flag.
        if not args.scripted_attach and all(v is None for v in attached_ball.values()):
            return
        for label in ROBOTS:
            closed = gripper_closed_fraction(label)
            if attached_ball[label] is not None:
                if closed < RELEASE_CLOSED_FRACTION and attach_mode[label] != "manual":
                    release_ball(label)
                    continue
                xf = gripper_frame_transform(label)
                if xf is None:
                    continue
                world = xf.Transform(attach_local_offset[label])
                ball_controls[attached_ball[label]]["translate_attr"].Set(
                    Gf.Vec3d(world[0], world[1], world[2])
                )
            elif args.scripted_attach and closed >= ATTACH_CLOSED_FRACTION:
                candidate = find_grabbable_ball(label, debug=True)
                if candidate is not None:
                    attach_ball(label, candidate)

    def apply_arm(message: LeaderMessage):
        control = robot_controls[labels[active_index]]
        state = control["last_targets"]
        now = time.monotonic()
        blending = now < control["blend_until"]
        if blending:
            span_start = control["blend_until"] - CONNECT_BLEND_SECONDS
            t = max(0.0, min(1.0, (now - span_start) / CONNECT_BLEND_SECONDS))
        for key, drive in control["arm_drives"].items():
            requested = float(message.joints[key])
            if key == "wrist_roll.pos":
                requested -= 90.0
            if key == "gripper.pos":
                limits = control["gripper_limits"]
                if limits is not None:
                    percent = max(0.0, min(100.0, requested))
                    requested = limits[0] + (limits[1] - limits[0]) * percent / 100.0
            if blending:
                start = control["blend_from"][key]
                target = start + (requested - start) * t
            else:
                max_step = 1.0 if key == "gripper.pos" else ARM_MAX_STEP_DEG[key]
                previous = state.get(key, requested)
                target = previous + max(-max_step, min(max_step, requested - previous))
            state[key] = target
            drive.CreateTargetPositionAttr().Set(target)

    # ------------------------------------------------------------------ #
    # Recording subsystem (--record only). Four independent render
    # products + rgb annotators, decoupled from the interactive viewport:
    # switching what the user looks at, or how they navigate the viewport,
    # never touches these camera prims. Start/stop is signal-driven so a
    # second terminal can control it without competing with this process's
    # own keyboard-reading loop.
    # ------------------------------------------------------------------ #
    recording = None
    write_queue = None
    writer_thread = None
    if args.record:
        def camera_matrix(eye, target, up_hint=Gf.Vec3d(0, 0, 1)):
            forward = (target - eye).GetNormalized()
            right = Gf.Cross(forward, up_hint).GetNormalized()
            up = Gf.Cross(right, forward)
            matrix = Gf.Matrix4d(1)
            for i, v in enumerate((right, up, -forward)):
                matrix.SetRow(i, Gf.Vec4d(*v, 0))
            matrix.SetRow(3, Gf.Vec4d(*eye, 1))
            return matrix

        def make_camera(name, focal):
            cam = UsdGeom.Camera.Define(stage, f"/World/Arena/RecordCam_{name}")
            cam.CreateFocalLengthAttr(focal)
            cam.CreateClippingRangeAttr(Gf.Vec2f(0.02, 100.0))
            op = UsdGeom.Xformable(cam).AddTransformOp()
            return str(cam.GetPath()), op

        top_path, top_op = make_camera("Top", 28.0)
        top_op.Set(camera_matrix(Gf.Vec3d(0.25, -3.4, 5.7), Gf.Vec3d(0, 0, 0.05)))

        follow_path, follow_op = make_camera("Follow", 24.0)
        gripper_path, gripper_op = make_camera("Gripper", 24.0)
        basket_path, basket_op = make_camera("Basket", 24.0)

        blue_goal = stage.GetPrimAtPath("/World/Arena/Baskets/TeamBlue_Goal")
        if blue_goal.IsValid() and blue_goal.GetAttribute("arena:basketCenter").IsValid():
            bc = blue_goal.GetAttribute("arena:basketCenter").Get()
            basket_x, basket_y = float(bc[0]), float(bc[1])
        else:
            # Fallback for a stage without baskets (e.g. the plain arena):
            # point at the manual robot's own half, near the centre line.
            print("[REC][WARN] No TeamBlue_Goal on this stage; basket-side "
                  "camera falls back to a generic point in Blue's half.",
                  flush=True)
            fallback_sign = robot_controls[MANUAL_ROBOT]["team_sign"]
            basket_x, basket_y = 0.3 * fallback_sign, 0.0
        basket_facing = robot_controls[MANUAL_ROBOT]["facing_sign"]
        basket_op.Set(camera_matrix(
            Gf.Vec3d(basket_x - basket_facing * 0.4, basket_y + 0.4, 0.35),
            Gf.Vec3d(basket_x, basket_y, 0.08),
        ))

        # 'net' camera: a fixed view across the net, aimed when it is switched
        # on (at ball attach) so it frames the lane the manual robot is in.
        # Eye on the manual robot's side of the net, 1.0 m up (clears the
        # outer walls), offset in Y toward the arena centre; target just past
        # the net at pass height so the arm reaching over and the ball
        # landing on the far side are both in frame.
        net_path, net_op = make_camera("Net", 24.0)

        def aim_net_camera():
            x, y = base_world_xy(MANUAL_ROBOT)
            side = robot_controls[MANUAL_ROBOT]["team_sign"]
            y_eye = y - 1.25 if y >= 0.0 else y + 1.25
            net_op.Set(camera_matrix(
                Gf.Vec3d(side * 1.15, y_eye, 1.0),
                Gf.Vec3d(-side * 0.10, y, 0.30),
            ))

        aim_net_camera()

        # Fixed presets from task_recording_presets.py (single source of
        # truth shared with docs/verification). In --record-task mode the
        # 'net' camera is ALSO a fixed preset (stable during the pass, no
        # attach trigger); the attach-aimed variant above stays for the
        # multi-camera --record-cameras mode.
        fixed_view_ops = {}
        for view_name in ("opponent_basket", "own_basket"):
            preset = task_presets.VIEWS[view_name]
            cam_path, cam_op = make_camera(view_name, preset["focal_mm"])
            stage.GetPrimAtPath(cam_path).GetAttribute("clippingRange").Set(
                Gf.Vec2f(*preset["clip"]))
            cam_op.Set(camera_matrix(Gf.Vec3d(*preset["eye"]), Gf.Vec3d(*preset["target"])))
            fixed_view_ops[view_name] = (cam_path, cam_op)
        task_mode = bool(args.record_task) or bool(args.preview_views)
        if task_mode:
            preset = task_presets.VIEWS["net"]
            stage.GetPrimAtPath(net_path).GetAttribute("focalLength").Set(preset["focal_mm"])
            net_op.Set(camera_matrix(Gf.Vec3d(*preset["eye"]), Gf.Vec3d(*preset["target"])))

        follow_damped = {"eye": None, "target": None}

        def update_follow_camera():
            x, y = base_world_xy(MANUAL_ROBOT)
            facing = robot_controls[MANUAL_ROBOT]["facing_sign"]
            want_eye = Gf.Vec3d(x - facing * 0.5, y, 0.6)
            want_target = Gf.Vec3d(x + facing * 0.15, y, 0.15)
            if follow_damped["eye"] is None:
                follow_damped["eye"], follow_damped["target"] = want_eye, want_target
            else:
                follow_damped["eye"] += (want_eye - follow_damped["eye"]) * 0.15
                follow_damped["target"] += (want_target - follow_damped["target"]) * 0.15
            follow_op.Set(camera_matrix(follow_damped["eye"], follow_damped["target"]))

        def update_gripper_camera():
            p = gripper_world_pos(MANUAL_ROBOT)
            if p is None:
                return
            facing = robot_controls[MANUAL_ROBOT]["facing_sign"]
            # World-axis offset from the gripper frame position (never the
            # gripper's rotating local frame), so the view keeps the same
            # relative framing when the base turns and never swings behind
            # the arm. Pulled back from 0.18/0.16/0.14 (2026-09-11): at that
            # distance the jaws filled the frame and a ball beside them was
            # cut off (preview stills, screenshots/task_views/gripper.png).
            eye = Gf.Vec3d(p[0] - facing * 0.26, p[1] + 0.24, p[2] + 0.20)
            target = Gf.Vec3d(p[0] + facing * 0.08, p[1], p[2] - 0.04)
            gripper_op.Set(camera_matrix(eye, target))

        # 'robot_top' recording camera: same base-tracking as the viewport
        # top-down camera but its own prim and framing (further back and a
        # little higher so the whole base stays in frame -- the viewport
        # camera crops the base bottom, see screenshots/task_views).
        robot_top_path, robot_top_op = make_camera("RobotTop", 16.0)
        stage.GetPrimAtPath(robot_top_path).GetAttribute("clippingRange").Set(Gf.Vec2f(0.05, 100.0))
        ROBOT_TOP_BACK, ROBOT_TOP_AHEAD, ROBOT_TOP_HEIGHT = 0.30, 0.35, 0.95

        def update_robot_top_camera():
            update_topdown_camera(MANUAL_ROBOT, op=robot_top_op, back=ROBOT_TOP_BACK,
                                  ahead=ROBOT_TOP_AHEAD, height=ROBOT_TOP_HEIGHT)

        # Shadows the module-level RECORD_CAMERA_NAMES constant for the rest
        # of main() (start_recording/capture_tick/_finalize_session etc. all
        # just reference the bare name, so this one rebind is enough to make
        # every one of them iterate only the selected subset) -- fewer
        # cameras means fewer render products/annotator readbacks per tick,
        # which is the actual bottleneck (see --record-cameras help text).
        RECORD_CAMERA_NAMES = tuple(args.record_cameras)

        record_res = (args.record_width, args.record_height)
        camera_paths = {
            "top": top_path,
            "blue1_follow": follow_path,
            "blue1_gripper": gripper_path,
            "basket_side": basket_path,
            "blue1_topdown": robot_top_path,
            "net": net_path,
            "opponent_basket": fixed_view_ops["opponent_basket"][0],
            "own_basket": fixed_view_ops["own_basket"][0],
        }
        # Live render products, keyed by camera name. A camera that is
        # selected but not in this dict is simply not rendered/captured
        # right now (capture_tick logs it as not ok). Render products are
        # created/destroyed at runtime so 'top' can be switched off after
        # --record-top-seconds and 'net' switched on at ball attach; a
        # freshly created product returns empty data for a tick or two.
        cameras = {}

        def activate_camera(name):
            if name in cameras or name not in RECORD_CAMERA_NAMES:
                return
            product = rep.create.render_product(camera_paths[name], record_res)
            annotator = rep.AnnotatorRegistry.get_annotator("rgb")
            annotator.attach([product])
            cameras[name] = {"product": product, "annotator": annotator}

        def deactivate_camera(name):
            entry = cameras.pop(name, None)
            if entry is None:
                return
            entry["annotator"].detach([entry["product"]])
            entry["product"].destroy()

        # Idle state: every selected camera except 'net' renders (as before),
        # so the first capture tick after a start has data immediately. In
        # task mode the single selected camera (net included, fixed preset)
        # is the only render product that ever exists; --preview-views
        # activates cameras one at a time itself.
        if not args.preview_views:
            for name in RECORD_CAMERA_NAMES:
                if name != "net" or task_mode:
                    activate_camera(name)

        record_dir = Path(args.record_dir).expanduser().resolve()
        record_dir.mkdir(parents=True, exist_ok=True)
        # Fixed control location regardless of where takes are written, so
        # record_start.sh / record_stop.sh keep working for --record-task
        # runs (whose record_dir is logs/task_recordings/<task>/<view>).
        pid_dir = PROJECT_ROOT / "logs/recording_sessions"
        pid_dir.mkdir(parents=True, exist_ok=True)
        pid_file = pid_dir / "current.pid"
        pid_file.write_text(str(os.getpid()))
        # Command file for record_mark.sh: one command per line ("marker
        # <name>"), read and truncated by the main loop every frame.
        cmd_file = pid_dir / "current.cmd"
        cmd_file.write_text("")

        def poll_command_file():
            try:
                if cmd_file.stat().st_size == 0:
                    return
                lines = cmd_file.read_text().splitlines()
                cmd_file.write_text("")
            except OSError:
                return
            for line in lines:
                parts = line.strip().split(maxsplit=1)
                if not parts:
                    continue
                if parts[0] == "marker" and len(parts) == 2 and parts[1] in MARKER_NAMES:
                    if recording["active"]:
                        emit_event("marker", parts[1])
                        print(f"[REC] marker: {parts[1]}", flush=True)
                    else:
                        print(f"[REC] marker '{parts[1]}' ignored: not recording", flush=True)
                else:
                    print(f"[REC] unknown command in {cmd_file.name}: {line!r}", flush=True)

        # --- Async save pipeline -------------------------------------
        # PNG encoding must never run on this process's own render thread
        # (the one calling app.update() / annotator.get_data()),
        # and must never block the keyboard/leader control loop. A single
        # writer thread drains a bounded queue; it only ever touches numpy
        # arrays already copied out of the annotator buffers and does
        # plain file I/O -- no omni/rep/carb call happens off the main
        # thread. ffmpeg encoding runs later, per session, in its own
        # finalize thread (see _finalize_session), so stopping one
        # recording and immediately starting the next never wait on each
        # other.
        write_queue = queue.Queue(maxsize=RECORD_QUEUE_MAXSIZE)
        pending_lock = threading.Lock()
        pending_counts: dict[str, int] = {}
        encode_stats_lock = threading.Lock()
        encode_stats: dict[str, dict[str, float]] = {}

        def _writer_loop():
            while True:
                item = write_queue.get()
                if item is None:
                    write_queue.task_done()
                    break
                session_id, frame_path, data = item
                t0 = time.perf_counter()
                try:
                    iio.imwrite(frame_path, data, plugin="pillow", compress_level=1)
                except Exception as exc:  # noqa: BLE001 -- log and move on, never crash the writer
                    print(f"[REC][WARN] failed to write {frame_path}: {exc}", flush=True)
                save_ms = (time.perf_counter() - t0) * 1000.0
                with encode_stats_lock:
                    stats = encode_stats.setdefault(
                        session_id, {"count": 0, "sum_ms": 0.0, "max_ms": 0.0}
                    )
                    stats["count"] += 1
                    stats["sum_ms"] += save_ms
                    stats["max_ms"] = max(stats["max_ms"], save_ms)
                with pending_lock:
                    pending_counts[session_id] = pending_counts.get(session_id, 1) - 1
                write_queue.task_done()

        writer_thread = [
            threading.Thread(target=_writer_loop, daemon=True, name=f"record-writer-{i}")
            for i in range(RECORD_WRITER_THREADS)
        ]
        for t in writer_thread:
            t.start()

        recording = {
            "active": False,
            "pending_commands": [],
            "session_dir": None,
            "session_id": None,
            "session_seq": 0,
            "frame_id": 0,
            "next_capture_at": 0.0,
            "capture_interval": 1.0 / max(args.record_fps, 0.1),
            "log_file": None,
            "csv_writer": None,
            "start_wall": None,
            "start_sim": None,
            "delayed_ticks": 0,
            "total_ticks": 0,
            "rows": [],
            "dropped": [],
            "cameras": cameras,
            "pid_file": pid_file,
            "finalize_threads": [],
        }

        # ------------------------------------------------------------ #
        # --data-collect: LeRobot-style per-step episode for Blue 1,
        # sharing the same start/stop signal and PNG writer-queue/thread
        # as the video recorder above (reusing write_queue/pending_lock/
        # pending_counts -- a generic (session_id, path, ndarray) sink,
        # not specific to the 4 cinematic cameras). Camera images use
        # DATASET_FINALIZE_TIMEOUT_SECONDS the same way video does: stop
        # waits for this episode's queued writes to drain before the
        # meta.json summary is written, so "episode saved" means the PNGs
        # actually landed on disk, not just that they were queued.
        # ------------------------------------------------------------ #
        dataset_cameras = {}
        dataset_dir = None
        if args.data_collect:
            manual_robot_path = ROBOTS[MANUAL_ROBOT]
            for name, parent_link in DATASET_CAMERAS:
                cam_path = f"{manual_robot_path}/{parent_link}/{name}"
                if not stage.GetPrimAtPath(cam_path).IsValid():
                    raise RuntimeError(
                        f"--data-collect requires {cam_path} to exist on this stage "
                        f"(expected a real {name} prim on {MANUAL_ROBOT})."
                    )
                product = rep.create.render_product(cam_path, record_res)
                annotator = rep.AnnotatorRegistry.get_annotator("rgb")
                annotator.attach([product])
                cam_prim = UsdGeom.Camera(stage.GetPrimAtPath(cam_path))
                dataset_cameras[name] = {
                    "product": product, "annotator": annotator, "path": cam_path,
                    "focal_length": float(cam_prim.GetFocalLengthAttr().Get()),
                    "horizontal_aperture": float(cam_prim.GetHorizontalApertureAttr().Get()),
                }
            dataset_dir = Path(args.dataset_dir).expanduser().resolve()
            dataset_dir.mkdir(parents=True, exist_ok=True)

        last_leader_raw = {"joints": None, "wall_time": None}

        dataset = {
            "active": False,
            "episode_dir": None,
            "episode_id": None,
            "episode_seq": 0,
            "step_id": 0,
            "next_capture_at": 0.0,
            "capture_interval": 1.0 / max(args.record_fps, 0.1),
            "steps_file": None,
            "start_wall": None,
            "start_sim": None,
            "dropped": 0,
            "last_meta_path": None,
            "finalize_threads": [],
        }

        def start_dataset_episode():
            if not args.data_collect or dataset["active"]:
                return
            dataset["episode_seq"] += 1
            episode_id = f"ep_{time.strftime('%Y%m%d_%H%M%S')}_{dataset['episode_seq']:03d}"
            episode_dir = dataset_dir / episode_id
            for name, _ in DATASET_CAMERAS:
                (episode_dir / "images" / name).mkdir(parents=True, exist_ok=True)
            steps_file = open(episode_dir / "steps.jsonl", "w")
            with pending_lock:
                pending_counts[f"ds_{episode_id}"] = 0
            dataset.update(
                active=True, episode_dir=episode_dir, episode_id=episode_id,
                step_id=0, next_capture_at=time.monotonic(), steps_file=steps_file,
                start_wall=time.monotonic(), start_sim=timeline.get_current_time(),
                dropped=0,
            )
            print(f"[DATA] episode started -> {episode_dir}", flush=True)

        def _joint_state_deg(label):
            control = robot_controls[label]
            out = {}
            for key, prim in control["arm_joint_prims"].items():
                attr = prim.GetAttribute("state:angular:physics:position")
                out[key] = float(attr.Get()) if attr.IsValid() and attr.Get() is not None else None
            return out

        def dataset_capture_tick():
            if not dataset["active"]:
                return
            now = time.monotonic()
            if now < dataset["next_capture_at"]:
                return
            step_id = dataset["step_id"]
            sim_time = timeline.get_current_time()
            episode_dir = dataset["episode_dir"]
            episode_id = dataset["episode_id"]
            session_key = f"ds_{episode_id}"
            frame_paths = {}
            for name, _ in DATASET_CAMERAS:
                data = dataset_cameras[name]["annotator"].get_data()
                ok = data is not None and getattr(data, "size", 0) > 0
                if not ok:
                    frame_paths[name] = None
                    continue
                frame_path = episode_dir / "images" / name / f"frame_{step_id:06d}.png"
                try:
                    with pending_lock:
                        pending_counts[session_key] = pending_counts.get(session_key, 0) + 1
                        try:
                            write_queue.put_nowait((session_key, frame_path, data[..., :3].copy()))
                        except queue.Full:
                            pending_counts[session_key] -= 1
                            raise
                    frame_paths[name] = str(frame_path.relative_to(episode_dir))
                except queue.Full:
                    dataset["dropped"] += 1
                    frame_paths[name] = None

            control = robot_controls[MANUAL_ROBOT]
            bx, by = base_world_xy(MANUAL_ROBOT)
            transform = UsdGeom.Xformable(
                control["base_prim"]
            ).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
            forward = transform.TransformDir(Gf.Vec3d(1.0, 0.0, 0.0))
            base_yaw_deg = math.degrees(math.atan2(forward[1], forward[0]))
            vel = control["velocity"].Get()
            ang = control["angular"].Get()
            is_manual_now = labels[active_index] == MANUAL_ROBOT
            leader_fresh = (
                last_leader_raw["wall_time"] is not None
                and now - last_leader_raw["wall_time"] <= args.leader_timeout
            )
            record = {
                "step_id": step_id,
                "sim_time": sim_time,
                "wall_time": now,
                "control_mode": "teleop_blue1" if (is_manual_now and leader_fresh) else (
                    "blue1_active_no_leader" if is_manual_now else "blue1_not_active"
                ),
                "images": frame_paths,
                "base_state": {"x": bx, "y": by, "yaw_deg": base_yaw_deg},
                "base_action": {
                    "vx_mps": float(vel[0]), "vy_mps": float(vel[1]), "wz_degps": float(ang[2]),
                },
                "arm_state_deg": _joint_state_deg(MANUAL_ROBOT),
                "arm_action_deg": dict(control["last_targets"]),
                "leader_raw": dict(last_leader_raw["joints"]) if last_leader_raw["joints"] else None,
            }
            dataset["steps_file"].write(json.dumps(record) + "\n")
            dataset["steps_file"].flush()
            dataset["step_id"] += 1
            dataset["next_capture_at"] = max(now, dataset["next_capture_at"] + dataset["capture_interval"])

        def _finalize_dataset_episode(episode_id, episode_dir, step_count, duration, start_wall, dropped, outcome):
            deadline = time.monotonic() + DATASET_FINALIZE_TIMEOUT_SECONDS
            session_key = f"ds_{episode_id}"
            remaining = 0
            while time.monotonic() < deadline:
                with pending_lock:
                    remaining = pending_counts.get(session_key, 0)
                if remaining <= 0:
                    break
                time.sleep(0.05)
            else:
                print(f"[DATA][WARN] {episode_id}: gave up waiting for {remaining} queued "
                      f"frame(s) after {DATASET_FINALIZE_TIMEOUT_SECONDS:.0f}s", flush=True)
            with pending_lock:
                pending_counts.pop(session_key, None)
            meta = {
                "episode_id": episode_id,
                "arena_stage": str(stage_path),
                "robot_look": "confirmed_6D2077_arm_151515_base" if "_confirmed" in stage_path.name else "unconfirmed",
                "control_mode": "Blue 1: keyboard base + SO-101 leader arm teleop",
                "scripted_attach": bool(args.scripted_attach),
                "scripted_attach_note": ("balls were glued to any mostly-closed gripper near them "
                                         "(NOT physics grasping); do not treat lifts in this episode "
                                         "as real grasp demonstrations") if args.scripted_attach else None,
                "outcome": outcome,
                "step_count": step_count,
                "dropped_frames": dropped,
                "record_fps_target": args.record_fps,
                "duration_seconds": duration,
                "start_wall": start_wall,
                "start_sim": dataset["start_sim"],
                "cameras": {
                    name: {"prim_path": info["path"], "focal_length_mm": info["focal_length"],
                           "horizontal_aperture_mm": info["horizontal_aperture"],
                           "resolution": list(record_res)}
                    for name, info in dataset_cameras.items()
                },
                "joint_order_arm_deg": [k for k in ARM_JOINTS if k != "gripper.pos"],
                "gripper_key": "gripper.pos",
                "action_units": "degrees (absolute joint position target, physics:position convention)",
                "action_type": "absolute",
                "base_action_units": "vx/vy in m/s (world frame), wz in deg/s",
                "leader_raw_units": "degrees or 0-100 percent depending on joint, exactly as received "
                                     "from leader_sender.py before this script's offset/limit mapping",
                "ball_physics": {
                    "diameter_m": 2.0 * float(ball_geom.GetRadiusAttr().Get()),
                    "friction_static": ball_material.GetStaticFrictionAttr().Get(),
                    "friction_dynamic": ball_material.GetDynamicFrictionAttr().Get(),
                    "restitution": ball_material.GetRestitutionAttr().Get(),
                },
                "notes": "control_mode is per-step: 'teleop_blue1' only when Blue 1 is the active "
                         "robot AND a leader packet arrived within --leader-timeout; other values "
                         "mark steps that are NOT a valid expert demonstration and should be "
                         "excluded from imitation-learning targets.",
            }
            meta_path = episode_dir / "meta.json"
            meta_path.write_text(json.dumps(meta, indent=2))
            dataset["last_meta_path"] = meta_path
            print(f"[DATA] episode finalized -> {meta_path} ({step_count} steps, "
                  f"{dropped} dropped, outcome={outcome})", flush=True)

        def _discard_dataset_episode(episode_id, episode_dir):
            """다시 찍기: 큐에 남은 프레임이 빠질 때까지 기다린 뒤 에피소드 폴더를 지운다.

            기다리지 않고 바로 지우면 이미지 기록 스레드가 없어진 폴더에 쓰다가 예외를 던진다
            (_finalize_dataset_episode 와 같은 대기 패턴).
            """
            deadline = time.monotonic() + DATASET_FINALIZE_TIMEOUT_SECONDS
            session_key = f"ds_{episode_id}"
            while time.monotonic() < deadline:
                with pending_lock:
                    if pending_counts.get(session_key, 0) <= 0:
                        break
                time.sleep(0.05)
            with pending_lock:
                pending_counts.pop(session_key, None)
            shutil.rmtree(episode_dir, ignore_errors=True)
            print(f"[DATA] 에피소드 폐기 -> {episode_dir.name} (다시 찍기)", flush=True)

        def stop_dataset_episode(outcome="unmarked", discard=False):
            if not args.data_collect or not dataset["active"]:
                return
            if discard:
                dataset["active"] = False
                dataset["steps_file"].close()
                # 같은 번호를 다시 쓴다 — 폐기한 에피소드가 번호를 먹지 않게 한다.
                dataset["episode_seq"] -= 1
                t = threading.Thread(
                    target=_discard_dataset_episode,
                    args=(dataset["episode_id"], dataset["episode_dir"]),
                    daemon=True, name=f"dataset-discard-{dataset['episode_id']}",
                )
                t.start()
                dataset["finalize_threads"].append(t)
                return
            dataset["active"] = False
            dataset["steps_file"].close()
            episode_id = dataset["episode_id"]
            episode_dir = dataset["episode_dir"]
            step_count = dataset["step_id"]
            duration = time.monotonic() - dataset["start_wall"]
            dropped = dataset["dropped"]
            print(f"[DATA] stopping: {step_count} steps over {duration:.1f}s, {dropped} dropped. "
                  "Finalizing in the background.", flush=True)
            t = threading.Thread(
                target=_finalize_dataset_episode,
                args=(episode_id, episode_dir, step_count, duration, dataset["start_wall"], dropped, outcome),
                daemon=True, name=f"dataset-finalize-{episode_id}",
            )
            t.start()
            dataset["finalize_threads"].append(t)

        def mark_last_episode_outcome(outcome):
            meta_path = dataset["last_meta_path"]
            if meta_path is None or not meta_path.is_file():
                print("[DATA] no finalized episode to mark yet", flush=True)
                return
            meta = json.loads(meta_path.read_text())
            meta["outcome"] = outcome
            meta_path.write_text(json.dumps(meta, indent=2))
            print(f"[DATA] {meta_path.parent.name}: outcome marked '{outcome}'", flush=True)

        # A single ordered queue, not two independent booleans: a rapid
        # stop-then-start (SIGUSR2 immediately followed by SIGUSR1, e.g. an
        # operator re-arming a new take right after ending the last one) can
        # deliver both signals before the main loop's next iteration. Two
        # separate flags always checked in the same start-then-stop order
        # would silently drop that start request (recording still looks
        # "active" because the stop hasn't run yet) -- confirmed by an
        # actual back-to-back USR2/USR1 test, see CLAUDE_REVIEW.md. list.append
        # from a signal handler is safe: CPython list.append is atomic under
        # the GIL.
        def _on_sigusr1(_signum, _frame):
            recording["pending_commands"].append("start")

        def _on_sigusr2(_signum, _frame):
            recording["pending_commands"].append("stop")

        signal.signal(signal.SIGUSR1, _on_sigusr1)
        signal.signal(signal.SIGUSR2, _on_sigusr2)

        def start_recording():
            if recording["active"]:
                print("[REC] already recording; ignoring start request", flush=True)
                return
            recording["session_seq"] += 1
            if task_mode:
                session_id = f"{time.strftime('%Y%m%d_%H%M%S')}_take{recording['session_seq']:03d}"
            else:
                session_id = f"rec_{time.strftime('%Y%m%d_%H%M%S')}_{recording['session_seq']:03d}"
            session_dir = record_dir / session_id
            free_gb = shutil.disk_usage(record_dir).free / 1e9
            if free_gb < RECORD_MIN_FREE_DISK_GB:
                print(f"[REC][WARN] only {free_gb:.1f} GB free under {record_dir} -- "
                      f"PNG frames need ~1.5 GB per minute per 1280x720 camera at ~18 fps", flush=True)
            for name in RECORD_CAMERA_NAMES:
                (session_dir / "frames" / name).mkdir(parents=True, exist_ok=True)
            log_file = open(session_dir / "frame_log.csv", "w", newline="")
            writer = csv.writer(log_file)
            writer.writerow(
                ["frame_id", "sim_time", "wall_time", "capture_ms", "render_ms", "readback_ms"]
                + [f"{n}_ok" for n in RECORD_CAMERA_NAMES]
                + [f"{n}_queued" for n in RECORD_CAMERA_NAMES]
            )
            with pending_lock:
                pending_counts[session_id] = 0
            start_wall = time.monotonic()
            # 'top' may have been switched off by --record-top-seconds in a
            # previous take; 'net' waits for the first ball attach in the
            # multi-camera mode but is the (fixed) take camera in task mode.
            for name in RECORD_CAMERA_NAMES:
                if name != "net" or task_mode:
                    activate_camera(name)
            recording.update(
                active=True,
                session_dir=session_dir,
                session_id=session_id,
                frame_id=0,
                next_capture_at=start_wall,
                log_file=log_file,
                csv_writer=writer,
                start_wall=start_wall,
                start_sim=timeline.get_current_time(),
                delayed_ticks=0,
                total_ticks=0,
                rows=[],
                dropped=[],
                top_deadline=(start_wall + args.record_top_seconds
                              if args.record_top_seconds > 0 and "top" in RECORD_CAMERA_NAMES
                              else None),
            )
            recording["drop_warned_at"] = 0.0
            # events.csv: operator markers / resets / attach etc. with the
            # frame counter and both clocks, so an editor can find them.
            events_file = open(session_dir / "events.csv", "w", newline="")
            events_writer = csv.writer(events_file)
            events_writer.writerow(["frame_id", "sim_time", "wall_time", "event", "detail"])
            recording["events_file"] = events_file
            recording["events_writer"] = events_writer
            recording["events"] = []
            recording["take"] = task_take_metadata(session_id, session_dir, start_wall) if task_mode else None
            if task_mode:
                (session_dir / "metadata.json").write_text(json.dumps(recording["take"], indent=2))
            _write_event("take_start", "")
            print(f"[REC] recording started -> {session_dir} "
                  f"(live cameras: {', '.join(n for n in RECORD_CAMERA_NAMES if n in cameras)})",
                  flush=True)

        def _write_event(name, detail):
            if not recording["active"] or recording.get("events_writer") is None:
                return
            row = [recording["frame_id"], f"{timeline.get_current_time():.6f}",
                   f"{time.monotonic():.6f}", name, detail]
            recording["events_writer"].writerow(row)
            recording["events_file"].flush()
            recording["events"].append({"frame_id": row[0], "sim_time": float(row[1]),
                                        "wall_time": float(row[2]), "event": name, "detail": detail})

        event_sinks.append(_write_event)

        stage_sha256 = hashlib.sha256(stage_path.read_bytes()).hexdigest()

        def task_take_metadata(session_id, session_dir, start_wall):
            view = args.record_view
            preset = dict(task_presets.VIEWS[view]) if view else {}
            return {
                "task": args.record_task,
                "view": view,
                "take_id": session_id,
                "take_dir": str(session_dir),
                "stage": str(stage_path),
                "stage_sha256": stage_sha256,
                "robot": MANUAL_ROBOT,
                "control": "manual teleoperation (keyboard base + SO-101 leader arm/gripper)",
                "camera": preset.get("camera"),
                "camera_preset": preset,
                "resolution": list(record_res),
                "target_fps": args.record_fps,
                "wall_start_epoch": time.time(),
                "wall_start_monotonic": start_wall,
                "sim_start": timeline.get_current_time(),
                "command": " ".join(sys.argv),
                "clean_shutdown": False,
                "notes": "Markers are operator annotations, not physics verdicts. "
                         "Demo/rules footage only; not a training dataset.",
            }

        def _on_attach_for_net_camera(label, _ball_path):
            if label != MANUAL_ROBOT or not recording["active"]:
                return
            if "net" not in RECORD_CAMERA_NAMES or "net" in cameras:
                return
            aim_net_camera()
            activate_camera("net")
            print("[REC] 'net' camera switched on (ball attached)", flush=True)

        if not task_mode:
            attach_listeners.append(_on_attach_for_net_camera)
        attach_listeners.append(lambda label, ball_path: emit_event("attach", f"{label}:{ball_path}"))

        def _finalize_session(session_id, session_dir, rows, dropped, duration, achieved_fps, start_wall,
                              take=None, events=(), sim_end=None):
            """Runs on its own thread: waits for this session's queued PNG
            writes to drain, then encodes each camera with ffmpeg (parallel
            Popen, not subprocess.run) using each frame's *actual* measured
            wall-clock gap as its display duration -- never a flat assumed
            fps -- and skipping any frame whose PNG never actually landed on
            disk instead of relying on the capture-time 'ok' flag alone.
            Never touches an omni/rep/carb API, so it is safe to run
            concurrently with the next recording session's capture ticks.
            """
            deadline = time.monotonic() + RECORD_FINALIZE_TIMEOUT_SECONDS
            remaining = 0
            while time.monotonic() < deadline:
                with pending_lock:
                    remaining = pending_counts.get(session_id, 0)
                if remaining <= 0:
                    break
                time.sleep(0.05)
            else:
                print(
                    f"[REC][WARN] {session_id}: gave up waiting for {remaining} queued "
                    "frame(s) to finish saving after "
                    f"{RECORD_FINALIZE_TIMEOUT_SECONDS:.0f}s; encoding whatever is on disk.",
                    flush=True,
                )
            with pending_lock:
                pending_counts.pop(session_id, None)

            summary = {
                "session_id": session_id,
                "target_fps": args.record_fps,
                "achieved_fps": achieved_fps,
                "frames": len(rows),
                "duration_seconds": duration,
                "start_wall": start_wall,
                "end_wall": start_wall + duration,
                "dropped_frames": dropped,
                "resolution": list(record_res),
                "cameras": {},
            }

            pending_encodes = {}
            for name in RECORD_CAMERA_NAMES:
                ok_rows = [r for r in rows if r.get(f"{name}_ok") and r.get(f"{name}_queued")]
                existing = []
                for r in ok_rows:
                    frame_path = session_dir / "frames" / name / f"frame_{r['frame_id']:06d}.png"
                    if frame_path.is_file():
                        existing.append((r, frame_path))
                missing_on_disk = len(ok_rows) - len(existing)
                if not existing:
                    print(f"[REC] {name}: 0 usable frames, skipping encode", flush=True)
                    summary["cameras"][name] = {
                        "frames": 0, "missing_on_disk": missing_on_disk, "encoded": False,
                    }
                    continue
                # ffmpeg's image2 sequential-number demuxer stops at the
                # first missing frame number, so build an explicit concat
                # list instead: it tolerates gaps (missing frame ids are
                # simply absent from the list) and each `duration` line
                # carries that frame's real measured gap to the next
                # *actually captured* frame for this camera, preserving
                # variable inter-frame timing instead of a flat fps.
                concat_path = session_dir / f"{name}_concat.txt"
                lines = []
                # Every camera shares the session origin, even when its first
                # frame is missing. Explicit black padding is not invented imagery.
                import numpy as np
                padding = max(0.0, existing[0][0]["wall_time"] - start_wall)
                if padding > 0.001:
                    black_path = session_dir / f"{name}_leading_gap.png"
                    iio.imwrite(black_path, np.zeros((record_res[1], record_res[0], 3), dtype=np.uint8))
                    lines.extend([f"file '{black_path.as_posix()}'", f"duration {padding:.6f}"])
                for i, (r, frame_path) in enumerate(existing):
                    if i + 1 < len(existing):
                        dur = max(1.0 / 120.0, existing[i + 1][0]["wall_time"] - r["wall_time"])
                    else:
                        dur = max(0.001, start_wall + duration - r["wall_time"])
                    lines.append(f"file '{frame_path.as_posix()}'")
                    lines.append(f"duration {dur:.6f}")
                # concat demuxer quirk: the last `duration` is ignored unless
                # the file line is repeated once more after it.
                lines.append(f"file '{existing[-1][1].as_posix()}'")
                concat_path.write_text("\n".join(lines) + "\n")
                # Task takes hold exactly one camera: the wall-clock video is
                # video.mp4 (video_simtime.mp4 is added below).
                out_path = session_dir / ("video.mp4" if take is not None else f"{name}.mp4")
                cmd = [
                    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_path),
                    "-vsync", "vfr", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-preset", "veryfast", "-crf", "16",
                    str(out_path), "-loglevel", "error",
                ]
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                pending_encodes[name] = (proc, out_path, len(existing), missing_on_disk)

            for name, (proc, out_path, frame_count, missing_on_disk) in pending_encodes.items():
                _, stderr = proc.communicate()
                ok = proc.returncode == 0 and out_path.is_file()
                summary["cameras"][name] = {
                    "frames": frame_count,
                    "missing_on_disk": missing_on_disk,
                    "encoded": ok,
                    "path": str(out_path),
                }
                print(f"[REC] {name}: {frame_count} frames ({missing_on_disk} missing) -> "
                      f"{'OK' if ok else 'FAILED'} {out_path}", flush=True)
                if not ok and stderr:
                    print(stderr[-1500:], flush=True)

            with encode_stats_lock:
                stats = encode_stats.pop(session_id, None)
            if stats and stats["count"]:
                summary["save_ms"] = {
                    "avg": stats["sum_ms"] / stats["count"],
                    "max": stats["max_ms"],
                    "count": stats["count"],
                }

            (session_dir / "capture_summary.json").write_text(json.dumps(summary, indent=2))
            print(f"[REC] session finalized -> {session_dir / 'capture_summary.json'}", flush=True)

            if take is not None:
                # --- video_simtime.mp4: same frames, but each frame is shown
                # for its measured SIMULATION-time gap (the real speed of the
                # simulated motion). video.mp4 above uses wall-clock gaps and
                # looks like slow motion whenever the sim ran below real time.
                name = take["camera"]
                ok_rows = [r for r in rows if r.get(f"{name}_ok") and r.get(f"{name}_queued")]
                existing = [(r, session_dir / "frames" / name / f"frame_{r['frame_id']:06d}.png")
                            for r in ok_rows]
                existing = [(r, p) for r, p in existing if p.is_file()]
                simtime_ok = False
                if existing:
                    lines = []
                    for i, (r, p) in enumerate(existing):
                        if i + 1 < len(existing):
                            dur = max(1.0 / 120.0, existing[i + 1][0]["sim_time"] - r["sim_time"])
                        else:
                            dur = 1.0 / 30.0
                        lines.append(f"file '{p.as_posix()}'")
                        lines.append(f"duration {dur:.6f}")
                    lines.append(f"file '{existing[-1][1].as_posix()}'")
                    concat_sim = session_dir / "video_simtime_concat.txt"
                    concat_sim.write_text("\n".join(lines) + "\n")
                    out_sim = session_dir / "video_simtime.mp4"
                    # Constant 60 fps output: the single-camera capture lands
                    # ~60 frames per simulated second (sim runs well below
                    # real time), and a vfr encode would fold those onto a
                    # 25 fps timebase and silently discard most of them.
                    proc = subprocess.run(
                        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_sim),
                         "-vsync", "cfr", "-r", "60", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                         "-preset", "veryfast", "-crf", "16",
                         str(out_sim), "-loglevel", "error"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    )
                    simtime_ok = proc.returncode == 0 and out_sim.is_file()
                    print(f"[REC] video_simtime.mp4 -> {'OK' if simtime_ok else 'FAILED'}", flush=True)
                    if not simtime_ok and proc.stderr:
                        print(proc.stderr[-1500:], flush=True)
                cam = summary["cameras"].get(name, {})
                saved = int(cam.get("frames", 0))
                sim_duration = (sim_end - take["sim_start"]) if sim_end is not None else None
                take.update({
                    "wall_end_epoch": take["wall_start_epoch"] + duration,
                    "wall_duration_seconds": duration,
                    "sim_end": sim_end,
                    "sim_duration_seconds": sim_duration,
                    "capture_ticks": len(rows),
                    "frames_saved": saved,
                    "frames_dropped_queue_full": len(dropped),
                    "frames_ok_but_missing_on_disk": int(cam.get("missing_on_disk", 0)),
                    "capture_fps_achieved": achieved_fps,
                    "save_fps_achieved": (saved / duration) if duration > 0 else 0.0,
                    "sim_frames_per_sim_second": (saved / sim_duration) if sim_duration else None,
                    "video_wallclock": str(session_dir / "video.mp4") if cam.get("encoded") else None,
                    "video_simtime": str(session_dir / "video_simtime.mp4") if simtime_ok else None,
                    "encoded_ok": bool(cam.get("encoded")) and simtime_ok,
                    "events": list(events),
                    "clean_shutdown": True,
                })
                (session_dir / "metadata.json").write_text(json.dumps(take, indent=2))
                print(f"[REC] take metadata -> {session_dir / 'metadata.json'}", flush=True)

        def stop_recording():
            if not recording["active"]:
                print("[REC] not recording; ignoring stop request", flush=True)
                return
            _write_event("take_stop", "")
            recording["active"] = False
            recording["log_file"].close()
            if recording.get("events_file") is not None:
                recording["events_file"].close()
                recording["events_file"] = None
                recording["events_writer"] = None
            session_id = recording["session_id"]
            session_dir = recording["session_dir"]
            rows = recording["rows"]
            dropped = recording["dropped"]
            duration = time.monotonic() - recording["start_wall"]
            sim_duration = timeline.get_current_time() - recording["start_sim"]
            n = recording["frame_id"]
            achieved_fps = n / duration if duration > 0 else 0.0
            print(
                f"[REC] stopping: {n} frames captured over {duration:.1f}s wall / "
                f"{sim_duration:.1f}s sim (target {args.record_fps:.1f} fps, achieved "
                f"{achieved_fps:.2f} fps, {recording['delayed_ticks']}/{recording['total_ticks']} "
                f"capture ticks over budget, {len(dropped)} frame(s) dropped for a full save "
                "queue). Finalizing in the background -- teleop keeps running.",
                flush=True,
            )
            finalize_thread = threading.Thread(
                target=_finalize_session,
                args=(session_id, session_dir, rows, dropped, duration, achieved_fps, recording["start_wall"],
                      recording.get("take"), list(recording.get("events", [])),
                      timeline.get_current_time()),
                daemon=True,
                name=f"record-finalize-{session_id}",
            )
            finalize_thread.start()
            recording["finalize_threads"].append(finalize_thread)
            # Multi-camera mode: 'net' is take-scoped, off until the next
            # take's ball attach. Task mode keeps its single camera alive.
            if "net" in cameras and not task_mode:
                deactivate_camera("net")
                print("[REC] 'net' camera switched off (take ended)", flush=True)

        def capture_tick():
            if not recording["active"]:
                return
            now = time.monotonic()
            deadline = recording.get("top_deadline")
            if deadline is not None and now >= deadline and "top" in cameras:
                deactivate_camera("top")
                recording["top_deadline"] = None
                print(f"[REC] 'top' camera switched off after {args.record_top_seconds:.0f}s", flush=True)
            if now < recording["next_capture_at"]:
                return
            tick_start = time.perf_counter()
            # Annotators are updated by normal app rendering (capture-on-play).
            # No orchestrator step, nested app updates, or timeline ownership.
            render_ms = recording.get("last_app_update_ms", 0.0)
            frame_id = recording["frame_id"]
            sim_time = timeline.get_current_time()
            session_dir = recording["session_dir"]
            session_id = recording["session_id"]
            per_cam_ok = {}
            per_cam_queued = {}
            readback_ms = 0.0
            # Rotate the capture order every tick so that when the save queue
            # is full the drops are spread across cameras instead of always
            # hitting whichever camera comes last (first FHD take:
            # top 95% / follow 65% / gripper 35% / basket 22% kept).
            rot = frame_id % len(RECORD_CAMERA_NAMES)
            for name in RECORD_CAMERA_NAMES[rot:] + RECORD_CAMERA_NAMES[:rot]:
                if name not in recording["cameras"]:
                    # Not live right now ('top' past its deadline, 'net'
                    # before the first attach): logged as not ok, no drop.
                    per_cam_ok[name] = False
                    per_cam_queued[name] = False
                    continue
                rb_start = time.perf_counter()
                data = recording["cameras"][name]["annotator"].get_data()
                readback_ms += (time.perf_counter() - rb_start) * 1000.0
                ok = data is not None and getattr(data, "size", 0) > 0
                per_cam_ok[name] = ok
                queued = False
                if ok:
                    # Copy now, on the main/render thread: the annotator's
                    # buffer can be overwritten by the next get_data() call
                    # before the writer thread ever looks at it.
                    frame_path = session_dir / "frames" / name / f"frame_{frame_id:06d}.png"
                    try:
                        with pending_lock:
                            pending_counts[session_id] = pending_counts.get(session_id, 0) + 1
                            try:
                                write_queue.put_nowait((session_id, frame_path, data[..., :3].copy()))
                            except queue.Full:
                                pending_counts[session_id] -= 1
                                raise
                        queued = True
                    except queue.Full:
                        recording["dropped"].append(
                            {"frame_id": frame_id, "camera": name, "wall_time": now}
                        )
                        if now - recording.get("drop_warned_at", 0.0) >= 2.0:
                            recording["drop_warned_at"] = now
                            print(f"[REC][WARN] save queue full ({RECORD_QUEUE_MAXSIZE} frames "
                                  f"waiting): {len(recording['dropped'])} frame(s) dropped so far "
                                  "-- lower --record-fps or the resolution", flush=True)
                per_cam_queued[name] = queued
            capture_ms = (time.perf_counter() - tick_start) * 1000.0
            recording["csv_writer"].writerow(
                [frame_id, sim_time, now, f"{capture_ms:.1f}", f"{render_ms:.1f}", f"{readback_ms:.1f}"]
                + [int(per_cam_ok[n]) for n in RECORD_CAMERA_NAMES]
                + [int(per_cam_queued[n]) for n in RECORD_CAMERA_NAMES]
            )
            row = {"frame_id": frame_id, "sim_time": sim_time, "wall_time": now}
            row.update({f"{n}_ok": per_cam_ok[n] for n in RECORD_CAMERA_NAMES})
            row.update({f"{n}_queued": per_cam_queued[n] for n in RECORD_CAMERA_NAMES})
            recording["rows"].append(row)
            recording["total_ticks"] += 1
            if capture_ms / 1000.0 > recording["capture_interval"]:
                recording["delayed_ticks"] += 1
            recording["frame_id"] += 1
            recording["next_capture_at"] = max(
                now, recording["next_capture_at"] + recording["capture_interval"]
            )

    timeline = omni.timeline.get_timeline_interface()
    if recording is not None:
        rep.orchestrator.set_capture_on_play(True)
        timeline.set_looping(False)
        timeline.set_end_time(max(timeline.get_end_time(), 86400.0))
    timeline.play()
    for _ in range(10):
        app.update()

    # Declared before select_robot(0) below: select_robot reads
    # leader_announced (to re-activate arm drives when switching robots
    # mid-session), so it must already exist in this scope by then.
    last_leader_at = 0.0
    leader_announced = False

    print("=" * 72, flush=True)
    print("Four-LeKiwi switchable teleoperation ready", flush=True)
    if args.record:
        print(f"RECORDING MODE: {MANUAL_ROBOT} is manual-only, T/F disabled", flush=True)
        print("Other 3 robots wander at low speed until Q stops everything", flush=True)
        print(f"Start/stop recording from another terminal: "
              f"kill -USR1/-USR2 $(cat {recording['pid_file']})", flush=True)
        print("(or use ./record_start.sh / ./record_stop.sh)", flush=True)
        if args.data_collect:
            print(f"DATA COLLECTION ON: each start/stop also writes a Blue-1 training "
                  f"episode under {dataset_dir}", flush=True)
            print("K=mark last finalized episode SUCCESS  L=FAILURE  J=ABORTED "
                  "(defaults to 'unmarked' if you skip this)", flush=True)
    else:
        print("T=next robot  F=previous robot (also switches the top-down camera)", flush=True)
    print("W/S=forward/back  A/D=strafe  Z/X=rotate  Q=stop all  R=resume background",
          flush=True)
    print("G=glue the nearest ball (<=0.25 m from the gripper) to the selected robot's "
          "gripper / press again to drop -- scripted, NOT a physics grasp", flush=True)
    print("B=reset all balls to spawn positions (base/robot poses are not reset)",
          flush=True)
    print("V=toggle viewport between the selected robot's top-down camera (default) "
          "and the whole-arena overview", flush=True)
    if args.ai_mode:
        print("", flush=True)
        print("AI MODE: non-manual robots run a scripted SEARCH/APPROACH/ARM_UP/DESCEND/"
              "CLOSE/LIFT/VERIFY/PLACE/RETREAT ball-grasp-attempt state machine (simulator "
              "ground-truth ball positions + numerical IK -- NOT a trained policy). "
              "State changes print as [AI] <robot>: <old> -> <new>.", flush=True)
    else:
        print("Idle robots wander randomly; arm relaxes until the leader connects.", flush=True)
    print(f"Leader: {args.endpoint}  ROS_DOMAIN_ID=72", flush=True)
    print("Scoring reminder: a WHITE ball in your own basket is -4, not a score; "
          "YELLOW in your own basket is +3. No auto-scoring in this build.",
          flush=True)
    select_robot(active_index)
    print("=" * 72, flush=True)

    was_focused = True
    started_at = time.monotonic()
    period = 1.0 / max(args.fps, 1.0)
    diag_next_at = 0.0
    ai_diag_next_at = 0.0
    if args.preview_views:
        # One still per camera-view preset, cameras activated one at a time
        # (never more than one recording render product alive), then exit.
        preview_dir = Path(args.preview_views).expanduser().resolve()
        preview_dir.mkdir(parents=True, exist_ok=True)
        for _ in range(5):
            app.update()
        for view_name in task_presets.VIEW_ORDER:
            cam_name = task_presets.VIEWS[view_name]["camera"]
            for lbl in ROBOTS:
                update_topdown_camera(lbl)
            update_follow_camera()
            update_gripper_camera()
            update_robot_top_camera()
            activate_camera(cam_name)
            data = None
            for _ in range(8):
                app.update()
                data = cameras[cam_name]["annotator"].get_data()
            deactivate_camera(cam_name)
            if data is None or getattr(data, "size", 0) == 0:
                print(f"[PREVIEW] {view_name}: blank render (FAILED)", flush=True)
                continue
            out_png = preview_dir / f"{view_name}.png"
            iio.imwrite(out_png, data[..., :3])
            print(f"[PREVIEW] {view_name} ({cam_name}) -> {out_png}", flush=True)
        timeline.stop()
        app.close()
        return

    debug_g_times = sorted(float(s) for s in args.debug_press_g.split(",") if s.strip())
    try:
        while app.is_running() and not stop_requested:
            frame_started = time.perf_counter()

            if app_window is not None:
                now_focused = app_window.is_focused()
                if was_focused and not now_focused:
                    pressed_keys.clear()
                    active_control = robot_controls[labels[active_index]]
                    active_control["velocity"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                    active_control["angular"].Set(Gf.Vec3f(0.0, 0.0, 0.0))
                    print("[INPUT] window lost focus; manual driving input released",
                          flush=True)
                was_focused = now_focused

            newest = receive_latest(subscriber)
            if newest is not None:
                last_leader_at = time.monotonic()
                if args.data_collect:
                    # Raw leader input, stored separately from the applied
                    # action (arm_action_deg in dataset_capture_tick): this
                    # is exactly what left the leader arm before this
                    # script's wrist_roll offset / gripper-limit mapping /
                    # per-tick max-step rate limiting were applied.
                    last_leader_raw["joints"] = dict(newest.joints)
                    last_leader_raw["wall_time"] = last_leader_at
                if not leader_announced:
                    print("Leader stream received; arm control active.", flush=True)
                    leader_announced = True
                    activate_arm_drives(labels[active_index])
                    start_connect_blend(labels[active_index])
                apply_arm(newest)
            elif leader_announced and time.monotonic() - last_leader_at > args.leader_timeout:
                leader_announced = False
                print("[WARN] Leader stream stale; arm holds last safe target.", flush=True)

            apply_base_commands()
            if debug_g_times and time.monotonic() - started_at >= debug_g_times[0]:
                debug_g_times.pop(0)
                print(f"[DEBUG] simulated G press for {labels[active_index]}", flush=True)
                manual_attach_toggle(labels[active_index])
            if args.auto_base:
                update_auto_base(timeline.get_current_time())
            if args.ai_mode:
                # Simulation clock, not wall clock: with --record at 1280x720
                # the loop ran at ~13 Hz, i.e. the sim advanced at ~1/5 real
                # time, and wall-clock state timeouts (LIFT 4 s) expired after
                # <1 s of simulated motion. Timeouts, cooldowns and the deg/s
                # rate limits below are all in simulated seconds now.
                update_ai_robots(timeline.get_current_time())
                now_mono_ai = time.monotonic()
                if now_mono_ai >= ai_diag_next_at:
                    ai_diag_next_at = now_mono_ai + 3.0
                    states = ", ".join(
                        f"{label}:{ai_state[label]['state']}" for label in ROBOTS
                        if label != labels[active_index]
                    )
                    totals = ", ".join(
                        f"{label} att={ai_stats[label]['attempts']} "
                        f"lift={ai_stats[label]['successes']} "
                        f"scripted_lift={ai_stats[label]['scripted_successes']} "
                        f"pass={ai_stats[label]['passes']} fail={ai_stats[label]['fails']}"
                        for label in ROBOTS if label != labels[active_index]
                    )
                    print(f"[AI][STATUS] {states} | {totals}", flush=True)
                    for tip_label in ROBOTS:
                        up = UsdGeom.Xformable(
                            robot_controls[tip_label]["base_prim"]
                        ).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).TransformDir(Gf.Vec3d(0, 0, 1))
                        if float(up[2]) < 0.7:
                            print(f"[AI][WARN] {tip_label}: base is TIPPED (up.z={float(up[2]):.2f})", flush=True)
            else:
                update_background_robots(time.monotonic())
            update_scripted_attach()
            for topdown_label in ROBOTS:
                update_topdown_camera(topdown_label)

            if recording is not None:
                while recording["pending_commands"]:
                    command = recording["pending_commands"].pop(0)
                    if command == "start":
                        start_recording()
                        start_dataset_episode()
                        if args.grasp_demo:
                            place_demo_ball()
                    elif command == "redo_episode":
                        # 같은 색으로 다시: 지금 에피소드는 폴더째 버리고 공을 원위치로 되돌린다.
                        stop_dataset_episode(discard=True)
                        start_dataset_episode()
                        if args.grasp_demo:
                            place_demo_ball(advance=False)
                        else:
                            reset_balls(scatter=True)
                        if args.auto_base and auto_nav is not None:
                            for lb in auto_nav["labels"]:
                                auto_nav["claims"].pop(auto_nav["state"][lb].get("ball"), None)
                                auto_nav["state"][lb]["ball"] = None
                                auto_nav["state"][lb]["state"] = "SEARCH"
                    elif command == "next_episode":
                        # 현재 에피소드를 닫고 바로 다음 것을 연다(세션 녹화는 계속 유지).
                        stop_dataset_episode()
                        start_dataset_episode()
                        # 다음 시연 준비: --grasp-demo 면 다음 색 공을 로봇 앞에 갖다 놓고,
                        # 아니면 기존처럼 공을 흩는다.
                        if args.grasp_demo:
                            place_demo_ball()
                        else:
                            reset_balls(scatter=True)
                        if args.auto_base and auto_nav is not None:
                            for lb in auto_nav["labels"]:
                                auto_nav["claims"].pop(auto_nav["state"][lb].get("ball"), None)
                                auto_nav["state"][lb]["ball"] = None
                                auto_nav["state"][lb]["state"] = "SEARCH"
                            print("[AUTO] 공 재배치 → 전원 재정렬", flush=True)
                    else:
                        stop_recording()
                        stop_dataset_episode()
                poll_command_file()
                dataset_capture_tick()
                update_follow_camera()
                update_gripper_camera()
                update_robot_top_camera()
                # Proof that recording never freezes the simulation: log sim
                # time and a background robot's actual position before,
                # during and after a recording session so a monotonic sim
                # clock and a moving robot are visible across all three
                # phases in the same log.
                now_mono = time.monotonic()
                if now_mono >= diag_next_at:
                    diag_next_at = now_mono + 2.0
                    rx, ry = base_world_xy("Red 1")
                    print(
                        f"[DIAG] sim_time={timeline.get_current_time():.2f}s "
                        f"wall={now_mono - started_at:.2f}s "
                        f"recording={'ON' if recording['active'] else 'OFF'} "
                        f"Red1_xy=({rx:.3f},{ry:.3f})",
                        flush=True,
                    )

            update_started = time.perf_counter()
            app.update()
            if args.ai_mode:
                ai_flush_snapshots()
            if recording is not None:
                recording["last_app_update_ms"] = (time.perf_counter() - update_started) * 1000.0
                capture_tick()
            if args.run_seconds > 0 and time.monotonic() - started_at >= args.run_seconds:
                break
            delay = period - (time.perf_counter() - frame_started)
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        zero_all_bases()
        timeline.stop()
        if recording is not None and recording["active"]:
            stop_recording()
        if args.data_collect and dataset["active"]:
            stop_dataset_episode(outcome="aborted_at_exit")
        if recording is not None:
            # Encoding a long take (5 min at 720p = ~5500 PNGs -> two x264
            # encodes) takes minutes; a 20 s join here killed the daemon
            # finalize thread of a 5-minute test take before metadata.json
            # was written (2026-09-11). Wait for every pending finalize.
            pending = [t for t in recording["finalize_threads"] if t.is_alive()]
            if pending:
                print(f"[REC] waiting for {len(pending)} take(s) to finish encoding before exit "
                      "(1-2 min per take; Ctrl+C is ignored here -- a kill would leave a "
                      "truncated video.mp4, recoverable with tools/finalize_take.py)", flush=True)
            for finalize_thread in recording["finalize_threads"]:
                while finalize_thread.is_alive():
                    try:
                        finalize_thread.join(timeout=15.0)
                    except KeyboardInterrupt:
                        print("[REC] still encoding -- please wait", flush=True)
                        continue
                    if finalize_thread.is_alive():
                        print(f"[REC] still encoding: {finalize_thread.name}", flush=True)
            try:
                recording["pid_file"].unlink(missing_ok=True)
            except Exception:
                pass
        if args.data_collect:
            for finalize_thread in dataset["finalize_threads"]:
                finalize_thread.join(timeout=DATASET_FINALIZE_TIMEOUT_SECONDS + 5.0)
        if writer_thread is not None:
            for _ in writer_thread:
                write_queue.put(None)
            for t in writer_thread:
                t.join(timeout=5.0)
        zero_all_bases()
        app.update()
        timeline.stop()
        if input_interface is not None and keyboard_subscription is not None:
            input_interface.unsubscribe_to_keyboard_events(
                keyboard, keyboard_subscription
            )
        subscriber.close()
        zmq_context.term()
        app.close()


if __name__ == "__main__":
    main()
