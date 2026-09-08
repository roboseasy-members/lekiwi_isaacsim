"""LeKiwi 관측·행동과 두 RGB의 저장 규격. Isaac Sim과 하드웨어에 의존하지 않는다."""
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

import numpy as np
from PIL import Image

FPS = 30
CAMERAS = ("front", "wrist")
JOINTS = ("shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_roll", "gripper")
STATE_NAMES = list(JOINTS) + ["base_vx", "base_vy", "base_wz"]
ACTION_NAMES = [name + ".target" for name in JOINTS] + ["base_vx", "base_vy", "base_wz"]


def vector(values, size=9):
    result = np.asarray(values, dtype=np.float64)
    if result.shape != (size,) or not np.isfinite(result).all():
        raise ValueError(f"Expected {size} finite values")
    return result.tolist()


def check_transition(row, previous=None):
    """시간을 조작하거나 누락 프레임을 정상 FPS로 간주하지 않는다."""
    for key in ("observation.state", "action", "next_observation.state"):
        vector(row[key])
    vector(row["base_pose"], 7)
    t, end = row["simulation_time"], row["next_simulation_time"]
    if not all(type(v) in (int, float) and math.isfinite(v) for v in (t, end)):
        raise ValueError("Non-finite simulation time")
    if not math.isclose(end - t, 1 / FPS, abs_tol=1e-6):
        raise ValueError("Simulation frame gap: expected 1/30 s")
    if type(row["frame_index"]) is not int or row["frame_index"] < 0:
        raise ValueError("Invalid frame index")
    if not math.isclose(row["timestamp"], row["frame_index"] / FPS, abs_tol=1e-6):
        raise ValueError("Invalid episode timestamp")
    for name in CAMERAS:
        stamp = row["cameras"][name]["simulation_time"]
        if not math.isfinite(stamp) or not math.isclose(stamp, t, abs_tol=1e-6):
            raise ValueError(f"{name}: RGB and observation times differ")
        ref = row["cameras"][name]["render_reference"]
        if len(ref) != 2 or any(type(v) is not int for v in ref) or ref[1] <= 0:
            raise ValueError("Invalid render reference")
    if row["cameras"]["front"]["render_reference"] != row["cameras"]["wrist"]["render_reference"]:
        raise ValueError("Camera render references differ")
    if previous is None:
        if row["frame_index"] != 0:
            raise ValueError("Episode must begin at frame 0")
    elif (row["frame_index"] != previous["frame_index"] + 1
          or not math.isclose(t, previous["next_simulation_time"], abs_tol=1e-6)
          or not np.allclose(row["observation.state"], previous["next_observation.state"], atol=1e-6, rtol=0)):
        raise ValueError("Frames are not consecutive observations")
    elif row["cameras"]["front"]["render_reference"] == previous["cameras"]["front"]["render_reference"]:
        raise ValueError("Repeated render frame")


class EpisodeWriter:
    """이번 실행에서 만든 임시 에피소드만 관리하며 완료 manifest를 마지막에 쓴다."""
    def __init__(self, parent, metadata):
        parent = Path(parent)
        parent.mkdir(parents=True, exist_ok=True)
        self.path = Path(tempfile.mkdtemp(prefix="episode.", suffix=".partial", dir=parent))
        self.metadata = metadata
        self.stream = (self.path / "frames.jsonl").open("x")
        self.count = 0
        self.previous = None
        self.saved = False

    def append(self, row, images):
        if self.saved or self.stream.closed:
            raise RuntimeError("Episode is closed")
        row = dict(row, frame_index=self.count, timestamp=self.count / FPS)
        check_transition(row, self.previous)
        for name in CAMERAS:
            rgb = np.asarray(images[name])
            width, height = self.metadata["camera_config"]["cameras"][name]["resolution"]
            if rgb.dtype != np.uint8 or rgb.shape != (height, width, 3):
                raise ValueError(f"{name}: invalid RGB shape or dtype")
        # 배열 검사가 끝난 뒤 파일을 생성한다. 중간 실패는 .partial로 남는다.
        for name in CAMERAS:
            relative = f"images/{name}/{self.count:06d}.png"
            path = self.path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(images[name]).save(path, compress_level=1)
            row["cameras"][name].update(path=relative, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.stream.write(json.dumps(row, allow_nan=False) + "\n")
        self.count += 1
        self.previous = row

    def stop(self):
        self.stream.close()

    def save(self, success=False):
        if self.saved or not self.count:
            raise ValueError("No unsaved frames")
        self.stop()
        metadata = dict(self.metadata, version=1, fps=FPS, frames=self.count,
                        duration_s=self.count / FPS, success=bool(success), complete=True,
                        state_names=STATE_NAMES, action_names=ACTION_NAMES,
                        units=["rad"] * 6 + ["m/s", "m/s", "rad/s"])
        validate_episode(self.path, metadata, collect_rows=False)
        (self.path / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
        target = self.path.with_suffix("")
        if target.exists():
            raise FileExistsError(target)
        self.path.rename(target)
        self.path, self.saved = target, True
        return target

    def discard(self):
        if self.saved:
            raise ValueError("Saved episodes cannot be discarded")
        self.stop()
        shutil.rmtree(self.path)


def validate_episode(directory, metadata=None, *, collect_rows=True):
    """전체 프레임을 검사하되 저장 완료 검사에서는 직전 프레임만 보관한다."""
    directory = Path(directory)
    if metadata is None:
        if directory.name.endswith(".partial"):
            raise ValueError("Incomplete episode")
        metadata = json.loads((directory / "manifest.json").read_text())
    if metadata.get("version") != 1 or metadata.get("fps") != FPS or metadata.get("complete") is not True:
        raise ValueError("Unsupported or incomplete manifest")
    rows = [] if collect_rows else None
    previous = None
    count = 0
    with (directory / "frames.jsonl").open() as stream:
        for line in stream:
            row = json.loads(line)
            check_transition(row, previous)
            for name in CAMERAS:
                expected = f"images/{name}/{row['frame_index']:06d}.png"
                entry = row["cameras"][name]
                if entry["path"] != expected:
                    raise ValueError("Unexpected image path")
                path = directory / expected
                if not path.resolve().is_relative_to(directory.resolve()):
                    raise ValueError("Image outside episode")
                if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                    raise ValueError("Image checksum mismatch")
                with Image.open(path) as im:
                    if im.mode != "RGB" or list(im.size) != metadata["camera_config"]["cameras"][name]["resolution"]:
                        raise ValueError("Invalid image resolution")
                    im.load()
            previous = row
            count += 1
            if rows is not None:
                rows.append(row)
    if not count or count != metadata["frames"]:
        raise ValueError("Frame count mismatch")
    return metadata, rows
