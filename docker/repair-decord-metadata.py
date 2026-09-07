"""Repair only Decord 0.6.0's known incorrect installed Linux wheel tag.

Upstream: https://github.com/dmlc/decord/issues/356
The advertised PyPI filename uses py3-none; the implementation uses ctypes.
Runtime video decoding is checked separately, not inferred from this repair.
"""

import base64
import csv
import hashlib
from importlib.metadata import distribution
from pathlib import Path


def repair(dist_info: Path):
    wheel = dist_info / "WHEEL"
    original = wheel.read_bytes()
    old = b"Tag: cp36-cp36m-manylinux2010_x86_64"
    new = b"Tag: py3-none-manylinux2010_x86_64"
    if original.count(old) != 1:
        raise RuntimeError("Unexpected Decord wheel metadata; review before patching")
    updated = original.replace(old, new)
    record = dist_info / "RECORD"
    with record.open(newline="") as stream:
        rows = list(csv.reader(stream))
    matches = [row for row in rows if row[0] == f"{dist_info.name}/WHEEL"]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one WHEEL entry in Decord RECORD")
    digest = base64.urlsafe_b64encode(hashlib.sha256(updated).digest()).rstrip(b"=").decode()
    matches[0][1:] = [f"sha256={digest}", str(len(updated))]
    wheel.write_bytes(updated)
    with record.open("w", newline="") as stream:
        csv.writer(stream).writerows(rows)


if __name__ == "__main__":
    dist = distribution("decord")
    if dist.version != "0.6.0":
        raise RuntimeError("This repair is scoped to Decord 0.6.0 only")
    repair(Path(dist.locate_file("decord-0.6.0.dist-info")))
    print("Corrected Decord 0.6.0 WHEEL tag and its RECORD checksum")
