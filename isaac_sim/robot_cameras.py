"""Robot-mounted USD cameras. All mount poses describe the lens optical center.

No ROS dependency or hardware access. Optical axes: +X right, +Y down, +Z forward.
Camera bodies are visualization geometry only and do not alter robot physics.
"""

import json
import math
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent / "assets/cameras/mounts.json"
CAMERA_NAMES = ("front", "wrist")


def load_camera_config(path=None):
    config = json.loads(Path(path or DEFAULT_CONFIG).read_text())
    if (config.get("version") != 1 or config.get("units") != "m"
            or config.get("convention") != "optical_x_right_y_down_z_forward"):
        raise ValueError("Camera mounts require version 1, metres and optical axes")
    if not isinstance(config.get("calibrated"), bool):
        raise ValueError("Camera mounts must explicitly declare calibrated true/false")
    cameras = config.get("cameras", {})
    if set(cameras) != set(CAMERA_NAMES):
        raise ValueError("Expected exactly front and wrist cameras")
    for name, camera in cameras.items():
        if camera.get("parent_link") not in {"base_link", "wrist_link", "gripper_link"}:
            raise ValueError(f"{name}: unsupported physical parent link")
        for key, size in (("translation", 3), ("quaternion_xyzw", 4)):
            values = camera.get(key)
            if (not isinstance(values, list) or len(values) != size
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
                raise ValueError(f"{name}: expected {size} finite numbers for {key}")
        if any(abs(v) > 1.0 for v in camera["translation"]):
            raise ValueError(f"{name}: mount exceeds 1 m; check mm versus m")
        norm = math.sqrt(sum(v * v for v in camera["quaternion_xyzw"]))
        if abs(norm - 1.0) > 1e-5:
            raise ValueError(f"{name}: quaternion_xyzw must have unit length")
        resolution = camera.get("resolution")
        if (not isinstance(resolution, list) or len(resolution) != 2
                or any(type(v) is not int or not 16 <= v <= 4096 for v in resolution)):
            raise ValueError(f"{name}: invalid image resolution")
        fov = camera.get("horizontal_fov_deg")
        if type(fov) not in (int, float) or not math.isfinite(fov) or not 5 <= fov <= 150:
            raise ValueError(f"{name}: invalid horizontal field of view")
    if cameras["front"]["parent_link"] != "base_link":
        raise ValueError("Front camera must follow base_link")
    if cameras["wrist"]["parent_link"] not in {"wrist_link", "gripper_link"}:
        raise ValueError("Wrist camera must follow a wrist link")
    return config


def attach_cameras(stage, config=None):
    """Attach to physical links, preserving motion through USD parent transforms.

    Config quaternions map optical-frame vectors into parent-link coordinates.
    USD's camera sees along -Z with +Y up, hence its extra 180-degree X rotation.
    """
    from pxr import Gf, UsdGeom, UsdPhysics

    config = config or load_camera_config()
    parents = {}
    for name in CAMERA_NAMES:
        link = config["cameras"][name]["parent_link"]
        matches = [p for p in stage.Traverse()
                   if p.GetPath().HasPrefix("/LeKiwi") and p.GetName() == link
                   and p.HasAPI(UsdPhysics.RigidBodyAPI)]
        if len(matches) != 1:
            raise ValueError(f"Expected one rigid body for camera parent {link}")
        parents[name] = matches[0]
        path = matches[0].GetPath().AppendChild(f"{name}_camera_optical_frame")
        if stage.GetPrimAtPath(path):
            raise ValueError(f"Camera mount already exists: {path}")

    result = {}
    for name in CAMERA_NAMES:
        settings = config["cameras"][name]
        path = parents[name].GetPath().AppendChild(f"{name}_camera_optical_frame")
        mount = UsdGeom.Xform.Define(stage, path)
        mount.AddTranslateOp().Set(Gf.Vec3d(*settings["translation"]))
        x, y, z, w = settings["quaternion_xyzw"]
        mount.AddOrientOp().Set(Gf.Quatf(w, Gf.Vec3f(x, y, z)))
        mount.GetPrim().SetCustomDataByKey("calibrated", config["calibrated"])
        mount.GetPrim().SetCustomDataByKey("frameConvention", config["convention"])
        camera = UsdGeom.Camera.Define(stage, path.AppendChild("Camera"))
        camera.AddRotateXOp().Set(180.0)
        camera.CreateProjectionAttr("perspective")
        # USD aperture/focal-length values share tenths-of-stage-unit units.
        aperture = 20.955
        width, height = settings["resolution"]
        camera.CreateHorizontalApertureAttr(aperture)
        camera.CreateVerticalApertureAttr(aperture * height / width)
        camera.CreateFocalLengthAttr(aperture / (2 * math.tan(math.radians(settings["horizontal_fov_deg"]) / 2)))
        camera.CreateClippingRangeAttr(Gf.Vec2f(0.004, 100.0))
        camera.CreateFocusDistanceAttr(0.3)
        camera.CreateFStopAttr(0.0)

        # Body and lens end at optical Z=0; neither obstructs the forward view.
        body = UsdGeom.Cube.Define(stage, path.AppendChild("Housing"))
        body.CreateSizeAttr(1.0)
        body.AddTranslateOp().Set(Gf.Vec3d(0, 0, -0.012))
        body.AddScaleOp().Set(Gf.Vec3f(0.024, 0.024, 0.016))
        body.CreateDisplayColorAttr([Gf.Vec3f(0.08, 0.09, 0.11)])
        lens = UsdGeom.Cylinder.Define(stage, path.AppendChild("Lens"))
        lens.CreateAxisAttr("Z")
        lens.CreateRadiusAttr(0.006)
        lens.CreateHeightAttr(0.004)
        lens.AddTranslateOp().Set(Gf.Vec3d(0, 0, -0.002))
        lens.CreateDisplayColorAttr([Gf.Vec3f(0.08, 0.35, 0.55)])
        result[name] = {"camera_path": str(camera.GetPath()), "optical_frame": str(path),
                        "resolution": tuple(settings["resolution"])}
    return result
