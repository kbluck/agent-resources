"""Tests for check_branch.py. Run: python3 -m unittest discover -s plugins/git/skills/branch/scripts"""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_branch  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check_branch.py")

# Conformance fixtures from the Conventional Branch 1.1.0 repository (tests/fixtures.json).
FIXTURES = [
    ("main", True),
    ("master", True),
    ("develop", True),
    ("feature/add-login-page", True),
    ("feat/add-login-page", True),
    ("bugfix/fix-header-bug", True),
    ("fix/header-bug", True),
    ("hotfix/security-patch", True),
    ("release/v1.2.0", True),
    ("chore/upgrade-node-v20.11", True),
    ("chore/update-dependencies", True),
    ("feature/issue-123-new-login", True),
    ("chore/123", True),
    ("feature/a", True),
    ("ai/refactor-auth-flow", True),
    ("claude/security-patch", True),
    ("codex/optimize-query", True),
    ("copilot/add-login-page", True),
    ("cursor/fix-header-bug", True),
    ("Feature/Add-Login", False),
    ("Main", False),
    ("feature/new--login", False),
    ("feature/-new-login", False),
    ("feature/new-login-", False),
    ("feature/new..login", False),
    ("feature/.new", False),
    ("feature/new.", False),
    ("release/v1.-2.0", False),
    ("fix/header bug", False),
    ("fix/header_bug", False),
    ("unknown/some-task", False),
    ("feature", False),
    ("feature/", False),
    ("/add-login", False),
    ("feature/a/b", False),
]


class ConformanceTest(unittest.TestCase):
    def test_fixtures(self):
        for branch, valid in FIXTURES:
            with self.subTest(branch=branch):
                self.assertEqual(check_branch.is_valid(branch), valid)

    def test_every_invalid_fixture_has_a_reason(self):
        for branch, valid in FIXTURES:
            if not valid:
                with self.subTest(branch=branch):
                    self.assertTrue(check_branch.problems(branch))

    def test_valid_names_have_no_reasons(self):
        for branch, valid in FIXTURES:
            if valid:
                with self.subTest(branch=branch):
                    self.assertEqual(check_branch.problems(branch), [])


class ReasonTest(unittest.TestCase):
    def assertReason(self, branch, fragment, **kwargs):
        reasons = check_branch.problems(branch, **kwargs)
        self.assertTrue(
            any(fragment in r for r in reasons),
            f"{branch!r}: expected a reason containing {fragment!r}, got {reasons!r}",
        )

    def test_reasons_name_the_actual_problem(self):
        self.assertReason("Feature/Add-Login", "uppercase")
        self.assertReason("Main", "lowercase")
        self.assertReason("feature/new--login", "consecutive")
        self.assertReason("feature/new..login", "consecutive")
        self.assertReason("release/v1.-2.0", "next to a dot")
        self.assertReason("feature/-new-login", "start or end")
        self.assertReason("feature/new.", "start or end")
        self.assertReason("fix/header bug", "' '")
        self.assertReason("fix/header_bug", "'_'")
        self.assertReason("unknown/some-task", "unknown type")
        self.assertReason("feature", "no description")
        self.assertReason("feature/", "empty description")
        self.assertReason("/add-login", "missing type")
        self.assertReason("feature/a/b", "'/'")
        self.assertReason("add-login", "missing")

    def test_unknown_type_reason_lists_allowed_types(self):
        self.assertReason("docs/readme", "feature")


class ExtensionTest(unittest.TestCase):
    def test_team_types_are_accepted_only_when_allowed(self):
        self.assertFalse(check_branch.is_valid("docs/update-readme"))
        self.assertTrue(check_branch.is_valid("docs/update-readme", extra_types=["docs"]))
        self.assertEqual(check_branch.problems("docs/update-readme", extra_types=["docs"]), [])

    def test_team_trunk_names_are_accepted_only_when_allowed(self):
        self.assertFalse(check_branch.is_valid("staging"))
        self.assertTrue(check_branch.is_valid("staging", extra_names=["staging"]))

    def test_extensions_do_not_relax_description_rules(self):
        self.assertFalse(check_branch.is_valid("docs/Update_README", extra_types=["docs"]))


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, SCRIPT, *args], capture_output=True, text=True, check=False
        )

    def test_all_valid_exits_zero(self):
        result = self.run_cli("feature/add-login-page", "release/v1.2.0")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("ok", result.stdout)

    def test_any_invalid_exits_one_and_explains(self):
        result = self.run_cli("feature/add-login-page", "fix/header_bug")
        self.assertEqual(result.returncode, 1)
        self.assertIn("fix/header_bug", result.stdout)
        self.assertIn("'_'", result.stdout)

    def test_allow_type_option(self):
        result = self.run_cli("--allow-type", "docs", "docs/update-readme")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_checks_current_branch_when_no_name_given(self):
        import tempfile

        with tempfile.TemporaryDirectory() as repo:
            subprocess.run(["git", "init", "-q", "-b", "Bad_Name", repo], check=True)
            result = subprocess.run(
                [sys.executable, SCRIPT], cwd=repo, capture_output=True, text=True, check=False
            )
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Bad_Name", result.stdout)


if __name__ == "__main__":
    unittest.main()
