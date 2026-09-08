"""Course CLI; starts the existing keyboard/teleop runtime without duplicating it."""
import argparse
import json
import os
from pathlib import Path
import runpy

parser = argparse.ArgumentParser(description="Four matching-color lanes and a selectable block-to-basket task")
source = parser.add_mutually_exclusive_group()
source.add_argument("--seed", type=int, help="Repeatable layout; omitted means a new random seed")
source.add_argument("--layout", help="Replay a saved /data/scenes/course.*/layout.json")
parser.add_argument("--start-count", type=int, help="Legacy straight course only")
parser.add_argument("--middle-count", type=int, help="Legacy straight course only")
parser.add_argument("--block", choices=("red", "orange", "yellow", "green"))
parser.add_argument("--basket", choices=("red", "orange", "yellow", "green"))
args = parser.parse_args()
from collection_course import generate_layout, read_layout
from color_course import generate_color_layout, select_task
# Validate before loading the expensive SimulationApp.
if args.layout and (args.start_count is not None or args.middle_count is not None):
    parser.error("--layout cannot be combined with object counts")
if (args.block is None) != (args.basket is None):
    parser.error("Specify both --block and --basket")
if args.layout:
    layout = read_layout(args.layout)
elif args.start_count is not None or args.middle_count is not None:
    layout = generate_layout(args.seed, args.start_count if args.start_count is not None else 2,
                             args.middle_count if args.middle_count is not None else 3)
else:
    layout = generate_color_layout(args.seed)
if args.block is not None:
    layout = select_task(layout, args.block, args.basket)
os.environ["LEKIWI_COURSE_LAYOUT"] = "prepared"
os.environ["LEKIWI_COURSE_JSON"] = json.dumps(layout, allow_nan=False)
runpy.run_path(str(Path(__file__).with_name("keyboard_drive.py")), run_name="__main__")
