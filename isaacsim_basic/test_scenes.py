"""Portable USD checks; actual fall/contact checks live in smoke_test.py."""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pxr.Usd")
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade, UsdUtils

spec = importlib.util.spec_from_file_location("basic_scenes", Path(__file__).with_name("scenes.py"))
scenes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenes)


@pytest.mark.parametrize("lesson", scenes.LESSONS)
def test_stage_is_portable_and_has_explicit_units(tmp_path, lesson):
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
