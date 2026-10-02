#!/usr/bin/env python3
"""그리퍼가 공을 놓치는 문제 완화 (2026-10-01 사용자 요청).

실측으로 확인한 원인 두 가지:
  1) 그리퍼 턱(gripper_link, moving_jaw_so101_v1_link)에 **물리 재질이 없다** → PhysX 기본
     마찰(≈0.5)이 쓰인다. 공 재질은 3.2/2.4 이고 조합 모드가 max 라 공 쪽 값이 쓰이긴 하지만,
     턱에 높은 마찰 재질을 직접 주는 편이 확실하다.
  2) 그리퍼 드라이브가 약하다: stiffness 12.8 / maxForce 1.2 — 스펀지공(내부 정육면체 콜라이더)을
     눌러 유지하기에 모자라 들어 올릴 때 미끄러진다.

이 스크립트는 **override 레이어**를 새로 만들어 올린다 — 원본 USD 는 건드리지 않는다.
결과: <stage>_grip.usd

실행:
  cd /home/namin/isaacsim_lekiwi_arena
  env -u PYTHONPATH -u LD_LIBRARY_PATH ~/miniforge3/envs/isaacsim-6.0.1/bin/python sim_grip_tune.py
그 뒤 그 스테이지로 띄우면 된다:
  OMNI_KIT_ACCEPT_EULA=YES ./run_turf_teleop.sh R --record --data-collect --grasp-demo --low-render \\
      --stage lekiwi_arena_3p0x2p0_net_R_4robots_turf_grip.usd
"""
from __future__ import annotations

import argparse
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
ROBOTS = (
    "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_01",
    "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_02",
    "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_01",
    "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_02",
)
JAW_LINKS = ("gripper_link", "moving_jaw_so101_v1_link")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="lekiwi_arena_3p0x2p0_net_R_4robots_turf.usd")
    ap.add_argument("--out", default="")
    ap.add_argument("--friction", type=float, default=4.0, help="턱 재질 정지 마찰")
    ap.add_argument("--friction-dynamic", type=float, default=3.0)
    ap.add_argument("--stiffness", type=float, default=40.0, help="그리퍼 드라이브 stiffness (기본 12.8)")
    ap.add_argument("--max-force", type=float, default=6.0, help="그리퍼 드라이브 maxForce (기본 1.2)")
    ap.add_argument("--damping", type=float, default=3.0)
    # 2026-10-01 사용자 지시: "공이 튕겨져 나감 — 네모 박스를 말랑하게, 아니면 박스를 키우자".
    # 두 손잡이를 여기서 같이 돌린다. 둘 다 override 라 원본 USD 는 그대로다.
    ap.add_argument("--ball-stiffness", type=float, default=800.0,
                    help="공 재질 compliant contact stiffness (원본 3000 — 낮추면 말랑해진다)")
    ap.add_argument("--ball-damping", type=float, default=40.0,
                    help="공 재질 compliant contact damping (원본 20 — 높이면 튀어나감이 줄어든다)")
    ap.add_argument("--ball-cube-scale", type=float, default=1.0,
                    help="공 속 콜라이더 정육면체 한 변 배율 (1.0 = 원본 내접 정육면체 46.2 mm). "
                         "1.0 보다 키우면 턱이 더 빨리 평면에 닿지만 모서리가 공 밖으로 나온다")
    a = ap.parse_args()

    # PhysxSchema 는 Kit 확장이 올라온 뒤에만 import 된다 → 헤드리스 SimulationApp 을 먼저 띄운다.
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True})
    from pxr import PhysxSchema, Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

    src = (PROJECT / a.stage).resolve()
    out = Path(a.out).resolve() if a.out else src.with_name(src.stem + "_grip.usd")
    if out.exists():
        out.unlink()
    stage = Usd.Stage.CreateNew(str(out))
    stage.GetRootLayer().subLayerPaths = ["./" + src.name]

    # 높은 마찰의 턱 전용 물리 재질
    mat_path = "/World/Arena/Materials/GripperPhysics"
    mat = UsdShade.Material.Define(stage, mat_path)
    api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api.CreateStaticFrictionAttr(float(a.friction))
    api.CreateDynamicFrictionAttr(float(a.friction_dynamic))
    api.CreateRestitutionAttr(0.0)

    bound, drives = 0, 0
    for robot in ROBOTS:
        for link in JAW_LINKS:
            prim = stage.OverridePrim(f"{robot}/{link}")
            if not prim:
                continue
            UsdShade.MaterialBindingAPI.Apply(prim)
            UsdShade.MaterialBindingAPI(prim).Bind(
                mat, bindingStrength=UsdShade.Tokens.strongerThanDescendants,
                materialPurpose="physics")
            bound += 1
        joint = stage.OverridePrim(f"{robot}/joints/gripper")
        if joint:
            drive = UsdPhysics.DriveAPI.Apply(joint, "angular")
            drive.CreateStiffnessAttr(float(a.stiffness))
            drive.CreateDampingAttr(float(a.damping))
            drive.CreateMaxForceAttr(float(a.max_force))
            drives += 1

    # 공 쪽: 재질의 compliant contact 를 무르게 하고(필요하면) 콜라이더 정육면체를 키운다.
    ball_mat = stage.OverridePrim("/World/Arena/Materials/BallPhysics")
    ball_physx = PhysxSchema.PhysxMaterialAPI.Apply(ball_mat)
    ball_physx.CreateCompliantContactAccelerationSpringAttr(True)
    ball_physx.CreateCompliantContactStiffnessAttr(float(a.ball_stiffness))
    ball_physx.CreateCompliantContactDampingAttr(float(a.ball_damping))

    # 원본 한 변: 2 * BALL_RADIUS / sqrt(3) (내접 정육면체 — 모서리가 공 표면에 닿는다)
    base_side = 2.0 * 0.040 / (3.0 ** 0.5)
    new_side = base_side * float(a.ball_cube_scale)
    src_stage = Usd.Stage.Open(str(src))
    cubes = 0
    if abs(a.ball_cube_scale - 1.0) > 1e-9:
        for prim in src_stage.Traverse():
            path = str(prim.GetPath())
            if path.startswith("/World/Arena/Balls/Ball_") and path.endswith("/Collider"):
                ov = stage.OverridePrim(path)
                UsdGeom.Cube(ov).CreateSizeAttr(new_side)
                cubes += 1

    stage.GetRootLayer().Save()
    print(f"생성: {out}")
    print(f"  공 compliant contact: stiffness {a.ball_stiffness} (원본 3000), "
          f"damping {a.ball_damping} (원본 20)")
    if cubes:
        print(f"  공 콜라이더 정육면체 {cubes}개: 한 변 {base_side*1000:.1f} → {new_side*1000:.1f} mm "
              f"(배율 {a.ball_cube_scale})")
    else:
        print(f"  공 콜라이더 정육면체: 원본 유지 ({base_side*1000:.1f} mm)")
    print(f"  턱 재질 바인딩 {bound}개 (마찰 {a.friction}/{a.friction_dynamic})")
    print(f"  그리퍼 드라이브 {drives}개 (stiffness {a.stiffness}, maxForce {a.max_force}, damping {a.damping})")
    print("  원본 USD 는 변경하지 않았다 — 되돌리려면 이 파일만 지우면 된다.")
    app.close()


if __name__ == "__main__":
    main()
