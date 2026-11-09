"""Checks the markdown plugin's rumdl language-server client against the sample docs in tests/fixtures/rumdl-lsp.

Starts rumdl's language server through the same runner the script picks (rumdl, uvx, bunx, or npx), so it takes a few seconds,
and skips when none of them can run rumdl. Run: python3 -m unittest discover -s tests
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/markdown/skills/rumdl-language-server/scripts/rumdl_lsp.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rumdl-lsp"
DEPLOY = "docs/deploy.md"


def rumdl_available() -> bool:
    spec = importlib.util.spec_from_file_location("rumdl_lsp", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        cmd = module.rumdl_command()
        return subprocess.run(cmd + ["--version"], capture_output=True, timeout=120).returncode == 0
    except (module.LspError, OSError, subprocess.TimeoutExpired):
        return False


RUMDL = rumdl_available()


def sample_repo(add_cleanup) -> Path:
    """A git repository holding a copy of the sample docs; `add_cleanup` is a test's addCleanup or addClassCleanup."""
    tmp = Path(tempfile.mkdtemp())
    add_cleanup(shutil.rmtree, tmp, ignore_errors=True)
    repo = tmp / "repo"
    shutil.copytree(FIXTURE, repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True, timeout=300)


@unittest.skipUnless(RUMDL, "no runner (rumdl, uvx, bunx, npx) can start rumdl")
class RenameApply(unittest.TestCase):
    """Renaming the first of two "Setup" headings, with --apply."""

    @classmethod
    def setUpClass(cls):
        cls.repo = sample_repo(cls.addClassCleanup)
        cls.result = run(cls.repo, "rename", f"{DEPLOY}:3", "Registry Setup", "--apply")
        cls.check = cls.result.stdout.split("\nApplied", 1)[-1].split("\n", 1)[-1]

    def read(self, rel: str) -> str:
        return (self.repo / rel).read_text(encoding="utf-8")

    def test_applies(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        self.assertIn("## Registry Setup", self.read(DEPLOY))

    def test_links_follow_each_heading(self):
        upgrade = self.read("docs/upgrade.md")
        self.assertIn("[deploy setup](deploy.md#registry-setup)", upgrade)
        self.assertIn("[post-rollout checks](deploy.md#setup)", upgrade)  # #setup-1 shifted to #setup
        self.assertIn("[checks]: ./deploy.md#setup\n", upgrade)  # reference definitions are followed too
        self.assertIn("(docs/deploy.md#registry-setup)", self.read("README.md"))
        self.assertIn("[first setup](#registry-setup)", self.read(DEPLOY))

    def test_leaves_code_and_other_files_anchors_alone(self):
        self.assertIn("`[text](deploy.md#setup)`", self.read("docs/upgrade.md"))
        self.assertIn("(credentials.md#setup)", self.read("docs/cli.md"))
        self.assertIn("docs/deploy.md#setup", self.read("mkdocs.yml"))  # reported, not edited

    def test_check_opens_with_its_totals(self):
        # An agent that reads only part of the check can still see what the whole of it found.
        first = self.check.splitlines()[0]
        self.assertIn(f"6 Markdown link(s) to {DEPLOY}", first)
        self.assertIn("0 to a missing anchor", first)
        self.assertIn("2 line(s) outside Markdown", first)

    def test_check_lists_links_by_the_heading_they_reach(self):
        self.assertIn(f"{DEPLOY}#registry-setup: 3 link(s)", self.check)
        self.assertIn(f"{DEPLOY}#setup: 2 link(s)", self.check)
        self.assertIn(f"{DEPLOY}: 1 link(s) to the file itself", self.check)
        self.assertIn("docs/upgrade.md:7:", self.check)
        self.assertNotIn("docs/cli.md", self.check)

    def test_check_finds_no_missing_anchor(self):
        self.assertIn(f"No Markdown link points at a missing anchor in {DEPLOY}", self.check)

    def test_check_lists_non_markdown_files_naming_the_old_anchors(self):
        self.assertIn("mkdocs.yml:3:", self.check)
        self.assertIn("src/app.py:1:", self.check)


@unittest.skipUnless(RUMDL, "no runner (rumdl, uvx, bunx, npx) can start rumdl")
class RenameEdgeCases(unittest.TestCase):
    def test_preview_writes_nothing_and_has_no_check(self):
        repo = sample_repo(self.addCleanup)
        result = run(repo, "rename", f"{DEPLOY}:3", "Registry Setup")
        self.assertIn("Would apply", result.stdout)
        self.assertNotIn("Check", result.stdout)
        self.assertIn("## Setup\n\nConfigure", (repo / DEPLOY).read_text(encoding="utf-8"))

    def test_check_reports_a_link_to_a_missing_anchor(self):
        repo = sample_repo(self.addCleanup)
        with (repo / "docs/cli.md").open("a", encoding="utf-8") as f:
            f.write("\nSee [gone](deploy.md#no-such-section).\n")
        out = run(repo, "rename", f"{DEPLOY}:3", "Registry Setup", "--apply").stdout
        check = out.split("\nApplied", 1)[-1]
        self.assertIn("1 to a missing anchor", check.splitlines()[1])
        self.assertIn("docs/cli.md:5:", check.split("missing anchor", 2)[-1])
        self.assertIn("#no-such-section", check)


if __name__ == "__main__":
    unittest.main()
