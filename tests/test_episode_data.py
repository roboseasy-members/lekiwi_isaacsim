"""RGB·명령 시간 대응, 불완전 기록, 기존 저장본 보호를 검사한다."""
import json
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from episode_data import EpisodeWriter, validate_episode


def metadata():
    return {"camera_config": {"calibrated": False, "cameras": {
        name: {"resolution": [16, 16]} for name in ("front", "wrist")}},
        "task": "Move forward and stop", "source": "keyboard_home_hold", "course_layout": None}


def sample(i):
    return {"simulation_time": 2 + i/30, "next_simulation_time": 2 + (i+1)/30,
            "observation.state": [i/100]*9, "next_observation.state": [(i+1)/100]*9,
            "action": [.1]*9, "base_pose": [0, 0, .04, 1, 0, 0, 0],
            "cameras": {name: {"simulation_time": 2+i/30, "render_reference": [60+i, 30]}
                        for name in ("front", "wrist")}}


def images():
    return {name: np.full((16, 16, 3), value, dtype=np.uint8)
            for name, value in (("front", 20), ("wrist", 130))}


def saved(parent):
    writer = EpisodeWriter(parent, metadata())
    for i in range(3):
        writer.append(sample(i), images())
    return writer, writer.save(success=True)


def test_save_round_trip_and_camera_separation(tmp_path):
    writer, path = saved(tmp_path)
    meta, rows = validate_episode(path)
    assert writer.saved and not path.name.endswith(".partial")
    assert meta["frames"] == 3 and meta["success"] is True
    assert rows[0]["cameras"]["front"]["sha256"] != rows[0]["cameras"]["wrist"]["sha256"]
    assert rows[2]["action"] == sample(2)["action"]


@pytest.mark.parametrize("kind", ["stale_rgb", "gap", "nan", "observation_gap", "wrong_image", "render_mismatch", "repeated_render"])
def test_invalid_pair_is_not_appended(tmp_path, kind):
    writer = EpisodeWriter(tmp_path, metadata())
    writer.append(sample(0), images())
    row, rgb = sample(1), images()
    if kind == "stale_rgb": row["cameras"]["wrist"]["simulation_time"] -= 1/30
    if kind == "gap": row["next_simulation_time"] += 1/30
    if kind == "nan": row["action"][0] = float("nan")
    if kind == "observation_gap": row["observation.state"][0] = 5
    if kind == "wrong_image": rgb["front"] = np.zeros((10, 10, 3), dtype=np.uint8)
    if kind == "render_mismatch": row["cameras"]["wrist"]["render_reference"] = [99, 30]
    if kind == "repeated_render":
        for name in ("front", "wrist"): row["cameras"][name]["render_reference"] = [60, 30]
    with pytest.raises(ValueError): writer.append(row, rgb)
    assert writer.count == 1
    writer.stop()
    with pytest.raises(ValueError, match="Incomplete"): validate_episode(writer.path)


def test_discard_does_not_remove_saved_episode(tmp_path):
    old, path = saved(tmp_path)
    previous = (path / "frames.jsonl").read_bytes()
    new = EpisodeWriter(tmp_path, metadata())
    new.append(sample(0), images())
    new.discard()
    assert not new.path.exists()
    assert (path / "frames.jsonl").read_bytes() == previous
    with pytest.raises(ValueError): old.discard()


@pytest.mark.parametrize("kind", ["image_bytes", "path", "row_count"])
def test_corrupt_saved_episode_is_rejected(tmp_path, kind):
    _, path = saved(tmp_path)
    file = path / "frames.jsonl"
    rows = [json.loads(line) for line in file.read_text().splitlines()]
    if kind == "image_bytes": (path / rows[0]["cameras"]["front"]["path"]).write_bytes(b"bad")
    if kind == "path": rows[0]["cameras"]["front"]["path"] = "../../outside.png"
    if kind == "row_count": rows.pop()
    file.write_text("".join(json.dumps(row)+"\n" for row in rows))
    with pytest.raises(ValueError): validate_episode(path)
