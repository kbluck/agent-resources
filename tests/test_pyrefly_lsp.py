"""Checks the pyrefly plugin's language-server client against the sample project in tests/fixtures/pyrefly-lsp.

Starts `pyrefly lsp` through the same runner the script picks (the project's pyrefly, pyrefly on PATH, uvx, or pipx), so it takes a
few seconds per class, and skips when none of them can run pyrefly. Run: python3 -m unittest discover -s tests
"""

import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "plugins/pyrefly/skills/language-server/scripts/pyrefly_lsp.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "pyrefly-lsp"
MODELS = "shop/models.py"


def pyrefly_available() -> bool:
    if not SCRIPT.exists():
        return True  # let the tests fail rather than skip
    spec = importlib.util.spec_from_file_location("pyrefly_lsp", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        cmd = module.pyrefly_command(FIXTURE)
        return subprocess.run(cmd + ["--version"], capture_output=True, timeout=120).returncode == 0
    except (module.LspError, OSError, subprocess.TimeoutExpired):
        return False


PYREFLY = pyrefly_available()
needs_pyrefly = unittest.skipUnless(PYREFLY, "no runner (pyrefly, uvx, pipx) can start pyrefly")


def sample_repo(add_cleanup, keep_config: bool = True) -> Path:
    """A git repository holding a copy of the sample project; `add_cleanup` is a test's addCleanup or addClassCleanup."""
    tmp = Path(tempfile.mkdtemp())
    add_cleanup(shutil.rmtree, tmp, ignore_errors=True)
    repo = tmp / "repo"
    shutil.copytree(FIXTURE, repo)
    if not keep_config:
        (repo / "pyproject.toml").unlink()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


def run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=repo, capture_output=True, text=True, timeout=300)


def read(repo: Path, rel: str) -> str:
    return (repo / rel).read_text(encoding="utf-8")


@needs_pyrefly
class Queries(unittest.TestCase):
    """Read-only questions; the files the answers come from are never opened, so they prove the script waits for the index."""

    @classmethod
    def setUpClass(cls):
        cls.repo = sample_repo(cls.addClassCleanup)

    def ask(self, *args: str) -> subprocess.CompletedProcess:
        result = run(self.repo, *args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_references_follow_the_type_not_the_name(self):
        out = self.ask("references", f"{MODELS}:11:greeting").stdout
        self.assertIn("shop/service.py:5:", out)
        self.assertIn("shop/report.py:17:", out)
        self.assertIn(f"{MODELS}:16:", out)  # the override in VipCustomer
        self.assertNotIn("shop/report.py:10:", out)  # Report.greeting is another method with the same name

    def test_references_by_column(self):
        out = self.ask("references", f"{MODELS}:20:5").stdout
        self.assertIn("shop/service.py:1:", out)
        self.assertIn("tests/test_models.py:3:", out)

    def test_a_def_line_needs_no_column(self):
        out = self.ask("references", f"{MODELS}:20").stdout
        self.assertIn("shop/report.py:14:", out)

    def test_hover_shows_the_inferred_type(self):
        out = self.ask("hover", "shop/service.py:9:c").stdout
        self.assertIn("Customer", out)
        self.assertNotIn("file://", out)

    def test_definition(self):
        out = self.ask("definition", "shop/service.py:9:load_customer").stdout
        self.assertIn(f"{MODELS}:20:5:", out)

    def test_callers(self):
        out = self.ask("callers", "shop/service.py:4:welcome").stdout
        self.assertIn("main", out)
        self.assertIn("shop/service.py:10:", out)

    def test_callers_include_calls_through_an_import_alias(self):
        out = self.ask("callers", f"{MODELS}:20").stdout
        self.assertIn("shop/report.py:16:", out)  # lc("c") after `import load_customer as lc`
        self.assertIn("summary", out.split("shop/report.py:16:", 1)[1].splitlines()[0])

    def test_subtypes(self):
        out = self.ask("subtypes", f"{MODELS}:5:Customer").stdout
        self.assertIn("VipCustomer", out)

    def test_implementations(self):
        out = self.ask("implementations", f"{MODELS}:11:greeting").stdout
        self.assertIn(f"{MODELS}:16:", out)

    def test_symbols_stay_in_the_project(self):
        out = self.ask("symbols", "load_cust").stdout
        self.assertIn(f"{MODELS}:20:", out)
        self.assertNotIn(".pyi", out)
        self.assertNotIn("__loader__", out)

    def test_outline(self):
        out = self.ask("outline", MODELS).stdout
        for name in ("Customer", "greeting", "VipCustomer", "load_customer", "find_customer"):
            self.assertIn(name, out)

    def test_hints_show_inferred_return_types(self):
        out = self.ask("hints", MODELS).stdout
        self.assertIn(f"{MODELS}:20:", out)
        self.assertIn("Customer", out)

    def test_actions_are_listed_by_number(self):
        out = self.ask("actions", "shop/service.py:9:c").stdout
        self.assertIn("1. ", out)
        self.assertIn("Inline variable", out)

    def test_name_not_on_line_is_a_usage_error(self):
        result = run(self.repo, "references", f"{MODELS}:11:nonexistent")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nonexistent", result.stderr)


@needs_pyrefly
class Rename(unittest.TestCase):
    def test_preview_writes_nothing(self):
        repo = sample_repo(self.addCleanup)
        result = run(repo, "rename", f"{MODELS}:20", "fetch_customer")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("+def fetch_customer(name):", result.stdout)
        self.assertIn("def load_customer(name):", read(repo, MODELS))

    def test_apply_updates_every_import_style(self):
        repo = sample_repo(self.addCleanup)
        result = run(repo, "rename", f"{MODELS}:20", "fetch_customer", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = read(repo, "shop/report.py")
        self.assertIn("shop.models.fetch_customer(", report)
        self.assertIn("models.fetch_customer(", report)
        self.assertIn("from .models import fetch_customer as lc", report)
        self.assertIn('lc("c")', report)  # the alias stays
        self.assertIn("from shop.models import Customer, fetch_customer", read(repo, "shop/service.py"))
        self.assertIn("from shop.models import fetch_customer", read(repo, "tests/test_models.py"))

    def test_apply_lists_leftovers_the_server_does_not_rename(self):
        repo = sample_repo(self.addCleanup)
        out = run(repo, "rename", f"{MODELS}:20", "fetch_customer", "--apply").stdout
        leftovers = out.split("Still naming", 1)[-1]
        self.assertIn("tests/test_models.py:7:", leftovers)  # mock.patch("shop.models.load_customer")
        self.assertIn("README.md:3:", leftovers)
        self.assertIn('mock.patch("shop.models.load_customer")', read(repo, "tests/test_models.py"))

    def test_method_rename_skips_the_unrelated_class(self):
        repo = sample_repo(self.addCleanup)
        result = run(repo, "rename", f"{MODELS}:11:greeting", "salute", "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = read(repo, "shop/report.py")
        self.assertIn("a.salute(), b.salute(), c.salute(), Report().greeting()", report)
        self.assertIn("    def greeting(self) -> str:\n        return \"Quarterly report\"", report)
        self.assertIn("customer.salute()", read(repo, "shop/service.py"))

    def test_apply_reports_the_same_leftovers_as_the_preview(self):
        # Applying edits shifts text on the edited lines; leftovers on those lines must still be found.
        repo = sample_repo(self.addCleanup)
        out = run(repo, "rename", f"{MODELS}:11:greeting", "hey", "--apply").stdout
        self.assertIn("shop/report.py:17:", out.split("Still naming", 1)[-1])  # Report().greeting()

    def test_string_annotations_are_reported(self):
        repo = sample_repo(self.addCleanup)
        out = run(repo, "rename", f"{MODELS}:5:Customer", "Client", "--apply").stdout
        self.assertIn(f"{MODELS}:24:", out.split("Still naming", 1)[-1])  # -> "Customer | None"


@needs_pyrefly
class Move(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = sample_repo(cls.addClassCleanup)
        cls.result = run(cls.repo, "move", MODELS, "shop/entities.py", "--apply")

    def test_moves_the_file(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)
        self.assertTrue((self.repo / "shop/entities.py").is_file())
        self.assertFalse((self.repo / MODELS).exists())

    def test_rewrites_imports(self):
        self.assertIn("from shop.entities import Customer, load_customer", read(self.repo, "shop/service.py"))
        self.assertIn("from shop.entities import load_customer", read(self.repo, "tests/test_models.py"))
        self.assertIn("from .entities import load_customer as lc", read(self.repo, "shop/report.py"))

    def test_lists_leftovers(self):
        leftovers = self.result.stdout.split("Still naming", 1)[-1]
        self.assertIn("tests/test_models.py:7:", leftovers)  # the mock.patch target string
        self.assertIn("shop/report.py:14:", leftovers)  # shop.models.load_customer(...) after `import shop.models`
        self.assertIn("shop/report.py:2:", leftovers)  # from . import models
        self.assertIn("shop/legacy.py:1:", leftovers)  # from shop import models


@needs_pyrefly
class MoveToAnotherFolder(unittest.TestCase):
    def test_lists_the_moved_files_relative_imports(self):
        repo = sample_repo(self.addCleanup)
        (repo / "shop/sales").mkdir()
        (repo / "shop/sales/__init__.py").write_text("")
        (repo / "shop/service.py").write_text("from .models import Customer\n\n\ndef name(c: Customer) -> str:\n"
                                              "    return c.name\n")
        for flags in ([], ["--apply"]):
            with self.subTest(flags=flags):
                result = run(repo, "move", "shop/service.py", "shop/sales/service.py", *flags)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("service.py:1:1: from .models import Customer", result.stdout.split("Relative imports", 1)[-1])
        self.assertTrue((repo / "shop/sales/service.py").is_file())


@needs_pyrefly
class Actions(unittest.TestCase):
    def test_apply_inline_variable(self):
        repo = sample_repo(self.addCleanup)
        listing = run(repo, "actions", "shop/service.py:9:c").stdout
        number = next(line.split(".", 1)[0].strip() for line in listing.splitlines() if "Inline variable" in line)
        result = run(repo, "actions", "shop/service.py:9:c", number, "--apply")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('print(welcome(load_customer("ann")))', read(repo, "shop/service.py"))


@needs_pyrefly
class NoProject(unittest.TestCase):
    def test_warns_that_answers_cover_open_files_only(self):
        repo = sample_repo(self.addCleanup, keep_config=False)
        result = run(repo, "references", f"{MODELS}:20")
        self.assertIn("no project", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
