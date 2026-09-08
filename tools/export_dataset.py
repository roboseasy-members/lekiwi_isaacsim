"""완료된 LeKiwi 기록을 로컬 LeRobot v3 데이터셋으로 변환·재열기 검사한다."""
import argparse
import json
import os
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "isaac_sim"))
from episode_data import ACTION_NAMES, CAMERAS, FPS, STATE_NAMES, validate_episode


def export(source, output, repo_id, success_only=False):
    os.environ["HF_HUB_OFFLINE"] = "1"
    from lerobot.datasets.lerobot_dataset import LeRobotDataset

    source, output = Path(source), Path(output)
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    paths = [source] if (source / "manifest.json").exists() else sorted(source.glob("episode.*"))
    episodes = []
    for path in paths:
        if path.name.endswith(".partial"):
            continue
        metadata, rows = validate_episode(path)
        if not success_only or metadata["success"]:
            episodes.append((path, metadata, rows))
    if not episodes:
        raise ValueError("No complete episodes match the selection")
    camera_config = episodes[0][1]["camera_config"]
    for _, metadata, _ in episodes:
        if metadata["camera_config"] != camera_config:
            raise ValueError("Do not mix different camera mounts/resolutions in one dataset")
    features = {"observation.state": {"dtype": "float32", "shape": (9,), "names": STATE_NAMES},
                "action": {"dtype": "float32", "shape": (9,), "names": ACTION_NAMES}}
    for name in CAMERAS:
        w, h = camera_config["cameras"][name]["resolution"]
        features[f"observation.images.{name}"] = {"dtype": "video", "shape": (h, w, 3),
                                                 "names": ["height", "width", "channels"]}
    dataset = LeRobotDataset.create(repo_id=repo_id, fps=FPS, root=output, robot_type="lekiwi_sim",
                                   features=features, use_videos=True, video_backend="pyav",
                                   image_writer_threads=2)
    try:
        for path, metadata, rows in episodes:
            for row in rows:
                frame = {key: np.asarray(row[key], dtype=np.float32) for key in ("observation.state", "action")}
                for name in CAMERAS:
                    with Image.open(path / row["cameras"][name]["path"]) as im:
                        frame[f"observation.images.{name}"] = np.asarray(im).copy()
                frame["task"] = metadata["task"]
                dataset.add_frame(frame)
            dataset.save_episode()
    finally:
        dataset.finalize()
    # 변환 완료 표시는 실제 데이터 재열기와 두 영상의 디코딩 검사 후 기록한다.
    loaded = LeRobotDataset(repo_id=repo_id, root=output, video_backend="pyav")
    expected_count = sum(len(rows) for _, _, rows in episodes)
    if len(loaded) != expected_count or loaded.num_episodes != len(episodes):
        raise ValueError("Exported dataset counts differ")
    offset = 0
    for _, metadata, rows in episodes:
        for index in sorted({0, len(rows) // 2, len(rows) - 1}):
            item = loaded[offset + index]
            for key in ("observation.state", "action"):
                np.testing.assert_allclose(item[key].numpy(), rows[index][key], atol=1e-6, rtol=0)
            for name in CAMERAS:
                w, h = camera_config["cameras"][name]["resolution"]
                rgb = item[f"observation.images.{name}"]
                if tuple(rgb.shape) != (3, h, w) or not np.isfinite(rgb.numpy()).all():
                    raise ValueError("Decoded RGB is invalid")
        offset += len(rows)
    report = {"complete": True, "repo_id": repo_id, "episodes": len(episodes), "frames": expected_count,
              "fps": FPS, "camera_config": camera_config,
              "sources": [{"path": str(path), "source": m["source"], "success": m["success"],
                           "frames": len(rows), "course_layout": m["course_layout"]} for path, m, rows in episodes],
              "validation": "All raw frames/hashes/timestamps checked; first/middle/last state/action and both videos decoded per episode"}
    (output / "recording_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"LEKIWI_DATASET result=PASS episodes={len(episodes)} frames={expected_count} root={output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="/data/recordings/lekiwi.* or a saved episode")
    parser.add_argument("--output", required=True, type=Path, help="New /data/datasets/... directory")
    parser.add_argument("--repo-id", default="local/lekiwi_lesson6")
    parser.add_argument("--success-only", action="store_true")
    args = parser.parse_args()
    export(args.input, args.output, args.repo_id, args.success_only)
