#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""List coverage gaps from a Coverage.py JSON report, grouped by file and function, worst first.

Usage:
    coverage json -q -o - | python uncovered.py -
    python uncovered.py coverage.json --limit 10

Each gap shows the line number (or a range, or a branch as FROM->TO, with "exit" for leaving the function) and the source text,
so you can decide what test, if any, it needs. Branches whose destination is itself a missing line are folded into that line,
as in `coverage report -m`. Paths are resolved relative to the current directory, which should be where coverage ran.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def ranges(lines: list[int]) -> list[tuple[int, int]]:
    """Collapse sorted line numbers into inclusive (start, end) runs."""
    out: list[tuple[int, int]] = []
    for n in sorted(lines):
        if out and n == out[-1][1] + 1:
            out[-1] = (out[-1][0], n)
        else:
            out.append((n, n))
    return out


def source_lines(path: str) -> list[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def owner_map(file_data: dict) -> dict[int, str]:
    """Map line numbers to the function that contains them, when the report includes functions (Coverage.py 7.5+)."""
    owners: dict[int, str] = {}
    for name, fn in file_data.get("functions", {}).items():
        if not name:
            continue
        for n in fn.get("missing_lines", []) + fn.get("executed_lines", []) + fn.get("excluded_lines", []):
            owners[n] = name
        for a, _ in fn.get("missing_branches", []):
            owners.setdefault(a, name)
    return owners


def gaps(file_data: dict) -> list[tuple[int, str]]:
    """Return (sort_line, label) for each missing range and each partial branch."""
    missing = set(file_data.get("missing_lines", []))
    items = [(start, f"{start}" if start == end else f"{start}-{end}") for start, end in ranges(list(missing))]
    for a, b in file_data.get("missing_branches", []):
        if b in missing:
            continue
        items.append((a, f"{a}->{'exit' if b < 0 else b}"))
    return sorted(items)


def describe(path: str, file_data: dict, max_items: int) -> list[str]:
    summary = file_data["summary"]
    text = source_lines(path)
    owners = owner_map(file_data)
    items = gaps(file_data)
    lines = [
        (
            f"{path}  {summary['percent_covered_display']}%  "
            f"({summary['missing_lines']} lines, {summary.get('missing_branches', 0)} branches missing)"
        )
    ]
    current_owner = None
    for shown, (line_no, label) in enumerate(items):
        if shown == max_items:
            lines.append(f"    ... {len(items) - max_items} more")
            break
        owner = owners.get(line_no, "<module>")
        if owner != current_owner:
            lines.append(f"  {owner}")
            current_owner = owner
        code = text[line_no - 1].strip() if 0 < line_no <= len(text) else ""
        if len(code) > 90:
            code = code[:87] + "..."
        lines.append(f"    {label:<10} {code}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", nargs="?", default="coverage.json", help="JSON report path, or - for stdin")
    parser.add_argument("--limit", type=int, default=15, help="files to show (default 15)")
    parser.add_argument("--max-items", type=int, default=40, help="gaps to show per file (default 40)")
    args = parser.parse_args(argv)

    try:
        raw = sys.stdin.read() if args.report == "-" else Path(args.report).read_text(encoding="utf-8")
        # raw_decode tolerates the "Coverage failure: ..." line that fail_under appends after JSON written to stdout.
        data, _ = json.JSONDecoder().raw_decode(raw.lstrip())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read a Coverage.py JSON report from {args.report}: {exc}", file=sys.stderr)
        print("Run the tests under coverage, then: coverage json -q -o - | python uncovered.py -", file=sys.stderr)
        return 2

    totals = data["totals"]
    branch = data.get("meta", {}).get("branch_coverage", False)
    files = {p: f for p, f in data["files"].items() if f.get("missing_lines") or f.get("missing_branches")}
    ranked = sorted(files.items(), key=lambda kv: -(len(kv[1].get("missing_lines", [])) + len(kv[1].get("missing_branches", []))))

    header = f"Total {totals['percent_covered_display']}%"
    if branch:
        header += (
            f" (statements {totals.get('percent_statements_covered_display', '?')}%,"
            f" branches {totals.get('percent_branches_covered_display', '?')}%)"
        )
    header += f": {totals['missing_lines']} missing lines"
    if branch:
        header += f", {totals.get('missing_branches', 0)} missing branches"
    header += f" in {len(files)} file{'s' if len(files) != 1 else ''}"
    print(header)
    if not branch:
        print("Branch coverage is off; set branch = true under [tool.coverage.run] to see untaken branches.")

    for path, file_data in ranked[: args.limit]:
        print()
        print("\n".join(describe(path, file_data, args.max_items)))
    if len(ranked) > args.limit:
        print(f"\n... {len(ranked) - args.limit} more files with gaps (use --limit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
