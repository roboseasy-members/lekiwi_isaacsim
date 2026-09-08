"""Four matching-color lanes and explicit pick/place task metadata."""
import copy
import math
import random
import secrets

from collection_course import EDGE, GROUND_Z

COLORS = {
    "red": (.90, .12, .10), "orange": (1.0, .40, .04),
    "yellow": (.95, .82, .08), "green": (.12, .72, .25),
}
KOREAN = {"red": "빨간색", "orange": "주황색", "yellow": "노란색", "green": "초록색"}
# Initial overview: up=+X, down=-X, left=+Y, right=-Y. Camera-independent IDs.
LANES = {"red": (1, 0), "orange": (-1, 0), "yellow": (0, 1), "green": (0, -1)}
RING_RADIUS = 2.2
ROAD_WIDTH = .9
BASKET_DISTANCE = 3.05
SPOKE_END = 3.35
EDGE_WIDTH = .02


def road_boundary_strips():
    """Continuous white strips at exact line/circle intersections, in XY metres.

    Each inner island is a closed outline; each outer arc joins two spoke edges.
    Both sides of the strip have their own intersection so finite-width paint
    meets without overlapping caps, missing wedges or protruding straight ends.
    """
    half = ROAD_WIDTH / 2
    for name, radius, closed in (("Inside", RING_RADIUS - half, True),
                                  ("Outside", RING_RADIUS + half, False)):
        contours = []
        for h, r in ((half - EDGE_WIDTH, radius + EDGE_WIDTH / 2 if closed else radius - EDGE_WIDTH / 2),
                     (half, radius - EDGE_WIDTH / 2 if closed else radius + EDGE_WIDTH / 2)):
            angle = math.asin(h / r)
            arc = [(r * math.cos(angle + (math.pi / 2 - 2 * angle) * i / 48),
                    r * math.sin(angle + (math.pi / 2 - 2 * angle) * i / 48))
                   for i in range(49)]
            # Share exact coordinates with straight segments, including corners.
            arc[0] = (math.sqrt(r * r - h * h), h)
            arc[-1] = (h, math.sqrt(r * r - h * h))
            contours.append(([(h, h)] + arc) if closed else
                            ([(SPOKE_END, h)] + arc + [(h, SPOKE_END)]))
        points, faces = [], []
        count = len(contours[0])
        for quarter in range(4):
            offset = len(points)
            for contour in contours:
                for x, y in contour:
                    for _ in range(quarter):
                        x, y = -y, x
                    points.append((x, y))
            for i in range(count if closed else count - 1):
                j = (i + 1) % count
                face = (offset + i, offset + j, offset + count + j, offset + count + i)
                faces.append(face if closed else tuple(reversed(face)))
        yield name, points, faces


def make_task(block, basket):
    if not isinstance(block, str) or not isinstance(basket, str) or block not in COLORS or basket not in COLORS:
        raise ValueError("Choose red, orange, yellow or green for both block and basket")
    return {"id": f"pick_{block}_place_{basket}", "block": block, "basket": basket,
            "block_id": f"block_{block}", "basket_id": f"basket_{basket}",
            "instruction": f"Put the {block} block into the {basket} basket.",
            "instruction_ko": f"{KOREAN[block]} 블록을 {KOREAN[basket]} 바구니에 넣어."}


def basket_specs():
    return [{"id": f"basket_{name}", "lane": name, "color_name": name,
             "color": list(COLORS[name]), "position": [BASKET_DISTANCE * x, BASKET_DISTANCE * y, GROUND_Z]}
            for name, (x, y) in LANES.items()]


def validate_color_layout(layout):
    if layout.get("version") != 2 or layout.get("course") != "lekiwi_color_ring_cross_v2":
        raise ValueError("Unsupported color course")
    if type(layout.get("seed")) is not int or not 0 <= layout["seed"] < 2**32:
        raise ValueError("Invalid seed")
    if layout.get("baskets") != basket_specs():
        raise ValueError("Each lane must have its matching-color basket at its endpoint")
    objects = layout.get("objects")
    if not isinstance(objects, list) or len(objects) != 4:
        raise ValueError("Exactly four colored blocks are required")
    for obj, (name, (dx, dy)) in zip(objects, LANES.items()):
        if (not isinstance(obj, dict) or obj.get("id") != f"block_{name}"
                or obj.get("lane") != name or obj.get("color_name") != name
                or obj.get("color") != list(COLORS[name])):
            raise ValueError("Each lane must have exactly one matching-color block")
        xyz = obj.get("position")
        if (not isinstance(xyz, list) or len(xyz) != 3
                or any(type(v) not in (float, int) or not math.isfinite(v) for v in xyz)):
            raise ValueError("Expected finite object position")
        along, lateral = xyz[0] * dx + xyz[1] * dy, -xyz[0] * dy + xyz[1] * dx
        if not .7 <= along <= 1.5 or not .28 <= abs(lateral) <= .38:
            raise ValueError("Block outside its lane pickup zone / inside driving corridor")
        if abs(xyz[2] - (GROUND_Z + EDGE / 2 + .002)) > 1e-6:
            raise ValueError("Invalid block height")
        yaw = obj.get("yaw_deg")
        if type(yaw) not in (int, float) or not math.isfinite(yaw) or not -180 <= yaw <= 180:
            raise ValueError("Block yaw must be finite and within [-180, 180] degrees")
    task = layout.get("task")
    if not isinstance(task, dict) or task != make_task(task.get("block"), task.get("basket")):
        raise ValueError("Task instruction and object IDs must agree")
    return layout


def generate_color_layout(seed=None, block="red", basket="red"):
    seed = secrets.randbits(32) if seed is None else seed
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Seed must be an integer in [0, 2**32)")
    rng = random.Random(seed)
    objects = []
    for name, (dx, dy) in LANES.items():
        along = rng.uniform(.7, 1.5)
        lateral = rng.choice((-1, 1)) * rng.uniform(.28, .38)
        objects.append({"id": f"block_{name}", "lane": name, "color_name": name,
                        "color": list(COLORS[name]), "yaw_deg": 0,
                        "position": [dx * along - dy * lateral, dy * along + dx * lateral,
                                     GROUND_Z + EDGE / 2 + .002]})
    # Draw rotations after positions to preserve the existing seed-to-position mapping.
    for obj in objects:
        obj["yaw_deg"] = rng.uniform(-180, 180)
    return validate_color_layout({"version": 2, "course": "lekiwi_color_ring_cross_v2", "seed": seed,
                                  "objects": objects, "baskets": basket_specs(),
                                  "task": make_task(block, basket)})


def select_task(layout, block, basket):
    validate_color_layout(layout)
    result = copy.deepcopy(layout)
    result["task"] = make_task(block, basket)
    return result


def build_color_geometry(box, ring, layout):
    """Reuse the tested cube/physics builder; all road paint is visual-only."""
    box("Floor", (7.4, 7.4, .1), (0, 0, GROUND_Z - .05), (.23, .26, .28), collision=True)
    for name, (dx, dy) in LANES.items():
        rgb = COLORS[name]
        yaw = math.degrees(math.atan2(dy, dx))
        def point(along, lateral, z):
            return (dx * along - dy * lateral, dy * along + dx * lateral, z)
        prefix = f"Road/{name}"
        box(prefix + "/Surface", (SPOKE_END, ROAD_WIDTH, .0002), point(SPOKE_END / 2, 0, GROUND_Z + .0001),
            (.09, .10, .12), yaw=yaw)
        for i in range(5):
            box(prefix + f"/Dash_{i}", (.13, .015, .0002), point(.6 + i * .3, 0, GROUND_Z + .0003), rgb, yaw=yaw)
        box(prefix + "/Goal", (.6, .85, .0002), point(BASKET_DISTANCE, 0, GROUND_Z + .0005), rgb, yaw=yaw)
    ring("Road/Ring/Surface", RING_RADIUS, ROAD_WIDTH, (.09, .10, .12), GROUND_Z + .00025)
    ring("Road/Ring/Dashes", RING_RADIUS, .015, (.8, .7, .25), GROUND_Z + .00045,
         junction_gaps=True, dashed=True)
    box("Start", (.65, .65, .0002), (0, 0, GROUND_Z + .0007), (.65, .65, .65))


def task_display(layout):
    return layout["task"]["instruction"] if layout.get("version") == 2 else "Legacy course: collect blocks into blue basket"
