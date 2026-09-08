"""Compose untouched UI screenshots and vector callouts into standalone SVGs.

Run with standard Python after updating annotations.json. No raster editing,
resampling or image generation; the original PNG bytes are embedded verbatim.
"""
import base64
import hashlib
import html
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent


def main(root=ROOT):
    records = json.loads((root / "annotations.json").read_text())
    for record in records:
        source = root / "screenshots" / (record["name"] + ".png")
        raw = source.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", source
        width, height = struct.unpack(">II", raw[16:24])
        footer = 48 + len(record["marks"]) * 28
        caption = html.escape(record["title"])
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                 f'height="{height + footer}" viewBox="0 0 {width} {height + footer}" '
                 'role="img" aria-labelledby="title">',
                 f'<title id="title">{caption}</title>',
                 f'<metadata>Screenshot SHA256: {hashlib.sha256(raw).hexdigest()}</metadata>',
                 f'<image width="{width}" height="{height}" href="data:image/png;base64,'
                 + base64.b64encode(raw).decode() + '"/>',
                 f'<rect y="{height}" width="{width}" height="{footer}" fill="#101b2b"/>',
                 f'<text x="24" y="{height+29}" fill="white" font-family="sans-serif" '
                 f'font-size="20" font-weight="bold">{caption}</text>']
        for index, mark in enumerate(record["marks"], 1):
            x, y, w, h = mark["box"]
            assert 0 <= x < x+w <= width and 0 <= y < y+h <= height, mark
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                         'fill="none" stroke="#ff3939" stroke-width="3"/>')
            # Labels sit in the separate caption area, never over UI text.
            parts.append(f'<text x="24" y="{height+58+(index-1)*28}" fill="#edf3ff" '
                         f'font-family="sans-serif" font-size="17">{index}. '
                         f'{html.escape(mark["label"])}</text>')
        parts.append('</svg>')
        (root / (record["name"] + ".svg")).write_text("\n".join(parts))
    print(f"Built {len(records)} annotated screenshots")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT)
