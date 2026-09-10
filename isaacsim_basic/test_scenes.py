"""Portable USD checks; actual fall/contact checks live in smoke_test.py."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pxr.Usd")
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils, UsdLux

spec = importlib.util.spec_from_file_location("basic_scenes", Path(__file__).with_name("scenes.py"))
scenes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenes)


@pytest.mark.parametrize("lesson", scenes.LESSONS)
def test_stage_is_portable_and_has_explicit_units(tmp_path, lesson):
    if lesson == "experiment":
        pytest.importorskip("pxr.PhysxSchema")
    path = scenes.new_exercise(tmp_path / "clone with spaces", lesson)
    stage = Usd.Stage.Open(str(path))
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    assert UsdGeom.GetStageUpAxis(stage) == "Z"
    assert UsdPhysics.GetStageKilogramsPerUnit(stage) == 1
    assert stage.GetDefaultPrim().GetPath() == "/World"
    assert stage.GetPrimAtPath("/World/Ground").HasAPI(UsdPhysics.CollisionAPI)
    assert not stage.GetPrimAtPath("/World/Ground").HasAPI(UsdPhysics.RigidBodyAPI)
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(path))
    assert len(layers) == 1 and not assets and not unresolved


@pytest.mark.parametrize("gravity,collision", [(False, False), (True, False), (True, True)])
def test_experiments_change_only_gravity_and_cube_contact(tmp_path, gravity, collision):
    PhysxSchema = pytest.importorskip("pxr.PhysxSchema")
    stage = scenes.create_stage(tmp_path / "experiment.usda", "experiment",
        {"gravity_enabled": gravity, "collision_enabled": collision})
    cube = stage.GetPrimAtPath("/World/PracticeCube")
    assert cube.HasAPI(UsdPhysics.RigidBodyAPI)
    assert UsdPhysics.MassAPI(cube).GetMassAttr().Get() == pytest.approx(.1)
    assert PhysxSchema.PhysxRigidBodyAPI(cube).GetDisableGravityAttr().Get() == (not gravity)
    assert UsdPhysics.CollisionAPI(cube).GetCollisionEnabledAttr().Get() == collision
    assert UsdPhysics.CollisionAPI(stage.GetPrimAtPath("/World/Ground")).GetCollisionEnabledAttr().Get()
    assert UsdPhysics.Scene(stage.GetPrimAtPath("/World/PhysicsScene")).GetGravityMagnitudeAttr().Get() == pytest.approx(9.81)


def test_drop_has_three_different_behaviors(tmp_path):
    stage = scenes.create_stage(tmp_path / "drop.usda", "drop")
    for name, rigid, collision in (("VisualOnly", False, False),
                                    ("RigidOnly", True, False),
                                    ("RigidCollider", True, True)):
        prim = stage.GetPrimAtPath("/World/" + name)
        assert prim.HasAPI(UsdPhysics.RigidBodyAPI) == rigid
        assert prim.HasAPI(UsdPhysics.CollisionAPI) == collision


def test_basket_has_open_center_and_correct_landing_height(tmp_path):
    stage = scenes.create_stage(tmp_path / "basket.usda", "basket")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default"])
    parts = list(stage.GetPrimAtPath("/World/Basket").GetChildren())
    assert len(parts) == 5
    for part in parts:
        assert part.HasAPI(UsdPhysics.CollisionAPI)
        bounds = cache.ComputeWorldBound(part).ComputeAlignedRange()
        if part.GetName() == "Bottom":
            assert bounds.GetMax()[2] == pytest.approx(.02)
        else:
            # A vertical ray through the opening must not intersect a wall.
            assert not (bounds.GetMin()[0] < 0 < bounds.GetMax()[0]
                        and bounds.GetMin()[1] < 0 < bounds.GetMax()[1])


@pytest.mark.parametrize("lesson,pairs", [
    ("friction", (("RampLow", "CubeLow"), ("RampHigh", "CubeHigh"))),
    ("bounce", (("PadLow", "BallLow"), ("PadHigh", "BallHigh"))),
])
def test_contact_pairs_share_assigned_physics_material(tmp_path, lesson, pairs):
    stage = scenes.create_stage(tmp_path / "materials.usda", lesson)
    for left, right in pairs:
        materials = [UsdShade.MaterialBindingAPI(stage.GetPrimAtPath("/World/" + name))
                     .ComputeBoundMaterial("physics")[0] for name in (left, right)]
        assert all(materials)
        assert materials[0].GetPath() == materials[1].GetPath()


def test_exercise_does_not_overwrite_previous_work(tmp_path):
    first = scenes.new_exercise(tmp_path, "blank")
    first.write_text("student work")
    second = scenes.new_exercise(tmp_path, "blank")
    assert first != second
    assert first.read_text() == "student work"
    with pytest.raises(FileExistsError):
        scenes.create_stage(first)
    with pytest.raises(ValueError):
        scenes.new_exercise(tmp_path, "../../bad")


def test_mass_comparison_preserves_illumination_and_uses_saved_values(tmp_path):
    stage = scenes.create_stage(tmp_path / "mass.usda", "mass",
        {"light_mass_kg": .2, "heavy_mass_kg": 2.0, "gravity_m_s2": 1.62})
    assert stage.GetPrimAtPath("/World/Light").IsA(UsdLux.DomeLight)
    for name, mass in (("CubeLight", .2), ("CubeHeavy", 2.0)):
        cube = stage.GetPrimAtPath("/World/" + name)
        assert cube.IsA(UsdGeom.Cube)
        assert UsdPhysics.MassAPI(cube).GetMassAttr().Get() == pytest.approx(mass)
    assert UsdPhysics.Scene(stage.GetPrimAtPath("/World/PhysicsScene")).GetGravityMagnitudeAttr().Get() == pytest.approx(1.62)


@pytest.mark.parametrize("lesson,settings,attribute", [
    ("friction", {"low_friction": .8, "high_friction": .2}, "GetDynamicFrictionAttr"),
    ("bounce", {"low_restitution": .1, "high_restitution": .3}, "GetRestitutionAttr"),
])
def test_comparison_uses_custom_physics_material_values(tmp_path, lesson, settings, attribute):
    stage = scenes.create_stage(tmp_path / "custom.usda", lesson, settings)
    for name, expected in zip(("Low", "High"), settings.values()):
        mat = UsdPhysics.MaterialAPI(stage.GetPrimAtPath("/World/Materials/" + name))
        assert getattr(mat, attribute)().Get() == pytest.approx(expected)
