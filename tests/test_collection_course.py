import copy
import json
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from collection_course import (ROOT, EDGE, GROUND_Z, build_course, generate_layout,
                               read_layout, save_course, validate_layout)


def test_seed_reproduces_actual_layout_and_both_pickup_zones():
    a = generate_layout(42)
    assert a == generate_layout(42)
    assert a != generate_layout(43)
    assert [o["zone"] for o in a["objects"]] == ["start"] * 2 + ["middle"] * 3


@pytest.mark.parametrize("seed", range(20))
def test_dense_layouts_are_separated_and_leave_center_lane_clear(seed):
    layout = generate_layout(seed, 8, 8)
    for i, o in enumerate(layout["objects"]):
        x, y, z = o["position"]
        assert abs(y) - EDGE / math.sqrt(2) > .25
        assert z == pytest.approx(GROUND_Z + EDGE / 2 + .002)
        for other in layout["objects"][:i]:
            assert math.dist([x, y], other["position"][:2]) >= .12


@pytest.mark.parametrize("args", [(-1,), (2**32,), (True,), (42, 0), (42, 13), (42, 2, 0)])
def test_bad_generation_arguments_fail(args):
    with pytest.raises(ValueError):
        generate_layout(*args)


@pytest.mark.parametrize("kind", ["overlap", "nan", "center", "outside", "height", "id", "yaw"])
def test_bad_saved_layout_rejected(kind):
    layout = generate_layout(42)
    o = layout["objects"][0]
    if kind == "overlap": layout["objects"][1]["position"] = o["position"][:]
    if kind == "nan": o["position"][0] = math.nan
    if kind == "center": o["position"][1] = 0
    if kind == "outside": o["position"][0] = 9
    if kind == "height": o["position"][2] = .5
    if kind == "id": o["id"] = "../evil"
    if kind == "yaw": o["yaw_deg"] = math.inf
    with pytest.raises(ValueError):
        validate_layout(layout)


def test_portable_export_replay_collisions_and_no_external_assets(tmp_path):
    pytest.importorskip("pxr.Usd")
    from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils
    layout = generate_layout(42)
    directory = save_course(layout, tmp_path)
    second = save_course(layout, tmp_path)
    assert second != directory
    assert read_layout(directory / "layout.json") == layout
    stage = Usd.Stage.Open(str(directory / "course.usda"))
    root = "/CollectionCourse"
    assert stage.GetDefaultPrim().GetPath() == root
    assert UsdGeom.GetStageUpAxis(stage) == "Z"
    assert UsdGeom.GetStageMetersPerUnit(stage) == 1
    for o in layout["objects"]:
        p = stage.GetPrimAtPath(root + "/Objects/" + o["id"])
        assert p.HasAPI(UsdPhysics.RigidBodyAPI) and p.HasAPI(UsdPhysics.CollisionAPI)
        assert tuple(p.GetAttribute("xformOp:translate").Get()) == pytest.approx(o["position"])
    assert len(stage.GetPrimAtPath(root + "/Basket").GetChildren()) == 5
    for p in stage.Traverse():
        if "/Road/" in str(p.GetPath()):
            assert not p.HasAPI(UsdPhysics.CollisionAPI)
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(directory / "course.usda"))
    assert len(layers) == 1 and not assets and not unresolved
    with pytest.raises(ValueError, match="already exists"):
        build_course(stage, layout, root)


def test_wrong_stage_units_do_not_modify_existing_stage():
    pytest.importorskip("pxr.Usd")
    from pxr import Usd
    stage = Usd.Stage.CreateInMemory()
    before = stage.GetRootLayer().ExportToString()
    with pytest.raises(ValueError, match="metre"):
        build_course(stage, generate_layout(1))
    assert stage.GetRootLayer().ExportToString() == before
