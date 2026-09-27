"""Unzip/rezip helpers for OOXML (.pptx) packages.

A .pptx is a zip archive of XML parts. We unpack it to a working directory,
edit the XML parts as raw text (see slides.py / tables.py / text.py), then
repack. We never round-trip the XML through a generic tree parser+serializer
(e.g. xml.etree.ElementTree) for parts we write back out, since that rewrites
namespace prefixes and can corrupt the deck -- all edits are scoped string
substitutions on the raw part text instead.
"""

import shutil
import zipfile
from pathlib import Path


def unpack(pptx_path: Path, dest_dir: Path) -> Path:
    """Extract a .pptx into dest_dir (created fresh). Returns dest_dir."""
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True)
    with zipfile.ZipFile(pptx_path, "r") as z:
        z.extractall(dest_dir)
    return dest_dir


def repack(src_dir: Path, out_pptx_path: Path) -> Path:
    """Zip src_dir's contents back into a .pptx at out_pptx_path.

    [Content_Types].xml is written first, as some consumers expect it early
    in the archive, though OPC does not strictly require any particular order.
    """
    out_pptx_path.parent.mkdir(parents=True, exist_ok=True)
    if out_pptx_path.exists():
        out_pptx_path.unlink()

    all_files = sorted(p for p in src_dir.rglob("*") if p.is_file())
    content_types = src_dir / "[Content_Types].xml"
    ordered = [content_types] if content_types in all_files else []
    ordered += [p for p in all_files if p != content_types]

    with zipfile.ZipFile(out_pptx_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in ordered:
            arcname = path.relative_to(src_dir).as_posix()
            z.write(path, arcname)
    return out_pptx_path


def read_part(unpacked_dir: Path, part_path: str) -> str:
    """Read a package part (e.g. 'ppt/slides/slide1.xml') as text."""
    return (unpacked_dir / part_path).read_text(encoding="utf-8")


def write_part(unpacked_dir: Path, part_path: str, content: str) -> None:
    """Write text back to a package part, creating parent dirs if needed."""
    full_path = unpacked_dir / part_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
