#!/usr/bin/env python3
"""Apply safe in-place ASCII replacements to a POWDER ROM copy.

This intentionally rejects non-ASCII data. It is the staging tool for proving
pointer/terminator handling before the custom Chinese encoding is added.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--replace", action="append", default=[], metavar="OLD=NEW")
    args = ap.parse_args()
    data = bytearray(args.input.read_bytes())
    before = hashlib.sha256(data).hexdigest()
    for spec in args.replace:
        if "=" not in spec:
            raise SystemExit(f"bad replacement: {spec!r}")
        old, new = spec.split("=", 1)
        old_b, new_b = old.encode("ascii"), new.encode("ascii")
        if not old_b or len(new_b) > len(old_b):
            raise SystemExit(f"replacement must be non-empty and no longer than OLD: {spec!r}")
        count = data.count(old_b)
        if count != 1:
            raise SystemExit(f"expected exactly one OLD occurrence, found {count}: {old!r}")
        at = data.index(old_b)
        data[at:at + len(old_b)] = new_b + b"\0" * (len(old_b) - len(new_b))
        print(f"patched 0x{at:06X}: {old!r} -> {new!r}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"input sha256:  {before}")
    print(f"output sha256: {hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
