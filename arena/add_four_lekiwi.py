import argparse
from pathlib import Path

# 저장소 어디에 두든 동작하도록 이 파일 위치에서 저장소 루트를 잡는다.
REPO = Path(__file__).resolve().parent.parent

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, default=REPO / "stages/lekiwi_arena_3p0x2p0_net_R.usd")
parser.add_argument("--output", type=Path, default=REPO / "stages/lekiwi_arena_3p0x2p0_net_R_4robots.usd")
args = parser.parse_args()

from isaacsim import SimulationApp

app = SimulationApp({"headless": True})

from pxr import Sdf, Usd

arena_source = args.source.expanduser().resolve()
arena_output = args.output.expanduser().resolve()
robot_asset = REPO / "assets/lekiwi_soarm_no_lidar_collision/lekiwi_soarm_no_lidar_collision.usd"

spawn_paths = [
    "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_01",
    "/World/Arena/RobotSpawnPoints/TeamBlue/TeamBlue_Spawn_02",
    "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_01",
    "/World/Arena/RobotSpawnPoints/TeamRed/TeamRed_Spawn_02",
]

if not arena_source.is_file():
    raise FileNotFoundError(arena_source)

if not robot_asset.is_file():
    raise FileNotFoundError(robot_asset)

source_stage = Usd.Stage.Open(str(arena_source))
if source_stage is None:
    raise RuntimeError(f"Cannot open {arena_source}")

source_stage.GetRootLayer().Export(str(arena_output))

stage = Usd.Stage.Open(str(arena_output))
if stage is None:
    raise RuntimeError(f"Cannot open {arena_output}")

for path in spawn_paths:
    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        raise RuntimeError(f"Missing spawn point: {path}")

    prim.GetReferences().ClearReferences()
    prim.GetReferences().AddReference(str(robot_asset))
    print(f"Added LeKiwi: {path}")

arena = stage.GetPrimAtPath("/World/Arena")
arena.CreateAttribute(
    "arena:assetStatus",
    Sdf.ValueTypeNames.String,
).Set("Four bundled LeKiwi robots referenced at team spawn points")

stage.GetRootLayer().Save()

check_stage = Usd.Stage.Open(str(arena_output))
for path in spawn_paths:
    prim = check_stage.GetPrimAtPath(path)
    child_count = len(prim.GetChildren())
    if child_count == 0:
        raise RuntimeError(f"Robot reference did not compose: {path}")
    print(f"PASS: {path}, composed children={child_count}")

print(f"CREATED: {arena_output}")
print("PASS: 4 LeKiwi robot references")
app.close()
