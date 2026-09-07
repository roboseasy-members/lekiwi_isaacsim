"""Offline mobile-manipulation course; no ROS, asset downloads or SimulationApp.

All positions are metres in the robot's initial frame: +X forward, +Y left, +Z up.
The JSON stores the actual initial layout, not merely a random seed.
"""

import json
import math
from pathlib import Path
import random
import secrets
import tempfile

ROOT = "/World/CollectionCourse"
GROUND_Z = -.021
ZONES = {"start": (.45, .95), "middle": (1.4, 2.7)}
COLORS = ((.9, .15, .12), (.15, .4, .95), (.95, .75, .1), (.2, .8, .3), (.8, .2, .8))
BASKET_CENTER = (3.6, 0.0)
BASKET_SIZE = (.44, .44, .18)
EDGE = .04


def validate_layout(layout):
    if isinstance(layout, dict) and layout.get("version") == 2:
        from color_course import validate_color_layout
        return validate_color_layout(layout)
    if not isinstance(layout, dict) or layout.get("version") != 1:
        raise ValueError("Unsupported course layout version")
    if layout.get("course") != "lekiwi_collection_v1":
        raise ValueError("Unknown course geometry")
    if type(layout.get("seed")) is not int or not 0 <= layout["seed"] < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    objects = layout.get("objects")
    if not isinstance(objects, list) or not 2 <= len(objects) <= 24:
        raise ValueError("Expected 2..24 objects")
    counts = dict.fromkeys(ZONES, 0)
    positions = []
    for i, obj in enumerate(objects):
        if not isinstance(obj, dict):
            raise ValueError("Expected object records")
        if obj.get("id") != f"block_{i:02d}" or obj.get("zone") not in ZONES:
            raise ValueError("Invalid object ID or zone")
        xyz, color = obj.get("position"), obj.get("color")
        for vector in (xyz, color):
            if (not isinstance(vector, list) or len(vector) != 3
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in vector)):
                raise ValueError("Expected finite position and color vectors")
        x, y, z = xyz
        lo, hi = ZONES[obj["zone"]]
        if not lo <= x <= hi or not .28 <= abs(y) <= .46:
            raise ValueError("Object outside pickup zone / clear driving corridor")
        if abs(z - (GROUND_Z + EDGE / 2 + .002)) > 1e-6:
            raise ValueError("Object initial height must be just above the ground")
        if any(not 0 <= c <= 1 for c in color):
            raise ValueError("Color outside [0,1]")
        yaw = obj.get("yaw_deg")
        if type(yaw) not in (int, float) or not math.isfinite(yaw) or not -180 <= yaw <= 180:
            raise ValueError("Invalid yaw in degrees")
        if any(math.hypot(x - p[0], y - p[1]) < .12 - 1e-9 for p in positions):
            raise ValueError("Overlapping pickup objects")
        positions.append(xyz)
        counts[obj["zone"]] += 1
    if any(not 1 <= count <= 12 for count in counts.values()):
        raise ValueError("Each pickup zone needs 1..12 objects")
    return layout


def generate_layout(seed=None, start_count=2, middle_count=3):
    seed = secrets.randbits(32) if seed is None else seed
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    if any(type(n) is not int or not 1 <= n <= 12 for n in (start_count, middle_count)):
        raise ValueError("Each pickup zone needs 1..12 objects")
    rng = random.Random(seed)
    objects = []
    for zone, count in (("start", start_count), ("middle", middle_count)):
        for _ in range(count):
            for attempt in range(10000):
                x = rng.uniform(*ZONES[zone])
                y = rng.choice((-1, 1)) * rng.uniform(.28, .46)
                if all(math.hypot(x - o["position"][0], y - o["position"][1]) >= .12 for o in objects):
                    break
            else:
                raise ValueError("Pickup zone too crowded; reduce object count")
            i = len(objects)
            objects.append({"id": f"block_{i:02d}", "zone": zone,
                            "position": [x, y, GROUND_Z + EDGE / 2 + .002],
                            "yaw_deg": rng.uniform(-180, 180), "color": list(COLORS[i % len(COLORS)])})
    return validate_layout({"version": 1, "course": "lekiwi_collection_v1",
                            "seed": seed, "objects": objects})


def read_layout(path):
    return validate_layout(json.loads(Path(path).read_text()))


def build_course(stage, layout, root_path=ROOT):
    """Add only an unused namespace. Never clear a user's existing stage."""
    from pxr import Gf, UsdGeom, UsdPhysics, UsdShade
    validate_layout(layout)
    if stage.GetPrimAtPath(root_path):
        raise ValueError(f"Course already exists: {root_path}")
    if (UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z
            or not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1.0)):
        raise ValueError("Course requires a Z-up, metre-scale stage")
    root = UsdGeom.Xform.Define(stage, root_path).GetPrim()
    root.SetCustomDataByKey("course_version", layout["version"])
    root.SetCustomDataByKey("seed", str(layout["seed"]))
    material = UsdShade.Material.Define(stage, root_path + "/ContactMaterial")
    physics_material = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
    physics_material.CreateStaticFrictionAttr(.8)
    physics_material.CreateDynamicFrictionAttr(.6)
    physics_material.CreateRestitutionAttr(0)

    def box(name, size, position, color, collision=False, dynamic=False, yaw=0):
        cube = UsdGeom.Cube.Define(stage, root_path + "/" + name)
        cube.CreateSizeAttr(1.0)
        cube.AddTranslateOp().Set(Gf.Vec3d(*position))
        cube.AddRotateZOp().Set(yaw)
        cube.AddScaleOp().Set(Gf.Vec3f(*size))
        cube.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        if collision:
            UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
            UsdShade.MaterialBindingAPI.Apply(cube.GetPrim()).Bind(material, materialPurpose="physics")
        if dynamic:
            UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
            UsdPhysics.MassAPI.Apply(cube.GetPrim()).CreateMassAttr(.035)
        return cube

    def ring(name, radius, width, color, z, junction_gaps=False, dashed=False):
        # Annular quads are paint on the shared flat floor, not new colliders.
        segments = 192
        points, faces = [], []
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            for r in (radius - width / 2, radius + width / 2):
                points.append(Gf.Vec3f(r * math.cos(angle), r * math.sin(angle), z))
        for i in range(segments):
            angle = 2 * math.pi * (i + .5) / segments
            if junction_gaps and min(abs(radius * math.sin(angle)), abs(radius * math.cos(angle))) < .46:
                continue
            if dashed and (i // 4) % 2:
                continue
            j = (i + 1) % segments
            faces.extend((2 * i, 2 * i + 1, 2 * j + 1, 2 * j))
        mesh = UsdGeom.Mesh.Define(stage, root_path + "/" + name)
        mesh.CreatePointsAttr(points)
        mesh.CreateFaceVertexCountsAttr([4] * (len(faces) // 4))
        mesh.CreateFaceVertexIndicesAttr(faces)
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(*color)])

    if layout["version"] == 2:
        from color_course import build_color_geometry
        build_color_geometry(box, ring, layout)
    else:
        _build_straight_road(box)
    baskets = layout.get("baskets", [{"id": "legacy", "position": [*BASKET_CENTER, GROUND_Z],
                                       "color": [.2, .55, .7]}])
    for basket in baskets:
        prefix = "Basket" if layout["version"] == 1 else "Baskets/" + basket["id"]
        _build_basket(box, prefix, basket["position"][:2], basket["color"])
    for obj in layout["objects"]:
        box("Objects/" + obj["id"], (EDGE,) * 3, obj["position"], obj["color"],
            collision=True, dynamic=True, yaw=obj["yaw_deg"])
    return root


def _build_straight_road(box):
    box("Floor", (6, 4, .1), (1.7, 0, GROUND_Z - .05), (.23, .26, .28), collision=True)
    # Road paint is visual-only: no ridges/colliders for the small omni rollers.
    box("Road/Surface", (4.4, 1.2, .0002), (1.7, 0, GROUND_Z + .0001), (.09, .10, .12))
    for name, y in (("Left", .59), ("Right", -.59)):
        box("Road/" + name, (4.4, .02, .0002), (1.7, y, GROUND_Z + .0003), (.95, .95, .95))
    for i in range(12):
        box(f"Road/Dash_{i:02d}", (.16, .015, .0002), (-.25 + i * .34, 0, GROUND_Z + .0003), (.8, .7, .25))
    box("Start", (.5, 1.1, .0002), (0, 0, GROUND_Z + .0005), (.12, .5, .25))
    box("Goal", (.65, 1.1, .0002), (3.6, 0, GROUND_Z + .0005), (.15, .3, .65))


def _build_basket(box, prefix, center, color):
    # Open basket: separate bottom and four static walls, never a solid collider.
    x, y = center
    sx, sy, height = BASKET_SIZE
    wall = .015
    box(prefix + "/Bottom", (sx, sy, wall), (x, y, GROUND_Z + wall / 2), color, collision=True)
    for name, dx, dy, dims in (
        ("Front", sx / 2 - wall / 2, 0, (wall, sy, height)),
        ("Back", -sx / 2 + wall / 2, 0, (wall, sy, height)),
        ("Left", 0, sy / 2 - wall / 2, (sx - 2 * wall, wall, height)),
        ("Right", 0, -sy / 2 + wall / 2, (sx - 2 * wall, wall, height)),
    ):
        box(prefix + "/" + name, dims, (x + dx, y + dy, GROUND_Z + height / 2), color, collision=True)


def save_course(layout, parent="/data/scenes"):
    """Create a fresh portable USD + actual layout; never overwrite a past run."""
    from pxr import Usd, UsdGeom
    validate_layout(layout)
    Path(parent).mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="course.", dir=parent))
    (directory / "layout.json").write_text(json.dumps(layout, indent=2, allow_nan=False) + "\n")
    stage = Usd.Stage.CreateNew(str(directory / "course.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = build_course(stage, layout, "/CollectionCourse")
    stage.SetDefaultPrim(root)
    stage.GetRootLayer().Save()
    return directory


def attach_course(stage, directory):
    from pxr import UsdGeom
    if stage.GetPrimAtPath(ROOT):
        raise ValueError(f"Course already exists: {ROOT}")
    if (UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z
            or not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1.0)):
        raise ValueError("Course requires a Z-up, metre-scale stage")
    stage.DefinePrim(ROOT, "Xform").GetReferences().AddReference(str(Path(directory).resolve() / "course.usda"))


def add_in_script_editor(seed=42, layout_path=None, output_dir="/data/scenes", block=None, basket=None):
    """Run inside an existing Isaac app. Does not recreate or start SimulationApp."""
    import omni.usd
    from pxr import Gf, UsdGeom, UsdPhysics
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise ValueError("Open a stage before adding the course")
    if stage.GetPrimAtPath(ROOT):
        raise ValueError("Course already present; open a fresh stage to load another")
    if not list(stage.GetPseudoRoot().GetChildren()):
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    if (UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.z
            or not math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1.0)):
        raise ValueError("Use a Z-up, metre-scale stage; existing stage was not changed")
    from color_course import generate_color_layout, select_task
    layout = read_layout(layout_path) if layout_path else generate_color_layout(seed)
    if (block is None) != (basket is None):
        raise ValueError("Specify both block and basket")
    if block is not None:
        layout = select_task(layout, block, basket)
    directory = save_course(layout, output_dir)
    attach_course(stage, directory)
    if not any(p.IsA(UsdPhysics.Scene) for p in stage.Traverse()):
        scene = UsdPhysics.Scene.Define(stage, ROOT + "/PhysicsScene")
        scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
        scene.CreateGravityMagnitudeAttr(9.81)
    print(f"LEKIWI_COURSE saved={directory} seed={layout['seed']} objects={len(layout['objects'])}")
    return directory
