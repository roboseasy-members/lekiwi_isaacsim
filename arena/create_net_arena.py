#!/usr/bin/env python3
"""Build the 3.0 x 2.0 m LeKiwi arena with a central net and A/B/C basket layouts.

This is a separate generator from ``create_arena.py``. The original script stays
untouched so the existing no-net arena and ``run_switchable_teleop.sh`` keep
working exactly as before.

Differences from ``create_arena.py``:
  * a fixed physical net on X=0 that spans the full Y interior,
  * Red team on X<0 and Blue team on X>0 (the original had them swapped),
  * red / blue open-top baskets flush against the net (layout A, B, C or D),
  * white / red / yellow balls instead of a single orange colour.

Net height, basket size and ball counts are provisional test values, not a
verified final specification.
"""

import argparse
import os
import sys
from pathlib import Path

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent

# Provisional design values. None of these are a verified final specification.
NET_HEIGHT_CHOICES = (0.20, 0.25, 0.30)
NET_COLLIDER_THICKNESS = 0.02   # X extent of the thin static box collider
NET_CONTACT_OFFSET = 0.010      # PhysX contact offset for the net collider
NET_TOP_BAND_HEIGHT = 0.03      # white tape band at the top, visual only
NET_MESH_THICKNESS = 0.004      # visual grid bar thickness along X, no collider
NET_MESH_CELL = 0.0625          # visual grid spacing (open holes between bars)
NET_MESH_CORD = 0.005           # visual grid bar width
NET_POST_RADIUS = 0.02

# 2026-10-01 사용자 실측: 바구니 26(네트 방향 Y) x 12(네트에 수직 X) cm. 높이는 규정집 v0.1 값 0.18 m.
BASKET_OUTER_X = 0.12
BASKET_OUTER_Y = 0.26
# 2026-10-01 사용자 수정: 벽·테두리를 얇게(실물 바구니는 안쪽에 공 2개 반이 들어간다 →
# 벽이 두꺼우면 안쪽이 좁아진다). 테두리는 몸통과 **같은 색**이다 — 바구니 하나가 두 색이 아니라
# **단색 바구니가 두 개**(하나 회색, 하나 황토색)다.
BASKET_WALL_T = 0.012
BASKET_WALL_H = 0.18
BASKET_RIM_H = 0.012           # 윗단 테두리 높이(몸통과 같은 색, 얇게)

# 네트 하단 막음(2026-10-01 실물): 바닥부터 이 높이까지는 그물이 아니라 **막힌 벽**이다.
# 라이다(바닥 2 cm)가 네트선을 '벽'으로 보게 하려는 실물 설계를 그대로 재현한다.
NET_BOTTOM_WALL_H = 0.07
# 네트 고정대 (2026-10-01 사용자 그림·실측): 가로 12 cm(네트에 수직 X) x 세로 10 cm(네트 방향 Y)
# x 높이 13 cm. 네트 양 끝, **벽과 네트 사이에 유격이 없도록** 벽 안쪽 면에 붙여 세운다.
NET_POST_X = 0.12
NET_POST_Y = 0.10
NET_POST_Z = 0.13
BASKET_FLOOR_T = 0.025

# 2026-09-05: grown from 7 cm to 8 cm diameter and given a "rubber ball"
# contact model, adapted from a user-supplied reference (a separate
# SO-ARM101/MoveIt project's rigid-body "rubber egg" grasp tuning -- see
# create_arena.py's BALL_RADIUS comment for the full rationale; identical
# reasoning applies here since both generators share the same ball design.
BALL_RADIUS = 0.040
# Mass keeps the original ~100 kg/m^3 density, scaled with the new volume:
# 0.018 * (0.040/0.035)^3 = 0.0269 kg.
BALL_MASS = 0.0269

# Ball colour mix per team. 2026-10-01 사용자 실물 기준: 코트 전체 빨강 10 / 노랑 4 / 파랑 2.
# 두 진영에 대칭으로 깔므로 한 진영당 빨강 5 / 노랑 2 / 파랑 1 = 8개.
TEAM_BALL_COLORS = ("red", "red", "red", "red", "red", "yellow", "yellow", "blue")

# Half-field ball positions for the team on X<0. Mirrored to X>0 for the other
# team. |x| >= 0.55 keeps every ball clear of every basket footprint in A, B, C and D.
HALF_BALL_XY = (
    (-0.55, -0.35),
    (-0.55, 0.35),
    (-0.85, 0.00),
    (-1.20, -0.45),
    (-1.20, 0.45),
    # 2026-10-01: 한 진영 8개로 늘리면서 추가한 3자리. |x| >= 0.55 (바구니 발자국 회피) 유지,
    # 서로 >= 0.20 m 떨어뜨려 라이다에서 한 덩어리로 붙지 않게 했다.
    (-0.70, -0.70),
    (-0.95, 0.70),
    (-1.35, 0.00),
)

# Measured from the composed LeKiwi asset: the union world AABB of base_link plus
# the three wheel links at the default pose is 0.3053 m along X by 0.3558 m along Y
# (visual meshes; the asset ships no collision geometry). The wheels are the widest
# part, so 0.3558 m is the width a base needs in order to drive through a gap.
# verify_net_arena.py re-measures this from the stage instead of trusting the value.
ROBOT_BASE_FOOTPRINT_Y = 0.3558
B_CORRIDOR_STEER_MARGIN = 0.035          # per side, for teleoperated steering slop
B_REQUIRED_CORRIDOR = ROBOT_BASE_FOOTPRINT_Y + 2 * B_CORRIDOR_STEER_MARGIN  # 0.4258 m

# Basket centre Y per layout candidate. X is derived from the net face.
# B was moved in from +/-0.55 to +/-0.40 so the wall-side corridor becomes
# 1.00 - 0.40 - 0.17 = 0.43 m >= B_REQUIRED_CORRIDOR (was 0.28 m, too narrow for a
# 0.3558 m base). This is the smallest move that clears the criterion; the baskets
# stay at opposite ends of the net, diagonally dispersed, and flush against it.
#
# D pushes each basket all the way to the outer wall on that team's own right-hand
# side. Red spawns on X<0 facing +X, so its right is -Y; Blue spawns on X>0 facing
# -X, so its right is +Y. The Y values depend on the arena size and basket depth,
# so they are filled in after the arguments are parsed. D deliberately leaves no
# wall-side corridor: the user asked for the baskets to touch the wall, and the
# basket is approached from the open centre side instead.
BASKET_LAYOUTS = {
    "A": {"red_y": 0.00, "blue_y": 0.00},    # facing each other across the net
    "B": {"red_y": -0.40, "blue_y": 0.40},   # opposite ends of the net
    "C": {"red_y": -0.25, "blue_y": 0.25},   # staggered near the net centre
    "D": {"red_y": None, "blue_y": None},    # flush into each team's right-hand corner
    # R = 실물 경기장 실측(2026-10-01). 각 진영에서 네트를 바라봤을 때 **오른쪽**, 네트 밀착,
    # 옆벽 안쪽 면에서 60 cm 지점부터 바구니가 시작한다(폭 26 cm → 60~86 cm 구간).
    # 코트 반폭 1.00 m 이므로 가까운 모서리 |y| = 1.00 - 0.60 = 0.40, 중심 |y| = 0.40 - 0.13 = 0.27.
    # 레드는 X<0 에서 +X 를 보므로 오른쪽이 -Y, 블루는 X>0 에서 -X 를 보므로 오른쪽이 +Y.
    "R": {"red_y": -0.27, "blue_y": 0.27},
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run without the GUI")
    parser.add_argument("--validate", action="store_true", help="Run physics and structural checks")
    parser.add_argument("--screenshot", action="store_true", help="Render a spectator-camera PNG")
    parser.add_argument("--width", type=float, default=3.0, help="Playable interior width along X in metres")
    parser.add_argument("--height", type=float, default=2.0, help="Playable interior height along Y in metres")
    parser.add_argument("--layout", choices=sorted(BASKET_LAYOUTS), default="A", help="Basket layout candidate")
    parser.add_argument(
        "--net-height",
        type=float,
        choices=NET_HEIGHT_CHOICES,
        default=0.30,
        help="Net top height above the floor in metres (provisional test value)",
    )
    parser.add_argument("--basket-outer-x", type=float, default=BASKET_OUTER_X)
    parser.add_argument("--basket-outer-y", type=float, default=BASKET_OUTER_Y)
    parser.add_argument("--basket-wall-height", type=float, default=BASKET_WALL_H)
    parser.add_argument("--output", type=Path, default=None, help="Output USD path")
    return parser.parse_args()


ARGS = parse_args()
WANT_HEADLESS = bool(ARGS.headless)
WANT_VALIDATE = bool(ARGS.validate)
WANT_SCREENSHOT = bool(ARGS.screenshot)
ARENA_WIDTH = float(ARGS.width)
ARENA_HEIGHT = float(ARGS.height)
LAYOUT = ARGS.layout
NET_HEIGHT = float(ARGS.net_height)
BASKET_OUTER_X = float(ARGS.basket_outer_x)
BASKET_OUTER_Y = float(ARGS.basket_outer_y)
BASKET_WALL_H = float(ARGS.basket_wall_height)
if LAYOUT == "D":
    # Outer face of the basket touches the inner face of the outer wall exactly.
    wall_flush_y = ARENA_HEIGHT / 2.0 - BASKET_OUTER_Y / 2.0
    BASKET_LAYOUTS["D"] = {"red_y": -wall_flush_y, "blue_y": wall_flush_y}
if ARENA_WIDTH < 2.0 or ARENA_HEIGHT < 1.0:
    raise ValueError("Arena must be at least 2.0 x 1.0 m for this layout")
if BASKET_WALL_H >= NET_HEIGHT:
    raise ValueError("Basket walls must stay below the net top so the net cannot cover the opening")

DEFAULT_NAME = f"lekiwi_arena_3p0x2p0_net_{LAYOUT}.usd"
USD_PATH = (ARGS.output.expanduser().resolve() if ARGS.output else (ROOT / DEFAULT_NAME).resolve())
SCREENSHOT_PATH = USD_PATH.with_suffix(".png")

APP = SimulationApp(
    {
        "headless": ARGS.headless,
        "renderer": "RayTracedLighting",
        "width": 960,
        "height": 600,
        "anti_aliasing": 0,
    }
)

from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade  # noqa: E402
import omni.replicator.core as rep  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402


COLORS = {
    "green": (0.035, 0.34, 0.12),
    "white": (0.9, 0.9, 0.9),
    "yellow": (0.95, 0.82, 0.05),
    "blue": (0.02, 0.16, 0.75),
    "red": (0.75, 0.025, 0.025),
    "black": (0.015, 0.015, 0.015),
    "netdark": (0.10, 0.10, 0.11),
    "metal": (0.55, 0.58, 0.62),
    # 2026-10-01: 실물 바구니 색 — 몸통 회색, 위 테두리 노랑
    "basketgrey": (0.42, 0.44, 0.46),
    "basketochre": (0.72, 0.56, 0.22),      # 약간 황토색 — 다른 쪽 바구니
}

# Net face X coordinates; baskets sit flush against these planes.
NET_HALF_T = NET_COLLIDER_THICKNESS / 2.0


def material(stage, name, color, roughness=0.85, metallic=0.0):
    mat = UsdShade.Material.Define(stage, f"/World/Arena/Materials/{name}")
    shader = UsdShade.Shader.Define(stage, f"/World/Arena/Materials/{name}/Shader")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(metallic)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def bind(prim, mat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat)


def cube(stage, path, center, size, mat, collider=True):
    obj = UsdGeom.Cube.Define(stage, path)
    obj.CreateSizeAttr(1.0)
    obj.AddTranslateOp().Set(Gf.Vec3d(*center))
    obj.AddScaleOp().Set(Gf.Vec3d(*size))
    bind(obj.GetPrim(), mat)
    if collider:
        UsdPhysics.CollisionAPI.Apply(obj.GetPrim())
    return obj.GetPrim()


def sphere(stage, path, center, radius, mat, collider=True):
    obj = UsdGeom.Sphere.Define(stage, path)
    obj.CreateRadiusAttr(radius)
    obj.AddTranslateOp().Set(Gf.Vec3d(*center))
    bind(obj.GetPrim(), mat)
    if collider:
        UsdPhysics.CollisionAPI.Apply(obj.GetPrim())
    return obj.GetPrim()


def cylinder(stage, path, center, radius, height, mat, axis="Z", collider=True):
    obj = UsdGeom.Cylinder.Define(stage, path)
    obj.CreateRadiusAttr(radius)
    obj.CreateHeightAttr(height)
    obj.CreateAxisAttr(axis)
    obj.AddTranslateOp().Set(Gf.Vec3d(*center))
    bind(obj.GetPrim(), mat)
    if collider:
        UsdPhysics.CollisionAPI.Apply(obj.GetPrim())
    return obj.GetPrim()


def basket_center_x(team):
    """Outer face of the basket touches the net collider face without overlapping."""
    offset = NET_HALF_T + BASKET_OUTER_X / 2.0
    return -offset if team == "TeamRed" else offset


def make_basket(stage, name, team, center, mats):
    """Open-top rectangular bin built from stable box colliders, hollow inside."""
    root_path = f"/World/Arena/Baskets/{name}"
    root = UsdGeom.Xform.Define(stage, root_path)
    root.GetPrim().CreateAttribute("arena:scoringZone", Sdf.ValueTypeNames.Bool).Set(True)
    root.GetPrim().CreateAttribute("arena:team", Sdf.ValueTypeNames.String).Set(team)
    root.GetPrim().CreateAttribute("arena:basketCenter", Sdf.ValueTypeNames.Double2).Set(Gf.Vec2d(*center))

    x, y = center
    # 2026-10-01 실물: 단색 바구니 두 개 — 레드 진영 회색, 블루 진영 황토색.
    # (전에는 '회색 몸통 + 노란 테두리' 한 종류로 만들었는데 사용자 정정: 바구니마다 단색이다.)
    mat = mats["basketgrey"] if team == "TeamRed" else mats["basketochre"]
    rim = mat
    ox, oy, wt, wh, ft = BASKET_OUTER_X, BASKET_OUTER_Y, BASKET_WALL_T, BASKET_WALL_H, BASKET_FLOOR_T
    body_h = max(wh - BASKET_RIM_H, wt)
    cube(stage, f"{root_path}/Bottom", (x, y, ft / 2), (ox, oy, ft), mat)
    cube(stage, f"{root_path}/Wall_West", (x - (ox - wt) / 2, y, body_h / 2), (wt, oy, body_h), mat)
    cube(stage, f"{root_path}/Wall_East", (x + (ox - wt) / 2, y, body_h / 2), (wt, oy, body_h), mat)
    cube(stage, f"{root_path}/Wall_South", (x, y - (oy - wt) / 2, body_h / 2), (ox - 2 * wt, wt, body_h), mat)
    cube(stage, f"{root_path}/Wall_North", (x, y + (oy - wt) / 2, body_h / 2), (ox - 2 * wt, wt, body_h), mat)
    # 노란 테두리(윗단) — 같은 벽 두께로 몸통 위에 얹는다. 콜라이더 포함(바구니 벽의 일부다)
    rz = body_h + BASKET_RIM_H / 2.0
    cube(stage, f"{root_path}/Rim_West", (x - (ox - wt) / 2, y, rz), (wt, oy, BASKET_RIM_H), rim)
    cube(stage, f"{root_path}/Rim_East", (x + (ox - wt) / 2, y, rz), (wt, oy, BASKET_RIM_H), rim)
    cube(stage, f"{root_path}/Rim_South", (x, y - (oy - wt) / 2, rz), (ox - 2 * wt, wt, BASKET_RIM_H), rim)
    cube(stage, f"{root_path}/Rim_North", (x, y + (oy - wt) / 2, rz), (ox - 2 * wt, wt, BASKET_RIM_H), rim)


def make_net(stage, mats):
    """Thin static box collider plus separate visual mesh sheet and top band."""
    UsdGeom.Xform.Define(stage, "/World/Arena/Net")
    root = stage.GetPrimAtPath("/World/Arena/Net")
    root.CreateAttribute("arena:netTopHeight", Sdf.ValueTypeNames.Double).Set(NET_HEIGHT)
    root.CreateAttribute("arena:netColliderThickness", Sdf.ValueTypeNames.Double).Set(NET_COLLIDER_THICKNESS)
    root.CreateAttribute("arena:netSpanY", Sdf.ValueTypeNames.Double).Set(ARENA_HEIGHT)
    root.CreateAttribute("arena:netStatus", Sdf.ValueTypeNames.String).Set(
        "Provisional test height; blocks robot bases and balls, not arms reaching over the top"
    )

    # Physics: one simple thin box from the floor top (Z=0) to the net top.
    collider = cube(
        stage,
        "/World/Arena/Net/Collider",
        (0.0, 0.0, NET_HEIGHT / 2.0),
        (NET_COLLIDER_THICKNESS, ARENA_HEIGHT, NET_HEIGHT),
        mats["netdark"],
    )
    physx_collision = PhysxSchema.PhysxCollisionAPI.Apply(collider)
    physx_collision.CreateContactOffsetAttr(NET_CONTACT_OFFSET)
    physx_collision.CreateRestOffsetAttr(0.0)
    # The collider is hidden; the visual mesh below represents the net.
    UsdGeom.Imageable(collider).CreateVisibilityAttr(UsdGeom.Tokens.invisible)

    # 네트 하단 막음(2026-10-01 실물): 바닥~NET_BOTTOM_WALL_H 는 그물이 아니라 막힌 판이다.
    # 콜라이더는 위의 Collider 박스가 이미 전 구간을 막고 있으므로 여기서는 보이는 판만 만든다.
    cube(
        stage,
        "/World/Arena/Net/BottomWall",
        (0.0, 0.0, NET_BOTTOM_WALL_H / 2.0),
        (NET_COLLIDER_THICKNESS, ARENA_HEIGHT, NET_BOTTOM_WALL_H),
        mats["white"],
        collider=False,
    )
    root.CreateAttribute("arena:netBottomWallHeight", Sdf.ValueTypeNames.Double).Set(NET_BOTTOM_WALL_H)

    # Visual only: an open grid of thin bars so the holes are actually visible,
    # under a white top band, like a table-tennis net. No colliders here.
    # 하단 막힌 벽 위에서 시작한다.
    mesh_h = NET_HEIGHT - NET_TOP_BAND_HEIGHT
    UsdGeom.Xform.Define(stage, "/World/Arena/Net/Mesh")
    n_vertical = max(2, int(round(ARENA_HEIGHT / NET_MESH_CELL)) + 1)
    for i in range(n_vertical):
        y = -ARENA_HEIGHT / 2.0 + i * (ARENA_HEIGHT / (n_vertical - 1))
        cube(
            stage,
            f"/World/Arena/Net/Mesh/Cord_V_{i:02d}",
            (0.0, y, mesh_h / 2.0),
            (NET_MESH_THICKNESS, NET_MESH_CORD, mesh_h),
            mats["netdark"],
            collider=False,
        )
    n_horizontal = max(1, int(mesh_h / NET_MESH_CELL))
    for i in range(n_horizontal):
        z = (i + 0.5) * (mesh_h / n_horizontal)
        cube(
            stage,
            f"/World/Arena/Net/Mesh/Cord_H_{i:02d}",
            (0.0, 0.0, z),
            (NET_MESH_THICKNESS, ARENA_HEIGHT, NET_MESH_CORD),
            mats["netdark"],
            collider=False,
        )
    cube(
        stage,
        "/World/Arena/Net/TopBand",
        (0.0, 0.0, NET_HEIGHT - NET_TOP_BAND_HEIGHT / 2.0),
        (NET_MESH_THICKNESS * 2.0, ARENA_HEIGHT, NET_TOP_BAND_HEIGHT),
        mats["white"],
        collider=False,
    )

    # 네트 고정대 (2026-10-01 실물): 원기둥이 아니라 한 변 7 cm 박스. 코트 안쪽 모서리에
    # 서 있어 라이다에도 잡힌다 → 콜라이더를 준다(예전 원기둥은 시각 전용이었다).
    # 벽 안쪽 면에 딱 붙인다(유격 0): 코트 반폭 - 고정대 세로/2
    post_y = ARENA_HEIGHT / 2.0 - NET_POST_Y / 2.0
    for label, sign in (("South", -1.0), ("North", 1.0)):
        cube(
            stage,
            f"/World/Arena/Net/Post_{label}",
            (0.0, sign * post_y, NET_POST_Z / 2.0),
            (NET_POST_X, NET_POST_Y, NET_POST_Z),
            mats["metal"],
        )
    root.CreateAttribute("arena:netPostSize", Sdf.ValueTypeNames.Double3).Set(
        Gf.Vec3d(NET_POST_X, NET_POST_Y, NET_POST_Z))


def make_robot_spawn(stage, team, index, position, yaw):
    """Create an empty Xform where add_four_lekiwi.py attaches the LeKiwi asset."""
    path = f"/World/Arena/RobotSpawnPoints/{team}/{team}_Spawn_{index:02d}"
    root = UsdGeom.Xform.Define(stage, path)
    root.AddTranslateOp().Set(Gf.Vec3d(position[0], position[1], 0.0))
    root.AddRotateZOp().Set(yaw)
    root.GetPrim().CreateAttribute("arena:team", Sdf.ValueTypeNames.String).Set(team)
    root.GetPrim().CreateAttribute("arena:recommendedBaseDiameter", Sdf.ValueTypeNames.Double).Set(0.2)


def ball_plan():
    """Return [(index, x, y, color, team)] 공 배치. 한 진영 8개를 대칭 복제 → 총 16개
    (2026-10-01 실물 기준: 빨강 10, 노랑 4, 파랑 2)."""
    plan = []
    index = 1
    for team, sign in (("TeamRed", -1.0), ("TeamBlue", 1.0)):
        for (x, y), color in zip(HALF_BALL_XY, TEAM_BALL_COLORS):
            plan.append((index, sign * abs(x), y, color, team))
            index += 1
    return plan


def build_stage():
    stage = Usd.Stage.CreateNew(str(USD_PATH))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    arena = UsdGeom.Xform.Define(stage, "/World/Arena")
    arena_prim = arena.GetPrim()
    arena_prim.CreateAttribute("arena:interiorSizeMeters", Sdf.ValueTypeNames.Double2).Set(
        Gf.Vec2d(ARENA_WIDTH, ARENA_HEIGHT)
    )
    arena_prim.CreateAttribute("arena:basketLayout", Sdf.ValueTypeNames.String).Set(LAYOUT)
    arena_prim.CreateAttribute("arena:teamSides", Sdf.ValueTypeNames.String).Set("TeamRed X<0, TeamBlue X>0")
    arena_prim.CreateAttribute("arena:assetStatus", Sdf.ValueTypeNames.String).Set(
        "Map only; LeKiwi robots intentionally omitted"
    )

    scene = UsdPhysics.Scene.Define(stage, "/World/Arena/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(9.81)
    physx_scene = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
    # 2026-09-10: raised from 60 as part of the grasp-stability fix (see the
    # ball collider block below and ARENA_BUILD_GUIDE.md) -- a finer physics
    # step reduces per-step position error for the TGS solver holding a
    # squeezed rigid ball, matching the user's own working reference recipe.
    # Physics stays CPU-only (unchanged); doubling the step rate for 4
    # robots + 10 balls was not GPU-memory relevant either way.
    physx_scene.CreateTimeStepsPerSecondAttr(120)
    physx_scene.CreateEnableGPUDynamicsAttr(False)
    physx_scene.CreateEnableCCDAttr(True)

    UsdGeom.Scope.Define(stage, "/World/Arena/Materials")
    mats = {key: material(stage, key.title(), value) for key, value in COLORS.items()}
    ball_physics = UsdShade.Material.Define(stage, "/World/Arena/Materials/BallPhysics")
    ball_api = UsdPhysics.MaterialAPI.Apply(ball_physics.GetPrim())
    # "Rubber ball" contact -- see create_arena.py's matching block for the
    # earlier rationale (adapted from a user-supplied external rigid-body
    # "rubber egg" reference; restitution goes down, not up; max/min combine
    # modes let the ball's own material dominate contact friction/bounce
    # without touching the gripper's material).
    #
    # 2026-09-10: revised per a deep-research pass the user commissioned
    # (Notion "260910 LeKiwi 2읰2 공 이동 경기 — 심층 레퍼런스 조사 요약") that
    # flagged 3.2/2.4 as above an NVIDIA-maintainer-recommended range and
    # identified contact geometry/compliance -- not gripper force -- as the
    # actual failure driver (rated STS3215 fingertip pinch force ~5N vs the
    # ball's 0.26N weight). The user asked for a ball-only retry (gripper
    # drive, gripper collider, and gripper material untouched this time):
    # friction lowered into that research's 1.0-1.5 comparison range, and
    # PhysX "compliant contact" turned on for the ball's own material so a
    # squeeze yields a soft, spring-like give instead of a hard penalty
    # contact -- the closest approximation to "the ball presses in" available
    # without an actual deformable-body extension (confirmed not installed
    # in this Isaac Sim build; see ARENA_BUILD_GUIDE.md). This is still a
    # rigid sphere collider, not a real shape change.
    # The research doc's cited "friction exceeds recommendation" was not
    # itself locally tested (see its own section 10 -- no local physics runs
    # were part of that pass). Headless A/B testing here (same close+lift+
    # release procedure, gripper untouched) showed lowering friction to the
    # doc's 1.0-1.5 range *reintroduced* the pop (max close speed 0.80 m/s)
    # at the validated jaw-gap placement, so the original 3.2/2.4 is kept --
    # empirical local evidence overrides the untested literature suggestion
    # here. See ARENA_BUILD_GUIDE.md for both runs' numbers.
    ball_api.CreateStaticFrictionAttr(3.2)
    ball_api.CreateDynamicFrictionAttr(2.4)
    ball_api.CreateRestitutionAttr(0.0)
    ball_physx_api = PhysxSchema.PhysxMaterialAPI.Apply(ball_physics.GetPrim())
    ball_physx_api.CreateFrictionCombineModeAttr("max")
    ball_physx_api.CreateRestitutionCombineModeAttr("min")
    # PhysX "compliant contact" (ball-only: CompliantContact{Stiffness,
    # Damping,AccelerationSpring} on this material) lets the ball itself
    # give under the gripper's squeeze without touching the gripper at all.
    # accelerationSpring=True, stiffness=3000, damping=20 eliminated the
    # >0.5 m/s pop during both closing and lifting in headless A/B testing
    # (down from 0.52/0.78 m/s to 0.39/0.22 m/s) -- the best grip-only
    # result found. See ARENA_BUILD_GUIDE.md 13.2 for the full sweep,
    # including why a stiffer 6000 setting made the pop worse instead.
    #
    # 2026-09-10 (second pass): re-enabled. The same softness also lets
    # balls sink 24-26mm into the net collider during
    # verify_net_arena.py's net-contact stress test, versus the ~51mm
    # baseline clearance that check assumed (essentially no margin even at
    # baseline -- see 13.3). The user decided grip success takes priority
    # over that test's rigid-contact assumption, so this stays on and
    # verify_net_arena.py's too-deep margin (COMPLIANT_PENETRATION_MARGIN)
    # was widened to match the measured penetration instead. Gripper
    # drive, collider and material remain untouched -- still a ball-only
    # change.
    ball_physx_api.CreateCompliantContactAccelerationSpringAttr(True)
    ball_physx_api.CreateCompliantContactStiffnessAttr(3000.0)
    ball_physx_api.CreateCompliantContactDampingAttr(20.0)

    # 1. Floor: top surface at Z=0, exact requested playable interior.
    UsdGeom.Xform.Define(stage, "/World/Arena/Floor")
    floor = cube(stage, "/World/Arena/Floor/Field", (0, 0, -0.025), (ARENA_WIDTH, ARENA_HEIGHT, 0.05), mats["green"])
    floor.CreateAttribute("arena:interiorDimensions", Sdf.ValueTypeNames.Double3).Set(
        Gf.Vec3d(ARENA_WIDTH, ARENA_HEIGHT, 0.0)
    )

    # 2. Walls: inner faces exactly match the interior, 0.70 m tall.
    UsdGeom.Xform.Define(stage, "/World/Arena/Walls")
    half_x, half_y = ARENA_WIDTH / 2, ARENA_HEIGHT / 2
    cube(stage, "/World/Arena/Walls/West", (-half_x - 0.03, 0, 0.35), (0.06, ARENA_HEIGHT + 0.12, 0.70), mats["white"])
    cube(stage, "/World/Arena/Walls/East", (half_x + 0.03, 0, 0.35), (0.06, ARENA_HEIGHT + 0.12, 0.70), mats["white"])
    cube(stage, "/World/Arena/Walls/South", (0, -half_y - 0.03, 0.35), (ARENA_WIDTH, 0.06, 0.70), mats["white"])
    cube(stage, "/World/Arena/Walls/North", (0, half_y + 0.03, 0.35), (ARENA_WIDTH, 0.06, 0.70), mats["white"])

    # 3. Centre line stays as a visual marking; the net now provides the physics.
    UsdGeom.Xform.Define(stage, "/World/Arena/Markings")
    cube(stage, "/World/Arena/Markings/CenterLine", (0, 0, 0.0015), (0.018, ARENA_HEIGHT - 0.04, 0.003), mats["white"], False)

    # 4. Central net on X=0 spanning the full Y interior.
    make_net(stage, mats)

    # 5. Hollow, open-top scoring baskets flush against the net.
    UsdGeom.Xform.Define(stage, "/World/Arena/Baskets")
    layout = BASKET_LAYOUTS[LAYOUT]
    make_basket(stage, "TeamRed_Goal", "TeamRed", (basket_center_x("TeamRed"), layout["red_y"]), mats)
    make_basket(stage, "TeamBlue_Goal", "TeamBlue", (basket_center_x("TeamBlue"), layout["blue_y"]), mats)

    # 6. Ten lightweight rigid balls: 6 white, 2 red, 2 yellow, mirrored per team.
    UsdGeom.Xform.Define(stage, "/World/Arena/Balls")
    for index, x, y, color, team in ball_plan():
        path = f"/World/Arena/Balls/Ball_{index:02d}"
        ball = UsdGeom.Xform.Define(stage, path)
        prim = ball.GetPrim()
        ball.AddTranslateOp().Set(Gf.Vec3d(x, y, BALL_RADIUS + 0.002))
        prim.CreateAttribute("arena:ballColor", Sdf.ValueTypeNames.String).Set(color)
        prim.CreateAttribute("arena:startTeam", Sdf.ValueTypeNames.String).Set(team)
        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdPhysics.MassAPI.Apply(prim).CreateMassAttr(BALL_MASS)
        physx_body = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        physx_body.CreateEnableCCDAttr(True)
        physx_body.CreateLinearDampingAttr(0.45)
        physx_body.CreateAngularDampingAttr(0.80)
        physx_body.CreateMaxDepenetrationVelocityAttr(0.30)
        physx_body.CreateMaxLinearVelocityAttr(0.80)
        physx_body.CreateMaxAngularVelocityAttr(360.0)
        # 2026-09-10: grasp investigation (see ARENA_BUILD_GUIDE.md) found the
        # ball popping out of a closed gripper under a real user's leader-arm
        # test. Solver iteration count explicitly authored (was only the
        # PhysxSchema fallback of 16, never actually set) to 32, per both an
        # initial user-supplied "rubber egg" reference and a later deep
        # research pass that separately recommended 16->32.
        physx_body.CreateSolverPositionIterationCountAttr(32)
        # Not 8 (the reference project's value): this PhysX build warns
        # "more than 4 velocity iterations being added to a TGS scene ...
        # behavior changed recently" when actually tried, so 8 was reverted
        # to the schema's recommended ceiling for a TGS scene instead.
        physx_body.CreateSolverVelocityIterationCountAttr(4)

        # Visual only: a perfectly round sphere, no collider. The ball must
        # still LOOK round -- only its collision shape (below) changes.
        sphere(stage, f"{path}/Visual", (0, 0, 0), BALL_RADIUS, mats[color], collider=False)

        # 2026-09-10 (fourth pass): the user diagnosed the remaining grasp
        # instability as geometric, not force-related -- a perfectly round
        # analytic UsdGeom.Sphere collider meets each flat gripper jaw at a
        # single point/line (matches the research doc's "rigid sphere-plane
        # 2-point contact" finding, ARENA_BUILD_GUIDE.md 13.5(b)), which is
        # inherently unstable to hold. The collision shape only (see the
        # Visual sphere above, still perfectly round) is an invisible mesh
        # so the jaws land on flats instead of a point. Gripper untouched --
        # still a ball-only change.
        #
        # 2026-09-10 (fifth pass): the user asked to go further -- a cube
        # "inside" the visual ball, gripped directly, for the biggest flat
        # jaw contact possible (replaces the fourth pass's 20-face
        # icosahedron). Side length is set so the cube's CORNERS -- not its
        # faces -- touch BALL_RADIUS (same circumradius-based sizing as the
        # icosahedron), so this collider still never exceeds the nominal
        # ball size every distance check elsewhere assumes. That sizing
        # choice inevitably insets the cube's faces further from the visual
        # surface than the icosahedron's did (~17mm vs ~8mm here) -- the
        # jaws will visually sink further into the ball before contacting
        # anything solid.
        cube_side = 2.0 * BALL_RADIUS / (3.0 ** 0.5)
        collider_geom = UsdGeom.Cube.Define(stage, f"{path}/Collider")
        collider_geom.CreateSizeAttr(cube_side)
        collider_geom.AddTranslateOp().Set(Gf.Vec3d(0, 0, 0))
        collider = collider_geom.GetPrim()
        UsdGeom.Imageable(collider).CreateVisibilityAttr(UsdGeom.Tokens.invisible)
        UsdShade.MaterialBindingAPI.Apply(collider).Bind(ball_physics, materialPurpose="physics")
        UsdPhysics.CollisionAPI.Apply(collider)
        physx_collision = PhysxSchema.PhysxCollisionAPI.Apply(collider)
        # contactOffset/restOffset: unchanged values from the prior (sphere,
        # then icosahedron) collider -- an NVIDIA-maintainer-recommended
        # 0.005-0.01 range for this kind of contact.
        physx_collision.CreateContactOffsetAttr(0.01)
        physx_collision.CreateRestOffsetAttr(0.002)

    # 7. Team spawn transforms. Red on X<0, Blue on X>0; local +X faces the net.
    UsdGeom.Xform.Define(stage, "/World/Arena/RobotSpawnPoints")
    UsdGeom.Xform.Define(stage, "/World/Arena/RobotSpawnPoints/TeamBlue")
    UsdGeom.Xform.Define(stage, "/World/Arena/RobotSpawnPoints/TeamRed")
    robot_x = ARENA_WIDTH * 0.272
    robot_y = ARENA_HEIGHT * 0.287
    make_robot_spawn(stage, "TeamRed", 1, (-robot_x, -robot_y), 0)
    make_robot_spawn(stage, "TeamRed", 2, (-robot_x, robot_y), 0)
    make_robot_spawn(stage, "TeamBlue", 1, (robot_x, -robot_y), 180)
    make_robot_spawn(stage, "TeamBlue", 2, (robot_x, robot_y), 180)

    # One spectator camera and inexpensive dome lighting (unchanged settings).
    camera = UsdGeom.Camera.Define(stage, "/World/Arena/SpectatorCamera")
    camera.CreateFocalLengthAttr(28.0)
    camera.CreateClippingRangeAttr(Gf.Vec2f(0.05, 100.0))
    camera_z = max(4.0, ARENA_WIDTH * 1.55, ARENA_HEIGHT * 2.35)
    camera.AddTranslateOp().Set(Gf.Vec3d(0.0, 0.0, camera_z))
    dome = UsdLux.DomeLight.Define(stage, "/World/Arena/Lighting/DomeLight")
    dome.CreateIntensityAttr(850.0)
    dome.CreateColorAttr(Gf.Vec3f(0.85, 0.88, 1.0))

    stage.GetRootLayer().Save()
    return stage


def world_xy(prim):
    t = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
    return float(t[0]), float(t[1]), float(t[2])


def verify_structure(stage):
    errors = []
    balls = [
        p for p in stage.Traverse()
        if str(p.GetPath()).startswith("/World/Arena/Balls/Ball_") and p.HasAttribute("arena:ballColor")
    ]
    spawns = [p for p in stage.Traverse() if p.HasAttribute("arena:recommendedBaseDiameter")]
    expected_balls = len(ball_plan())        # 2026-10-01: 10 → 16 (빨강10/노랑4/파랑2)
    if len(balls) != expected_balls:
        errors.append(f"expected {expected_balls} balls, found {len(balls)}")
    if len(spawns) != 4:
        errors.append(f"expected 4 robot spawn points, found {len(spawns)}")
    if stage.GetPrimAtPath("/World/Arena/Robots"):
        errors.append("map-only build must not contain robot geometry")

    required_colliders = [
        "/World/Arena/Floor/Field",
        "/World/Arena/Walls/West", "/World/Arena/Walls/East",
        "/World/Arena/Walls/South", "/World/Arena/Walls/North",
        "/World/Arena/Net/Collider",
        "/World/Arena/Baskets/TeamRed_Goal/Bottom",
        "/World/Arena/Baskets/TeamBlue_Goal/Bottom",
    ]
    for team in ("TeamRed_Goal", "TeamBlue_Goal"):
        for wall in ("Wall_West", "Wall_East", "Wall_South", "Wall_North"):
            required_colliders.append(f"/World/Arena/Baskets/{team}/{wall}")
    required_colliders += [f"/World/Arena/Balls/Ball_{i:02d}/Collider" for i in range(1, 11)]
    for path in required_colliders:
        prim = stage.GetPrimAtPath(path)
        if not prim or not prim.HasAPI(UsdPhysics.CollisionAPI):
            errors.append(f"missing collider: {path}")

    # The visual net parts must not add colliders.
    # 2026-10-01: 고정대(Post_*)는 실물처럼 7 cm 박스가 코트 안에 서 있고 라이다에도 잡혀야 하므로
    # **콜라이더를 갖는다** — 이 목록에서 뺐다. BottomWall 은 Collider 박스가 이미 막으므로 시각 전용.
    for path in ("/World/Arena/Net/Mesh", "/World/Arena/Net/TopBand",
                 "/World/Arena/Net/BottomWall"):
        prim = stage.GetPrimAtPath(path)
        if not prim:
            errors.append(f"missing net part: {path}")
        elif prim.HasAPI(UsdPhysics.CollisionAPI):
            errors.append(f"visual net part must not be a collider: {path}")
    grid = [p for p in stage.Traverse() if str(p.GetPath()).startswith("/World/Arena/Net/Mesh/Cord_")]
    if len(grid) < 4:
        errors.append(f"net visual grid has too few bars: {len(grid)}")
    for prim in grid:
        if prim.HasAPI(UsdPhysics.CollisionAPI):
            errors.append(f"net visual grid bar must not be a collider: {prim.GetPath()}")

    expected = Gf.Vec2d(ARENA_WIDTH, ARENA_HEIGHT)
    if stage.GetPrimAtPath("/World/Arena").GetAttribute("arena:interiorSizeMeters").Get() != expected:
        errors.append("arena dimensions metadata mismatch")

    # Wall height check from the authored scale.
    for wall in ("West", "East", "South", "North"):
        scale = UsdGeom.Xformable(stage.GetPrimAtPath(f"/World/Arena/Walls/{wall}")).GetOrderedXformOps()[1].Get()
        if abs(float(scale[2]) - 0.70) > 1e-6:
            errors.append(f"wall {wall} height {float(scale[2])} != 0.70")

    # Net geometry.
    net = stage.GetPrimAtPath("/World/Arena/Net/Collider")
    if net:
        cx, cy, cz = world_xy(net)
        scale = UsdGeom.Xformable(net).GetOrderedXformOps()[1].Get()
        if abs(cx) > 1e-6:
            errors.append(f"net collider centre X={cx} != 0")
        if abs(float(scale[1]) - ARENA_HEIGHT) > 1e-6:
            errors.append(f"net collider Y span {float(scale[1])} != {ARENA_HEIGHT}")
        if abs((cz + float(scale[2]) / 2.0) - NET_HEIGHT) > 1e-6:
            errors.append(f"net top {cz + float(scale[2]) / 2.0} != {NET_HEIGHT}")
        if abs((cz - float(scale[2]) / 2.0)) > 1e-6:
            errors.append("net bottom does not reach the floor top (Z=0)")

    # Baskets flush against the net, inside their own half, below the net top.
    for team, name in (("TeamRed", "TeamRed_Goal"), ("TeamBlue", "TeamBlue_Goal")):
        root = stage.GetPrimAtPath(f"/World/Arena/Baskets/{name}")
        if not root:
            errors.append(f"missing basket: {name}")
            continue
        bx, by = root.GetAttribute("arena:basketCenter").Get()
        near_face = bx - BASKET_OUTER_X / 2.0 if bx > 0 else bx + BASKET_OUTER_X / 2.0
        if abs(abs(near_face) - NET_HALF_T) > 1e-6:
            errors.append(f"{name} not flush with the net face: near_face={near_face}")
        if team == "TeamRed" and bx >= 0:
            errors.append(f"{name} must sit on X<0")
        if team == "TeamBlue" and bx <= 0:
            errors.append(f"{name} must sit on X>0")
        if abs(by) + BASKET_OUTER_Y / 2.0 > ARENA_HEIGHT / 2.0 + 1e-6:
            errors.append(f"{name} sticks through the outer wall at y={by}")
        if LAYOUT == "B":
            corridor = ARENA_HEIGHT / 2.0 - (abs(by) + BASKET_OUTER_Y / 2.0)
            if corridor < B_REQUIRED_CORRIDOR - 1e-6:
                errors.append(
                    f"{name} wall-side corridor {corridor:.4f} m < required {B_REQUIRED_CORRIDOR:.4f} m"
                )
        if LAYOUT == "D":
            gap = ARENA_HEIGHT / 2.0 - (abs(by) + BASKET_OUTER_Y / 2.0)
            if abs(gap) > 1e-6:
                errors.append(f"{name} is not flush with the outer wall (gap {gap:.4f} m)")
            # Red faces +X so its right is -Y; Blue faces -X so its right is +Y.
            if (by < 0) != (team == "TeamRed"):
                errors.append(f"{name} is not on its own team's right-hand side (y={by})")
        if BASKET_WALL_H >= NET_HEIGHT:
            errors.append(f"{name} walls reach the net top")

    # Ball colour mix and per-team symmetry.
    counts = {}
    per_team = {}
    for prim in balls:
        color = prim.GetAttribute("arena:ballColor").Get()
        team = prim.GetAttribute("arena:startTeam").Get()
        counts[color] = counts.get(color, 0) + 1
        per_team.setdefault(team, {}).setdefault(color, 0)
        per_team[team][color] += 1
    # 2026-10-01 실물 기준: 코트 전체 빨강 10 / 노랑 4 / 파랑 2, 진영별 대칭(빨강5/노랑2/파랑1).
    want_all, want_team = {}, {}
    for color in TEAM_BALL_COLORS:
        want_team[color] = want_team.get(color, 0) + 1
        want_all[color] = want_all.get(color, 0) + 2
    if counts != want_all:
        errors.append(f"ball colour mix {counts} != {want_all}")
    for team in ("TeamRed", "TeamBlue"):
        if per_team.get(team) != want_team:
            errors.append(f"{team} ball mix {per_team.get(team)} != {want_team}")
    for prim in balls:
        x, y, _ = world_xy(prim)
        team = prim.GetAttribute("arena:startTeam").Get()
        if team == "TeamRed" and x >= -NET_HALF_T - BALL_RADIUS:
            errors.append(f"{prim.GetPath()} not clear of the net on the red side")
        if team == "TeamBlue" and x <= NET_HALF_T + BALL_RADIUS:
            errors.append(f"{prim.GetPath()} not clear of the net on the blue side")

    # No initial overlap: ball/ball, ball/basket, ball/net.
    positions = [world_xy(p) for p in balls]
    for i, a in enumerate(positions):
        for b in positions[i + 1:]:
            d = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5
            if d < (2.0 * BALL_RADIUS) - 1e-6:
                errors.append("balls overlap at startup")
    for name in ("TeamRed_Goal", "TeamBlue_Goal"):
        root = stage.GetPrimAtPath(f"/World/Arena/Baskets/{name}")
        bx, by = root.GetAttribute("arena:basketCenter").Get()
        x0, x1 = bx - BASKET_OUTER_X / 2.0, bx + BASKET_OUTER_X / 2.0
        y0, y1 = by - BASKET_OUTER_Y / 2.0, by + BASKET_OUTER_Y / 2.0
        for prim, (px, py, _) in zip(balls, positions):
            if x0 - BALL_RADIUS < px < x1 + BALL_RADIUS and y0 - BALL_RADIUS < py < y1 + BALL_RADIUS:
                errors.append(f"{prim.GetPath()} starts inside the {name} footprint")

    # Robot spawns on the correct sides.
    for prim in spawns:
        x, _, _ = world_xy(prim)
        team = prim.GetAttribute("arena:team").Get()
        if team == "TeamRed" and x >= 0:
            errors.append(f"{prim.GetPath()} TeamRed must be on X<0")
        if team == "TeamBlue" and x <= 0:
            errors.append(f"{prim.GetPath()} TeamBlue must be on X>0")

    if errors:
        raise RuntimeError("; ".join(errors))
    print(
        "STRUCTURE PASS: "
        f"layout={LAYOUT}, arena={ARENA_WIDTH}x{ARENA_HEIGHT}m, wall_h=0.70m, "
        f"net_top={NET_HEIGHT}m, net_span_y={ARENA_HEIGHT}m, net_thickness={NET_COLLIDER_THICKNESS}m, "
        f"balls={len(balls)} ({counts}), baskets=2, robot_spawns={len(spawns)}, "
        "teams=Red X<0 / Blue X>0",
        flush=True,
    )


def run_physics_validation():
    context = omni.usd.get_context()
    context.open_stage(str(USD_PATH))
    for _ in range(10):
        APP.update()
    stage = context.get_stage()
    verify_structure(stage)
    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    for _ in range(180):
        APP.update()
    timeline.pause()
    zs = []
    escaped = []
    crossed = []
    for i in range(1, 11):
        prim = stage.GetPrimAtPath(f"/World/Arena/Balls/Ball_{i:02d}")
        team = prim.GetAttribute("arena:startTeam").Get()
        p = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
        zs.append(float(p[2]))
        if abs(p[0]) > ARENA_WIDTH / 2 or abs(p[1]) > ARENA_HEIGHT / 2 or p[2] < -0.01:
            escaped.append((i, tuple(p)))
        if (team == "TeamRed" and float(p[0]) > 0.0) or (team == "TeamBlue" and float(p[0]) < 0.0):
            crossed.append((i, float(p[0])))
    timeline.stop()
    if escaped:
        raise RuntimeError(f"PHYSICS FAIL: escaped/fallen balls: {escaped}")
    if crossed:
        raise RuntimeError(f"PHYSICS FAIL: balls drifted across the net at rest: {crossed}")
    scene_hz = PhysxSchema.PhysxSceneAPI(
        stage.GetPrimAtPath("/World/Arena/PhysicsScene")
    ).GetTimeStepsPerSecondAttr().Get()
    print(f"PHYSICS PASS: 180 app updates at {scene_hz:g} Hz scene rate; "
          f"ball z range={min(zs):.4f}..{max(zs):.4f} m; none escaped or crossed", flush=True)


def capture_screenshot():
    context = omni.usd.get_context()
    if context.get_stage() is None or context.get_stage().GetRootLayer().realPath != str(USD_PATH):
        context.open_stage(str(USD_PATH))
    for _ in range(10):
        APP.update()
    render_product = rep.create.render_product("/World/Arena/SpectatorCamera", (960, 600))
    rgb = rep.AnnotatorRegistry.get_annotator("rgb")
    rgb.attach([render_product])
    rep.orchestrator.step()
    data = rgb.get_data()
    import imageio.v3 as iio
    iio.imwrite(str(SCREENSHOT_PATH), data)
    if not SCREENSHOT_PATH.is_file() or SCREENSHOT_PATH.stat().st_size == 0:
        raise RuntimeError("screenshot encoder returned without creating a file")
    rgb.detach([render_product])
    render_product.destroy()
    print(f"SCREENSHOT PASS: {SCREENSHOT_PATH}", flush=True)


EXIT_CODE = 0
try:
    build_stage()
    print(f"USD CREATED: {USD_PATH}", flush=True)
    reopened = Usd.Stage.Open(str(USD_PATH))
    if reopened is None:
        raise RuntimeError("USD could not be reopened")
    verify_structure(reopened)
    print(f"REOPEN PASS: {USD_PATH}", flush=True)
    if WANT_VALIDATE:
        run_physics_validation()
    if WANT_SCREENSHOT:
        capture_screenshot()
    if not WANT_HEADLESS:
        context = omni.usd.get_context()
        context.open_stage(str(USD_PATH))
        for _ in range(10):
            APP.update()
        print(f"GUI READY: opened {USD_PATH}; close the Isaac Sim window to exit", flush=True)
        while APP.is_running():
            APP.update()
except BaseException:
    import traceback
    traceback.print_exc()
    EXIT_CODE = 1
finally:
    sys.stdout.flush()
    sys.stderr.flush()
    # SimulationApp.close(exit_code=N) flushes stdio and, when fast shutdown is on
    # (the default), calls os._exit(N) so Kit cannot replace the status with 0.
    APP.close(exit_code=EXIT_CODE)
    # Reached only if fast shutdown is disabled and close() returns normally.
    sys.exit(EXIT_CODE)
