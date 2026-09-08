"""Camera geometry tests; no ROS, robot hardware or GPU required."""
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

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
    assert tuple(front_before.ExtractTranslation()) == pytest.approx((.106898279335, .001703025019, -.006396))
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


def test_drawing_camera_centers_and_optical_axes_at_measurement_pose(usd):
    """실제 URDF 관절 체인과 USD 카메라를 합성해 도면 치수·정면을 검증한다."""
    Gf, Usd, UsdGeom, UsdPhysics = usd
    model = ET.parse(ROOT / "isaac_sim/assets/lekiwi_soarm/urdf/lekiwi_soarm.urdf")
    joints = {j.find("child").get("link"): j for j in model.findall("joint")}
    angles = dict(shoulder_pan=0, shoulder_lift=-90, elbow_flex=90,
                  wrist_flex=0, wrist_roll=-90, gripper=0)

    def rotation(axis, degrees):
        return Gf.Matrix4d(1).SetRotate(Gf.Rotation(Gf.Vec3d(*axis), degrees))

    def link_transform(name):
        if name == "base_link":
            return Gf.Matrix4d(1)
        joint = joints[name]
        origin = joint.find("origin")
        rpy = [float(v) for v in origin.get("rpy", "0 0 0").split()]
        xyz = [float(v) for v in origin.get("xyz", "0 0 0").split()]
        local = Gf.Matrix4d(1)
        for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), rpy):
            local *= rotation(axis, math.degrees(angle))
        local *= Gf.Matrix4d(1).SetTranslate(Gf.Vec3d(*xyz))
        if joint.get("type") != "fixed":
            axis = [float(v) for v in joint.find("axis").get("xyz").split()]
            local = rotation(axis, angles.get(joint.get("name"), 0)) * local
        return local * link_transform(joint.find("parent").get("link"))

    stage = Usd.Stage.CreateInMemory()
    for name in ("base_link", "wrist_link"):
        link = UsdGeom.Xform.Define(stage, f"/LeKiwi/{name}")
        link.AddTransformOp().Set(link_transform(name))
        UsdPhysics.RigidBodyAPI.Apply(link.GetPrim())
    cameras = attach_cameras(stage)
    base_inverse = link_transform("soarm_base_link").GetInverse()
    expected = {
        "front": ((.08691, 0, -.05928), (1, 0, 0)),
        "wrist": ((.20540, 0, .20858), (math.sqrt(.5), 0, -math.sqrt(.5))),
    }
    for name, (center, forward) in expected.items():
        camera = UsdGeom.Xformable(stage.GetPrimAtPath(cameras[name]["camera_path"]))
        transform = camera.ComputeLocalToWorldTransform(0) * base_inverse
        assert tuple(transform.ExtractTranslation()) == pytest.approx(center, abs=1e-8)
        # USD orient의 float 정밀도를 허용한다.
        assert tuple(transform.TransformDir(Gf.Vec3d(0, 0, -1))) == pytest.approx(forward, abs=1e-7)
        assert tuple(transform.TransformDir(Gf.Vec3d(1, 0, 0))) == pytest.approx((0, -1, 0), abs=1e-7)
