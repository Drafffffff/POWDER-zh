#!/usr/bin/env python3
"""Patch three Chinese menu glyphs using native 8px Fusion Pixel bitmaps.

Input is the exact POWDER 118 original. All six built-in tilesets and all
five font styles are patched. Optional native-style black shadow, with no
antialiasing or scaling of the bitmap strokes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from PIL import Image

PROJECT = Path(__file__).resolve().parents[1]
FONT_PATH = PROJECT / "assets/fonts/fusion-pixel-8px/fusion-pixel-8px-monospaced-zh_hans.bdf"
ORIGINAL_SHA256 = "20bf244560265e8215ea9df2d23c3c85a93bb49f1a91010a230d0d125cc3b654"
TILESET_TABLE = 0x22BB78
TEXT_TABLE_ALIASES = 0x21EF65
NEW_GAME = 0x21F47C
GLYPH_INDEX = 111  # 0x8b is tile 110, its first following space is tile 111.
CHARACTERS = "新游戏"


def load_glyphs(path: Path) -> dict[str, bytes]:
    """Read BDF BBX coordinates at ascent=7 into each exact 8x8 cell."""
    result = {}
    text = path.read_text(encoding="utf-8")
    if "FONT_ASCENT 7\n" not in text or "PIXEL_SIZE 8\n" not in text:
        raise ValueError("Expected Fusion Pixel native 8px BDF")
    wanted = {ord(ch): ch for ch in CHARACTERS}
    for block in text.split("STARTCHAR ")[1:]:
        lines = block.splitlines()
        encoding = next(int(line.split()[1]) for line in lines if line.startswith("ENCODING "))
        if encoding not in wanted:
            continue
        width, height, xoff, yoff = next(
            tuple(map(int, line.split()[1:])) for line in lines if line.startswith("BBX ")
        )
        start = lines.index("BITMAP") + 1
        rows = lines[start:start + height]
        cell = bytearray(64)
        top = 7 - (height + yoff)
        for y, row in enumerate(rows):
            bits = int(row, 16)
            for x in range(width):
                if bits & (1 << (len(row) * 4 - x - 1)):
                    cx, cy = xoff + x, top + y
                    if not (0 <= cx < 8 and 0 <= cy < 8):
                        raise ValueError("Glyph escapes its 8x8 cell")
                    cell[cy * 8 + cx] = 1
        result[wanted[encoding]] = bytes(cell)
    if set(result) != set(CHARACTERS):
        raise ValueError("Missing Chinese glyphs")
    return result


def write_ips(original: bytes, patched: bytes, path: Path):
    patch = bytearray(b"PATCH")
    at = 0
    while at < len(original):
        if original[at] == patched[at]:
            at += 1
            continue
        start = at
        while at < len(original) and original[at] != patched[at] and at - start < 65535:
            at += 1
        patch.extend(start.to_bytes(3, "big"))
        patch.extend((at - start).to_bytes(2, "big"))
        patch.extend(patched[start:at])
    path.write_bytes(patch + b"EOF")


def render_tile(mask: bytes, foreground: int, shadow: int | None) -> bytes:
    if shadow is None:
        return bytes(foreground if pixel else 0 for pixel in mask)
    # The BDF's 7px Chinese ink occupies y=1..7. Move it up one row so the
    # lower-right shadow fits in the existing 8x8 cell without clipping ink.
    if any(mask[:8]) or any(mask[x] for x in range(7, 64, 8)):
        raise ValueError("Shadow requires a blank top row and right column")
    ink = mask[8:] + bytes(8)
    tile = bytearray(64)
    for y in range(7):
        for x in range(7):
            if ink[y * 8 + x]:
                tile[(y + 1) * 8 + x + 1] = shadow
    # Keep all white strokes above the shadow, including enclosed counters.
    for i, pixel in enumerate(ink):
        if pixel:
            tile[i] = foreground
    return bytes(tile)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--preview", type=Path)
    ap.add_argument("--shadow", action="store_true", help="Add original-style 1px lower-right black shadow")
    args = ap.parse_args()
    original = args.input.read_bytes()
    if hashlib.sha256(original).hexdigest() != ORIGINAL_SHA256:
        raise SystemExit("Input must be the unmodified POWDER 118 original ROM")
    data = bytearray(original)
    glyphs = load_glyphs(FONT_PATH)
    if data[TEXT_TABLE_ALIASES:TEXT_TABLE_ALIASES + 3] != b"   ":
        raise ValueError("Unexpected character table layout")
    if data[NEW_GAME:NEW_GAME + 9] != b"New Game\0":
        raise ValueError("Unexpected menu text")
    data[TEXT_TABLE_ALIASES:TEXT_TABLE_ALIASES + 3] = bytes((0x8C, 0x8D, 0x8E))
    data[NEW_GAME:NEW_GAME + 9] = bytes((0x8C, 0x8D, 0x8E)) + b"\0" * 6

    records = []
    for tileset in range(6):
        fields = struct.unpack_from("<13I", original, TILESET_TABLE + tileset * 52)
        if fields[12] != 8:
            raise ValueError("Expected an 8px built-in tileset")
        palette = struct.unpack_from("<256H", original, fields[8] - 0x08000000)
        # Select actual white from each tileset's palette; Lomaka uses another
        # index than the other five tilesets.
        foreground = max(range(1, 256), key=lambda i: sum(
            (palette[i] >> shift) & 31 for shift in (0, 5, 10)))
        # Index 0 is transparent. Use the opaque black already used by the
        # original Shadow font (32 in most tilesets, 31 in Chris Lomaka).
        shadow_sample = original[fields[2] - 0x08000000 + 30 * 64:
                                 fields[2] - 0x08000000 + 31 * 64]
        black = next((pixel for pixel in shadow_sample if pixel and palette[pixel] == 0), None)
        if args.shadow and black is None:
            raise ValueError("Original Shadow font has no opaque black")
        name_at = fields[11] - 0x08000000
        name = original[name_at:original.index(0, name_at)].decode("ascii")
        for style, address in enumerate(fields[:5]):
            block = address - 0x08000000
            for slot, ch in enumerate(CHARACTERS):
                offset = block + (GLYPH_INDEX + slot) * 64
                if any(original[offset:offset + 64]):
                    raise ValueError(f"Expected unused tile at 0x{offset:X}")
                tile = render_tile(glyphs[ch], foreground, black if args.shadow else None)
                data[offset:offset + 64] = tile
                records.append({"tileset": name, "style": style, "character": ch,
                                "tile_index": GLYPH_INDEX + slot,
                                "offset": f"0x{offset:X}", "foreground": foreground,
                                "shadow": black if args.shadow else None})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    write_ips(original, bytes(data), args.output.with_suffix(".ips"))
    result = {"font": "Fusion Pixel 8px Mono zh_Hans", "version": "2026.09.25",
              "license": "OFL-1.1", "shadow": args.shadow,
              "shadow_offset": [1, 1] if args.shadow else None,
              "ink_y_shift": -1 if args.shadow else 0, "input_sha256": ORIGINAL_SHA256,
              "font_sha256": hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),
              "output_sha256": hashlib.sha256(data).hexdigest(),
              "changed_bytes": sum(a != b for a, b in zip(original, data)),
              "glyphs": records}
    args.output.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if args.preview:
        # Decode the written Akoi Meexx shadow tiles, not the source font or an
        # antialiased approximation. It is the default tileset/font in POWDER.
        fields = struct.unpack_from("<13I", data, TILESET_TABLE + 4 * 52)
        block = fields[2] - 0x08000000
        palette = struct.unpack_from("<256H", data, fields[8] - 0x08000000)
        canvas = Image.new("RGB", (24, 8), (160, 160, 160))
        for i in range(3):
            offset = block + (GLYPH_INDEX + i) * 64
            rgb = bytearray()
            for pixel in data[offset:offset + 64]:
                rgb.extend(bytes(((palette[pixel] >> shift) & 31) * 255 // 31
                                 for shift in (0, 5, 10)) if pixel else b"\xa0\xa0\xa0")
            tile = Image.frombytes("RGB", (8, 8), bytes(rgb))
            canvas.paste(tile, (i * 8, 0))
        args.preview.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(args.preview.with_name(args.preview.stem + "_native.png"))
        canvas.resize((240, 80), Image.Resampling.NEAREST).save(args.preview)
    print(f"Output: {args.output}\nSHA-256: {result['output_sha256']}")
    print(f"Patched {len(records)} glyph tiles in 6 tilesets / 5 styles")
    print(f"Changed bytes: {result['changed_bytes']}")


if __name__ == "__main__":
    main()
