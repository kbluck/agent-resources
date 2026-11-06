"""Build the static skill pack site from packs.json. Run: python3 scripts/build_packs.py [out-dir]

The site follows the Agent Skills discovery index (v0.2.0) that the `skills` CLI reads, so a pack installs with
`bunx skills add https://<site>/packs/<pack>`. Each skill is archived once; every pack that lists it points at the same archive.

  skills/<skill>.tar.gz                              one archive per skill
  packs/<pack>/.well-known/agent-skills/index.json   one index per pack
  .well-known/agent-skills/index.json                every skill
"""

import gzip
import hashlib
import io
import json
import re
import shutil
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
INDEX = Path(".well-known/agent-skills")
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_DESCRIPTION = 1024  # the CLI silently drops index entries with longer descriptions


def frontmatter(skill_md: Path) -> dict[str, str]:
    """Top-level scalar fields of a SKILL.md frontmatter. Folded (>) and literal (|) blocks are joined into one line."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---", skill_md.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        raise ValueError(f"{skill_md}: no frontmatter")
    fields: dict[str, str] = {}
    block = None
    for line in match.group(1).splitlines():
        if line[:1] in (" ", "\t"):
            if block:
                fields[block] = f"{fields[block]} {line.strip()}".strip()
            continue
        key, sep, value = line.partition(":")
        if not sep:
            block = None
            continue
        key, value = key.strip(), value.strip()
        block = key if value[:1] in (">", "|") else None
        fields[key] = "" if block else value.strip("'\"")
    return fields


def find_skills(root: Path) -> dict[str, Path]:
    """Every plugin and standalone skill, by frontmatter name."""
    skills: dict[str, Path] = {}
    for skill_md in sorted([*root.glob("plugins/*/skills/*/SKILL.md"), *root.glob("skills/*/SKILL.md")]):
        name = frontmatter(skill_md).get("name", "")
        if name in skills:
            raise ValueError(f"duplicate skill name {name!r}: {skills[name]} and {skill_md.parent}")
        skills[name] = skill_md.parent
    return skills


def archive(skill_dir: Path) -> bytes:
    """A tar.gz of the skill folder with SKILL.md at its root. The same files always give the same bytes, and so the same
    digest, on any OS: the CLI reports a changed digest as an update."""
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w", format=tarfile.USTAR_FORMAT) as tar:
        for path in sorted(skill_dir.rglob("*")):
            parts = path.relative_to(skill_dir).parts
            if not path.is_file() or any(part.startswith(".") or part == "__pycache__" for part in parts):
                continue
            data = path.read_bytes()
            info = tarfile.TarInfo("/".join(parts))
            info.size, info.mode, info.mtime = len(data), 0o644, 0  # the CLI ignores modes when it extracts
            tar.addfile(info, io.BytesIO(data))
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as gz:
        gz.write(tar_bytes.getvalue())
    return out.getvalue()


def index_description(description: str) -> str:
    """The description, cut between words to fit the index. Only listings show it; installs read SKILL.md."""
    if len(description) <= MAX_DESCRIPTION:
        return description
    return description[: MAX_DESCRIPTION - 1].rsplit(" ", 1)[0] + "…"


def write_index(folder: Path, entries: list[dict], prefix: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    # Relative URLs keep the site independent of its host and base path.
    skills = [{**entry, "url": f"{prefix}skills/{entry['name']}.tar.gz"} for entry in entries]
    (folder / "index.json").write_text(json.dumps({"$schema": SCHEMA, "skills": skills}, indent=2) + "\n", encoding="utf-8")


def build(root: Path, out: Path) -> None:
    skills = find_skills(root)
    packs: dict[str, list[str]] = json.loads((root / "packs.json").read_text(encoding="utf-8"))
    for pack, names in packs.items():
        if not NAME.match(pack):
            raise ValueError(f"pack name {pack!r} must be lowercase words joined by hyphens")
        if unknown := [name for name in names if name not in skills]:
            raise ValueError(f"pack {pack!r} lists unknown skills: {', '.join(unknown)}")

    entries: dict[str, dict] = {}
    archives: dict[str, bytes] = {}
    for name in sorted(skills):
        description = frontmatter(skills[name] / "SKILL.md").get("description", "")
        if not NAME.match(name) or not description:
            raise ValueError(f"{name}: needs a lowercase hyphenated name and a description")
        archives[name] = archive(skills[name])
        digest = "sha256:" + hashlib.sha256(archives[name]).hexdigest()
        entries[name] = {"name": name, "description": index_description(description), "type": "archive", "digest": digest}

    shutil.rmtree(out, ignore_errors=True)
    (out / "skills").mkdir(parents=True)
    for name, data in archives.items():
        (out / "skills" / f"{name}.tar.gz").write_bytes(data)
    write_index(out / INDEX, list(entries.values()), "../../")
    for pack, names in packs.items():
        write_index(out / "packs" / pack / INDEX, [entries[name] for name in names], "../../../../")


if __name__ == "__main__":
    site = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "site"
    build(ROOT, site)
    print(f"Built {site}")
