#!/usr/bin/env python3
"""Check branch names against Conventional Branch 1.1.0 and explain any failure.

Usage:
    check_branch.py [--allow-type TYPE]... [--allow-name NAME]... [NAME]...

With no NAME, checks the current branch. Exits 0 when every name conforms, 1 when any does not, 2 on a usage or Git error.
--allow-type and --allow-name add a repository's own types (docs) or unprefixed long-lived branches (staging) on top of the
specification's.
"""

import argparse
import re
import subprocess
import sys

TRUNK_NAMES = ["main", "master", "develop"]
TYPES = [
    "feature", "feat", "bugfix", "fix", "hotfix", "release", "chore", "ai", "copilot", "cursor", "claude", "codex",
]
DESCRIPTION = r"[a-z0-9]+(?:\.[a-z0-9]+)*(?:-[a-z0-9]+(?:\.[a-z0-9]+)*)*"


def _pattern(extra_types=(), extra_names=()):
    names = "|".join(map(re.escape, [*TRUNK_NAMES, *extra_names]))
    types = "|".join(map(re.escape, [*TYPES, *extra_types]))
    return re.compile(rf"^(?:{names}|(?:{types})/{DESCRIPTION})$")


def is_valid(branch, extra_types=(), extra_names=()):
    return _pattern(extra_types, extra_names).fullmatch(branch) is not None


def problems(branch, extra_types=(), extra_names=()):
    """Return human-readable reasons the branch does not conform (empty if it does)."""
    if is_valid(branch, extra_types, extra_names):
        return []

    names = [*TRUNK_NAMES, *extra_names]
    types = [*TYPES, *extra_types]
    if branch.lower() in names:
        return [f"trunk branch names must be lowercase: use '{branch.lower()}'"]
    if "/" not in branch:
        if branch.lower() in types:
            return [f"'{branch}' is a type with no description: use '{branch.lower()}/<description>'"]
        return ["missing '<type>/' prefix"]

    kind, description = branch.split("/", 1)
    reasons = []
    if not kind:
        reasons.append("missing type before '/'")
    elif kind not in types:
        if kind.lower() in types:
            reasons.append(f"type must be lowercase: use '{kind.lower()}/'")
        else:
            reasons.append(f"unknown type '{kind}/': use one of {', '.join(t + '/' for t in types)}")

    if not description:
        reasons.append("empty description after '/'")
        return reasons
    if "/" in description:
        reasons.append("description must not contain '/': join the parts with '-'")
    if description != description.lower():
        reasons.append("uppercase letters are not allowed")
    bad = sorted({c for c in description.lower() if not re.match(r"[a-z0-9./-]", c)})
    if bad:
        reasons.append("characters not allowed: " + ", ".join(repr(c) for c in bad))
    if re.search(r"--|\.\.", description):
        reasons.append("consecutive '-' or '.' are not allowed")
    if re.search(r"-\.|\.-", description):
        reasons.append("'-' must not be next to a dot")
    if re.match(r"[-.]", description) or re.search(r"[-.]$", description):
        reasons.append("description must not start or end with '-' or '.'")
    return reasons or ["does not match the Conventional Branch grammar"]


def current_branch():
    result = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True, check=False
    )
    name = result.stdout.strip()
    if result.returncode != 0 or not name:
        sys.exit("check_branch: no branch name given and no current branch (detached HEAD or not a Git repository)")
    return name


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("names", nargs="*", metavar="NAME")
    parser.add_argument("--allow-type", action="append", default=[], metavar="TYPE")
    parser.add_argument("--allow-name", action="append", default=[], metavar="NAME")
    args = parser.parse_args(argv)

    failed = False
    for name in args.names or [current_branch()]:
        reasons = problems(name, args.allow_type, args.allow_name)
        if reasons:
            failed = True
            print(f"invalid  {name}: " + "; ".join(reasons))
        else:
            print(f"ok       {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
