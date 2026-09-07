"""Convert the prepared URDF to USD and apply Isaac-specific physics.

Run this file with Isaac Sim's ``python.sh``. LEKIWI_ASSET_DIR can select a
fresh output copy, so the distributed asset is never overwritten at runtime.
"""

from isaacsim import SimulationApp


simulation_app = SimulationApp({"headless": True})

import math
import os
import shutil
import sys
import traceback
from pathlib import Path

import omni.kit.commands
import omni.usd
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade


ASSET_DIR = os.environ.get(
    "LEKIWI_ASSET_DIR", str(Path(__file__).resolve().parent / "assets/lekiwi_soarm")
)
URDF_PATH = os.path.join(ASSET_DIR, "urdf", "lekiwi_soarm.urdf")
USD_PATH = os.path.join(ASSET_DIR, "usd", "lekiwi_soarm.usd")
ARM_JOINTS = (
    "shoulder_pan",
    "shoulder_lift",
    "elbow_flex",
    "wrist_flex",
    "wrist_roll",
    "gripper",
)
WHEEL_JOINTS = (
    "back_wheel_joint",
    "left_wheel_joint",
    "right_wheel_joint",
)
ROLLER_JOINTS = tuple(
    f"{wheel}_roller_{index:02d}_joint"
    for wheel in ("back", "left", "right")
    for index in range(12)
)
MATERIAL_COLORS = {
    "material_a_d_printed": (0.55, 0.25, 0.85),
    "material_sts3215": (0.55, 0.25, 0.85),
    "material_body_gray": (0.627451, 0.627451, 0.627451),
    "material_wheel_dark_gray": (0.6, 0.6, 0.6),
}


def _fail(exc_type, exc_value, exc_traceback):
    print("LEKIWI_USD_BUILD result=FATAL", flush=True)
    traceback.print_exception(exc_type, exc_value, exc_traceback)


sys.excepthook = _fail


def _joint_by_name(stage, name):
    matches = [
        prim
        for prim in stage.Traverse()
        if prim.IsA(UsdPhysics.Joint) and prim.GetName() == name
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one joint {name!r}, got {[str(p.GetPath()) for p in matches]}")
    return matches[0]


def _configure_drive(joint_prim, *, stiffness, damping, max_force):
    drive = UsdPhysics.DriveAPI.Apply(joint_prim, "angular")
    drive.CreateTypeAttr("acceleration")
    drive.CreateStiffnessAttr(float(stiffness))
    drive.CreateDampingAttr(float(damping))
    drive.CreateMaxForceAttr(float(max_force))
    drive.CreateTargetPositionAttr(0.0)
    drive.CreateTargetVelocityAttr(0.0)


def _configure_preview_materials(stage):
    found = set()
    for prim in stage.Traverse():
        if not prim.IsA(UsdShade.Material) or prim.GetName() not in MATERIAL_COLORS:
            continue
        color = MATERIAL_COLORS[prim.GetName()]
        material = UsdShade.Material(prim)
        # The importer-authored OmniPBR output can block the first RTX frame
        # indefinitely when its MDL cache is cold in the disposable container.
        # Author an explicit empty connection in this stronger layer; the
        # imported MDL data remains in the base layer and can still be restored.
        for surface_output in material.GetSurfaceOutputs():
            if surface_output.GetAttr().GetName().startswith("outputs:mdl:"):
                surface_output.GetAttr().SetConnections([])
        shader = UsdShade.Shader.Define(
            stage, prim.GetPath().AppendChild("PreviewSurface")
        )
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(*color)
        )
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.65)
        material.CreateSurfaceOutput().ConnectToSource(
            shader.ConnectableAPI(), "surface"
        )
        found.add(prim.GetName())
    missing = set(MATERIAL_COLORS) - found
    if missing:
        raise RuntimeError(f"Could not add preview shaders to materials: {sorted(missing)}")


def main():
    if not os.path.isfile(URDF_PATH):
        raise FileNotFoundError(URDF_PATH)
    os.makedirs(os.path.dirname(USD_PATH), exist_ok=True)

    # Isaac's layered importer may otherwise leave prim opinions from a prior
    # generated asset. Only these generated USD outputs are replaced; copied
    # meshes, Xacro, and URDF files are outside this directory.
    configuration_dir = os.path.join(os.path.dirname(USD_PATH), "configuration")
    if os.path.isdir(configuration_dir):
        shutil.rmtree(configuration_dir)
    if os.path.isfile(USD_PATH):
        os.remove(USD_PATH)

    status, config = omni.kit.commands.execute("URDFCreateImportConfig")
    if not status:
        raise RuntimeError("URDFCreateImportConfig failed")
    config.merge_fixed_joints = True
    config.convex_decomp = False
    config.import_inertia_tensor = True
    config.fix_base = False
    config.collision_from_visuals = False
    config.self_collision = False
    config.make_default_prim = True
    config.create_physics_scene = True
    config.distance_scale = 1.0
    config.density = 0.0
    config.override_joint_dynamics = False

    print(f"LEKIWI_USD_BUILD urdf={URDF_PATH}", flush=True)
    status, prim_path = omni.kit.commands.execute(
        "URDFParseAndImportFile",
        urdf_path=URDF_PATH,
        import_config=config,
        dest_path=USD_PATH,
        get_articulation_root=True,
    )
    if not status:
        raise RuntimeError("URDFParseAndImportFile failed")
    print(f"LEKIWI_USD_BUILD imported_prim={prim_path}", flush=True)

    context = omni.usd.get_context()
    if not context.open_stage(USD_PATH):
        raise RuntimeError(f"Could not open generated USD: {USD_PATH}")
    for _ in range(20):
        simulation_app.update()
    stage = context.get_stage()
    root = stage.GetPrimAtPath("/LeKiwi")
    if not root.IsValid():
        raise RuntimeError("Generated asset does not have the required /LeKiwi root")

    articulation_roots = [
        prim for prim in stage.Traverse() if prim.HasAPI(UsdPhysics.ArticulationRootAPI)
    ]
    for prim in articulation_roots:
        if prim != root:
            prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
    UsdPhysics.ArticulationRootAPI.Apply(root)
    # Lift the new base_link root by the removed ROS fixed-frame offset so the
    # assembled wheel/ground relationship remains unchanged.
    UsdGeom.XformCommonAPI(root).SetTranslate(Gf.Vec3d(0.0, 0.0, 0.055))
    physx_articulation = PhysxSchema.PhysxArticulationAPI.Apply(root)
    physx_articulation.CreateEnabledSelfCollisionsAttr(False)
    physx_articulation.CreateSolverPositionIterationCountAttr(32)
    physx_articulation.CreateSolverVelocityIterationCountAttr(1)

    # Carry over the current Isaac drive gains.  Arm max force is bounded by
    # the new SO101 URDF effort limit instead of retaining the old unbounded
    # CAD-import value.
    for name in WHEEL_JOINTS:
        _configure_drive(
            _joint_by_name(stage, name),
            stiffness=0.0,
            damping=625.0,
            max_force=3.4028234663852886e38,
        )
    for name in ARM_JOINTS:
        _configure_drive(
            _joint_by_name(stage, name),
            stiffness=625.0,
            damping=0.25,
            max_force=10.0,
        )
    # Match the bundled NVIDIA Kaya strategy: roller joints are passive with
    # only a tiny viscous term to suppress numerical chatter.
    for name in ROLLER_JOINTS:
        _configure_drive(
            _joint_by_name(stage, name),
            stiffness=0.0,
            damping=0.0001,
            max_force=3.4028234663852886e38,
        )

    # Use a deterministic PreviewSurface output for the local STL assets. The
    # importer-authored OmniPBR data remains preserved in the weaker base layer.
    _configure_preview_materials(stage)

    root.SetCustomDataByKey("lekiwiGeometrySource", "dumyAssem4 + SO101")
    root.SetCustomDataByKey(
        "lekiwiMountPose",
        "xyz=0.019988279335 0.001703025019 0.052884; rpy=0 0 0",
    )
    root.SetCustomDataByKey(
        "lekiwiMountPoseSource",
        "xyz=-0.008519 -0.018162 0.052884; rpy=0 0 -2.094379865161",
    )
    root.SetCustomDataByKey(
        "lekiwiBaseForward", "base_link +X aligned with SO101 arm forward"
    )
    root.SetCustomDataByKey("lekiwiPhysicsSource", "existing Isaac USD + SO101 URDF")
    root.SetCustomDataByKey(
        "lekiwiOmniRollers",
        "36 passive sphere colliders measured from omni_wheel.stl; Kaya strategy",
    )

    stage.GetRootLayer().Save()
    print(f"LEKIWI_USD_BUILD usd={USD_PATH}", flush=True)
    print("LEKIWI_USD_BUILD result=PASS", flush=True)


try:
    main()
finally:
    simulation_app.close()
