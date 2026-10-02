#!/usr/bin/env python3
"""Verify a generated net-arena USD (map + four LeKiwi robots).

Checks structure against expected values passed on the command line, initial
penetration, a physics settle, a controlled net contact test driven by real PhysX
contact reports, and teleoperation compatibility. Every stage edit is in-memory
only; nothing is written back to the USD.

Exit codes:
    0  every check passed
    1  at least one check failed
    2  the run raised an exception

Usage:
    python verify_net_arena.py --stage lekiwi_arena_3p0x2p0_net_A_4robots.usd \
        [--expect-net-height 0.30] [--screenshot] [--net-view-screenshot]
"""

import argparse
import os
import sys
import time
from pathlib import Path

from isaacsim import SimulationApp


ROOT = Path(__file__).resolve().parent

ROBOT_PATHS = {
    "Blue 1": "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_01",
    "Blue 2": "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_02",
    "Red 1": "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_01",
    "Red 2": "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_02",
}
ROBOT_BASE_SUBTREES = ("base_link", "back_wheel_link", "left_wheel_link", "right_wheel_link")

# 2026-09-05: grown from 0.035 (7 cm diameter) to match create_net_arena.py's
# BALL_RADIUS after the "rubber ball" contact-model change.
BALL_RADIUS = 0.040
BALL_MAX_SPEED = 0.80        # the balls' authored maxLinearVelocity
NET_PATH = "/World/Arena/Net/Collider"

# Distance-based contact fallback. A ball centre this close to the net plane is
# touching the net face: ball radius + net half thickness + PhysX contact offset,
# plus slack for solver separation of a resting contact.
CONTACT_DISTANCE_SLACK = 0.004

# 2026-09-10: create_net_arena.py's BallPhysics material now has PhysX
# compliant contact enabled (grip-stability fix -- see ARENA_BUILD_GUIDE.md
# 13.2-13.3). That softness applies to every contact this material is part
# of, including this test's net collision, so balls sink into the net
# instead of the ~0mm a fully rigid contact gives. Widened past the measured
# worst case (with headroom) rather than reverting the ball material, per
# the user's explicit priority that grip success matters more than this
# test's rigid-contact assumption.
#
# 2026-09-10 (second widening, same day): the ball's collision shape changed
# from an exact sphere to a 20-face icosahedron mesh -- a geometry-based grip
# fix. Measured penetration against the net got deeper again with this shape
# (worst case seen: ball centre 14.1mm from the net plane, i.e. ~36mm sunk
# past the 50mm nominal surface distance) -- plausibly because a convex
# mesh's edges/vertices interact with PhysX's compliant-contact spring
# differently than an analytic sphere's smooth curvature does.
#
# 2026-09-10 (third widening, same day): the ball's collision shape changed
# again, from the icosahedron to a cube (see the "ball" loop in
# build_stage() -- the user wanted the biggest flat jaw contact possible).
# A cube's face sits much further inside the nominal BALL_RADIUS sphere than
# the icosahedron's did (face-centre distance is only ~58% of the radius,
# vs. ~79% for the icosahedron), so a face-on rigid contact alone is already
# ~17mm shallower than the sphere assumption before compliant contact adds
# any further give. Measured worst case: ball centre 7.5mm from the net
# plane (~42.5mm sunk), consistent across all 10 balls in both passes (a
# cube apparently settles into a repeatable face-on orientation, unlike the
# icosahedron's more varied per-ball readings). Re-measure after any further
# ball-collider change instead of assuming this margin still covers it.
COMPLIANT_PENETRATION_MARGIN = 0.048

CONTACT_TEST_START_X = 0.25   # start distance of the ball centre from X=0
B_CORRIDOR_STEER_MARGIN = 0.035   # must match create_net_arena.py
# The two sides use different Y lanes. With identical lanes the opposing balls meet
# head-on at X=0 and stop each other, which would let the test pass with no net at all.
CONTACT_TEST_Y_LEFT = (-0.80, -0.40, 0.00, 0.40, 0.80)
CONTACT_TEST_Y_RIGHT = (-0.90, -0.60, -0.20, 0.20, 0.60)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--screenshot", action="store_true", help="Spectator-camera PNG")
    parser.add_argument("--net-view-screenshot", action="store_true",
                        help="Extra diagonal PNG from a temporary camera, to inspect the net grid")
    parser.add_argument("--screenshot-dir", type=Path, default=ROOT / "screenshots")
    parser.add_argument("--settle-steps", type=int, default=180)
    parser.add_argument("--contact-steps", type=int, default=90,
                        help="Maximum app updates per contact pass; too few is a FAIL, not a pass")
    # Expected geometry. These must match what create_net_arena.py was given.
    parser.add_argument("--expect-arena-width", type=float, default=3.0)
    parser.add_argument("--expect-arena-height", type=float, default=2.0)
    parser.add_argument("--expect-wall-height", type=float, default=0.70)
    parser.add_argument("--expect-net-height", type=float, default=0.30)
    parser.add_argument("--expect-physics-hz", type=float, default=120.0,
                         help="Raised from 60 on 2026-09-10 as part of the grasp-stability "
                              "fix in create_net_arena.py -- see ARENA_BUILD_GUIDE.md.")
    parser.add_argument("--expect-basket-outer-x", type=float, default=0.34)
    parser.add_argument("--expect-basket-outer-y", type=float, default=0.34)
    parser.add_argument("--expect-basket-wall-height", type=float, default=0.18)
    parser.add_argument("--expect-layout", choices=("A", "B", "C", "D"), default=None)
    return parser.parse_args()


ARGS = parse_args()
STAGE_PATH = ARGS.stage.expanduser().resolve()
if not STAGE_PATH.is_file():
    raise FileNotFoundError(STAGE_PATH)

os.environ["OMNI_KIT_ACCEPT_EULA"] = "YES"
APP = SimulationApp({"headless": True, "renderer": "RayTracedLighting", "width": 960, "height": 600, "anti_aliasing": 0})

from pxr import Gf, PhysicsSchemaTools, PhysxSchema, Usd, UsdGeom, UsdPhysics  # noqa: E402
from omni.physx import get_physx_interface, get_physx_simulation_interface  # noqa: E402
import omni.replicator.core as rep  # noqa: E402
import omni.timeline  # noqa: E402
import omni.usd  # noqa: E402


FAILURES = []
UNVERIFIED = []
BLOCKERS = []
TOL = 1e-6


def check(condition, message):
    if condition:
        print(f"  PASS  {message}", flush=True)
    else:
        print(f"  FAIL  {message}", flush=True)
        FAILURES.append(message)
    return bool(condition)


def info(message):
    print(f"  INFO  {message}", flush=True)


def warn(message):
    print(f"  WARN  {message}", flush=True)
    BLOCKERS.append(message)


def world_translation(prim):
    t = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()).ExtractTranslation()
    return float(t[0]), float(t[1]), float(t[2])


def authored_scale(prim):
    for op in UsdGeom.Xformable(prim).GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeScale:
            v = op.Get()
            return float(v[0]), float(v[1]), float(v[2])
    return None


def box_extent(prim):
    """World AABB of a cube authored as translate + scale, taken from its transform."""
    if not prim or not prim.IsValid():
        return None
    cx, cy, cz = world_translation(prim)
    s = authored_scale(prim)
    if s is None:
        return None
    return (cx - s[0] / 2, cy - s[1] / 2, cz - s[2] / 2,
            cx + s[0] / 2, cy + s[1] / 2, cz + s[2] / 2)


def make_bbox_cache():
    """Bounding boxes that include invisible prims.

    The net collider is authored with visibility=invisible so that only the visual
    grid renders. A default BBoxCache skips invisible prims and would silently drop
    the net from every overlap test, so ignoreVisibility must be set.
    """
    return UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy, UsdGeom.Tokens.guide],
        useExtentsHint=False,
        ignoreVisibility=True,
    )


def aabb(bbox_cache, prim):
    """World AABB, or None when it cannot be computed. None is never 'no overlap'."""
    if not prim or not prim.IsValid():
        return None
    box = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
    if box.IsEmpty():
        return None
    lo, hi = box.GetMin(), box.GetMax()
    return (float(lo[0]), float(lo[1]), float(lo[2]), float(hi[0]), float(hi[1]), float(hi[2]))


def union_aabb(bbox_cache, prims):
    out = None
    for prim in prims:
        b = aabb(bbox_cache, prim)
        if b is None:
            continue
        out = b if out is None else (
            min(out[0], b[0]), min(out[1], b[1]), min(out[2], b[2]),
            max(out[3], b[3]), max(out[4], b[4]), max(out[5], b[5]),
        )
    return out


def overlap_volume(a, b):
    if a is None or b is None:
        return 0.0
    dx = min(a[3], b[3]) - max(a[0], b[0])
    dy = min(a[4], b[4]) - max(a[1], b[1])
    dz = min(a[5], b[5]) - max(a[2], b[2])
    if dx <= 0 or dy <= 0 or dz <= 0:
        return 0.0
    return dx * dy * dz


def net_geometry(stage):
    """Measured net collider geometry, taken from the prim rather than metadata."""
    prim = stage.GetPrimAtPath(NET_PATH)
    box = box_extent(prim)
    if box is None:
        return None
    return {
        "prim": prim,
        "active": bool(prim.IsActive()),
        "half_thickness": (box[3] - box[0]) / 2.0,
        "centre_x": (box[0] + box[3]) / 2.0,
        "span_y": box[4] - box[1],
        "bottom": box[2],
        "top": box[5],
        "contact_offset": PhysxSchema.PhysxCollisionAPI(prim).GetContactOffsetAttr().Get(),
    }


def all_prims(root_prim):
    """Traverse including instance proxies and every prim class.

    stage.Traverse() and Prim.GetChildren() use the default predicate, which skips
    instance proxies. The LeKiwi collision meshes live inside instanced subtrees, so
    a default traversal reports zero colliders for a robot that in fact has 21.
    """
    return Usd.PrimRange(root_prim, Usd.TraverseInstanceProxies(Usd.PrimAllPrimsPredicate))


def ball_prims(stage):
    return [stage.GetPrimAtPath(f"/World/Arena/Balls/Ball_{i:02d}") for i in range(1, 11)]


# --------------------------------------------------------------------------- #
# [1] structure
# --------------------------------------------------------------------------- #

def structural_checks(stage, net):
    print("[1] Structure (compared against expected values given on the command line)", flush=True)
    arena = stage.GetPrimAtPath("/World/Arena")
    size = arena.GetAttribute("arena:interiorSizeMeters").Get()
    layout = arena.GetAttribute("arena:basketLayout").Get()
    info(f"expected: arena {ARGS.expect_arena_width} x {ARGS.expect_arena_height} m, "
         f"wall {ARGS.expect_wall_height} m, net top {ARGS.expect_net_height} m, "
         f"basket {ARGS.expect_basket_outer_x} x {ARGS.expect_basket_outer_y} x "
         f"{ARGS.expect_basket_wall_height} m")
    info(f"basket layout in stage = {layout}")
    if ARGS.expect_layout:
        check(layout == ARGS.expect_layout, f"basket layout = {ARGS.expect_layout} (got {layout})")

    # Metadata must agree, but the geometry checks below are what actually decide.
    check(size is not None
          and abs(size[0] - ARGS.expect_arena_width) < TOL
          and abs(size[1] - ARGS.expect_arena_height) < TOL,
          f"interior size metadata = {ARGS.expect_arena_width} x {ARGS.expect_arena_height} m "
          f"(got {tuple(size) if size else None})")

    floor = stage.GetPrimAtPath("/World/Arena/Floor/Field")
    fbox = box_extent(floor)
    if check(fbox is not None, "floor geometry is readable"):
        check(abs((fbox[3] - fbox[0]) - ARGS.expect_arena_width) < TOL
              and abs((fbox[4] - fbox[1]) - ARGS.expect_arena_height) < TOL,
              f"floor geometry spans {ARGS.expect_arena_width} x {ARGS.expect_arena_height} m "
              f"(got {fbox[3] - fbox[0]:.4f} x {fbox[4] - fbox[1]:.4f})")
        check(abs(fbox[5]) < TOL, f"floor top surface at Z = 0 (got {fbox[5]:.6f})")
    check(floor.HasAPI(UsdPhysics.CollisionAPI), "floor has a collider")

    for wall in ("West", "East", "South", "North"):
        prim = stage.GetPrimAtPath(f"/World/Arena/Walls/{wall}")
        box = box_extent(prim)
        if check(box is not None, f"wall {wall} geometry is readable"):
            check(abs((box[5] - box[2]) - ARGS.expect_wall_height) < TOL,
                  f"wall {wall} height = {ARGS.expect_wall_height} m (got {box[5] - box[2]:.4f})")
        check(prim.HasAPI(UsdPhysics.CollisionAPI), f"wall {wall} has a collider")

    if check(net is not None, "net collider geometry is readable"):
        check(abs(net["centre_x"]) < TOL, f"net plane at X = 0 (got {net['centre_x']:.6f})")
        check(abs(net["span_y"] - ARGS.expect_arena_height) < TOL,
              f"net spans Y = {ARGS.expect_arena_height} m (got {net['span_y']:.4f})")
        check(abs(net["top"] - ARGS.expect_net_height) < TOL,
              f"net top at Z = {ARGS.expect_net_height} m (got {net['top']:.4f})")
        check(abs(net["bottom"]) < TOL, f"net bottom reaches the floor at Z = 0 (got {net['bottom']:.6f})")
        check(net["prim"].HasAPI(UsdPhysics.CollisionAPI), "net has a collider")
        # An inactive prim still answers attribute queries but is invisible to PhysX,
        # so reading its geometry is not enough.
        check(net["active"], "net collider prim is active, so PhysX actually sees it")
        check(bool(net["prim"].GetAttribute("physics:collisionEnabled").Get()
                   if net["prim"].GetAttribute("physics:collisionEnabled")
                   and net["prim"].GetAttribute("physics:collisionEnabled").HasAuthoredValue()
                   else True),
              "net collision is enabled")
        info(f"net collider thickness (X) = {2 * net['half_thickness']:.4f} m, "
             f"contact offset = {net['contact_offset']}")

    for visual in ("Mesh", "TopBand", "Post_South", "Post_North"):
        prim = stage.GetPrimAtPath(f"/World/Arena/Net/{visual}")
        check(bool(prim) and prim.IsValid() and not prim.HasAPI(UsdPhysics.CollisionAPI),
              f"net visual part {visual} exists and carries no collider")
    grid = [p for p in stage.Traverse() if str(p.GetPath()).startswith("/World/Arena/Net/Mesh/Cord_")]
    check(len(grid) >= 4, f"net visual mesh is an open grid of bars (got {len(grid)} bars)")
    check(all(not p.HasAPI(UsdPhysics.CollisionAPI) for p in grid),
          "no net grid bar carries a collider")
    if grid:
        boxes = [box_extent(p) for p in grid]
        vertical = [b for b in boxes if b and (b[4] - b[1]) < 0.05]
        thickest = max((b[3] - b[0]) for b in boxes if b)
        info(f"net grid: {len(vertical)} vertical bars, {len(grid) - len(vertical)} horizontal bars, "
             f"bar thickness along X = {thickest:.4f} m")

    balls = ball_prims(stage)
    check(all(p and p.IsValid() for p in balls), "ball count = 10")
    counts, per_team = {}, {}
    for prim in balls:
        color = prim.GetAttribute("arena:ballColor").Get()
        team = prim.GetAttribute("arena:startTeam").Get()
        counts[color] = counts.get(color, 0) + 1
        per_team.setdefault(team, {})
        per_team[team][color] = per_team[team].get(color, 0) + 1
        collider_prim = prim.GetChild("Collider")
        check(bool(collider_prim) and collider_prim.HasAPI(UsdPhysics.CollisionAPI),
              f"{prim.GetName()} has a collider")
        visual_prim = prim.GetChild("Visual")
        r = float(UsdGeom.Sphere(visual_prim).GetRadiusAttr().Get())
        check(abs(r - BALL_RADIUS) < 1e-9,
              f"{prim.GetName()} radius = {BALL_RADIUS} m ({BALL_RADIUS * 2} m diameter) (got {r})")
    check(counts == {"white": 6, "red": 2, "yellow": 2}, f"ball colours = white 6 / red 2 / yellow 2 (got {counts})")
    for team in ("TeamRed", "TeamBlue"):
        check(per_team.get(team) == {"white": 3, "red": 1, "yellow": 1},
              f"{team} ball mix = white 3 / red 1 / yellow 1 (got {per_team.get(team)})")
    for prim in balls:
        x, _, _ = world_translation(prim)
        team = prim.GetAttribute("arena:startTeam").Get()
        check((team == "TeamRed" and x < 0) or (team == "TeamBlue" and x > 0),
              f"{prim.GetName()} starts in the {team} half (x={x:.3f})")


# --------------------------------------------------------------------------- #
# [2] baskets, measured from the real wall geometry
# --------------------------------------------------------------------------- #

def basket_checks(stage, net):
    print("[2] Baskets (cavity measured from the actual floor and wall boxes)", flush=True)
    cache = make_bbox_cache()
    results = {}
    for team, name in (("TeamRed", "TeamRed_Goal"), ("TeamBlue", "TeamBlue_Goal")):
        root = stage.GetPrimAtPath(f"/World/Arena/Baskets/{name}")
        if not check(bool(root) and root.IsValid(), f"{name} exists"):
            continue
        parts = {}
        for part in ("Bottom", "Wall_West", "Wall_East", "Wall_South", "Wall_North"):
            prim = stage.GetPrimAtPath(f"/World/Arena/Baskets/{name}/{part}")
            ok = bool(prim) and prim.IsValid() and prim.HasAPI(UsdPhysics.CollisionAPI)
            check(ok, f"{name}/{part} exists and has a collider")
            if ok:
                parts[part] = box_extent(prim)
        if len(parts) != 5 or any(v is None for v in parts.values()):
            check(False, f"{name} geometry is readable for all five parts")
            continue

        outer = union_aabb(cache, [root])
        outer_x = outer[3] - outer[0]
        outer_y = outer[4] - outer[1]
        check(abs(outer_x - ARGS.expect_basket_outer_x) < 1e-4,
              f"{name} outer X = {ARGS.expect_basket_outer_x} m (measured {outer_x:.4f})")
        check(abs(outer_y - ARGS.expect_basket_outer_y) < 1e-4,
              f"{name} outer Y = {ARGS.expect_basket_outer_y} m (measured {outer_y:.4f})")

        wall_top = max(parts[p][5] for p in ("Wall_West", "Wall_East", "Wall_South", "Wall_North"))
        check(abs(wall_top - ARGS.expect_basket_wall_height) < 1e-4,
              f"{name} wall top = {ARGS.expect_basket_wall_height} m (measured {wall_top:.4f})")

        # Cavity from the real inner faces, not from assumed wall thicknesses.
        cavity = (parts["Wall_West"][3], parts["Wall_South"][4], parts["Bottom"][5],
                  parts["Wall_East"][0], parts["Wall_North"][1], wall_top)
        cw, cd, ch = cavity[3] - cavity[0], cavity[4] - cavity[1], cavity[5] - cavity[2]
        check(cw > 0 and cd > 0 and ch > 0,
              f"{name} has a real interior cavity ({cw:.4f} x {cd:.4f} x {ch:.4f} m)")
        info(f"{name} cavity x[{cavity[0]:+.4f},{cavity[3]:+.4f}] y[{cavity[1]:+.4f},{cavity[4]:+.4f}] "
             f"z[{cavity[2]:.4f},{cavity[5]:.4f}]")

        # Nothing may sit inside the cavity, and nothing may cap the opening.
        lid_zone = (cavity[0], cavity[1], wall_top + 1e-4, cavity[3], cavity[4], wall_top + 0.10)
        own = {f"/World/Arena/Baskets/{name}/{p}" for p in parts}
        intruders, lids = [], []
        for prim in all_prims(stage.GetPseudoRoot()):
            path = str(prim.GetPath())
            if path in own or not (prim.IsA(UsdGeom.Cube) or prim.IsA(UsdGeom.Sphere)
                                   or prim.IsA(UsdGeom.Cylinder) or prim.IsA(UsdGeom.Mesh)):
                continue
            b = aabb(cache, prim)
            if b is None:
                continue
            if overlap_volume(b, cavity) > 1e-9:
                intruders.append(path)
            if overlap_volume(b, lid_zone) > 1e-9:
                lids.append(path)
        check(not intruders, f"{name} interior is empty (intruding prims: {intruders})")
        check(not lids, f"{name} top opening is clear, nothing caps it (prims above the rim: {lids})")

        bx = (outer[0] + outer[3]) / 2.0
        by = (outer[1] + outer[4]) / 2.0
        check((team == "TeamRed" and bx < 0) or (team == "TeamBlue" and bx > 0),
              f"{name} sits in its own half (measured centre x={bx:.3f})")

        if net is not None:
            near_face = outer[0] if bx > 0 else outer[3]
            gap = abs(near_face) - net["half_thickness"]
            check(abs(gap) < 1e-4,
                  f"{name} net-side face is flush with the net face (face |x|={abs(near_face):.4f}, "
                  f"net face |x|={net['half_thickness']:.4f}, gap={gap * 1000:+.3f} mm)")
            check(wall_top < net["top"] - 1e-9,
                  f"{name} wall top {wall_top:.3f} m stays below the net top {net['top']:.3f} m, "
                  "so the net cannot cover the opening")

        corridor = ARGS.expect_arena_height / 2.0 - max(abs(outer[1]), abs(outer[4]))
        info(f"{name} centre = ({bx:.3f}, {by:.3f}); wall-side corridor = {corridor:.4f} m")
        results[name] = {"centre": (bx, by), "corridor": corridor, "outer": outer}
    return results


def basket_wall_flush_check(stage, baskets):
    """Layout D must have both baskets touching the outer wall on their own right."""
    layout = stage.GetPrimAtPath("/World/Arena").GetAttribute("arena:basketLayout").Get()
    if layout != "D" or not baskets:
        return
    print("[2c] Layout D wall-flush placement", flush=True)
    for name, data in baskets.items():
        by = data["centre"][1]
        check(abs(data["corridor"]) < 1e-4,
              f"{name} outer face touches the wall (measured wall-side gap "
              f"{data['corridor'] * 1000:+.3f} mm)")
        check(data["corridor"] > -1e-4,
              f"{name} does not push through the wall (gap {data['corridor'] * 1000:+.3f} mm)")
        # Red spawns on X<0 facing +X, so its right is -Y; Blue is mirrored.
        want_negative = name.startswith("TeamRed")
        check((by < 0) == want_negative,
              f"{name} sits on its own team's right-hand side (measured centre y={by:+.3f})")
    info("layout D leaves no wall-side corridor by design; the baskets are approached "
         "from the open centre side")


def basket_corridor_check(stage, baskets, base_union):
    """Layout B must leave a corridor a base can actually drive through."""
    layout = stage.GetPrimAtPath("/World/Arena").GetAttribute("arena:basketLayout").Get()
    if layout != "B" or not baskets or base_union is None:
        return
    print("[2b] Layout B wall-side corridor", flush=True)
    base_width = base_union[4] - base_union[1]
    required = base_width + 2 * B_CORRIDOR_STEER_MARGIN
    info(f"measured base+wheels width = {base_width:.4f} m; required corridor = base width + "
         f"2 x {B_CORRIDOR_STEER_MARGIN} m steering margin = {required:.4f} m")
    for name, data in baskets.items():
        check(data["corridor"] >= required - 1e-6,
              f"{name} wall-side corridor {data['corridor']:.4f} m >= required {required:.4f} m")
    info("this is a straight-line clearance figure; free rotation in place needs more room, and "
         "the basket can also be approached from the open centre side")


# --------------------------------------------------------------------------- #
# [3] robots
# --------------------------------------------------------------------------- #

def robot_checks(stage):
    print("[3] Robots", flush=True)
    cache = make_bbox_cache()
    for label, path in ROBOT_PATHS.items():
        prim = stage.GetPrimAtPath(path)
        if not check(prim.IsValid(), f"{label} spawn prim {path} exists"):
            continue
        check(len(prim.GetChildren()) > 0, f"{label} LeKiwi reference composed ({len(prim.GetChildren())} children)")
        base = stage.GetPrimAtPath(f"{path}/base_footprint")
        check(base.IsValid() and base.HasAPI(UsdPhysics.RigidBodyAPI),
              f"{label} base_footprint is a rigid body (teleop control path)")
        x, y, _ = world_translation(prim)
        team = prim.GetAttribute("arena:team").Get()
        check((team == "TeamRed" and x < 0) or (team == "TeamBlue" and x > 0),
              f"{label} ({team}) is on the correct side (x={x:.3f})")
        info(f"{label} spawn = ({x:.3f}, {y:.3f})")

    # Collision geometry is what the net can actually stop, so count it with a
    # traversal that descends into instance proxies.
    total_colliders = 0
    for label, path in ROBOT_PATHS.items():
        n = sum(1 for p in all_prims(stage.GetPrimAtPath(path))
                if p.HasAPI(UsdPhysics.CollisionAPI))
        base_n = sum(1 for sub in ROBOT_BASE_SUBTREES
                     for p in all_prims(stage.GetPrimAtPath(f"{path}/{sub}"))
                     if p.HasAPI(UsdPhysics.CollisionAPI))
        info(f"{label} collision-geometry prims = {n} total, {base_n} on base_link and the wheels")
        total_colliders += n
    check(total_colliders > 0,
          f"the LeKiwi links carry collision geometry, so the net can act on them "
          f"({total_colliders} collider prims across four robots)")

    base_union = union_aabb(cache, [stage.GetPrimAtPath(f"{ROBOT_PATHS['Red 1']}/{s}")
                                    for s in ROBOT_BASE_SUBTREES])
    whole = aabb(cache, stage.GetPrimAtPath(ROBOT_PATHS["Red 1"]))
    if base_union and whole:
        info(f"base+wheels footprint (visual mesh AABB) = {base_union[3] - base_union[0]:.4f} x "
             f"{base_union[4] - base_union[1]:.4f} m, height {base_union[5] - base_union[2]:.4f} m")
        info(f"whole robot incl. arm = {whole[3] - whole[0]:.4f} x {whole[4] - whole[1]:.4f} m, "
             f"top at Z {whole[5]:.4f} m")
    return base_union


# --------------------------------------------------------------------------- #
# [4] initial penetration
# --------------------------------------------------------------------------- #

def penetration_checks(stage):
    print("[4] Initial penetration (world AABB overlap, invisible prims included)", flush=True)
    info("this is a conservative axis-aligned bounding-box test: an overlap here is a strong "
         "signal, but the absence of one does not prove that convex colliders are separated")
    cache = make_bbox_cache()
    groups, unreadable = {}, []
    for label, path in ROBOT_PATHS.items():
        groups[f"robot:{label}"] = aabb(cache, stage.GetPrimAtPath(path))
    for name in ("TeamRed_Goal", "TeamBlue_Goal"):
        groups[f"basket:{name}"] = aabb(cache, stage.GetPrimAtPath(f"/World/Arena/Baskets/{name}"))
    groups["net"] = aabb(cache, stage.GetPrimAtPath(NET_PATH))
    for i, prim in enumerate(ball_prims(stage), 1):
        groups[f"ball:{i:02d}"] = aabb(cache, prim)

    unreadable = [k for k, v in groups.items() if v is None]
    check(not unreadable,
          f"every tested body has a computable bounding box; an empty box is never treated as "
          f"'no overlap' (unreadable: {unreadable})")

    net_box = groups.get("net")
    if net_box is not None:
        info(f"net AABB (invisible prim) x[{net_box[0]:+.4f},{net_box[3]:+.4f}] "
             f"z[{net_box[2]:.4f},{net_box[5]:.4f}] - proves the invisible collider is included")

    keys = [k for k, v in groups.items() if v is not None]
    overlaps = []
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            v = overlap_volume(groups[a], groups[b])
            if v > 1e-9:
                overlaps.append((a, b, v))
    check(not overlaps, f"no ball/robot/basket/net AABB overlaps at startup (found {len(overlaps)})")
    for a, b, v in overlaps:
        info(f"overlap {a} <-> {b}: {v * 1e6:.1f} cm^3")


# --------------------------------------------------------------------------- #
# physics instrumentation
# --------------------------------------------------------------------------- #

class PhysicsProbe:
    """Counts real PhysX steps and records per-step positions and net contacts."""

    def __init__(self, tracked_prims):
        self.tracked = tracked_prims          # list of (key, prim)
        self.steps = 0
        self.sim_time = 0.0
        self.samples = {key: [] for key, _ in tracked_prims}
        self.net_contacts = set()
        self._step_sub = None
        self._contact_sub = None

    def _on_step(self, dt):
        self.steps += 1
        self.sim_time += float(dt)
        for key, prim in self.tracked:
            self.samples[key].append(world_translation(prim))

    def _on_contact(self, contact_headers, contact_data):
        for header in contact_headers:
            a = str(PhysicsSchemaTools.intToSdfPath(header.actor0))
            b = str(PhysicsSchemaTools.intToSdfPath(header.actor1))
            for one, other in ((a, b), (b, a)):
                if other.startswith(NET_PATH) and one.startswith("/World/Arena/Balls/Ball_"):
                    self.net_contacts.add(one.rsplit("/", 1)[-1])

    def start(self):
        self._step_sub = get_physx_interface().subscribe_physics_step_events(self._on_step)
        self._contact_sub = get_physx_simulation_interface().subscribe_contact_report_events(self._on_contact)

    def stop(self):
        self._step_sub = None
        self._contact_sub = None


# --------------------------------------------------------------------------- #
# [5] settle
# --------------------------------------------------------------------------- #

def physics_settle(stage, steps):
    print(f"[5] Physics settle ({steps} app updates)", flush=True)
    timeline = omni.timeline.get_timeline_interface()
    before = {label: world_translation(stage.GetPrimAtPath(f"{path}/base_footprint"))
              for label, path in ROBOT_PATHS.items()}
    probe = PhysicsProbe([])
    probe.start()
    timeline.play()
    wall_started = time.perf_counter()
    for _ in range(steps):
        APP.update()
    wall_elapsed = time.perf_counter() - wall_started
    timeline.pause()
    probe.stop()

    scene = PhysxSchema.PhysxSceneAPI(stage.GetPrimAtPath("/World/Arena/PhysicsScene"))
    configured = scene.GetTimeStepsPerSecondAttr().Get()
    check(int(configured) == int(ARGS.expect_physics_hz),
          f"PhysX scene is configured for {ARGS.expect_physics_hz:g} Hz (got {configured})")
    check(probe.steps > 0, f"physics actually advanced (physics step callbacks = {probe.steps})")
    rate = probe.steps / probe.sim_time if probe.sim_time else 0.0
    info(f"{steps} app updates drove {probe.steps} PhysX steps totalling {probe.sim_time:.4f} s of "
         f"simulated time ({rate:.1f} steps per simulated second)")
    info(f"wall-clock throughput = {steps / wall_elapsed:.1f} app updates/s and "
         f"{probe.steps / wall_elapsed:.1f} PhysX steps/s (headless, no GUI viewport; this is NOT "
         "a measurement of interactive GUI performance)")

    zs, escaped, crossed = [], [], []
    for i, prim in enumerate(ball_prims(stage), 1):
        team = prim.GetAttribute("arena:startTeam").Get()
        x, y, z = world_translation(prim)
        zs.append(z)
        if abs(x) > ARGS.expect_arena_width / 2 or abs(y) > ARGS.expect_arena_height / 2 or z < -0.01:
            escaped.append((i, round(x, 4), round(y, 4), round(z, 4)))
        if (team == "TeamRed" and x > 0) or (team == "TeamBlue" and x < 0):
            crossed.append((i, round(x, 4)))
    check(not escaped, f"no ball fell through the floor or left the arena (escaped={escaped})")
    check(not crossed, f"no ball drifted across the net while settling (crossed={crossed})")
    info(f"ball Z range after settle = {min(zs):.4f}..{max(zs):.4f} m")

    pushed, sunk = [], []
    for label, path in ROBOT_PATHS.items():
        a = before[label]
        b = world_translation(stage.GetPrimAtPath(f"{path}/base_footprint"))
        dxy = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
        dz = b[2] - a[2]
        info(f"{label} base drift: horizontal {dxy * 1000:.1f} mm, vertical {dz * 1000:+.1f} mm")
        if dxy > 0.01:
            pushed.append((label, round(dxy, 4)))
        if dz < -0.05:
            sunk.append((label, round(dz, 4)))
    check(not pushed, f"no robot was pushed sideways by an initial penetration (>10 mm horizontal: {pushed})")
    check(not sunk, f"no robot sank into the floor (>50 mm downward: {sunk})")
    timeline.stop()
    for _ in range(5):
        APP.update()


# --------------------------------------------------------------------------- #
# [6] net contact test
# --------------------------------------------------------------------------- #

def net_contact_test(stage, max_updates, net):
    """Drive every ball into the net and prove, per physics step, that none passes.

    Two claims are reported separately:
      (a) every ball actually reached the net and registered contact, and
      (b) no ball was ever on the far side of X=0 at any recorded physics step.
    A run that ends without (a) is a FAIL, not a pass: never reaching the net
    proves nothing about the net.
    """
    if net is None:
        check(False, "net contact test skipped: net geometry unreadable")
        return
    surface_distance = BALL_RADIUS + net["half_thickness"]     # centre distance when touching
    contact_distance = surface_distance + float(net["contact_offset"] or 0.0) + CONTACT_DISTANCE_SLACK
    print(f"[6] Net contact test (drive {BALL_MAX_SPEED} m/s into the net, "
          f"max {max_updates} app updates per pass)", flush=True)
    info(f"contact criterion: PhysX contact report between the ball and {NET_PATH}; distance "
         f"fallback |x| <= {contact_distance:.4f} m (ball radius {BALL_RADIUS} + net half thickness "
         f"{net['half_thickness']:.4f} + contact offset {net['contact_offset']} + "
         f"{CONTACT_DISTANCE_SLACK} slack). The fallback cannot tell touching from resting a "
         "millimetre away, so the contact report is the primary evidence.")

    baskets = stage.GetPrimAtPath("/World/Arena/Baskets")
    baskets.SetActive(False)                     # isolate the net; in-memory only
    balls = ball_prims(stage)
    for prim in balls:
        PhysxSchema.PhysxContactReportAPI.Apply(prim).CreateThresholdAttr(0.0)
    timeline = omni.timeline.get_timeline_interface()

    passes = (
        ("floor-resting", BALL_RADIUS, False),
        ("mid-net height", net["top"] / 2.0, True),
    )
    for pass_name, target_z, no_gravity in passes:
        placements = []
        for index, (sign, lanes) in enumerate(((-1.0, CONTACT_TEST_Y_LEFT),
                                               (1.0, CONTACT_TEST_Y_RIGHT))):
            for j, y in enumerate(lanes):
                prim = balls[index * len(lanes) + j]
                UsdGeom.Xformable(prim).GetOrderedXformOps()[0].Set(
                    Gf.Vec3d(sign * CONTACT_TEST_START_X, y, target_z))
                rigid = UsdPhysics.RigidBodyAPI(prim)
                rigid.CreateVelocityAttr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
                rigid.CreateAngularVelocityAttr().Set(Gf.Vec3f(0.0, 0.0, 0.0))
                # Gravity is switched off for the mid-height pass so the ball keeps
                # the intended height instead of dropping to the floor on the way.
                PhysxSchema.PhysxRigidBodyAPI(prim).CreateDisableGravityAttr(bool(no_gravity))
                placements.append((prim.GetName(), prim, sign))
        for _ in range(3):
            APP.update()

        probe = PhysicsProbe([(name, prim) for name, prim, _ in placements])
        probe.start()
        timeline.play()
        for _ in range(max_updates):
            for _, prim, sign in placements:
                UsdPhysics.RigidBodyAPI(prim).CreateVelocityAttr().Set(
                    Gf.Vec3f(-sign * BALL_MAX_SPEED, 0.0, 0.0))
            APP.update()
        timeline.pause()
        probe.stop()

        crossed, never_reached, height_error, too_deep = [], [], [], []
        closest_overall = None
        for name, prim, sign in placements:
            path = probe.samples.get(name, [])
            if not path:
                never_reached.append((name, "no samples"))
                continue
            min_abs_x, z_at_min = None, None
            for x, _y, z in path:
                if sign * x < 0:                       # far side of X=0 at this step
                    crossed.append((name, round(x, 4), round(z, 4)))
                    break
                if min_abs_x is None or abs(x) < min_abs_x:
                    min_abs_x, z_at_min = abs(x), z
            if min_abs_x is None:
                continue
            closest_overall = min_abs_x if closest_overall is None else min(closest_overall, min_abs_x)
            if name not in probe.net_contacts:
                # The PhysX contact report is the primary evidence. A ball that merely
                # ended up near the plane may have been stopped by something else.
                never_reached.append((name, round(min_abs_x, 4),
                                      "within distance fallback" if min_abs_x <= contact_distance
                                      else "never near the net"))
            if min_abs_x < surface_distance - COMPLIANT_PENETRATION_MARGIN:
                too_deep.append((name, round(min_abs_x, 4)))
            if z_at_min is not None and abs(z_at_min - target_z) > 0.02:
                height_error.append((name, round(z_at_min, 4)))

        samples_each = len(probe.samples[placements[0][0]])
        info(f"{pass_name}: {probe.steps} PhysX steps, {probe.sim_time:.4f} s simulated, "
             f"{samples_each} position samples per ball ({max_updates} app updates requested)")
        info(f"{pass_name}: PhysX reported net contact for {len(probe.net_contacts)}/10 balls "
             f"{sorted(probe.net_contacts)}")
        if closest_overall is not None:
            info(f"{pass_name}: closest ball-centre distance to the net plane over the whole run = "
                 f"{closest_overall * 1000:.1f} mm (contact threshold {contact_distance * 1000:.1f} mm)")

        check(not never_reached,
              f"{pass_name}: PhysX reported a net contact for every ball during the run; a ball "
              f"that never touched the net proves nothing (missing: {never_reached})")
        check(not too_deep,
              f"{pass_name}: no ball centre sank more than {COMPLIANT_PENETRATION_MARGIN * 1000:.0f} mm "
              f"past the {surface_distance * 1000:.1f} mm surface distance (too deep: {too_deep})")
        check(not height_error,
              f"{pass_name}: contact happened at the intended height {target_z:.4f} m +/- 20 mm "
              f"(out of band: {height_error})")
        check(not crossed,
              f"{pass_name}: no ball was ever on the far side of X=0 at any physics step "
              f"(crossings: {crossed})")

        timeline.stop()
        for _ in range(5):
            APP.update()

    for prim in balls:
        PhysxSchema.PhysxRigidBodyAPI(prim).CreateDisableGravityAttr(False)
    baskets.SetActive(True)
    UNVERIFIED.append("this contact test drives BALLS into the net only; it says nothing about a "
                      "robot base (measured separately in section [7])")


# --------------------------------------------------------------------------- #
# [7] robot base drive test
# --------------------------------------------------------------------------- #

def _drive_base_at_net(stage, label, max_updates, net_face, front_offset, net_active):
    """One drive run. Returns (samples, steps, sim_time, converged)."""
    net_prim = stage.GetPrimAtPath(NET_PATH)
    net_prim.SetActive(bool(net_active))
    base = stage.GetPrimAtPath(f"{ROBOT_PATHS[label]}/base_footprint")
    rigid = UsdPhysics.RigidBodyAPI(base)
    velocity = rigid.CreateVelocityAttr()
    angular = rigid.CreateAngularVelocityAttr()
    probe = PhysicsProbe([(label, base)])
    timeline = omni.timeline.get_timeline_interface()
    for _ in range(5):
        APP.update()
    probe.start()
    timeline.play()
    for _ in range(max_updates):
        # teleoperate_four_switchable.py zeroes every base and then writes the command.
        velocity.Set(Gf.Vec3f(0.0, 0.0, 0.0))
        angular.Set(Gf.Vec3f(0.0, 0.0, 0.0))
        velocity.Set(Gf.Vec3f(0.35, 0.0, 0.0))     # teleop default linear speed
        APP.update()
        if world_translation(base)[0] > net_face + 0.10:
            break
    timeline.pause()
    probe.stop()
    xs = [q[0] for q in probe.samples[label]]
    timeline.stop()
    for _ in range(10):
        APP.update()
    net_prim.SetActive(True)
    # "Stopped" means the base is no longer making progress. A few millimetres of
    # residual creep while pressed against the net still counts as stopped.
    converged = len(xs) >= 120 and (max(xs[-120:]) - min(xs[-120:])) < 0.02
    return xs, probe.steps, probe.sim_time, converged


def robot_drive_test(stage, max_updates, net, base_union):
    """Drive a base at the net the way the teleop script does, with a control run.

    The control run repeats the drive with the net collider deactivated in memory.
    Without that control, a base that merely stalls would look identical to a base
    that the net stopped.
    """
    print("[7] Robot base drive test (measured, with a net-disabled control)", flush=True)
    if net is None:
        check(False, "robot drive test skipped: net geometry unreadable")
        return
    label = "Red 1"
    spawn_x = world_translation(stage.GetPrimAtPath(ROBOT_PATHS[label]))[0]
    front_offset = (base_union[3] - spawn_x) if base_union else 0.0
    net_face = net["half_thickness"]
    info(f"{label} drives at the teleop default 0.35 m/s toward +X; the base+wheels front face is "
         f"{front_offset:+.4f} m ahead of the base origin and the net near face is at "
         f"x={-net_face:+.4f} m")

    xs, steps, sim_time, converged = _drive_base_at_net(
        stage, label, max_updates, net_face, front_offset, net_active=True)
    if not xs:
        check(False, f"{label} drive test recorded no physics samples")
        return
    fronts = [x + front_offset for x in xs]
    info(f"net ACTIVE: {steps} PhysX steps / {sim_time:.3f} s simulated; base origin "
         f"{xs[0]:+.4f} -> {xs[-1]:+.4f} m, front face reached {max(fronts):+.4f} m, "
         f"converged={converged}")

    ctrl_xs, ctrl_steps, ctrl_time, ctrl_converged = _drive_base_at_net(
        stage, label, max_updates, net_face, front_offset, net_active=False)
    info(f"net DISABLED control: {ctrl_steps} PhysX steps / {ctrl_time:.3f} s simulated; base "
         f"origin {ctrl_xs[0]:+.4f} -> {ctrl_xs[-1]:+.4f} m")

    crossed = max(xs) > net_face
    control_crossed = bool(ctrl_xs) and max(ctrl_xs) > net_face
    stopped_at_net = converged and max(fronts) >= -net_face - 0.05

    check(control_crossed,
          "control run: with the net collider disabled the same drive command does carry the base "
          f"across X=0 (max base X {max(ctrl_xs):+.4f} m). Without this, a stalled base would look "
          "like a blocked one.")
    check(not crossed,
          f"the base never crossed the net plane while the net was active "
          f"(max base origin X {max(xs):+.4f} m, net face +/-{net_face:.4f} m)")
    check(stopped_at_net,
          f"the base actually reached the net and stopped there rather than stalling early "
          f"(front face {max(fronts):+.4f} m vs net face {-net_face:+.4f} m, converged={converged})")
    if control_crossed and not crossed and stopped_at_net:
        info("conclusion: the net collider stops a driven robot base in this build")
    UNVERIFIED.append("net behaviour against an arm swung over the top (only the base was driven)")


# --------------------------------------------------------------------------- #
# [8] teleop compatibility, [9] reach geometry
# --------------------------------------------------------------------------- #

def teleop_path_check(stage):
    print("[8] Teleoperation compatibility", flush=True)
    ok = all(stage.GetPrimAtPath(p).IsValid() and stage.GetPrimAtPath(f"{p}/base_footprint").IsValid()
             for p in ROBOT_PATHS.values())
    check(ok, "all four teleop robot prim paths from teleoperate_four_switchable.py resolve in this stage")
    for joint in ("left_wheel_joint", "back_wheel_joint", "right_wheel_joint",
                  "shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper"):
        found = 0
        for path in ROBOT_PATHS.values():
            matches = [p for p in all_prims(stage.GetPrimAtPath(path))
                       if p.GetName() == joint and p.GetTypeName() == "PhysicsRevoluteJoint"]
            if len(matches) == 1:
                found += 1
        check(found == 4, f"joint '{joint}' resolves uniquely under all four robots (got {found}/4)")


def reach_geometry(stage, baskets, base_union):
    print("[9] Reach geometry (measured, informational only)", flush=True)
    cache = make_bbox_cache()
    for label, path in ROBOT_PATHS.items():
        prim = stage.GetPrimAtPath(path)
        box = aabb(cache, prim)
        cx, cy, _ = world_translation(prim)
        if box is None:
            continue
        reach = max(abs(box[0] - cx), abs(box[3] - cx), abs(box[1] - cy), abs(box[4] - cy))
        info(f"{label} default-pose AABB span = {box[3] - box[0]:.3f} x {box[4] - box[1]:.3f} x "
             f"{box[5] - box[2]:.3f} m; max horizontal extent from spawn origin = {reach:.3f} m")
        for name, data in baskets.items():
            o = data["outer"]
            nx = max(o[0], min(cx, o[3]))
            ny = max(o[1], min(cy, o[4]))
            info(f"  -> {name} nearest rim is {((cx - nx) ** 2 + (cy - ny) ** 2) ** 0.5:.3f} m "
                 "from the spawn origin")
    if base_union:
        info(f"base+wheels width used for corridor checks = {base_union[4] - base_union[1]:.4f} m "
             "(visual mesh AABB; the asset has no colliders)")
    UNVERIFIED.append("actual arm reach into either basket (requires driving the arm joints, not done here)")


# --------------------------------------------------------------------------- #
# screenshots
# --------------------------------------------------------------------------- #

def look_at_matrix(eye, target, up=Gf.Vec3d(0, 0, 1)):
    """Camera-to-world transform for a USD camera, which looks along its local -Z."""
    forward = (target - eye).GetNormalized()
    right = Gf.Cross(forward, up).GetNormalized()
    true_up = Gf.Cross(right, forward)
    m = Gf.Matrix4d(1.0)
    m.SetRow(0, Gf.Vec4d(right[0], right[1], right[2], 0.0))
    m.SetRow(1, Gf.Vec4d(true_up[0], true_up[1], true_up[2], 0.0))
    m.SetRow(2, Gf.Vec4d(-forward[0], -forward[1], -forward[2], 0.0))
    m.SetRow(3, Gf.Vec4d(eye[0], eye[1], eye[2], 1.0))
    return m


def render_png(camera_path, out_path):
    """Render one frame; return (mean, std) so a blank or flat frame can be failed."""
    render_product = rep.create.render_product(camera_path, (960, 600))
    rgb = rep.AnnotatorRegistry.get_annotator("rgb")
    rgb.attach([render_product])
    for _ in range(6):
        rep.orchestrator.step()
    data = rgb.get_data()
    import imageio.v3 as iio
    iio.imwrite(str(out_path), data)
    rgb.detach([render_product])
    render_product.destroy()
    try:
        return float(data[..., :3].mean()), float(data[..., :3].std())
    except Exception:
        return None, None


def capture_screenshots(stage_path, out_dir):
    print("[10] Screenshots", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    # Reopen from disk: the tests moved balls in memory and the shot must show the
    # authored initial layout.
    context = omni.usd.get_context()
    context.open_stage(str(stage_path))
    for _ in range(20):
        APP.update()
    stage = context.get_stage()

    if ARGS.screenshot:
        out_path = out_dir / (stage_path.stem + ".png")
        mean_value, spread = render_png("/World/Arena/SpectatorCamera", out_path)
        check(out_path.is_file() and out_path.stat().st_size > 0,
              f"spectator screenshot written to {out_path}")
        check(mean_value is not None and mean_value > 5.0 and spread is not None and spread > 15.0,
              f"spectator screenshot shows actual scene content, not a blank or flat frame "
              f"(mean {mean_value}, std {spread})")

    if ARGS.net_view_screenshot:
        # Move the existing spectator camera in memory for one diagonal frame, then
        # reopen from disk. The saved USD, and therefore the default teleop
        # viewpoint, are never written to.
        cam_path = "/World/Arena/SpectatorCamera"
        cam_prim = stage.GetPrimAtPath(cam_path)
        # Inside the arena: outside the outer wall the camera would only see the wall.
        eye, target = Gf.Vec3d(1.15, -0.85, 0.42), Gf.Vec3d(0.0, 0.0, 0.14)
        UsdGeom.Xformable(cam_prim).MakeMatrixXform().Set(look_at_matrix(eye, target))
        UsdGeom.Camera(cam_prim).CreateFocalLengthAttr(22.0)
        for _ in range(15):
            APP.update()
        out_path = out_dir / (stage_path.stem + "_netview.png")
        mean_value, spread = render_png(cam_path, out_path)
        check(out_path.is_file() and out_path.stat().st_size > 0,
              f"net-grid inspection screenshot written to {out_path}")
        check(mean_value is not None and mean_value > 5.0 and spread is not None and spread > 15.0,
              f"net-grid screenshot shows actual scene content, not a blank or flat frame "
              f"(mean {mean_value}, std {spread})")
        # Prove the file on disk still holds the original camera placement.
        context.open_stage(str(stage_path))
        for _ in range(10):
            APP.update()
        restored = context.get_stage().GetPrimAtPath(cam_path)
        ops = UsdGeom.Xformable(restored).GetOrderedXformOps()
        check(len(ops) == 1 and ops[0].GetOpType() == UsdGeom.XformOp.TypeTranslate,
              "the saved USD still holds the original spectator camera (single translate op); "
              "the diagonal view existed only in memory")


# --------------------------------------------------------------------------- #

EXIT_CODE = 0
try:
    context = omni.usd.get_context()
    context.open_stage(str(STAGE_PATH))
    for _ in range(30):
        APP.update()
    stage = context.get_stage()
    if stage is None:
        raise RuntimeError("stage did not open")
    print(f"STAGE: {STAGE_PATH}", flush=True)

    net = net_geometry(stage)
    structural_checks(stage, net)
    baskets = basket_checks(stage, net)
    base_union = robot_checks(stage)
    basket_corridor_check(stage, baskets, base_union)
    basket_wall_flush_check(stage, baskets)
    penetration_checks(stage)
    physics_settle(stage, ARGS.settle_steps)
    net_contact_test(stage, ARGS.contact_steps, net)
    robot_drive_test(stage, 600, net, base_union)
    teleop_path_check(stage)
    reach_geometry(stage, baskets, base_union)
    if ARGS.screenshot or ARGS.net_view_screenshot:
        capture_screenshots(STAGE_PATH, ARGS.screenshot_dir.expanduser().resolve())
    else:
        UNVERIFIED.append("screenshots (not requested)")

    print("=" * 72, flush=True)
    if FAILURES:
        print(f"VERIFY FAIL: {len(FAILURES)} check(s) failed", flush=True)
        for item in FAILURES:
            print(f"  - {item}", flush=True)
        EXIT_CODE = 1
    else:
        print(f"VERIFY PASS: {STAGE_PATH.name}", flush=True)
    for item in BLOCKERS:
        print(f"  BLOCKER: {item}", flush=True)
    for item in UNVERIFIED:
        print(f"  UNVERIFIED: {item}", flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    EXIT_CODE = 2
finally:
    sys.stdout.flush()
    sys.stderr.flush()
    # SimulationApp.close(exit_code=N) flushes stdio and, with fast shutdown on (the
    # default), calls os._exit(N) itself, so Kit cannot replace the status with 0.
    APP.close(exit_code=EXIT_CODE)
    # Reached only when fast shutdown is disabled and close() returns.
    sys.exit(EXIT_CODE)
