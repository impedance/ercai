#!/usr/bin/env python3
"""Lightweight AICODE anchor validator used by lint-aicode.sh."""

from __future__ import annotations

import pathlib
import re
import shutil
import subprocess
import sys
from typing import Iterator, List, Tuple

ALLOWED_PREFIXES = {
    "AICODE-NOTE",
    "AICODE-TODO",
    "AICODE-CONTRACT",
    "AICODE-TRAP",
    "AICODE-LINK",
    "AICODE-ASK",
}

LINE_PATTERN = re.compile(r"(?P<path>[^:]+):(?P<line>\d+):(?P<text>.*)")
DATE_PATTERN = re.compile(r"\[\d{4}-\d{2}-\d{2}\]")
EXCLUDED_DIRS = {"docs", ".venv", "__pycache__", "repo-erc3-agents"}
EXCLUDED_SUFFIXES = {".md"}


def _yield_rg_matches() -> Iterator[Tuple[str, int, str]]:
    rg_path = shutil.which("rg")
    if not rg_path:
        return

    cmd = [
        rg_path,
        "--pcre2",
        "-n",
        "AICODE-",
        "--glob",
        "!docs/**",
        "--glob",
        "!*.md",
        "--glob",
        "!.venv/**",
        "--glob",
        "!__pycache__/**",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.stdout:
        for raw in proc.stdout.splitlines():
            match = LINE_PATTERN.match(raw)
            if match:
                yield match.group("path"), int(match.group("line")), match.group("text")


def _yield_manual_matches() -> Iterator[Tuple[str, int, str]]:
    root = pathlib.Path(__file__).resolve().parents[1]
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            if "AICODE-" in line:
                yield str(path.relative_to(root)), idx, line


def main() -> int:
    matches: List[Tuple[str, int, str]] = list(_yield_rg_matches())
    if not matches:
        matches = list(_yield_manual_matches())

    errors: List[str] = []
    for path, line, text in matches:
        for prefix in re.findall(r"(AICODE-[A-Z]+):", text):
            if prefix not in ALLOWED_PREFIXES:
                errors.append(f"{path}:{line}: unknown prefix '{prefix}'")
                continue
            if prefix in {"AICODE-CONTRACT", "AICODE-TRAP"} and not DATE_PATTERN.search(text):
                errors.append(f"{path}:{line}: '{prefix}' missing [YYYY-MM-DD] date")

    if errors:
        sys.stderr.write("AICODE lint failures:\n")
        for err in errors:
            sys.stderr.write(err + "\n")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
