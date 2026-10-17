#!/usr/bin/env python3
"""Check that translated rows preserve POWDER's formatting tokens."""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

TOKEN = re.compile(r"%(?:[A-Za-z]|[0-9])|<[A-Za-z][^>]*>")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table", type=Path)
    args = ap.parse_args()
    errors = 0
    with args.table.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row.get("status") in {"skip", "planned"}:
                # planned rows are still checked; status only documents whether
                # the bytes have been put into a build yet.
                pass
            old, new = tokens(row["english"]), tokens(row["chinese"])
            if old != new:
                errors += 1
                print(f"TOKEN MISMATCH {row['id']}: {old!r} -> {new!r}")
    if errors:
        raise SystemExit(1)
    print("translation token checks: OK")


if __name__ == "__main__":
    main()
