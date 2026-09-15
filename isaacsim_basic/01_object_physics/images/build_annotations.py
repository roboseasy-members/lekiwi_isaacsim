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
import unicodedata

ROOT = Path(__file__).resolve().parent


def caption_lines(label, index, width, wrap=False):
    text = f"{index}. {label}"
    if not wrap:
        return [text]
    # 한글은 영문보다 넓게 잡아 좁은 메뉴 캡처의 설명도 잘리지 않게 합니다.
    limit = max(12, int((width - 48) / 10))
    lines, line, units = [], "", 0
    for char in text:
        size = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if units + size > limit:
            lines.append(line.rstrip())
            line, units = "  ", 2
        line += char
        units += size
    lines.append(line.rstrip())
    return lines


def main(root=ROOT):
    records = json.loads((root / "annotations.json").read_text())
    for record in records:
        source = root / "screenshots" / (record["name"] + ".png")
        raw = source.read_bytes()
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", source
        source_width, source_height = struct.unpack(">II", raw[16:24])
        left, top, width, height = record.get("crop", [0, 0, source_width, source_height])
        assert 0 <= left < left+width <= source_width and 0 <= top < top+height <= source_height, record
        screenshot = (f'<image width="{source_width}" height="{source_height}" href="data:image/png;base64,'
                      + base64.b64encode(raw).decode() + '"/>')
        if "crop" in record:
            # 원본 PNG를 유지하며, 해당 단계에 필요한 메뉴·속성 영역만 표시합니다.
            screenshot = (f'<svg width="{width}" height="{height}" '
                          f'viewBox="{left} {top} {width} {height}" overflow="hidden">'
                          + screenshot + '</svg>')
        labels = [line for index, mark in enumerate(record["marks"], 1)
                  for line in caption_lines(mark["label"], index, width,
                                            record.get("wrap_labels", False))]
        footer = 48 + len(labels) * 28
        caption = html.escape(record["title"])
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
                 f'height="{height + footer}" viewBox="0 0 {width} {height + footer}" '
                 'role="img" aria-labelledby="title">',
                 f'<title id="title">{caption}</title>',
                 f'<metadata>Screenshot SHA256: {hashlib.sha256(raw).hexdigest()}</metadata>',
                 screenshot,
                 f'<rect y="{height}" width="{width}" height="{footer}" fill="#101b2b"/>',
                 f'<text x="24" y="{height+29}" fill="white" font-family="sans-serif" '
                 f'font-size="20" font-weight="bold">{caption}</text>']
        for index, mark in enumerate(record["marks"], 1):
            x, y, w, h = mark["box"]
            x, y = x-left, y-top
            assert 0 <= x < x+w <= width and 0 <= y < y+h <= height, mark
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                         'fill="none" stroke="#ff3939" stroke-width="3"/>')
            if not record.get("wrap_labels", False):
                # 이전 표시본의 출력 순서를 유지합니다.
                parts.append(f'<text x="24" y="{height+58+(index-1)*28}" fill="#edf3ff" '
                             f'font-family="sans-serif" font-size="17">{index}. '
                             f'{html.escape(mark["label"])}</text>')
        if record.get("wrap_labels", False):
            # 설명은 화면 위에 겹치지 않고 별도 영역에서 줄바꿈합니다.
            for index, label in enumerate(labels):
                parts.append(f'<text x="24" y="{height+58+index*28}" fill="#edf3ff" '
                             f'font-family="sans-serif" font-size="17">{html.escape(label)}</text>')
        parts.append('</svg>')
        (root / (record["name"] + ".svg")).write_text("\n".join(parts))
    print(f"Built {len(records)} annotated screenshots")


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT)
