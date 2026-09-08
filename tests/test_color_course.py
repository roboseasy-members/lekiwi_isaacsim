import copy
import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from collection_course import EDGE, read_layout, save_course, validate_layout
from color_course import (COLORS, LANES, RING_RADIUS, ROAD_WIDTH, BASKET_DISTANCE,
                          generate_color_layout, make_task, select_task, road_boundary_strips)


def _paint_contains(points, faces, position):
    def cross(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    for face in faces:
        for triangle in ((face[0], face[1], face[2]), (face[0], face[2], face[3])):
            a, b, c = (points[i] for i in triangle)
            if min(cross(a, b, position), cross(b, c, position), cross(c, a, position)) >= -1e-10:
                return True
    return False


@pytest.mark.parametrize("quarter", range(4))
def test_white_edges_join_without_corner_gaps_or_inner_protrusions(quarter):
    strips = {name: (points, faces) for name, points, faces in road_boundary_strips()}
    def painted(name, x, y):
        for _ in range(quarter):
            x, y = -y, x
        return _paint_contains(*strips[name], (x, y))
    inner, outer = RING_RADIUS - ROAD_WIDTH / 2, RING_RADIUS + ROAD_WIDTH / 2
    # Previously missing center-corner join, inner overhang, and outer gap.
    assert painted("Inside", .44, .44)
    assert painted("Inside", math.sqrt(inner**2 - .44**2) - .005, .44)
    assert not painted("Inside", inner - .015, .44)
    assert painted("Outside", math.sqrt(outer**2 - .44**2) + .015, .44)
    for name, radius in (("Inside", inner), ("Outside", outer)):
        assert painted(name, radius / math.sqrt(2), radius / math.sqrt(2))


def test_boundary_mesh_has_shared_seams_and_upward_faces():
    from collections import Counter
    for name, points, faces in road_boundary_strips():
        edges = Counter()
        for face in faces:
            polygon = [points[i] for i in face]
            area2 = sum(a[0]*b[1] - a[1]*b[0] for a, b in zip(polygon, polygon[1:] + polygon[:1]))
            assert area2 > 0  # Visible from above, including outer junction caps.
            for a, b in zip(face, face[1:] + face[:1]):
                edges[tuple(sorted((a, b)))] += 1
        assert set(edges.values()) == {1, 2}
        assert len(points) - len(edges) + len(faces) == (0 if name == "Inside" else 4)


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
        assert -180 <= original["yaw_deg"] <= 180
        assert original["yaw_deg"] != new["yaw_deg"]
        assert {k: v for k, v in original.items() if k not in {"position", "yaw_deg"}} == {
            k: v for k, v in new.items() if k not in {"position", "yaw_deg"}}


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
        assert old["yaw_deg"] != new["yaw_deg"]
        assert {k: v for k, v in old.items() if k not in {"position", "yaw_deg"}} == {
            k: v for k, v in new.items() if k not in {"position", "yaw_deg"}}


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
                                   "nan", "rotation", "rotation_nan", "rotation_bool",
                                   "task_id", "instruction", "unknown_basket"])
def test_reject_inconsistent_saved_scene_or_task(kind):
    layout = generate_color_layout(42)
    if kind == "count": layout["objects"].pop()
    if kind == "duplicate": layout["objects"][1] = layout["objects"][0]
    if kind == "basket_color": layout["baskets"][0]["color_name"] = "green"
    if kind == "block_color": layout["objects"][0]["color"] = [0, 0, 1]
    if kind == "position": layout["objects"][0]["position"] = [0, 0, 0]
    if kind == "nan": layout["objects"][0]["position"][0] = math.nan
    if kind == "rotation": layout["objects"][0]["yaw_deg"] = 181
    if kind == "rotation_nan": layout["objects"][0]["yaw_deg"] = math.nan
    if kind == "rotation_bool": layout["objects"][0]["yaw_deg"] = True
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
        expected_yaw = next(obj["yaw_deg"] for obj in layout["objects"] if obj["color_name"] == name)
        assert block.GetAttribute("xformOp:rotateZ").Get() == pytest.approx(expected_yaw)
        assert tuple(block.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(rgb)
        assert len(basket.GetChildren()) == 5
        for wall in basket.GetChildren():
            assert wall.HasAPI(UsdPhysics.CollisionAPI)
            assert not wall.HasAPI(UsdPhysics.RigidBodyAPI)
            assert tuple(wall.GetAttribute("primvars:displayColor").Get()[0]) == pytest.approx(rgb)
    for prim in stage.Traverse():
        if "/Road/" in str(prim.GetPath()):
            assert not prim.HasAPI(UsdPhysics.CollisionAPI)
    for name in COLORS:
        assert not stage.GetPrimAtPath(root + f"/Road/{name}/Left0")
    for name, points, faces in road_boundary_strips():
        border = stage.GetPrimAtPath(root + f"/Road/Ring/{name}")
        assert len(border.GetAttribute("points").Get()) == len(points)
        assert len(border.GetAttribute("faceVertexCounts").Get()) == len(faces)
    layers, assets, missing = UsdUtils.ComputeAllDependencies(str(folder / "course.usda"))
    assert len(layers) == 1 and not assets and not missing
    ring = stage.GetPrimAtPath(root + "/Road/Ring/Surface")
    assert len(ring.GetAttribute("faceVertexCounts").Get()) == 192
    radii = [math.hypot(p[0], p[1]) for p in ring.GetAttribute("points").Get()]
    assert min(radii) == pytest.approx(RING_RADIUS - ROAD_WIDTH / 2)
    assert max(radii) == pytest.approx(RING_RADIUS + ROAD_WIDTH / 2)
    assert BASKET_DISTANCE - .44 / 2 > RING_RADIUS + ROAD_WIDTH / 2
