#!/usr/bin/env python3
"""Validate the generated USD composition and Isaac physics attributes."""

from __future__ import annotations

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

import math
import os
import sys
from pathlib import Path

from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

from bundle_dependencies import validate_bundle_dependencies


USD_PATH = os.environ.get(
    "LEKIWI_USD",
    str(Path(__file__).resolve().parent / "assets/lekiwi_soarm/usd/lekiwi_soarm.usd"),
)
ARM_ORDER = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]
WHEEL_ORDER = ["back_wheel_joint", "left_wheel_joint", "right_wheel_joint"]
ROLLER_ORDER = [
    f"{wheel}_roller_{index:02d}_joint"
    for wheel in ("back", "left", "right")
    for index in range(12)
]
EXPECTED_LIMITS_RAD = {
    "shoulder_pan": (-1.91986, 1.91986),
    "shoulder_lift": (-1.74533, 1.74533),
    "elbow_flex": (-1.69, 1.69),
    "wrist_flex": (-1.65806, 1.65806),
    "wrist_roll": (-2.74385, 2.84121),
    "gripper": (-0.174533, 1.74533),
}


def _require(condition, message):
    if not condition:
        raise AssertionError(message)


def _color(material):
    surface = UsdShade.Material(material).ComputeSurfaceSource()
    shader = UsdShade.Shader(surface[0]) if surface and surface[0] else None
    if not shader:
        shader_prims = [child for child in material.GetChildren() if child.IsA(UsdShade.Shader)]
        shader = UsdShade.Shader(shader_prims[0]) if len(shader_prims) == 1 else None
    if not shader:
        return None
    for name in ("diffuse_color_constant", "diffuseColor"):
        value = shader.GetInput(name).Get()
        if value is not None:
            return tuple(float(v) for v in value)
    return None


def main():
    validate_bundle_dependencies(USD_PATH)
    stage = Usd.Stage.Open(USD_PATH)
    _require(stage is not None, f"could not open {USD_PATH}")
    root = stage.GetPrimAtPath("/LeKiwi")
    _require(root.IsValid(), "missing /LeKiwi root")
    _require(stage.GetDefaultPrim() == root, "default prim is not /LeKiwi")
    custom_data = root.GetCustomData()
    _require(
        custom_data.get("lekiwiBaseForward")
        == "base_link +X aligned with SO101 arm forward",
        "base forward metadata changed",
    )
    _require(
        custom_data.get("lekiwiMountPose")
        == "xyz=0.019988279335 0.001703025019 0.052884; rpy=0 0 0",
        "reframed arm mount metadata changed",
    )

    articulations = [
        prim for prim in stage.Traverse() if prim.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    _require([str(prim.GetPath()) for prim in articulations] == ["/LeKiwi"], f"articulation roots={articulations}")
    _require(root.GetAttribute("physxArticulation:solverPositionIterationCount").Get() == 32, "solver position iterations changed")
    _require(root.GetAttribute("physxArticulation:solverVelocityIterationCount").Get() == 1, "solver velocity iterations changed")
    _require(root.GetAttribute("physxArticulation:enabledSelfCollisions").Get() is False, "self collision changed")

    joints = {
        prim.GetName(): prim
        for prim in stage.Traverse()
        if prim.IsA(UsdPhysics.RevoluteJoint)
    }
    _require(
        set(joints) == set(WHEEL_ORDER + ARM_ORDER + ROLLER_ORDER),
        f"unexpected joints={sorted(joints)}",
    )
    for name in WHEEL_ORDER + ARM_ORDER + ROLLER_ORDER:
        joint = joints[name]
        body0 = [str(path) for path in UsdPhysics.Joint(joint).GetBody0Rel().GetTargets()]
        body1 = [str(path) for path in UsdPhysics.Joint(joint).GetBody1Rel().GetTargets()]
        _require(len(body0) == 1 and len(body1) == 1, f"{name} body relationship invalid")
        _require(joint.GetAttribute("physics:axis").Get() in {"X", "Y", "Z"}, f"{name} axis missing")
        drive = UsdPhysics.DriveAPI(joint, "angular")
        _require(bool(drive), f"{name} drive missing")
        _require(drive.GetTypeAttr().Get() == "acceleration", f"{name} drive type changed")
        if name in ARM_ORDER:
            _require(math.isclose(drive.GetStiffnessAttr().Get(), 625.0), f"{name} stiffness changed")
            _require(math.isclose(drive.GetDampingAttr().Get(), 0.25), f"{name} damping changed")
            _require(math.isclose(drive.GetMaxForceAttr().Get(), 10.0), f"{name} max force changed")
            expected = tuple(math.degrees(v) for v in EXPECTED_LIMITS_RAD[name])
            actual = (
                float(joint.GetAttribute("physics:lowerLimit").Get()),
                float(joint.GetAttribute("physics:upperLimit").Get()),
            )
            _require(all(math.isclose(a, e, abs_tol=2e-3) for a, e in zip(actual, expected)), f"{name} limits={actual}")
        elif name in WHEEL_ORDER:
            _require(math.isclose(drive.GetStiffnessAttr().Get(), 0.0), f"{name} stiffness changed")
            _require(math.isclose(drive.GetDampingAttr().Get(), 625.0), f"{name} damping changed")
        else:
            _require(math.isclose(drive.GetStiffnessAttr().Get(), 0.0), f"{name} stiffness changed")
            roller_damping = drive.GetDampingAttr().Get()
            _require(
                math.isclose(roller_damping, 0.0001, abs_tol=1e-8),
                f"{name} is not passive: damping={roller_damping}",
            )
            _require(joint.GetAttribute("physics:axis").Get() == "X", f"{name} axis changed")

    # Verify the parent/child chain after fixed links are merged by checking the
    # body target names in order.  wrist_roll must connect before gripper.
    chain_children = [
        UsdPhysics.Joint(joints[name]).GetBody1Rel().GetTargets()[0].name
        for name in ARM_ORDER
    ]
    expected_children = [
        "shoulder_link",
        "upper_arm_link",
        "lower_arm_link",
        "wrist_link",
        "gripper_link",
        "moving_jaw_so101_v1_link",
    ]
    _require(chain_children == expected_children, f"arm chain children={chain_children}")

    rigid_bodies = [
        prim for prim in stage.Traverse() if prim.HasAPI(UsdPhysics.RigidBodyAPI)
    ]
    # Twelve original bodies plus 36 passive roller collision bodies. The
    # ROS-only base_footprint remains omitted from the Isaac physical asset.
    _require(len(rigid_bodies) == 48, f"expected 48 rigid bodies, got {len(rigid_bodies)}")
    fixed_joints = [prim for prim in stage.Traverse() if prim.IsA(UsdPhysics.FixedJoint)]
    _require(len(fixed_joints) == 2, f"expected 2 fixed joints, got {len(fixed_joints)}")

    proxy_predicate = Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)
    proxy_prims = list(Usd.PrimRange.Stage(stage, proxy_predicate))
    collision_count = sum(
        1 for prim in proxy_prims if prim.HasAPI(UsdPhysics.CollisionAPI)
    )
    _require(collision_count == 57, f"expected 57 colliders, got {collision_count}")

    materials = {
        prim.GetName(): _color(prim)
        for prim in stage.Traverse()
        if prim.IsA(UsdShade.Material)
    }
    expected_colors = {
        "material_a_d_printed": (0.55, 0.25, 0.85),
        "material_sts3215": (0.55, 0.25, 0.85),
        "material_body_gray": (0.627451, 0.627451, 0.627451),
        "material_wheel_dark_gray": (0.6, 0.6, 0.6),
    }
    for name, expected in expected_colors.items():
        actual = materials.get(name)
        _require(actual is not None, f"material missing: {name}")
        _require(
            all(math.isclose(a, b, abs_tol=1e-5) for a, b in zip(actual, expected)),
            f"{name} color={actual}",
        )

    arm_bodies = {
        "soarm_base_link",
        "shoulder_link",
        "upper_arm_link",
        "lower_arm_link",
        "wrist_link",
        "gripper_link",
        "moving_jaw_so101_v1_link",
    }
    purple_materials = {"material_a_d_printed", "material_sts3215"}
    arm_visual_count = 0
    for prim in proxy_prims:
        if not prim.IsA(UsdGeom.Mesh) or "/visuals/" not in str(prim.GetPath()):
            continue
        if not any(f"/{body}/" in str(prim.GetPath()) for body in arm_bodies):
            continue
        material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        _require(material and material.GetPrim().GetName() in purple_materials, f"non-purple arm mesh: {prim.GetPath()}")
        arm_visual_count += 1
    _require(arm_visual_count == 17, f"expected 17 arm visuals, got {arm_visual_count}")

    print(f"LEKIWI_USD_VALIDATE usd={USD_PATH}", flush=True)
    print(f"LEKIWI_USD_VALIDATE bodies={len(rigid_bodies)} joints={len(joints)} colliders={collision_count} passive_rollers={len(ROLLER_ORDER)} arm_visuals={arm_visual_count}", flush=True)
    print(f"LEKIWI_USD_VALIDATE arm_order={ARM_ORDER}", flush=True)
    print("LEKIWI_USD_VALIDATE result=PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"LEKIWI_USD_VALIDATE result=FAIL error={exc}", file=sys.stderr)
        raise
    finally:
        simulation_app.close()
