#!/usr/bin/env python3
"""Render the copied LeKiwi + SO101 Xacro into an Isaac-ready URDF.

The ROS description under ``src/`` is a read-only geometric reference.  This
script only reads the copied Xacro below ``isaac_sim/assets`` and augments the
rendered URDF with the base/wheel inertials and colors carried over from the
existing Isaac Sim asset.
"""

from __future__ import annotations

import math
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSET_DIR = SCRIPT_DIR / "assets" / "lekiwi_soarm"
XACRO_PATH = ASSET_DIR / "source_xacro" / "lekiwi_soarm.urdf.xacro"
URDF_PATH = ASSET_DIR / "urdf" / "lekiwi_soarm.urdf"

# Existing Isaac asset: /LeKiwi/base_plate_layer1_v5.  The 0.147 kg fixed arm
# base is imported separately and merged back into the base rigid body, so it
# is subtracted here to keep the resulting rigid-body mass near 7.931429 kg.
# COM and inertia are re-expressed in the base frame whose +X points along the
# SO101 arm-forward direction; the physical mass distribution is unchanged.
BASE_INERTIAL = {
    "mass": "7.784429386",
    "xyz": "-0.010693670776 -0.000809065310 0.037199240",
    "ixx": "0.0312966086",
    "ixy": "0.0003278457",
    "ixz": "0.0001562681",
    "iyy": "0.0265191942",
    "iyz": "-0.0026145673",
    "izz": "0.0386193512",
}

# The existing wheel rigid body includes the passive rollers.  Preserve its
# total mass/inertia while splitting the measured rollers into physical links.
WHEEL_TOTAL_MASS = 1.477856278
WHEEL_TOTAL_IXX = 0.0019124525
WHEEL_TOTAL_IYY = 0.0011462600
WHEEL_TOTAL_IZZ = 0.0019124525

# Measured directly from omni_wheel.stl.  The visual mesh contains 12 rollers
# alternating across the two wheel sides.  This follows Isaac's bundled Kaya
# strategy: invisible sphere colliders on passive continuous joints.
ROLLER_COUNT = 12
ROLLER_RADIUS = 0.00988918
ROLLER_AXIS_OFFSET = 0.04089530
ROLLER_SIDE_OFFSET = 0.009525
ROLLER_DENSITY = 1000.0
ROLLER_MASS = 4.0 / 3.0 * math.pi * ROLLER_RADIUS**3 * ROLLER_DENSITY
ROLLER_INERTIA = 2.0 / 5.0 * ROLLER_MASS * ROLLER_RADIUS**2
WHEEL_HUB_COLLISION_RADIUS = 0.043


def _wheel_hub_inertial() -> dict[str, str]:
    roller_ixx = ROLLER_COUNT * (
        ROLLER_INERTIA
        + ROLLER_MASS
        * (ROLLER_SIDE_OFFSET**2 + ROLLER_AXIS_OFFSET**2 / 2.0)
    )
    roller_iyy = ROLLER_COUNT * (
        ROLLER_INERTIA + ROLLER_MASS * ROLLER_AXIS_OFFSET**2
    )
    roller_izz = roller_ixx
    values = {
        "mass": WHEEL_TOTAL_MASS - ROLLER_COUNT * ROLLER_MASS,
        "ixx": WHEEL_TOTAL_IXX - roller_ixx,
        "iyy": WHEEL_TOTAL_IYY - roller_iyy,
        "izz": WHEEL_TOTAL_IZZ - roller_izz,
    }
    if any(value <= 0.0 for value in values.values()):
        raise RuntimeError(f"Roller split produced invalid wheel inertia: {values}")
    return {
        "mass": f"{values['mass']:.12g}",
        "xyz": "0 0 0",
        "ixx": f"{values['ixx']:.12g}",
        "ixy": "0",
        "ixz": "0",
        "iyy": f"{values['iyy']:.12g}",
        "iyz": "0",
        "izz": f"{values['izz']:.12g}",
    }


def _add_inertial(link: ET.Element, values: dict[str, str]) -> None:
    if link.find("inertial") is not None:
        raise RuntimeError(f"{link.get('name')} already has an inertial block")
    inertial = ET.Element("inertial")
    ET.SubElement(inertial, "origin", xyz=values["xyz"], rpy="0 0 0")
    ET.SubElement(inertial, "mass", value=values["mass"])
    ET.SubElement(
        inertial,
        "inertia",
        ixx=values["ixx"],
        ixy=values["ixy"],
        ixz=values["ixz"],
        iyy=values["iyy"],
        iyz=values["iyz"],
        izz=values["izz"],
    )
    link.insert(0, inertial)


def _set_material_color(root: ET.Element, name: str, rgba: str) -> None:
    material = root.find(f"material[@name='{name}']")
    if material is None:
        raise RuntimeError(f"Material {name!r} was not rendered")
    color = material.find("color")
    if color is None:
        raise RuntimeError(f"Material {name!r} has no color")
    color.set("rgba", rgba)


def _set_wheel_hub_collision(link: ET.Element) -> None:
    cylinder = link.find("collision/geometry/cylinder")
    if cylinder is None:
        raise RuntimeError(f"{link.get('name')} has no cylinder collision")
    cylinder.set("radius", f"{WHEEL_HUB_COLLISION_RADIUS:.12g}")


def _add_passive_rollers(root: ET.Element, wheel_name: str) -> None:
    parent_name = f"{wheel_name}_wheel_link"
    for index in range(ROLLER_COUNT):
        side = index % 2
        angle = index * 2.0 * math.pi / ROLLER_COUNT
        roller_name = f"{wheel_name}_roller_{index:02d}"

        link = ET.SubElement(root, "link", name=roller_name)
        inertial = ET.SubElement(link, "inertial")
        ET.SubElement(inertial, "origin", xyz="0 0 0", rpy="0 0 0")
        ET.SubElement(inertial, "mass", value=f"{ROLLER_MASS:.12g}")
        ET.SubElement(
            inertial,
            "inertia",
            ixx=f"{ROLLER_INERTIA:.12g}",
            ixy="0",
            ixz="0",
            iyy=f"{ROLLER_INERTIA:.12g}",
            iyz="0",
            izz=f"{ROLLER_INERTIA:.12g}",
        )
        # Isaac's layered URDF importer creates an unresolved visual reference
        # for links with no visual element. A one-micrometre helper sphere is
        # effectively invisible and keeps the generated layer composition
        # valid without adding another mesh file.
        visual = ET.SubElement(link, "visual")
        visual_geometry = ET.SubElement(visual, "geometry")
        ET.SubElement(visual_geometry, "sphere", radius="0.000001")
        collision = ET.SubElement(link, "collision")
        ET.SubElement(collision, "origin", xyz="0 0 0", rpy="0 0 0")
        geometry = ET.SubElement(collision, "geometry")
        ET.SubElement(geometry, "sphere", radius=f"{ROLLER_RADIUS:.12g}")

        joint = ET.SubElement(
            root, "joint", name=f"{roller_name}_joint", type="continuous"
        )
        side_y = ROLLER_SIDE_OFFSET if side == 0 else -ROLLER_SIDE_OFFSET
        x = -math.sin(angle) * ROLLER_AXIS_OFFSET
        z = math.cos(angle) * ROLLER_AXIS_OFFSET
        ET.SubElement(
            joint,
            "origin",
            xyz=f"{x:.12g} {side_y:.12g} {z:.12g}",
            rpy=f"0 {-angle:.12g} 0",
        )
        ET.SubElement(joint, "parent", link=parent_name)
        ET.SubElement(joint, "child", link=roller_name)
        ET.SubElement(joint, "axis", xyz="1 0 0")
        ET.SubElement(joint, "dynamics", damping="0.0001", friction="0")


def main() -> None:
    URDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "xacro",
        str(XACRO_PATH),
        "base_mesh_dir:=../meshes/base",
        "soarm_mesh_dir:=../meshes/soarm",
    ]
    rendered = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    root = ET.fromstring(rendered)
    root.set("name", "LeKiwi")

    # Preserve the two neutral gray colors from the current Isaac asset.  The
    # SO101 materials remain the required purple from the copied Xacro.
    _set_material_color(root, "body_gray", "0.627451 0.627451 0.627451 1.0")
    _set_material_color(root, "wheel_dark_gray", "0.6 0.6 0.6 1.0")

    links = {link.get("name"): link for link in root.findall("link")}
    _add_inertial(links["base_link"], BASE_INERTIAL)
    wheel_hub_inertial = _wheel_hub_inertial()
    for name in ("back_wheel_link", "left_wheel_link", "right_wheel_link"):
        _add_inertial(links[name], wheel_hub_inertial)
        _set_wheel_hub_collision(links[name])

    for name in ("back", "left", "right"):
        _add_passive_rollers(root, name)

    # The ROS-only base_footprint frame is useful for TF, but Isaac 5.1 imports
    # it as a separate zero-mass root rigid body. Direct base velocity then
    # fights the fixed joint to the heavy base_link and can turn translation
    # commands into rotation. Keep the reference Xacro untouched and omit only
    # this physical dummy from the generated Isaac URDF.
    base_footprint_joint = root.find("joint[@name='base_footprint_joint']")
    base_footprint_link = root.find("link[@name='base_footprint']")
    if base_footprint_joint is None or base_footprint_link is None:
        raise RuntimeError("Expected ROS base_footprint frame was not rendered")
    root.remove(base_footprint_joint)
    root.remove(base_footprint_link)

    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tree.write(URDF_PATH, encoding="utf-8", xml_declaration=True)
    print(f"LEKIWI_URDF output={URDF_PATH}")
    print(
        f"LEKIWI_URDF passive_rollers={3 * ROLLER_COUNT} "
        f"radius={ROLLER_RADIUS:.8f} axis_offset={ROLLER_AXIS_OFFSET:.8f}"
    )


if __name__ == "__main__":
    main()
