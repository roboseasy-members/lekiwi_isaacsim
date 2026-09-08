"""Self-contained classroom stages. Only USD primitives; no robot/remote assets."""
from pathlib import Path
import math
import tempfile

from pxr import Gf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade

LESSONS = ("blank", "drop", "mass", "friction", "bounce", "basket", "joints")


def box(stage, path, position, size, color, *, collision=True, mass=None, angle=0):
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    cube.AddTranslateOp().Set(Gf.Vec3d(*position))
    cube.AddRotateXYZOp().Set(Gf.Vec3f(0, angle, 0))
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    cube.CreateDisplayColorAttr([Gf.Vec3f(*color)])
    if collision:
        UsdPhysics.CollisionAPI.Apply(cube.GetPrim())
    if mass is not None:
        UsdPhysics.RigidBodyAPI.Apply(cube.GetPrim())
        UsdPhysics.MassAPI.Apply(cube.GetPrim()).CreateMassAttr(mass)
    return cube.GetPrim()


def material(stage, name, friction=0.5, restitution=0):
    mat = UsdShade.Material.Define(stage, "/World/Materials/" + name)
    physics = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    physics.CreateStaticFrictionAttr(friction)
    physics.CreateDynamicFrictionAttr(friction)
    physics.CreateRestitutionAttr(restitution)
    # Both sides of every comparison use identical values; no reliance on
    # combine-mode defaults or inherited materials.
    return mat


def bind(prim, mat):
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(mat, materialPurpose="physics")


def create_stage(path, lesson="blank"):
    if lesson not in LESSONS:
        raise ValueError(f"Unknown lesson: {lesson}")
    if Path(path).exists():
        raise FileExistsError(path)
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    stage.SetTimeCodesPerSecond(60)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    scene = UsdPhysics.Scene.Define(stage, "/World/PhysicsScene")
    scene.CreateGravityDirectionAttr(Gf.Vec3f(0, 0, -1))
    scene.CreateGravityMagnitudeAttr(9.81)
    UsdLux.DomeLight.Define(stage, "/World/Light").CreateIntensityAttr(800)
    floor = box(stage, "/World/Ground", (0, 0, -.05), (6, 4, .1), (.18, .21, .25))
    bind(floor, material(stage, "Ground"))

    if lesson == "drop":
        for name, x, color, collision, mass in (
            ("VisualOnly", -.5, (.9, .2, .2), False, None),
            ("RigidOnly", 0, (.95, .6, .1), False, .1),
            ("RigidCollider", .5, (.1, .7, .35), True, .1),
        ):
            box(stage, "/World/" + name, (x, 0, .7), (.1,)*3,
                color, collision=collision, mass=mass)
    elif lesson == "mass":
        for name, x, mass in (("Light", -.3, .1), ("Heavy", .3, 1.0)):
            box(stage, "/World/" + name, (x, 0, 1), (.1,)*3, (.2, .6, .95), mass=mass)
    elif lesson == "friction":
        for name, y, mu, color in (("Low", -.4, .05, (.95, .5, .1)),
                                    ("High", .4, .8, (.1, .65, .95))):
            mat = material(stage, name, friction=mu)
            ramp = box(stage, f"/World/Ramp{name}", (0, y, .4),
                       (1.6, .5, .06), (.4, .45, .5), angle=15)
            # Place on the slope using its local tangent and normal. Avoid
            # initial penetration or a drop impact that hides static friction.
            theta = math.radians(15)
            along, normal = -.5, .081
            x = along * math.cos(theta) + normal * math.sin(theta)
            z = .4 - along * math.sin(theta) + normal * math.cos(theta)
            cube = box(stage, f"/World/Cube{name}", (x, y, z), (.1,)*3,
                       color, mass=.1, angle=15)
            bind(ramp, mat)
            bind(cube, mat)
    elif lesson == "bounce":
        for name, x, restitution, color in (("Low", -.5, 0.0, (.95, .5, .1)),
                                            ("High", .5, .8, (.1, .65, .95))):
            mat = material(stage, name, restitution=restitution)
            pad = box(stage, f"/World/Pad{name}", (x, 0, .05), (.7, .7, .1), (.4, .45, .5))
            sphere = UsdGeom.Sphere.Define(stage, f"/World/Ball{name}")
            sphere.CreateRadiusAttr(.05)
            sphere.AddTranslateOp().Set(Gf.Vec3d(x, 0, 1))
            sphere.CreateDisplayColorAttr([Gf.Vec3f(*color)])
            UsdPhysics.RigidBodyAPI.Apply(sphere.GetPrim())
            UsdPhysics.CollisionAPI.Apply(sphere.GetPrim())
            UsdPhysics.MassAPI.Apply(sphere.GetPrim()).CreateMassAttr(.1)
            bind(pad, mat)
            bind(sphere.GetPrim(), mat)
    elif lesson == "basket":
        UsdGeom.Xform.Define(stage, "/World/Basket")
        for name, pos, size in (
            ("Bottom", (0, 0, .01), (.44, .44, .02)),
            ("Left", (0, -.21, .12), (.44, .02, .2)),
            ("Right", (0, .21, .12), (.44, .02, .2)),
            ("Front", (.21, 0, .12), (.02, .4, .2)),
            ("Back", (-.21, 0, .12), (.02, .4, .2)),
        ):
            box(stage, "/World/Basket/" + name, pos, size, (.15, .55, .8))
        box(stage, "/World/Cube", (0, 0, .6), (.04,)*3, (.95, .25, .12), mass=.035)
    elif lesson == "joints":
        # Scales belong to the visual/collision children. Joint anchor distances
        # are then measured in unscaled rigid-body frames, directly in meters.
        for name, z, size, color, mass in (
            ("Base", .15, (.18, .18, .3), (.15, .55, .8), 1.0),
            ("Arm", .45, (.06, .06, .3), (.95, .5, .1), .1),
        ):
            body = UsdGeom.Xform.Define(stage, "/World/Hinge/" + name)
            body.AddTranslateOp().Set(Gf.Vec3d(0, 0, z))
            UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
            UsdPhysics.MassAPI.Apply(body.GetPrim()).CreateMassAttr(mass)
            box(stage, str(body.GetPath()) + "/Shape", (0, 0, 0), size, color)
        fixed = UsdPhysics.FixedJoint.Define(stage, "/World/Hinge/FixedBase")
        fixed.CreateBody1Rel().SetTargets(["/World/Hinge/Base"])
        fixed.CreateLocalPos0Attr(Gf.Vec3f(0, 0, .15))
        UsdPhysics.ArticulationRootAPI.Apply(fixed.GetPrim())
        joint = UsdPhysics.RevoluteJoint.Define(stage, "/World/Hinge/Shoulder")
        joint.CreateBody0Rel().SetTargets(["/World/Hinge/Base"])
        joint.CreateBody1Rel().SetTargets(["/World/Hinge/Arm"])
        joint.CreateLocalPos0Attr(Gf.Vec3f(0, 0, .15))
        joint.CreateLocalPos1Attr(Gf.Vec3f(0, 0, -.15))
        joint.CreateAxisAttr("Y")
        joint.CreateLowerLimitAttr(-60)
        joint.CreateUpperLimitAttr(60)
        joint.CreateCollisionEnabledAttr(False)
        drive = UsdPhysics.DriveAPI.Apply(joint.GetPrim(), "angular")
        drive.CreateTypeAttr("force")
        drive.CreateStiffnessAttr(1000)
        drive.CreateDampingAttr(50)
        drive.CreateMaxForceAttr(100)
        drive.CreateTargetPositionAttr(0)
        drive.CreateTargetVelocityAttr(0)
    stage.GetRootLayer().Save()
    return stage


def new_exercise(parent, lesson):
    """Fresh writable copy each launch; never overwrite an earlier exercise."""
    if lesson not in LESSONS:
        raise ValueError(f"Unknown lesson: {lesson}")
    parent = Path(parent)
    parent.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f"{lesson}.", dir=parent))
    path = directory / "scene.usda"
    create_stage(path, lesson)
    return path
