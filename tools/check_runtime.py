"""Check installed ML modules without a model download or hardware access."""

import argparse
import importlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", action="store_true", help="Also require a working CUDA device")
    args = parser.parse_args()
    for module in (
        "torch", "torchvision", "torchcodec", "zmq", "serial",
        "lerobot.datasets.lerobot_dataset",
        "lerobot.policies.act.modeling_act",
        "lerobot.policies.groot.modeling_groot",
        "lerobot.teleoperators.so_leader",
        "decord",
    ):
        importlib.import_module(module)
    # Validate the actual FFmpeg/Decord/TorchCodec ABI, not only imports.
    from decord import VideoReader
    from torchcodec.decoders import VideoDecoder

    with tempfile.TemporaryDirectory(prefix="lekiwi-video-check-") as directory:
        video = Path(directory) / "test.mp4"
        subprocess.run([
            "ffmpeg", "-v", "error", "-f", "lavfi", "-i",
            "testsrc2=size=64x64:rate=5", "-t", "1", "-c:v", "mpeg4", str(video),
        ], check=True)
        decord_reader = VideoReader(str(video))
        torch_reader = VideoDecoder(str(video), device="cpu")
        if len(decord_reader) != 5 or decord_reader[0].shape != (64, 64, 3):
            raise RuntimeError("Decord failed to decode the synthetic video")
        if len(torch_reader) != 5 or tuple(torch_reader[0].shape) != (3, 64, 64):
            raise RuntimeError("TorchCodec failed to decode the synthetic video")
    if args.gpu:
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available inside the LeRobot container")
        # Exercise a CUDA operation, not just driver discovery.
        value = (torch.ones(4, device="cuda") * 2).sum().item()
        if value != 8:
            raise RuntimeError("CUDA computation failed")
    print(json.dumps({
        "result": "PASS",
        "gpu_checked": args.gpu,
        "video_decode_checked": ["decord", "torchcodec"],
        "packages": {name: importlib.metadata.version(name)
                     for name in ("lerobot", "torch", "torchvision", "torchcodec")},
    }, indent=2))


if __name__ == "__main__":
    main()
