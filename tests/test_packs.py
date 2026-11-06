"""Checks packs.json and the skill pack site that scripts/build_packs.py builds from it."""

import hashlib
import importlib.util
import json
import re
import tarfile
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")  # what the skills CLI accepts in a discovery index
BASE = "https://example.test/agent-resources/"

spec = importlib.util.spec_from_file_location("build_packs", ROOT / "scripts" / "build_packs.py")
build_packs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_packs)


def skill_md(name: str, description: str = "Does a thing. Use it when testing.") -> str:
    return f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n# {name}\n"


def make_repo(root: Path, skills: dict[str, str], packs: dict) -> Path:
    """A minimal repository: plugin skills under plugins/p/skills, standalone skills under skills/."""
    for i, (name, text) in enumerate(skills.items()):
        folder = root / "plugins" / "p" / "skills" / name if i % 2 == 0 else root / "skills" / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(text, encoding="utf-8")
    (root / "packs.json").write_text(json.dumps(packs), encoding="utf-8")
    return root


def source_files(skill_dir: Path) -> set[str]:
    return {
        p.relative_to(skill_dir).as_posix()
        for p in skill_dir.rglob("*")
        if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in p.relative_to(skill_dir).parts)
    }


class PacksFileTests(unittest.TestCase):
    def setUp(self):
        self.packs = json.loads((ROOT / "packs.json").read_text(encoding="utf-8"))
        self.skills = build_packs.find_skills(ROOT)

    def test_find_skills_finds_every_plugin_and_standalone_skill(self):
        folders = {p.parent.name for p in [*ROOT.glob("plugins/*/skills/*/SKILL.md"), *ROOT.glob("skills/*/SKILL.md")]}
        self.assertEqual(set(self.skills), folders)

    def test_packs_have_valid_names_and_at_least_one_skill(self):
        self.assertTrue(self.packs, "packs.json defines no packs")
        for pack, names in self.packs.items():
            with self.subTest(pack=pack):
                self.assertRegex(pack, NAME)
                self.assertIsInstance(names, list)
                self.assertTrue(names, "empty pack")

    def test_readme_table_matches_packs_json(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        section = readme.split("### Skill Packs", 1)[1].split("\n#", 1)[0]
        rows = re.findall(r"^\| `([a-z0-9-]+)` \| (.+?) \|$", section, re.MULTILINE)
        self.assertEqual({pack: re.findall(r"`([a-z0-9-]+)`", skills) for pack, skills in rows}, self.packs)

    def test_every_pack_skill_exists_and_appears_once(self):
        for pack, names in self.packs.items():
            with self.subTest(pack=pack):
                self.assertEqual(sorted(set(names) - set(self.skills)), [], "unknown skills")
                self.assertEqual(len(names), len(set(names)), "a skill is listed twice")


class FrontmatterTests(unittest.TestCase):
    def test_folded_description_is_joined_into_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("---\nname: demo\ndescription: >\n  First line,\n  second line.\nlicense: MIT\n---\nBody\n")
            self.assertEqual(
                build_packs.frontmatter(path), {"name": "demo", "description": "First line, second line.", "license": "MIT"}
            )

    def test_plain_and_quoted_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text("---\nname: 'demo'\ndescription: \"Says: hello\"\n---\n")
            self.assertEqual(build_packs.frontmatter(path), {"name": "demo", "description": "Says: hello"})


class BuildErrorTests(unittest.TestCase):
    def build(self, skills: dict[str, str], packs: dict) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "repo", skills, packs)
            build_packs.build(repo, Path(tmp) / "site")

    def test_unknown_skill_in_a_pack_fails(self):
        with self.assertRaisesRegex(ValueError, "nope"):
            self.build({"one": skill_md("one")}, {"demo": ["one", "nope"]})

    def test_duplicate_skill_names_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.build({"one": skill_md("one"), "two": skill_md("one")}, {"demo": ["one"]})

    def test_missing_description_fails(self):
        with self.assertRaisesRegex(ValueError, "one"):
            self.build({"one": "---\nname: one\n---\n"}, {"demo": ["one"]})

    def test_invalid_pack_name_fails(self):
        with self.assertRaisesRegex(ValueError, "Bad_Name"):
            self.build({"one": skill_md("one")}, {"Bad_Name": ["one"]})


class DescriptionTests(unittest.TestCase):
    def test_long_description_is_shortened_to_fit_the_index(self):
        # The CLI silently drops index entries over 1024 characters. Installs read SKILL.md, so only the listing is shortened.
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_repo(Path(tmp) / "repo", {"one": skill_md("one", "word " * 300)}, {"demo": ["one"]})
            build_packs.build(repo, Path(tmp) / "site")
            index = json.loads((Path(tmp) / "site/packs/demo/.well-known/agent-skills/index.json").read_text())
            description = index["skills"][0]["description"]
            self.assertLessEqual(len(description), 1024)
            self.assertGreater(len(description), 1000)
            self.assertTrue(description.endswith(" word…"), description[-20:])  # cut between words

    def test_short_description_is_unchanged(self):
        self.assertEqual(build_packs.index_description("Short. Use it now."), "Short. Use it now.")


class BuiltSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.site = Path(cls.tmp.name) / "site"
        build_packs.build(ROOT, cls.site)
        cls.packs = json.loads((ROOT / "packs.json").read_text(encoding="utf-8"))
        cls.skills = build_packs.find_skills(ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def index(self, rel: str) -> dict:
        return json.loads((self.site / rel / ".well-known/agent-skills/index.json").read_text(encoding="utf-8"))

    def check_entries(self, rel: str, expected: list[str]) -> None:
        index = self.index(rel)
        self.assertEqual(index["$schema"], SCHEMA)
        self.assertEqual([e["name"] for e in index["skills"]], expected)
        index_url = urljoin(BASE, f"{rel}/.well-known/agent-skills/index.json".lstrip("/"))
        for entry in index["skills"]:
            with self.subTest(index=rel or "/", skill=entry["name"]):
                self.assertEqual(entry["type"], "archive")
                self.assertTrue(0 < len(entry["description"]) <= 1024)
                url = urljoin(index_url, entry["url"])
                self.assertTrue(url.startswith(BASE), f"{entry['url']} escapes the site: {url}")
                archive = self.site / urlparse(url).path.removeprefix(urlparse(BASE).path)
                self.assertTrue(archive.is_file(), f"{entry['url']} resolves to a missing file")
                self.assertEqual(entry["digest"], "sha256:" + hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_each_pack_index_lists_its_skills_in_order(self):
        for pack, names in self.packs.items():
            self.check_entries(f"packs/{pack}", names)

    def test_root_index_lists_every_skill(self):
        self.check_entries("", sorted(self.skills))

    def test_archives_hold_the_skill_folder_with_skill_md_at_the_root(self):
        for name, folder in self.skills.items():
            with self.subTest(skill=name), tarfile.open(self.site / "skills" / f"{name}.tar.gz") as tar:
                members = tar.getmembers()
                self.assertTrue(all(m.isfile() for m in members), "the CLI rejects links and needs no directory entries")
                self.assertEqual({m.name for m in members}, source_files(folder))
                self.assertIn("SKILL.md", {m.name for m in members})
                for member in members:
                    self.assertEqual(tar.extractfile(member).read(), (folder / member.name).read_bytes())

    def test_rebuilding_produces_identical_bytes(self):
        # Changed bytes mean a changed digest, which every installed copy would report as an update.
        with tempfile.TemporaryDirectory() as tmp:
            again = Path(tmp) / "site"
            build_packs.build(ROOT, again)
            first = {p.relative_to(self.site): p.read_bytes() for p in self.site.rglob("*") if p.is_file()}
            second = {p.relative_to(again): p.read_bytes() for p in again.rglob("*") if p.is_file()}
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
