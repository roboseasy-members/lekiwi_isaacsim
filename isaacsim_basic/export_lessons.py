"""Export chapter Markdown and vector annotations to Notion HTML + PNG ZIPs.

Authoring utility, Ubuntu: python3-markdown-it, python3-gi, python3-cairo,
gir1.2-rsvg-2.0. Students only need the already generated files.
Run: /usr/bin/python3 isaacsim_basic/export_lessons.py [chapter directory ...]
"""
from pathlib import Path
import argparse
import html
import tempfile
import zipfile

import cairo
import gi
gi.require_version("Rsvg", "2.0")
from gi.repository import Rsvg
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent


def render_svg(source, target):
    handle = Rsvg.Handle.new_from_file(str(source))
    valid, width, height = handle.get_intrinsic_size_in_pixels()
    if not valid:
        raise ValueError(f"SVG needs explicit dimensions: {source}")
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
    bounds = Rsvg.Rectangle()
    bounds.x = bounds.y = 0
    bounds.width, bounds.height = width, height
    handle.render_document(cairo.Context(surface), bounds)
    surface.write_to_png(str(target))


def export(chapter):
    # PNGs also make the ordinary Markdown portable to readers without SVG support.
    for source in sorted((chapter / "images").glob("*.svg")):
        render_svg(source, source.with_suffix(".png"))
    parser = MarkdownIt("commonmark").enable("table")
    used_images = set()
    with tempfile.TemporaryDirectory(prefix="isaacsim-notion-") as tmp:
        output = Path(tmp)
        for source in sorted(chapter.glob("*.md")):
            tokens = parser.parse(source.read_text())
            for block in tokens:
                for token in block.children or []:
                    if token.type == "image":
                        ref = token.attrGet("src")
                        path = (chapter / ref).resolve()
                        if not path.is_relative_to(chapter.resolve()) or not path.is_file():
                            raise ValueError(f"Image is not self contained: {source}: {ref}")
                        if path.suffix == ".svg":
                            path = path.with_suffix(".png")
                        relative = path.relative_to(chapter.resolve()).as_posix()
                        token.attrSet("src", relative)
                        used_images.add((path, relative))
                    elif token.type == "link_open":
                        ref = token.attrGet("href")
                        if ":" not in ref and not ref.startswith("#"):
                            path = (chapter / ref.split("#")[0]).resolve()
                            if path.parent == chapter.resolve() and path.suffix == ".md":
                                token.attrSet("href", path.with_suffix(".html").name)
                            else:
                                # Cross-chapter/repository navigation is useful in Git,
                                # but cannot resolve inside a single-chapter import.
                                token.attrSet("href", "#repository-links")
            body = parser.renderer.render(tokens, parser.options, {})
            page = ('<!doctype html><html lang="ko"><meta charset="utf-8">'
                    f'<title>{html.escape(chapter.name)} · {html.escape(source.stem)}</title>'
                    '<body>' + body + '<p id="repository-links">다른 편과 저장소 파일 링크는 '
                    '전체 교재의 Markdown에서 열어 주세요.</p></body></html>')
            (output / source.with_suffix(".html").name).write_text(page)
        target = chapter / f"{chapter.name}_notion.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
            for page in sorted(output.glob("*.html")):
                archive.write(page, page.name)
            for image_path, relative in sorted(used_images):
                archive.write(image_path, relative)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
        print(f"{target}: {len(used_images)} images, {target.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapters", nargs="*")
    args = parser.parse_args()
    for chapter in [Path(p).resolve() for p in args.chapters] or sorted(ROOT.glob("[0-9][0-9]_*")):
        if (chapter / "README.md").is_file():
            export(chapter)
