#!/usr/bin/env python3
"""Ask Pyrefly's language server one question about Python code from the command line.

Starts `pyrefly lsp`, opens the file in question, waits for the project index, sends one request, prints the answer, and exits.
Use it for what an agent's harness does not offer: rename, moving a module, refactoring code actions, and every query on harnesses
without an LSP tool.

A position is FILE:LINE:COL or FILE:LINE:NAME, 1-based as editors show them. NAME is the identifier on that line to ask about (its
first occurrence). On a `def` or `class` line, FILE:LINE alone means the name being defined.

    pyrefly_lsp.py hover shop/service.py:9:c                   # type and docs of a name
    pyrefly_lsp.py definition shop/service.py:9:load_customer  # where it is defined (type-definition: where its type is)
    pyrefly_lsp.py references shop/models.py:11:greeting       # every use, resolved by type, across the project
    pyrefly_lsp.py implementations shop/models.py:11:greeting  # overrides in subclasses
    pyrefly_lsp.py callers shop/service.py:4                   # every call site, and the function it is in
    pyrefly_lsp.py subtypes shop/models.py:5                   # subclass tree (supertypes: base classes)
    pyrefly_lsp.py symbols load_cust [--all]                   # definitions whose names match, in the project
    pyrefly_lsp.py outline shop/models.py                      # classes, functions, and attributes of a file
    pyrefly_lsp.py hints shop/models.py[:20-30]                # inferred types of unannotated returns and variables
    pyrefly_lsp.py rename shop/models.py:20 fetch_customer [--apply]
    pyrefly_lsp.py move shop/models.py shop/entities.py [--apply]  # move a module and rewrite imports of it
    pyrefly_lsp.py actions shop/service.py:9:c                 # list refactors and quick fixes there (or FILE:L1-L2)
    pyrefly_lsp.py actions shop/service.py:9:c 2 [--apply]     # preview or apply action 2

Edits are previewed as a diff unless --apply is given. Rename and move also list lines that still name the old symbol or module
and that the server does not change (strings, comments, docs, __all__, dynamic access, same-named symbols): review each.

Exit codes: 0 answered, 1 nothing found, 2 usage or server error.
Needs Python 3.8+ and Pyrefly: the project's own (.venv), pyrefly on PATH, or uv (uvx) or pipx to run it without installing.
Set PYREFLY_CMD to choose the command, for example PYREFLY_CMD="uv run pyrefly".
"""

from __future__ import annotations

import argparse
import difflib
import functools
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

INDEX_TIMEOUT = 180.0  # seconds to wait for the project index after opening a file
OPEN_TIMEOUT = 30.0  # seconds to wait for the first check of an opened file
REQUEST_TIMEOUT = 120.0
INDEX_FILE_LIMIT = 100_000  # files to index in a project with no Pyrefly config (Pyrefly's default is 2,000)
PROJECT_MARKERS = ("pyrefly.toml", "pyproject.toml", "setup.py", "mypy.ini", "pyrightconfig.json")
SKIP_DIRS = {".git", ".hg", ".venv", "venv", "env", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
             ".nox", "build", "dist", "site-packages", ".pixi"}
SYMBOL_KINDS = {1: "file", 2: "module", 3: "namespace", 4: "package", 5: "class", 6: "method", 7: "property", 8: "field",
                9: "constructor", 10: "enum", 11: "interface", 12: "function", 13: "variable", 14: "constant", 15: "string",
                22: "enum member", 23: "struct", 26: "type parameter"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
DEF_LINE = re.compile(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


class LspError(Exception):
    pass


class NotFound(Exception):
    pass


def note(message: str) -> None:
    print(f"pyrefly_lsp: {message}", file=sys.stderr)


# --- Starting the server ------------------------------------------------------------------------------------------------

def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / ".git").exists():
            return folder
    return start


def pyrefly_command(root: Path) -> list[str]:
    """The project's own Pyrefly first, so answers match its pinned version and CI; then PATH, then a runner."""
    override = os.environ.get("PYREFLY_CMD")
    if override:
        return shlex.split(override, posix=os.name != "nt")
    exe = Path("Scripts/pyrefly.exe") if os.name == "nt" else Path("bin/pyrefly")
    for folder in [root, *root.parents]:
        for venv in (".venv", "venv", "env"):
            candidate = folder / venv / exe
            if candidate.is_file():
                return [str(candidate)]
        if (folder / ".git").exists():
            break
    found = shutil.which("pyrefly")
    if found:
        return [found]
    for runner, args in (("uvx", ["pyrefly"]), ("pipx", ["run", "pyrefly"])):
        found = shutil.which(runner)
        if found:
            return [found, *args]
    raise LspError("pyrefly not found: install it in the project or on PATH, install uv or pipx, or set PYREFLY_CMD")


class Client:
    def __init__(self, root: Path):
        self.root = root
        base = pyrefly_command(root)
        self.cmd = base + ["lsp"]
        # Without a [tool.pyrefly] config, Pyrefly indexes at most 2,000 files and silently answers from those alone.
        try:
            usage = subprocess.run(base + ["lsp", "--help"], cwd=root, capture_output=True, text=True, timeout=120).stdout
        except (OSError, subprocess.TimeoutExpired):
            usage = ""
        if "--workspace-indexing-limit" in usage:
            self.cmd += ["--workspace-indexing-limit", str(INDEX_FILE_LIMIT)]
        try:
            self.proc = subprocess.Popen(self.cmd, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
        except OSError as e:
            raise LspError(f"cannot start `{' '.join(self.cmd)}`: {e}") from None
        self.lock = threading.Lock()
        self.responses: dict[int, queue.Queue] = {}
        self.next_id = 0
        self.stderr_tail: list[str] = []
        self.indexed = threading.Event()  # the server logs "Populated all files" once the project is indexed
        self.published: dict[str, int] = {}  # publishDiagnostics count per URI
        self.diagnostics: dict[str, list] = {}
        self.changed = threading.Condition()
        self.opened: set[Path] = set()
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        threading.Thread(target=self._read, daemon=True).start()

    def _drain_stderr(self) -> None:
        for raw in self.proc.stderr:
            line = raw.decode("utf-8", "replace").rstrip()
            if "Populated all files" in line:
                self.indexed.set()
                with self.changed:
                    self.changed.notify_all()
            self.stderr_tail = (self.stderr_tail + [line])[-5:]

    def _write(self, msg: dict) -> None:
        body = json.dumps(msg).encode("utf-8")
        with self.lock:
            try:
                self.proc.stdin.write(b"Content-Length: %d\r\n\r\n" % len(body) + body)
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                pass  # the server has exited; request() reports why

    def _read(self) -> None:
        stream = self.proc.stdout
        while True:
            length = None
            while True:
                line = stream.readline()
                if not line:
                    return
                line = line.strip()
                if not line:
                    break
                name, _, value = line.decode("ascii").partition(":")
                if name.lower() == "content-length":
                    length = int(value)
            if length is None:
                continue
            msg = json.loads(stream.read(length))
            method = msg.get("method")
            if method and "id" in msg:  # a request from the server
                result = None
                if method == "workspace/configuration":
                    result = [None] * len(msg["params"].get("items", []))
                self._write({"jsonrpc": "2.0", "id": msg["id"], "result": result})
            elif method == "textDocument/publishDiagnostics":
                uri = msg["params"]["uri"]
                with self.changed:
                    self.published[uri] = self.published.get(uri, 0) + 1
                    self.diagnostics[uri] = msg["params"]["diagnostics"]
                    self.changed.notify_all()
            elif not method and msg.get("id") in self.responses:
                self.responses[msg["id"]].put(msg)

    def request(self, method: str, params):
        with self.lock:
            self.next_id += 1
            rid = self.next_id
        box: queue.Queue = queue.Queue()
        self.responses[rid] = box
        self._write({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        deadline = time.monotonic() + REQUEST_TIMEOUT
        while True:
            try:
                msg = box.get(timeout=0.25)
                break
            except queue.Empty:
                if self.proc.poll() is not None:
                    time.sleep(0.1)  # let the stderr reader catch up
                    detail = "; ".join(self.stderr_tail) or "no output"
                    raise LspError(f"`{' '.join(self.cmd)}` exited with code {self.proc.returncode}: {detail}") from None
                if time.monotonic() > deadline:
                    raise LspError(f"{method}: no answer from pyrefly in {REQUEST_TIMEOUT:.0f}s") from None
        if "error" in msg:
            raise LspError(f"{method}: {msg['error'].get('message')}")
        return msg.get("result")

    def notify(self, method: str, params) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def start(self) -> None:
        capabilities = {
            "general": {"positionEncodings": ["utf-16"]},
            "window": {"workDoneProgress": True},
            "workspace": {
                "workspaceFolders": True, "configuration": True, "symbol": {},
                "workspaceEdit": {"documentChanges": True, "resourceOperations": ["create", "rename", "delete"]},
                "fileOperations": {"willRename": True},
            },
            "textDocument": {
                "definition": {}, "typeDefinition": {}, "references": {}, "implementation": {},
                "hover": {"contentFormat": ["markdown", "plaintext"]},
                "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                "rename": {"prepareSupport": True}, "callHierarchy": {}, "typeHierarchy": {}, "inlayHint": {},
                "publishDiagnostics": {},
                "codeAction": {
                    "codeActionLiteralSupport": {"codeActionKind": {"valueSet": [
                        "quickfix", "refactor", "refactor.extract", "refactor.inline", "refactor.rewrite", "refactor.move",
                        "source", "source.organizeImports", "source.fixAll"]}},
                    "resolveSupport": {"properties": ["edit"]}, "dataSupport": True,
                },
            },
        }
        self.request("initialize", {
            "processId": os.getpid(), "rootUri": self.root.as_uri(), "capabilities": capabilities,
            "workspaceFolders": [{"uri": self.root.as_uri(), "name": self.root.name}],
        })
        self.notify("initialized", {})

    def open(self, path: Path) -> None:
        if path in self.opened:
            return
        self.opened.add(path)
        self.notify("textDocument/didOpen", {"textDocument": {
            "uri": path.as_uri(), "languageId": "python", "version": 1, "text": read_text(path)}})

    def wait_ready(self, path: Path) -> None:
        """Wait until cross-file answers are complete. Pyrefly indexes the project in the background after the first file
        opens and reports nothing over LSP when done; asking earlier silently returns results from the open files only."""
        uri = path.as_uri()
        marker = project_marker(path)
        start = time.monotonic()
        with self.changed:
            if not marker:
                self.changed.wait_for(lambda: self.published.get(uri, 0) >= 1, timeout=OPEN_TIMEOUT)
                note(f"no project around {display(path, self.root)} (none of {', '.join(PROJECT_MARKERS)} in it or a parent "
                     "folder), so Pyrefly indexes no project: cross-file answers cover open files only")
                return
            # Done when the indexing log line appears, or the open file is rechecked after indexing (its second publish).
            done = self.changed.wait_for(lambda: self.indexed.is_set() or self.published.get(uri, 0) >= 2,
                                         timeout=INDEX_TIMEOUT)
        if not done:
            note(f"the project index was not ready after {INDEX_TIMEOUT:.0f}s; cross-file answers may be incomplete")
        elif time.monotonic() - start > 20:
            note(f"indexing took {time.monotonic() - start:.0f}s")

    def close(self) -> None:
        try:
            if self.proc.poll() is None:
                self.request("shutdown", None)
                self.notify("exit", None)
                self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()
        for stream in (self.proc.stdin, self.proc.stdout):
            try:
                stream.close()
            except OSError:
                pass


def project_marker(path: Path) -> Path | None:
    for folder in path.parents:
        for name in PROJECT_MARKERS:
            if (folder / name).is_file():
                return folder / name
    return None


# --- Paths and positions --------------------------------------------------------------------------------------------------

def uri_to_path(uri: str) -> Path:
    return Path(url2pathname(unquote(urlparse(uri).path)))


def read_text(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def read_lines(path: Path) -> list[str]:
    return read_text(path).splitlines(keepends=True)


def display(path: Path, root: Path) -> str:
    text = str(path)
    marker = "pyrefly_bundled_typeshed_"
    if marker in text:  # Pyrefly unpacks its bundled typeshed stubs into a temporary folder
        tail = Path(text[text.index(marker):]).parts[1:]
        return "<typeshed>/" + "/".join(tail)
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return text


def utf16_to_index(line: str, units: int) -> int:
    count = 0
    for index, char in enumerate(line):
        if count >= units:
            return index
        count += 2 if ord(char) > 0xFFFF else 1
    return len(line)


def index_to_utf16(line: str, index: int) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in line[:index])


@functools.lru_cache(maxsize=256)
def cached_lines(path: Path) -> list[str]:
    return read_lines(path)


def line_text(path: Path, line0: int) -> str:
    """One line of a file as it is on disk now; for printing answers, never for computing edits."""
    try:
        return cached_lines(path)[line0].rstrip("\r\n")
    except (OSError, IndexError, UnicodeDecodeError):
        return ""


def location(uri: str, pos: dict, root: Path, label: str = "") -> str:
    """FILE:LINE:COL (1-based, columns in characters), then a label or the line's text."""
    path = uri_to_path(uri)
    text = line_text(path, pos["line"])
    col = utf16_to_index(text, pos["character"]) + 1
    tail = label or text.strip()
    if len(tail) > 160:
        tail = tail[:157] + "..."
    return f"{display(path, root)}:{pos['line'] + 1}:{col}: {tail}"


class Target:
    """A parsed FILE[:LINE[-LINE2][:COL|:NAME]] argument."""

    SPEC = re.compile(r"^(?P<file>.+?)(?::(?P<line>\d+)(?:-(?P<end>\d+))?(?::(?P<col>[^:]+))?)?$")

    def __init__(self, spec: str, root: Path):
        match = self.SPEC.match(spec)
        if not match:
            raise LspError(f"cannot read position {spec!r}; use FILE:LINE:COL or FILE:LINE:NAME")
        self.path = Path(match["file"]).resolve()
        if not self.path.is_file():
            raise LspError(f"no such file: {match['file']}")
        self.line = int(match["line"]) if match["line"] else None
        self.end_line = int(match["end"]) if match["end"] else None
        self.name: str | None = None
        self.col: int | None = None  # 0-based character index
        lines = read_lines(self.path)
        if self.line is not None and not 1 <= self.line <= len(lines):
            raise LspError(f"{match['file']} has {len(lines)} lines, not {self.line}")
        text = lines[self.line - 1].rstrip("\r\n") if self.line else ""
        col = match["col"]
        if col and col.isdigit():
            self.col = int(col) - 1
            ident = IDENT.match(text, self.col)
            self.name = ident.group() if ident else None
        elif col:
            found = re.search(rf"(?<![A-Za-z0-9_]){re.escape(col)}(?![A-Za-z0-9_])", text)
            if not found:
                raise LspError(f"{col!r} is not on line {self.line} of {match['file']}: {text.strip()}")
            self.col, self.name = found.start(), col
        elif self.line:
            definition = DEF_LINE.match(text)
            if definition:
                self.col, self.name = definition.start(1), definition.group(1)
            else:
                self.col = len(text) - len(text.lstrip())
        self.text = text

    @property
    def uri(self) -> str:
        return self.path.as_uri()

    def position(self) -> dict:
        if self.line is None:
            raise LspError(f"{display(self.path, Path.cwd())} needs a line: FILE:LINE:COL or FILE:LINE:NAME")
        return {"line": self.line - 1, "character": index_to_utf16(self.text, self.col or 0)}

    def params(self) -> dict:
        return {"textDocument": {"uri": self.uri}, "position": self.position()}

    def range(self) -> dict:
        """The name's span, a whole line, or a span of whole lines (for code actions and hints)."""
        lines = read_lines(self.path)
        if self.line is None:
            return {"start": {"line": 0, "character": 0}, "end": {"line": len(lines), "character": 0}}
        if self.end_line:
            last = lines[self.end_line - 1].rstrip("\r\n")
            return {"start": {"line": self.line - 1, "character": 0},
                    "end": {"line": self.end_line - 1, "character": index_to_utf16(last, len(last))}}
        start = self.position()
        if self.name and self.col is not None:
            end = index_to_utf16(self.text, self.col + len(self.name))
        else:
            end = index_to_utf16(self.text, len(self.text.rstrip()))
        return {"start": start, "end": {"line": start["line"], "character": end}}


# --- Workspace edits --------------------------------------------------------------------------------------------------

def edit_ops(result: dict) -> list[tuple]:
    """A WorkspaceEdit as ordered operations: ("edit", path, edits), ("create", path), ("rename", old, new), ("delete", path)."""
    ops: list[tuple] = []
    for uri, edits in (result.get("changes") or {}).items():
        ops.append(("edit", uri_to_path(uri), edits))
    for change in result.get("documentChanges") or []:
        kind = change.get("kind")
        if kind == "create":
            ops.append(("create", uri_to_path(change["uri"])))
        elif kind == "rename":
            ops.append(("rename", uri_to_path(change["oldUri"]), uri_to_path(change["newUri"])))
        elif kind == "delete":
            ops.append(("delete", uri_to_path(change["uri"])))
        else:
            ops.append(("edit", uri_to_path(change["textDocument"]["uri"]), change["edits"]))
    return ops


def apply_text_edits(text: str, edits: list[dict]) -> str:
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(pos: dict) -> int:
        if pos["line"] >= len(lines):
            return len(text)
        return offsets[pos["line"]] + utf16_to_index(lines[pos["line"]].rstrip("\r\n"), pos["character"])

    spans = {(offset(e["range"]["start"]), offset(e["range"]["end"]), e["newText"]) for e in edits}  # drops duplicates
    for start, end, new in sorted(spans, key=lambda s: (s[0], s[1]), reverse=True):
        text = text[:start] + new + text[end:]
    return text


def simulate(ops: list[tuple]) -> tuple[dict[Path, str | None], dict[Path, Path]]:
    """Final content of every touched path (None: gone) and where each renamed file went, without touching disk."""
    state: dict[Path, str | None] = {}
    moved: dict[Path, Path] = {}

    def get(path: Path) -> str:
        if path not in state:
            state[path] = read_text(path) if path.is_file() else None
        return state[path] or ""

    for op in ops:
        if op[0] == "edit":
            state[op[1]] = apply_text_edits(get(op[1]), op[2])
        elif op[0] == "create":
            if get(op[1]) is None or state.get(op[1]) is None:
                state[op[1]] = ""
        elif op[0] == "rename":
            content = get(op[1])
            state[op[1]] = None
            state[op[2]] = content
            origin = next((k for k, v in moved.items() if v == op[1]), op[1])
            moved[origin] = op[2]
        elif op[0] == "delete":
            get(op[1])
            state[op[1]] = None
    return state, moved


def preview(ops: list[tuple], root: Path) -> str:
    state, moved = simulate(ops)
    sources = {new: old for old, new in moved.items()}
    out: list[str] = []
    for old, new in moved.items():
        out.append(f"rename {display(old, root)} -> {display(new, root)}")
    for path, final in state.items():
        if final is None:
            if path not in moved:
                out.append(f"delete {display(path, root)}")
            continue
        source = sources.get(path, path)
        before = read_text(source) if source.is_file() else ""
        if before == final:
            continue
        out.extend(line.rstrip("\n") for line in difflib.unified_diff(
            before.splitlines(keepends=True), final.splitlines(keepends=True),
            fromfile=f"a/{display(source, root)}", tofile=f"b/{display(path, root)}", n=1))
    return "\n".join(out)


def git_tracked(path: Path, root: Path) -> bool:
    try:
        return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root, capture_output=True).returncode == 0
    except OSError:
        return False


def apply_ops(ops: list[tuple], root: Path) -> tuple[int, int]:
    """Write the operations to disk in order. Returns (text edits, files changed)."""
    count, files = 0, set()
    for op in ops:
        if op[0] == "edit":
            path = op[1]
            new = apply_text_edits(read_text(path) if path.is_file() else "", op[2])
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new)
            count += len(op[2])
            files.add(path)
        elif op[0] == "create":
            op[1].parent.mkdir(parents=True, exist_ok=True)
            op[1].touch(exist_ok=True)
            files.add(op[1])
        elif op[0] == "rename":
            old, new = op[1], op[2]
            new.parent.mkdir(parents=True, exist_ok=True)
            if git_tracked(old, root):
                subprocess.run(["git", "mv", str(old), str(new)], cwd=root, check=True, capture_output=True)
            else:
                os.replace(old, new)
            files.discard(old)
            files.add(new)
        elif op[0] == "delete":
            op[1].unlink(missing_ok=True)
            files.add(op[1])
    return count, len(files)


# --- Leftovers: what the server does not rewrite ---------------------------------------------------------------------

def project_files(root: Path) -> list[Path]:
    try:
        listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=root, capture_output=True,
                                check=True).stdout.decode("utf-8", "replace")
        paths = [root / p for p in listed.split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        paths = []
        for folder, dirs, names in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            paths.extend(Path(folder) / n for n in names)
    return [p for p in paths if p.is_file() and p.stat().st_size < 2_000_000]


def leftovers(root: Path, patterns: list[re.Pattern], ops: list[tuple]) -> list[str]:
    """Lines matching a pattern at a spot no edit touches."""
    covered: dict[Path, list[tuple[int, int, int, int]]] = {}
    for op in ops:
        if op[0] == "edit":
            for e in op[2]:
                r = e["range"]
                covered.setdefault(op[1].resolve(), []).append(
                    (r["start"]["line"], r["start"]["character"], r["end"]["line"], r["end"]["character"]))
    found = []
    for path in project_files(root):
        try:
            lines = read_text(path).splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        spans = covered.get(path.resolve(), [])
        for n, text in enumerate(lines):
            for pattern in patterns:
                hits = [m for m in pattern.finditer(text)
                        if not any((sl, sc) <= (n, index_to_utf16(text, m.start())) <= (el, ec) for sl, sc, el, ec in spans)]
                if hits:
                    found.append(f"{display(path, root)}:{n + 1}:{hits[0].start() + 1}: {text.strip()[:160]}")
                    break
    return found


def print_leftovers(found: list[str], what: str, advice: str) -> None:
    if not found:
        print(f"\nNothing else in the project names {what}.")
        return
    print(f"\nStill naming {what}: {len(found)} line(s) the server does not change. Review each: {advice}")
    for line in found:
        print(f"  {line}")


def module_name(path: Path) -> str | None:
    """Dotted module name, found by walking up through packages (folders with __init__.py)."""
    parts = [] if path.stem == "__init__" else [path.stem]
    folder = path.parent
    while (folder / "__init__.py").is_file():
        parts.insert(0, folder.name)
        folder = folder.parent
    return ".".join(parts) or None


# --- Commands -----------------------------------------------------------------------------------------------------------

def hover_text(result) -> str:
    contents = result.get("contents") if isinstance(result, dict) else result
    if isinstance(contents, list):
        text = "\n\n".join(c.get("value", "") if isinstance(c, dict) else c for c in contents)
    elif isinstance(contents, dict):
        text = contents.get("value", "")
    else:
        text = contents or ""
    kept = [line for line in text.splitlines() if not line.startswith("Go to [")]  # links to temporary file:// paths
    text = "\n".join(kept).strip()
    return re.sub(r"\]\(file://[^)#]*?([^/)#]+)#L(\d+),(\d+)\)", r"](\1:\2:\3)", text)


def locations(result) -> list[tuple[str, dict]]:
    if not result:
        return []
    items = result if isinstance(result, list) else [result]
    out = []
    for item in items:
        if "targetUri" in item:
            out.append((item["targetUri"], item["targetSelectionRange"]["start"]))
        else:
            out.append((item["uri"], item["range"]["start"]))
    return out


def print_locations(found: list[tuple[str, dict]], root: Path, what: str) -> int:
    if not found:
        return 1
    found = sorted(set((uri, pos["line"], pos["character"]) for uri, pos in found))
    files = {uri for uri, _, _ in found}
    print(f"{len(found)} {what} in {len(files)} file(s):")
    for uri, line, char in found:
        print(location(uri, {"line": line, "character": char}, root))
    return 0


def in_project(uri: str, root: Path) -> bool:
    path = uri_to_path(uri)
    try:
        rel = path.resolve().relative_to(root)
    except ValueError:
        return False
    return not any(part in SKIP_DIRS for part in rel.parts)


def print_symbols(symbols: list, depth: int = 0) -> None:
    for s in symbols:
        kind = SYMBOL_KINDS.get(s.get("kind"), "symbol")
        detail = f"  {s['detail']}" if s.get("detail") else ""
        print(f"{'  ' * depth}{s['selectionRange']['start']['line'] + 1}: {kind} {s['name']}{detail}")
        print_symbols(s.get("children") or [], depth + 1)


def first_python_file(root: Path) -> Path | None:
    for path in sorted(project_files(root)):
        if path.suffix in (".py", ".pyi") and project_marker(path):
            return path
    return None


def enclosing(path: Path, line0: int) -> str:
    """Dotted name of the def or class around a line, by indentation (for calls the call hierarchy does not report)."""
    lines = cached_lines(path)
    indent = len(lines[line0]) - len(lines[line0].lstrip())
    names = []
    for text in reversed(lines[:line0]):
        match = DEF_LINE.match(text)
        if match and len(text) - len(text.lstrip()) < indent:
            names.insert(0, match.group(1))
            indent = len(text) - len(text.lstrip())
    return ".".join(names) or "module level"


def alias_calls(client: Client, target: Target, name: str):
    """Calls through `import name as alias`, found from the references to `name` and then to each alias."""
    refs = client.request("textDocument/references", {**target.params(), "context": {"includeDeclaration": False}}) or []
    for ref in refs:
        path = uri_to_path(ref["uri"])
        text = line_text(path, ref["range"]["start"]["line"])
        match = re.search(rf"\b{re.escape(name)}\s+as\s+([A-Za-z_][A-Za-z0-9_]*)", text)
        if not match or not re.match(r"\s*(from|import)\b", text):
            continue
        pos = {"line": ref["range"]["start"]["line"], "character": index_to_utf16(text, match.start(1))}
        client.open(path)  # the server answers about positions only in files it has open
        uses = client.request("textDocument/references", {"textDocument": {"uri": ref["uri"]}, "position": pos,
                                                         "context": {"includeDeclaration": False}}) or []
        for use in uses:
            use_path = uri_to_path(use["uri"])
            line0 = use["range"]["start"]["line"]
            use_text = line_text(use_path, line0)
            end = utf16_to_index(use_text, use["range"]["end"]["character"])
            if use_text[end:].lstrip().startswith("("):
                yield ((use["uri"], line0, use["range"]["start"]["character"]),
                       f"in {enclosing(use_path, line0)}, as `{match.group(1)}`: {use_text.strip()}")


def show_edit(result, root: Path, apply: bool, what: str) -> None:
    if not result:
        raise NotFound(f"the server has no edit for {what}")
    ops = edit_ops(result)
    if not apply:
        print(preview(ops, root) or "(no changes)")
        print(f"\nPreview only: run again with --apply to write {what}.")
    else:
        count, files = apply_ops(ops, root)
        print(f"Applied {what}: {count} text edit(s) in {files} file(s).")


def run(args, client: Client, root: Path) -> int:
    cmd = args.command
    if cmd == "symbols":
        anchor = first_python_file(root)
        if anchor:
            client.open(anchor)
            client.wait_ready(anchor)
        result = client.request("workspace/symbol", {"query": args.query}) or []
        rows = []
        for s in result:
            loc = s.get("location", {})
            if "range" not in loc:
                continue
            start = loc["range"]["start"]
            if not args.all and (not in_project(loc["uri"], root) or (start == {"line": 0, "character": 0}
                                                                     and s["name"].startswith("__"))):
                continue
            kind = SYMBOL_KINDS.get(s.get("kind"), "symbol")
            rows.append((display(uri_to_path(loc["uri"]), root), start["line"], location(loc["uri"], start, root,
                                                                                          f"{kind} {s['name']}")))
        for _, _, row in sorted(rows):
            print(row)
        return 0 if rows else 1

    if cmd == "move":
        old, new = Path(args.target).resolve(), Path(args.destination).resolve()
        if not old.is_file() or old.suffix not in (".py", ".pyi"):
            raise LspError(f"{args.target}: move takes one existing .py or .pyi file (the server cannot move a package folder)")
        if new.exists():
            raise LspError(f"{args.destination} already exists")
        client.open(old)
        client.wait_ready(old)
        result = client.request("workspace/willRenameFiles", {"files": [{"oldUri": old.as_uri(), "newUri": new.as_uri()}]})
        old_module = module_name(old)
        ops = edit_ops(result or {}) + [("rename", old, new)]
        patterns = [re.compile(re.escape(display(old, root)))]
        if old_module:
            patterns.insert(0, re.compile(rf"(?<![\w.]){re.escape(old_module)}(?!\w)"))
            # `from . import mod` and `from pkg import mod`: the server rewrites neither form
            parent = re.escape(old_module.rpartition(".")[0])
            source = rf"(?:\.+|{parent})" if parent else r"\.+"
            patterns.append(re.compile(rf"^\s*from\s+{source}\s+import\b.*\b{re.escape(old.stem)}\b"))
        found = leftovers(root, patterns, ops)
        relative = []  # scanned before the move: the file's own `from .x import y` now resolve from the new folder
        if old.parent != new.parent:
            for n, text in enumerate(read_text(old).splitlines()):
                if re.match(r"\s*from\s+\.", text):
                    relative.append((n + 1, text.strip()))
        if not args.apply:
            print(preview(ops, root))
            print("\nPreview only: run again with --apply to move the file and rewrite its imports.")
        else:
            count, files = apply_ops(ops, root)
            print(f"Moved {display(old, root)} -> {display(new, root)}; {count} import edit(s) in {files - 1} other file(s).")
        if relative:
            print(f"\nRelative imports in the moved file: {len(relative)} line(s) the server does not change, which now resolve "
                  f"from {display(new.parent, root)}/. Rewrite each for its new folder (for example `.x` becomes `..x`):")
            where = display(new if args.apply else old, root)
            for n, text in relative:
                print(f"  {where}:{n}:1: {text}")
        print_leftovers(found, f"the old module ({old_module or display(old, root)})",
                        "imports the server missed (`from . import x`, `import a.b` then `a.b.f()`), patch targets and other "
                        "strings, docs, and config.")
        if args.apply:
            print("\nRun `pyrefly check` and the tests to confirm nothing still imports the old path.")
        return 0

    target = Target(args.target, root)
    client.open(target.path)
    client.wait_ready(target.path)

    if cmd == "hover":
        result = client.request("textDocument/hover", target.params())
        text = hover_text(result) if result else ""
        if not text:
            return 1
        print(text)
        return 0

    if cmd in ("definition", "type-definition"):
        method = "textDocument/definition" if cmd == "definition" else "textDocument/typeDefinition"
        found = locations(client.request(method, target.params()))
        for uri, pos in found:
            print(location(uri, pos, root))
        return 0 if found else 1

    if cmd == "references":
        params = {**target.params(), "context": {"includeDeclaration": True}}
        return print_locations(locations(client.request("textDocument/references", params)), root, "reference(s)")

    if cmd == "implementations":
        return print_locations(locations(client.request("textDocument/implementation", target.params())), root,
                               "implementation(s)")

    if cmd == "callers":
        items = client.request("textDocument/prepareCallHierarchy", target.params())
        if not items:
            raise NotFound("no function or method at that position")
        item = items[0]
        calls = client.request("callHierarchy/incomingCalls", {"item": item}) or []
        rows = {}
        for call in calls:
            who = call["from"].get("detail") or call["from"]["name"]
            for r in call.get("fromRanges", []):
                key = (call["from"]["uri"], r["start"]["line"], r["start"]["character"])
                rows[key] = f"in {who}: " + line_text(uri_to_path(key[0]), key[1]).strip()
        # The server's call hierarchy misses calls through an import alias (`import f as g`, then `g()`); follow each alias.
        for key, label in alias_calls(client, target, item["name"]):
            rows.setdefault(key, label)
        print(f"{len(rows)} call(s) of {item.get('detail') or item['name']}:")
        for (uri, line, char), label in sorted(rows.items()):
            print(location(uri, {"line": line, "character": char}, root, label))
        return 0 if rows else 1

    if cmd in ("subtypes", "supertypes"):
        items = client.request("textDocument/prepareTypeHierarchy", target.params())
        if not items:
            raise NotFound("no class at that position")
        # Pyrefly answers with every descendant (or ancestor), not just the direct ones, so print them as one list.
        found = client.request(f"typeHierarchy/{cmd}", {"item": items[0]}) or []
        rows = sorted({(display(uri_to_path(c["uri"]), root), c["selectionRange"]["start"]["line"]):
                       location(c["uri"], c["selectionRange"]["start"], root, c.get("detail") or c["name"]) for c in found}.items())
        kind = "subclass(es)" if cmd == "subtypes" else "base class(es)"
        print(f"{len(rows)} {kind} of {items[0].get('detail') or items[0]['name']}, direct and indirect:")
        for _, row in rows:
            print(row)
        return 0 if rows else 1

    if cmd == "outline":
        symbols = client.request("textDocument/documentSymbol", {"textDocument": {"uri": target.uri}}) or []
        if symbols and "location" in symbols[0]:  # flat SymbolInformation
            for s in symbols:
                print(location(s["location"]["uri"], s["location"]["range"]["start"], root,
                               f"{SYMBOL_KINDS.get(s.get('kind'), 'symbol')} {s['name']}"))
        else:
            print_symbols(symbols)
        return 0 if symbols else 1

    if cmd == "hints":
        hints = client.request("textDocument/inlayHint", {"textDocument": {"uri": target.uri}, "range": target.range()}) or []
        for h in sorted(hints, key=lambda h: (h["position"]["line"], h["position"]["character"])):
            label = h["label"] if isinstance(h["label"], str) else "".join(part["value"] for part in h["label"])
            print(location(target.uri, h["position"], root, f"{label.strip()}    | {line_text(target.path, h['position']['line']).strip()}"))
        return 0 if hints else 1

    if cmd == "rename":
        prepared = client.request("textDocument/prepareRename", target.params())
        if not prepared:
            raise NotFound("nothing renamable at that position")
        old = target.name or ""
        result = client.request("textDocument/rename", {**target.params(), "newName": args.new_name})
        # Scan before writing: the edit ranges describe the files as they are now.
        found = leftovers(root, [re.compile(rf"(?<![A-Za-z0-9_]){re.escape(old)}(?![A-Za-z0-9_])")],
                          edit_ops(result or {})) if old else []
        show_edit(result, root, args.apply, f"the rename of `{old}` to `{args.new_name}`")
        if old:
            print_leftovers(found, f"`{old}`", "a string, comment, doc, __all__ entry, or getattr may need the new name; "
                            "a different symbol that only shares the name must keep it.")
        return 0

    if cmd == "actions":
        uri = target.uri
        rng = target.range()
        diags = [d for d in client.diagnostics.get(uri, [])
                 if d["range"]["start"]["line"] <= rng["end"]["line"] and d["range"]["end"]["line"] >= rng["start"]["line"]]
        actions = client.request("textDocument/codeAction", {"textDocument": {"uri": uri}, "range": rng,
                                                             "context": {"diagnostics": diags, "triggerKind": 1}}) or []
        actions = [a for a in actions if "command" not in a or "edit" in a or "data" in a]
        if not actions:
            return 1
        if args.number is None:
            for n, a in enumerate(actions, 1):
                print(f"{n}. {a['title']}  [{a.get('kind', 'action')}]")
            print("\nPreview one with: actions TARGET NUMBER; write it with --apply.")
            return 0
        if not 1 <= args.number <= len(actions):
            raise LspError(f"there are {len(actions)} action(s) here, not {args.number}")
        action = actions[args.number - 1]
        if "edit" not in action:
            action = client.request("codeAction/resolve", action)
        show_edit(action.get("edit"), root, args.apply, f"\"{action['title']}\"")
        return 0

    raise LspError(f"unknown command {cmd}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n\n", 2)[2])
    parser.add_argument("--root", help="workspace root (default: the enclosing git repository, else the current directory)")
    sub = parser.add_subparsers(dest="command", required=True)
    position = "FILE:LINE:COL|FILE:LINE:NAME"
    for name, text in (("hover", "type and docs at a position"), ("definition", "where a name is defined"),
                       ("type-definition", "where the type of a name is defined"),
                       ("references", "every reference to the symbol, project-wide"),
                       ("implementations", "overrides of a method, or implementations of a protocol member"),
                       ("callers", "every call of the function or method, and the function each is in"),
                       ("subtypes", "subclass tree of a class"), ("supertypes", "base-class tree of a class")):
        sub.add_parser(name, help=text).add_argument("target", metavar=position)
    p = sub.add_parser("symbols", help="definitions in the project whose names match QUERY")
    p.add_argument("query")
    p.add_argument("--all", action="store_true", help="include the standard library, dependencies, and module dunders")
    sub.add_parser("outline", help="symbols defined in a file").add_argument("target", metavar="FILE")
    sub.add_parser("hints", help="inferred types Pyrefly would show as inlay hints").add_argument(
        "target", metavar="FILE[:LINE[-LINE]]")
    p = sub.add_parser("rename", help="rename the symbol everywhere it is referenced")
    p.add_argument("target", metavar=position)
    p.add_argument("new_name", metavar="NEW_NAME")
    p.add_argument("--apply", action="store_true", help="write the edits (default: preview only)")
    p = sub.add_parser("move", help="move a module file and rewrite the imports of it")
    p.add_argument("target", metavar="OLD.py")
    p.add_argument("destination", metavar="NEW.py")
    p.add_argument("--apply", action="store_true", help="move the file and write the edits (default: preview only)")
    p = sub.add_parser("actions", help="list, preview, or apply the code actions at a position or line range")
    p.add_argument("target", metavar=f"{position}|FILE:LINE-LINE")
    p.add_argument("number", nargs="?", type=int, help="the action to preview or apply, from the list")
    p.add_argument("--apply", action="store_true", help="write the action's edits (default: preview only)")
    args = parser.parse_args()
    if getattr(args, "apply", False) and args.command == "actions" and args.number is None:
        parser.error("--apply needs the NUMBER of the action to apply")

    root = Path(args.root).resolve() if args.root else find_root(Path.cwd().resolve())
    client = None
    try:
        client = Client(root)
        client.start()
        return run(args, client, root)
    except NotFound as e:
        note(str(e))
        return 1
    except LspError as e:
        note(str(e))
        return 2
    except BrokenPipeError:  # output piped into head or similar
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
