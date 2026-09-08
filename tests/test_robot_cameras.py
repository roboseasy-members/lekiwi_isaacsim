"""Camera geometry tests; no ROS, robot hardware or GPU required."""
import json
import math
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "isaac_sim"))
from robot_cameras import attach_cameras, load_camera_config


@pytest.mark.parametrize("key,value", [
    ("translation", [110, 0, 0]),
    ("translation", [float("nan"), 0, 0]),
    ("quaternion_xyzw", [0, 0, 0, 0]),
    ("quaternion_xyzw", [0, 0, 0]),
    ("parent_link", "soarm_base_link"),
    ("resolution", [0, 480]),
    ("horizontal_fov_deg", 180),
])
def test_rejects_invalid_mount_or_camera_settings(tmp_path, key, value):
    config = load_camera_config()
    config["cameras"]["front"][key] = value
    path = tmp_path / "mounts.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError):
        load_camera_config(path)


def test_rejects_unstated_coordinate_convention(tmp_path):
    config = load_camera_config()
    config["convention"] = "usd"
    path = tmp_path / "mounts.json"
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="optical axes"):
        load_camera_config(path)


@pytest.fixture
def usd():
    pytest.importorskip("pxr.Usd")
    from pxr import Gf, Usd, UsdGeom, UsdPhysics
    return Gf, Usd, UsdGeom, UsdPhysics


def test_usd_camera_axis_conversion_and_attachment_motion(usd):
    Gf, Usd, UsdGeom, UsdPhysics = usd
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, "/LeKiwi")
    root_motion = root.AddTranslateOp()
    root_motion.Set(Gf.Vec3d(0))
    for name in ("base_link", "wrist_link"):
        link = UsdGeom.Xform.Define(stage, f"/LeKiwi/{name}")
        UsdPhysics.RigidBodyAPI.Apply(link.GetPrim())
    wrist = UsdGeom.Xformable(stage.GetPrimAtPath("/LeKiwi/wrist_link"))
    rotation = wrist.AddRotateZOp()
    rotation.Set(0)
    mounts = attach_cameras(stage)

    def transform(name):
        return UsdGeom.Xformable(stage.GetPrimAtPath(mounts[name]["camera_path"])).ComputeLocalToWorldTransform(0)

    front_before, wrist_before = transform("front"), transform("wrist")
    # USD forward -Z and up +Y must match optical forward +Z and up -Y.
    assert tuple(front_before.TransformDir(Gf.Vec3d(0, 0, -1))) == pytest.approx((1, 0, 0), abs=1e-6)
    assert tuple(front_before.TransformDir(Gf.Vec3d(0, 1, 0))) == pytest.approx((0, 0, 1), abs=1e-6)
    assert tuple(front_before.ExtractTranslation()) == pytest.approx((.110, .0017, -.0063))
    rotation.Set(40)
    assert transform("front") == front_before
    assert (transform("wrist").ExtractTranslation() - wrist_before.ExtractTranslation()).GetLength() > .02
    root_motion.Set(Gf.Vec3d(.7, -.2, 0))
    assert tuple(transform("front").ExtractTranslation() - front_before.ExtractTranslation()) == pytest.approx((.7, -.2, 0))
    assert len([p for p in stage.Traverse() if p.HasAPI(UsdPhysics.RigidBodyAPI)]) == 2
    assert not any(p.HasAPI(UsdPhysics.CollisionAPI) for p in stage.Traverse())
    with pytest.raises(ValueError, match="already exists"):
        attach_cameras(stage)


def test_bundled_robot_camera_placement_preserves_physics(usd):
    Gf, Usd, UsdGeom, UsdPhysics = usd
    stage = Usd.Stage.Open(str(ROOT / "isaac_sim/assets/lekiwi_soarm/usd/lekiwi_soarm.usd"))
    def physics_paths():
        return {str(p.GetPath()) for p in stage.Traverse() if
                p.HasAPI(UsdPhysics.RigidBodyAPI) or p.HasAPI(UsdPhysics.CollisionAPI)
                or p.IsA(UsdPhysics.Joint)}
    before = physics_paths()
    cameras = attach_cameras(stage)
    assert physics_paths() == before
    for name in ("front", "wrist"):
        prim = stage.GetPrimAtPath(cameras[name]["camera_path"])
        assert prim.IsA(UsdGeom.Camera)
        c = UsdGeom.Camera(prim)
        assert c.GetHorizontalApertureAttr().Get() / c.GetVerticalApertureAttr().Get() == pytest.approx(4 / 3)
        fov = math.degrees(2 * math.atan(c.GetHorizontalApertureAttr().Get() / (2 * c.GetFocalLengthAttr().Get())))
        assert fov == pytest.approx(70.0, abs=1e-5)
    wrist = UsdGeom.Xformable(stage.GetPrimAtPath(cameras["wrist"]["camera_path"])).ComputeLocalToWorldTransform(0)
    forward = wrist.TransformDir(Gf.Vec3d(0, 0, -1))
    assert tuple(forward) == pytest.approx((math.cos(math.radians(25)), 0, -math.sin(math.radians(25))), abs=2e-5)
    assert tuple(wrist.ExtractTranslation()) == pytest.approx((.297122, .001526, .377254), abs=2e-5)
