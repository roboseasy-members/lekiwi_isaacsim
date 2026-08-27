#!/usr/bin/env python3
"""Static validation for the copied LeKiwi + SO101 Isaac asset."""

from __future__ import annotations

import math
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
ASSET_DIR = SCRIPT_DIR / "assets" / "lekiwi_soarm"
URDF_PATH = ASSET_DIR / "urdf" / "lekiwi_soarm.urdf"
REFERENCE_DIR = SCRIPT_DIR.parent / "src" / "lekiwi_soarm_description"
ASSEMBLY_PATH = SCRIPT_DIR.parent / "src" / "0. dumyAssem5.STL"
ARM_ORDER = [
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
]
WHEEL_ORDER = ["back_wheel_joint", "left_wheel_joint", "right_wheel_joint"]
ROLLER_RADIUS = 0.00988918
ROLLER_AXIS_OFFSET = 0.04089530
ROLLER_SIDE_OFFSET = 0.009525
ROLLER_COUNT_PER_WHEEL = 12
ROLLER_JOINTS = [
    f"{wheel}_roller_{index:02d}_joint"
    for wheel in ("back", "left", "right")
    for index in range(ROLLER_COUNT_PER_WHEEL)
]


def _as_floats(value: str) -> np.ndarray:
    return np.array([float(part) for part in value.split()])


def _rotation(rpy) -> np.ndarray:
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


def _origin_transform(origin: ET.Element | None) -> np.ndarray:
    transform = np.eye(4)
    if origin is None:
        return transform
    transform[:3, :3] = _rotation(_as_floats(origin.get("rpy", "0 0 0")))
    transform[:3, 3] = _as_floats(origin.get("xyz", "0 0 0"))
    return transform


def _load_binary_stl(path: Path) -> np.ndarray:
    raw = np.memmap(path, dtype=np.uint8, mode="r")
    triangles = struct.unpack_from("<I", raw, 80)[0]
    dtype = np.dtype(
        [("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")]
    )
    records = np.memmap(path, dtype=dtype, mode="r", offset=84, shape=(triangles,))
    return np.asarray(records["vertices"]).reshape(-1, 3).astype(np.float64)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_urdf() -> ET.Element:
    root = ET.parse(URDF_PATH).getroot()
    _require(root.get("name") == "LeKiwi", "USD root compatibility name must be LeKiwi")
    joints = {joint.get("name"): joint for joint in root.findall("joint")}
    links = {link.get("name"): link for link in root.findall("link")}
    _require("base_footprint" not in links, "Isaac URDF retained zero-mass base_footprint body")
    _require("base_footprint_joint" not in joints, "Isaac URDF retained base_footprint fixed joint")

    movable = [
        joint.get("name")
        for joint in root.findall("joint")
        if joint.get("type") in {"continuous", "revolute"}
    ]
    _require(movable[:3] == WHEEL_ORDER, "wheel order changed")
    _require(movable[3:9] == ARM_ORDER, f"arm order changed: {movable[3:9]}")
    _require(movable[9:] == ROLLER_JOINTS, "passive roller order changed")

    mount = joints["soarm_mount_joint"].find("origin")
    _require(
        np.allclose(
            _as_floats(mount.get("xyz")),
            [0.019988279335, 0.001703025019, 0.052884],
            atol=1e-12,
        ),
        "SO101 mount xyz changed",
    )
    _require(
        np.allclose(_as_floats(mount.get("rpy")), [0, 0, 0], atol=1e-12),
        "SO101 mount rpy changed",
    )

    base_inertial = links["base_link"].find("inertial")
    _require(base_inertial is not None, "base_link inertial missing")
    _require(
        math.isclose(float(base_inertial.find("mass").get("value")), 7.784429386),
        "base mass changed",
    )
    _require(
        np.allclose(
            _as_floats(base_inertial.find("origin").get("xyz")),
            [-0.010693670776, -0.000809065310, 0.037199240],
            atol=1e-12,
        ),
        "base COM was not re-expressed with the new +X axis",
    )

    expected_chain = [
        ("shoulder_pan", "soarm_base_link", "shoulder_link"),
        ("shoulder_lift", "shoulder_link", "upper_arm_link"),
        ("elbow_flex", "upper_arm_link", "lower_arm_link"),
        ("wrist_flex", "lower_arm_link", "wrist_link"),
        ("wrist_roll", "wrist_link", "gripper_link"),
        ("gripper", "gripper_link", "moving_jaw_so101_v1_link"),
    ]
    for name, parent, child in expected_chain:
        joint = joints[name]
        _require(joint.find("parent").get("link") == parent, f"{name} parent changed")
        _require(joint.find("child").get("link") == child, f"{name} child changed")
        _require(joint.find("axis").get("xyz") == "0 0 1", f"{name} axis changed")

    wheel_expected = {
        "back_wheel_mount_joint": (
            [0.065688326518, -0.114631545219, -0.024939],
            3.665176191951,
        ),
        "left_wheel_mount_joint": (
            [-0.127599301296, 0.000428428396, -0.024148],
            1.570781089571,
        ),
        "right_wheel_mount_joint": (
            [0.065153184202, 0.111987337491, -0.023661],
            -0.523614012829,
        ),
    }
    for name, (xyz, yaw) in wheel_expected.items():
        origin = joints[name].find("origin")
        _require(np.allclose(_as_floats(origin.get("xyz")), xyz, atol=1e-9), f"{name} position changed")
        _require(abs(_as_floats(origin.get("rpy"))[2] - yaw) < 1e-9, f"{name} yaw changed")
    for name in ("back", "left", "right"):
        _require(joints[f"{name}_wheel_joint"].find("axis").get("xyz") == "0 1 0", f"{name} wheel axis changed")
        _require(links[f"{name}_wheel_link"].find("inertial") is not None, f"{name} wheel inertial missing")
        hub_radius = float(
            links[f"{name}_wheel_link"]
            .find("collision/geometry/cylinder")
            .get("radius")
        )
        _require(math.isclose(hub_radius, 0.043), f"{name} hub collider radius={hub_radius}")

        for index in range(ROLLER_COUNT_PER_WHEEL):
            roller_name = f"{name}_roller_{index:02d}"
            roller_link = links[roller_name]
            roller_joint = joints[f"{roller_name}_joint"]
            angle = index * 2.0 * math.pi / ROLLER_COUNT_PER_WHEEL
            expected_xyz = [
                -math.sin(angle) * ROLLER_AXIS_OFFSET,
                ROLLER_SIDE_OFFSET if index % 2 == 0 else -ROLLER_SIDE_OFFSET,
                math.cos(angle) * ROLLER_AXIS_OFFSET,
            ]
            _require(
                roller_joint.find("parent").get("link") == f"{name}_wheel_link",
                f"{roller_name} parent changed",
            )
            _require(
                roller_joint.find("child").get("link") == roller_name,
                f"{roller_name} child changed",
            )
            _require(
                roller_joint.find("axis").get("xyz") == "1 0 0",
                f"{roller_name} axis changed",
            )
            _require(
                np.allclose(
                    _as_floats(roller_joint.find("origin").get("xyz")),
                    expected_xyz,
                    atol=1e-10,
                ),
                f"{roller_name} position changed",
            )
            radius = float(
                roller_link.find("collision/geometry/sphere").get("radius")
            )
            _require(
                math.isclose(radius, ROLLER_RADIUS, abs_tol=1e-12),
                f"{roller_name} radius={radius}",
            )
            helper_radius = float(
                roller_link.find("visual/geometry/sphere").get("radius")
            )
            _require(
                math.isclose(helper_radius, 1e-6, abs_tol=1e-12),
                f"{roller_name} helper visual is not microscopic",
            )

    materials = {
        material.get("name"): material.find("color").get("rgba")
        for material in root.findall("material")
    }
    _require(materials["body_gray"] == "0.627451 0.627451 0.627451 1.0", "base color changed")
    _require(materials["wheel_dark_gray"] == "0.6 0.6 0.6 1.0", "wheel color changed")
    for name in ("3d_printed", "sts3215"):
        _require(materials[name] == "0.55 0.25 0.85 1.0", f"{name} is not purple")

    for visual in root.findall(".//visual"):
        mesh = visual.find("geometry/mesh")
        if mesh is None or "/soarm/" not in mesh.get("filename"):
            continue
        material = visual.find("material")
        _require(material is not None and material.get("name") in {"3d_printed", "sts3215"}, "SO101 visual is not purple")
        mesh_path = (URDF_PATH.parent / mesh.get("filename")).resolve()
        _require(mesh_path.is_file(), f"missing mesh: {mesh_path}")

    subprocess.run(["check_urdf", str(URDF_PATH)], check=True, capture_output=True, text=True)
    print(
        f"LEKIWI_VALIDATE urdf=PASS passive_rollers={len(ROLLER_JOINTS)}"
    )
    return root


def validate_base_forward(root: ET.Element) -> None:
    children: dict[str, list[tuple[str, np.ndarray]]] = {}
    for joint in root.findall("joint"):
        parent = joint.find("parent").get("link")
        child = joint.find("child").get("link")
        children.setdefault(parent, []).append(
            (child, _origin_transform(joint.find("origin")))
        )

    transforms = {"base_link": np.eye(4)}
    pending = ["base_link"]
    while pending:
        parent = pending.pop()
        for child, parent_to_child in children.get(parent, []):
            transforms[child] = transforms[parent] @ parent_to_child
            pending.append(child)

    _require("gripper_frame_link" in transforms, "gripper frame is disconnected")
    gripper = transforms["gripper_frame_link"][:3, 3]
    yaw = math.atan2(gripper[1], gripper[0])
    _require(gripper[0] > 0.35, f"arm does not extend along base +X: {gripper}")
    _require(
        abs(gripper[1]) < 0.015,
        f"arm forward is not aligned with base +X: {gripper}",
    )
    print(
        "LEKIWI_VALIDATE base_forward=PASS "
        f"gripper_xy={gripper[0]:+.6f},{gripper[1]:+.6f} "
        f"yaw_deg={math.degrees(yaw):+.3f}"
    )


def validate_mount_geometry() -> None:
    try:
        from scipy.spatial import cKDTree
    except ImportError:
        print("LEKIWI_VALIDATE mount_geometry=SKIP scipy_unavailable")
        return

    assembly = _load_binary_stl(ASSEMBLY_PATH)
    body_rotation = _rotation([0, 0, 0.523583538371])
    body_translation = np.array([-0.310264249096, -1.449350080211, -1.159469])
    assembly_in_base = assembly * 0.001 @ body_rotation.T + body_translation
    assembly_points = np.unique(np.round(assembly_in_base, 6), axis=0)
    tree = cKDTree(assembly_points)

    holder = _load_binary_stl(ASSET_DIR / "meshes" / "soarm" / "base_motor_holder_so101_v1.stl")
    holder = holder @ _rotation([1.5708, -1.67685e-15, 1.5708]).T
    holder += np.array([-0.00636471, -9.94414e-05, -0.0024])
    holder = holder @ _rotation([0, 0, 0]).T
    holder += np.array([0.019988279335, 0.001703025019, 0.052884])
    stride = max(1, len(holder) // 25000)
    distances, _ = tree.query(holder[::stride], workers=-1)
    within = float(np.mean(distances <= 0.0005))
    _require(within >= 0.999, f"assembly alignment dropped to {within:.6f}")
    print(
        "LEKIWI_VALIDATE mount_geometry=PASS "
        f"within_0.5mm={within:.6f} p99_mm={np.percentile(distances, 99) * 1000:.6f}"
    )


def main() -> None:
    root = validate_urdf()
    validate_base_forward(root)
    validate_mount_geometry()
    print("LEKIWI_VALIDATE result=PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"LEKIWI_VALIDATE result=FAIL error={exc}", file=sys.stderr)
        raise
