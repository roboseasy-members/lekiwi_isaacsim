import copy
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from collection_course import EDGE, read_layout, save_course, validate_layout
from color_course import (COLORS, LANES, RING_RADIUS, ROAD_WIDTH, BASKET_DISTANCE,
                          generate_color_layout, make_task, select_task)


@pytest.mark.parametrize("seed", range(12))
def test_four_matching_color_lanes_with_clear_center_and_repeatable_positions(seed):
    layout = generate_color_layout(seed)
    assert layout == generate_color_layout(seed)
    assert len(layout["objects"]) == len(layout["baskets"]) == 4
    assert [o["color_name"] for o in layout["objects"]] == list(COLORS)
    for obj, basket in zip(layout["objects"], layout["baskets"]):
        assert obj["lane"] == basket["lane"] == obj["color_name"] == basket["color_name"]
        assert obj["color"] == basket["color"]
        x, y, _ = obj["position"]
        dx, dy = LANES[obj["lane"]]
        assert abs(-x * dy + y * dx) - EDGE / math.sqrt(2) > .25
        assert math.hypot(x, y) > .7
    assert layout["objects"] != generate_color_layout(seed + 100)["objects"]
    changed = generate_color_layout(seed + 100)
    assert layout["baskets"] == changed["baskets"]
    for original, new in zip(layout["objects"], changed["objects"]):
        assert original["yaw_deg"] == new["yaw_deg"] == 0
        assert {k: v for k, v in original.items() if k != "position"} == {
            k: v for k, v in new.items() if k != "position"}


@pytest.mark.parametrize("block", COLORS)
@pytest.mark.parametrize("basket", COLORS)
def test_all_sixteen_tasks_do_not_change_geometry(block, basket):
    original = generate_color_layout(42)
    snapshot = copy.deepcopy(original)
    selected = select_task(original, block, basket)
    assert original == snapshot
    assert selected["objects"] == original["objects"] and selected["baskets"] == original["baskets"]
    assert selected["task"] == make_task(block, basket)
    assert selected["task"]["block_id"] == f"block_{block}"
    assert selected["task"]["basket_id"] == f"basket_{basket}"
    assert block in selected["task"]["instruction"] and basket in selected["task"]["instruction"]
    assert validate_layout(selected) is selected


def test_unseeded_course_randomizes_every_block_but_keeps_lanes(monkeypatch):
    seeds = iter((42, 123))
    monkeypatch.setattr("color_course.secrets.randbits", lambda bits: next(seeds))
    first, second = generate_color_layout(), generate_color_layout()
    assert first["baskets"] == second["baskets"]
    for old, new in zip(first["objects"], second["objects"]):
        assert old["position"] != new["position"]
        assert {k: v for k, v in old.items() if k != "position"} == {
            k: v for k, v in new.items() if k != "position"}


def test_runtime_random_course_branch_and_no_task_window():
    import ast
    source = (Path(__file__).resolve().parents[1] / "isaac_sim/keyboard_drive.py").read_text()
    tree = ast.parse(source)
    branch = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                  and ast.unparse(node.test) == "COURSE_LAYOUT == 'random'")
    namespace = {}
    exec(compile(ast.Module(body=branch.body, type_ignores=[]), "random-course", "exec"), namespace)
    assert validate_layout(namespace["layout"])["version"] == 2
    assert "Collection Task" not in source
    assert "Apply task" not in source


@pytest.mark.parametrize("kind", ["count", "duplicate", "basket_color", "block_color", "position",
                                   "nan", "rotation", "task_id", "instruction", "unknown_basket"])
def test_reject_inconsistent_saved_scene_or_task(kind):
    layout = generate_color_layout(42)
    if kind == "count": layout["objects"].pop()
    if kind == "duplicate": layout["objects"][1] = layout["objects"][0]
    if kind == "basket_color": layout["baskets"][0]["color_name"] = "green"
    if kind == "block_color": layout["objects"][0]["color"] = [0, 0, 1]
    if kind == "position": layout["objects"][0]["position"] = [0, 0, 0]
    if kind == "nan": layout["objects"][0]["position"][0] = math.nan
    if kind == "rotation": layout["objects"][0]["yaw_deg"] = 20
    if kind == "task_id": layout["task"]["block_id"] = "block_green"
    if kind == "instruction": layout["task"]["instruction"] = "Wrong instruction"
    if kind == "unknown_basket": layout["task"]["basket"] = "blue"
    with pytest.raises(ValueError):
        validate_layout(layout)


def test_color_usd_is_portable_and_all_baskets_are_open(tmp_path):
    pytest.importorskip("pxr.Usd")
    from pxr import Usd, UsdPhysics, UsdUtils
    layout = generate_color_layout(42, "green", "red")
    folder = save_course(layout, tmp_path)
    assert read_layout(folder / "layout.json") == layout
    stage = Usd.Stage.Open(str(folder / "course.usda"))
    root = "/CollectionCourse"
    for name, rgb in COLORS.items():
        block = stage.GetPrimAtPath(root + f"/Objects/block_{name}")
        basket = stage.GetPrimAtPath(root + f"/Baskets/basket_{name}")
        assert block.HasAPI(UsdPhysics.RigidBodyAPI)
        assert tuple(block.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(rgb)
        assert len(basket.GetChildren()) == 5
        for wall in basket.GetChildren():
            assert wall.HasAPI(UsdPhysics.CollisionAPI)
            assert not wall.HasAPI(UsdPhysics.RigidBodyAPI)
            assert tuple(wall.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(rgb)
    for prim in stage.Traverse():
        if "/Road/" in str(prim.GetPath()):
            assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    layers, assets, missing = UsdUtils.ComputeAllDependencies(str(folder / "course.usda"))
    assert len(layers) == 1 and not assets and not missing
    ring = stage.GetPrimAtPath(root + "/Road/Ring/Surface")
    assert len(ring.GetAttribute("faceVertexCounts").Get()) == 192
    radii = [math.hypot(p[0], p[1]) for p in ring.GetAttribute("points").Get()]
    assert min(radii) == pytest.approx(RING_RADIUS - ROAD_WIDTH / 2)
    assert max(radii) == pytest.approx(RING_RADIUS + ROAD_WIDTH / 2)
    assert BASKET_DISTANCE - .44 / 2 > RING_RADIUS + ROAD_WIDTH / 2
