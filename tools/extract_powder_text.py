#!/usr/bin/env python3
"""Extract POWDER's source literals and the ROM's printable text region.

This is an inventory tool, not a translator: it preserves byte offsets and
flags strings containing POWDER's grammar placeholders for later review.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROM_START = 0x1FF000
ROM_END = 0x229800
PRINTABLE = set(range(0x20, 0x7F)) | {0x09}
PLACEHOLDER_RE = re.compile(r"%(?:[A-Za-z]|[0-9])|<[A-Za-z][^>]*>")


def extract_rom_strings(data: bytes, start: int, end: int):
    rows = []
    pos = start
    while pos < end:
        nul = data.find(b"\0", pos, end)
        if nul < 0:
            break
        raw = data[pos:nul]
        if len(raw) >= 4 and all(c in PRINTABLE for c in raw):
            text = raw.decode("ascii")
            rows.append(
                {
                    "offset": f"0x{pos:06X}",
                    "length": len(raw),
                    "text": text,
                    "placeholders": PLACEHOLDER_RE.findall(text),
                }
            )
        pos = nul + 1
    return rows


def extract_source_literals(root: Path):
    # C/C++ literals are useful as a second inventory, but comments and macro
    # arguments still need human review. Keep file and line for traceability.
    rx = re.compile(r'"((?:\\.|[^"\\])*)"')
    rows = []
    for path in sorted(root.rglob("*.cpp")) + sorted(root.rglob("*.h")):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for match in rx.finditer(line):
                raw = match.group(1)
                if len(raw) < 2:
                    continue
                value = bytes(raw, "utf-8").decode("unicode_escape")
                if not any(c.isalpha() for c in value):
                    continue
                rows.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "text": value,
                        "placeholders": PLACEHOLDER_RE.findall(value),
                    }
                )
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("--source", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    data = args.rom.read_bytes()
    rom_rows = extract_rom_strings(data, ROM_START, min(ROM_END, len(data)))
    source_rows = extract_source_literals(args.source) if args.source else []
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "rom_strings.json").write_text(
        json.dumps(rom_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "source_literals.json").write_text(
        json.dumps(source_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (args.out / "rom_strings.tsv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["offset", "length", "placeholders", "text"], delimiter="\t")
        w.writeheader()
        for row in rom_rows:
            row = dict(row)
            row["placeholders"] = ",".join(row["placeholders"])
            w.writerow(row)
    print(f"ROM strings: {len(rom_rows)}")
    print(f"Source literals: {len(source_rows)}")
    print(f"ROM range: 0x{ROM_START:06X}..0x{ROM_END:06X}")


if __name__ == "__main__":
    main()
