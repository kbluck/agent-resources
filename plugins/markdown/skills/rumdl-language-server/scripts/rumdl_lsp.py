#!/usr/bin/env python3
"""Ask rumdl's language server one question from the command line.

Starts `rumdl server`, waits for it to index the workspace, sends one request, prints the answer, and exits. Use it for the
language-server operations an agent's harness does not expose, chiefly renaming a heading together with every link to it.

Positions are 1-based, as editors and `rumdl check` show them: FILE:LINE or FILE:LINE:COL.

    rumdl_lsp.py outline docs/guide.md
    rumdl_lsp.py headings "install"                 # search headings across the workspace
    rumdl_lsp.py anchors docs/guide.md [PREFIX]     # exact anchors a link to that file may use
    rumdl_lsp.py references docs/guide.md:12        # links to the heading on line 12
    rumdl_lsp.py references docs/guide.md           # links to the file
    rumdl_lsp.py definition README.md:8:30          # where the link at that position goes
    rumdl_lsp.py hover README.md:8:30               # preview of the link's target section
    rumdl_lsp.py mentions docs/guide.md:12          # non-Markdown files (nav, code, HTML) naming that section
    rumdl_lsp.py mentions docs/guide.md             # ... or that file
    rumdl_lsp.py rename docs/guide.md:12 "New Title"          # preview the edits
    rumdl_lsp.py rename docs/guide.md:12 "New Title" --apply  # write them

Exit codes: 0 answered, 1 nothing found, 2 usage or server error.
Needs Python 3.8+ and rumdl on PATH, or uv (uvx), Bun (bunx), or Node.js (npx) to run it without installing.
"""

from __future__ import annotations

import argparse
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

INDEX_START_TIMEOUT = 10.0  # seconds to wait for indexing to begin; none starts when there are no Markdown files
INDEX_DONE_TIMEOUT = 120.0
REQUEST_TIMEOUT = 60.0


class LspError(Exception):
    pass


def rumdl_command() -> list[str]:
    override = os.environ.get("RUMDL_CMD")
    if override:
        return shlex.split(override)
    if shutil.which("rumdl"):
        return ["rumdl"]
    if shutil.which("uvx"):
        return ["uvx", "rumdl"]
    if shutil.which("bunx"):
        return ["bunx", "rumdl"]
    if shutil.which("npx"):
        return ["npx", "--yes", "rumdl"]
    raise LspError("rumdl not found: install it, or install uv, Bun, or Node.js, or set RUMDL_CMD")


class Client:
    def __init__(self, root: Path, config: str | None):
        cmd = rumdl_command() + ["server"]
        if config:
            cmd += ["--config", config]
        if os.name == "nt" and cmd[0] in ("uvx", "bunx", "npx"):
            cmd[0] = shutil.which(cmd[0]) or cmd[0]
        self.cmd = cmd
        self.proc = subprocess.Popen(cmd, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)
        self.stderr_tail: list[str] = []
        threading.Thread(target=self._drain_stderr, daemon=True).start()
        self.lock = threading.Lock()
        self.responses: dict[int, queue.Queue] = {}
        self.progress: queue.Queue = queue.Queue()
        self.next_id = 0
        threading.Thread(target=self._read, daemon=True).start()

    def _drain_stderr(self) -> None:
        for line in self.proc.stderr:
            self.stderr_tail = (self.stderr_tail + [line.decode("utf-8", "replace").rstrip()])[-5:]

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
            if "method" in msg:
                if "id" in msg:  # a request from the server: progress tokens, capability registration
                    self._write({"jsonrpc": "2.0", "id": msg["id"], "result": None})
                elif msg["method"] == "$/progress":
                    self.progress.put(msg["params"].get("value", {}).get("kind"))
            elif msg.get("id") in self.responses:
                self.responses[msg["id"]].put(msg)

    def request(self, method: str, params: dict):
        self.next_id += 1
        box: queue.Queue = queue.Queue()
        self.responses[self.next_id] = box
        self._write({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params})
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
                    raise LspError(f"{method}: no answer from rumdl server in {REQUEST_TIMEOUT:.0f}s") from None
        if "error" in msg:
            raise LspError(f"{method}: {msg['error'].get('message')}")
        return msg.get("result")

    def notify(self, method: str, params: dict) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def start(self, root: Path) -> None:
        capabilities = {
            "window": {"workDoneProgress": True},
            "workspace": {"workspaceFolders": True, "symbol": {}, "workspaceEdit": {"documentChanges": False}},
            "textDocument": {
                "definition": {}, "references": {}, "hover": {"contentFormat": ["markdown", "plaintext"]},
                "documentSymbol": {"hierarchicalDocumentSymbolSupport": True},
                "rename": {"prepareSupport": True}, "completion": {},
            },
        }
        self.request("initialize", {
            "processId": os.getpid(), "rootUri": root.as_uri(), "capabilities": capabilities,
            "workspaceFolders": [{"uri": root.as_uri(), "name": root.name}],
        })
        self.notify("initialized", {})
        self._wait_for_index()

    def _wait_for_index(self) -> None:
        # Cross-file answers come from the workspace index, which rumdl builds in the background after startup and reports
        # as work-done progress. Asking before it ends gets empty results.
        try:
            kind = self.progress.get(timeout=INDEX_START_TIMEOUT)
        except queue.Empty:
            return
        deadline = time.monotonic() + INDEX_DONE_TIMEOUT
        while kind != "end":
            try:
                kind = self.progress.get(timeout=max(0.1, deadline - time.monotonic()))
            except queue.Empty:
                raise LspError("rumdl server did not finish indexing the workspace") from None

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


def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / ".git").exists():
            return folder
    return start


def uri_to_path(uri: str) -> Path:
    return Path(url2pathname(unquote(urlparse(uri).path)))


def utf16_to_index(line: str, units: int) -> int:
    count = 0
    for index, char in enumerate(line):
        if count >= units:
            return index
        count += 2 if ord(char) > 0xFFFF else 1
    return len(line)


def index_to_utf16(line: str, index: int) -> int:
    return sum(2 if ord(c) > 0xFFFF else 1 for c in line[:index])


def read_lines(path: Path) -> list[str]:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read().splitlines(keepends=True)


def display(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def location(path: Path, line0: int, char16: int, root: Path) -> str:
    """FILE:LINE:COL (1-based, columns in characters) plus the line's text."""
    try:
        lines = read_lines(path)
        text = lines[line0].rstrip("\r\n")
        col = utf16_to_index(text, char16) + 1
    except (OSError, IndexError):
        text, col = "", char16 + 1
    return f"{display(path, root)}:{line0 + 1}:{col}: {text.strip()}"


def parse_target(spec: str, need_col: bool = False):
    parts = spec.rsplit(":", 2)
    nums = []
    while len(parts) > 1 and parts[-1].isdigit() and len(nums) < 2:
        nums.insert(0, int(parts.pop()))
    path = Path(":".join(parts)).resolve()
    if not path.is_file():
        raise LspError(f"no such file: {path}")
    line = nums[0] if nums else None
    col = nums[1] if len(nums) > 1 else None
    if need_col and col is None:
        raise LspError(f"give a position inside the link, as FILE:LINE:COL (got {spec})")
    return path, line, col


def position(path: Path, line: int, col: int | None) -> dict:
    lines = read_lines(path)
    if not 1 <= line <= len(lines):
        raise LspError(f"{path.name} has {len(lines)} lines; line {line} is out of range")
    text = lines[line - 1].rstrip("\r\n")
    return {"line": line - 1, "character": index_to_utf16(text, (col or 1) - 1)}


def doc_params(path: Path, line: int | None = None, col: int | None = None) -> dict:
    params = {"textDocument": {"uri": path.as_uri()}}
    if line is not None:
        params["position"] = position(path, line, col)
    return params


def print_symbols(symbols, root: Path, path: Path | None, depth: int = 0) -> None:
    for sym in symbols:
        if "location" in sym:  # SymbolInformation from workspace/symbol
            loc = sym["location"]
            print(f"{display(uri_to_path(loc['uri']), root)}:{loc['range']['start']['line'] + 1}: {sym['name']}")
        else:  # DocumentSymbol tree from textDocument/documentSymbol
            print(f"{'  ' * depth}{sym['selectionRange']['start']['line'] + 1}: {sym['name']}")
            print_symbols(sym.get("children") or [], root, path, depth + 1)


def workspace_edits(result: dict) -> dict[Path, list[dict]]:
    edits: dict[Path, list[dict]] = {}
    for uri, changes in (result.get("changes") or {}).items():
        edits.setdefault(uri_to_path(uri), []).extend(changes)
    for change in result.get("documentChanges") or []:
        if "edits" in change:
            edits.setdefault(uri_to_path(change["textDocument"]["uri"]), []).extend(change["edits"])
    return edits


def apply_edits(lines: list[str], changes: list[dict]) -> list[str]:
    text = "".join(lines)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def offset(pos: dict) -> int:
        if pos["line"] >= len(lines):
            return len(text)
        return offsets[pos["line"]] + utf16_to_index(lines[pos["line"]], pos["character"])

    spans = sorted(((offset(e["range"]["start"]), offset(e["range"]["end"]), e["newText"]) for e in changes), reverse=True)
    for start, end, new in spans:
        text = text[:start] + new + text[end:]
    return text.splitlines(keepends=True)


# --- Workarounds for gaps in rumdl's link index (see references/upstream-bugs.md) -------------------------------------
# The server's index treats link-like text inside inline code as a link, and leaves reference definitions
# (`[id]: guide.md#anchor`) out entirely. The script drops the first and adds the second, so its answers cover every real
# link in the Markdown files. Each is reported on stderr so the reader knows the server alone would have differed.

REF_DEF = re.compile(r"^( {0,3})\[((?:[^\]\\]|\\.)+)\]:[ \t]*(<?)([^\s>]*)")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def code_spans(line: str) -> list[tuple[int, int]]:
    """Character ranges of the inline code spans on one line."""
    spans, i = [], 0
    while i < len(line):
        if line[i] != "`":
            i += 1
            continue
        n = len(line[i:]) - len(line[i:].lstrip("`"))
        j = i + n
        while j < len(line):
            k = line.find("`" * n, j)
            if k < 0:
                j = len(line)
                break
            m = len(line[k:]) - len(line[k:].lstrip("`"))
            if m == n:
                spans.append((i, k + n))
                break
            j = k + m
        i = spans[-1][1] if spans and spans[-1][0] == i else i + n
    return spans


def in_code_span(path: Path, line0: int, char16: int) -> bool:
    try:
        text = read_lines(path)[line0]
    except (OSError, IndexError):
        return False
    index = utf16_to_index(text, char16)
    return any(a <= index < b for a, b in code_spans(text))


def markdown_files(root: Path) -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z", "--", "*.md", "*.markdown"], cwd=root,
                             capture_output=True, text=True, check=True).stdout
        return [root / name for name in out.split("\0") if name]
    except (OSError, subprocess.CalledProcessError):
        skip = {".git", "node_modules", "target"}
        return [p for ext in ("*.md", "*.markdown") for p in root.rglob(ext) if not skip & set(p.parts)]


def prose_lines(root: Path):
    """(file, line0, text) for every line of the workspace's Markdown outside fenced code blocks."""
    for file in markdown_files(root):
        try:
            lines = read_lines(file)
        except OSError:
            continue
        fence = None
        for n, line in enumerate(lines):
            opener = FENCE.match(line)
            if fence:
                if opener and opener.group(1)[0] == fence[0] and len(opener.group(1)) >= len(fence):
                    fence = None
                continue
            if opener:
                fence = opener.group(1)
                continue
            yield file, n, line


def resolve_link(file: Path, dest: str):
    """(resolved path, fragment) of a relative link destination, or None for URLs and site-absolute paths."""
    if not dest or SCHEME.match(dest) or dest.startswith("/"):
        return None
    path_part, _, frag = dest.partition("#")
    return ((file.parent / unquote(path_part)).resolve() if path_part else file.resolve()), frag


def reference_definitions(root: Path, target: Path, anchor: str | None):
    """Reference definitions that point at `target` (and `#anchor`, when given): (file, line0, start, end) of the part
    to replace, where start..end covers the anchor when one is given and the destination path otherwise."""
    target = target.resolve()
    for file, n, line in prose_lines(root):
        m = REF_DEF.match(line)
        resolved = resolve_link(file, m.group(4)) if m else None
        if not resolved or resolved[0] != target:
            continue
        path_part, frag = m.group(4).partition("#")[0], resolved[1]
        if anchor is None:
            yield file, n, m.start(4), m.start(4) + len(path_part)
        elif frag.lower() == anchor.lower():
            start = m.start(4) + len(path_part) + 1
            yield file, n, start, start + len(frag)


def links_to(root: Path, target: Path):
    """(file, line0, start, fragment) for every inline link and reference definition in the workspace's Markdown that
    points at `target`, read from disk, outside code."""
    target = target.resolve()
    for file, n, line in prose_lines(root):
        spans = code_spans(line)
        found = [(m.start(), m.group(1)) for m in INLINE_LINK.finditer(line) if not any(a <= m.start() < b for a, b in spans)]
        ref = REF_DEF.match(line)
        if ref:
            found.append((ref.start(4), ref.group(4)))
        for start, dest in found:
            resolved = resolve_link(file, dest)
            if resolved and resolved[0] == target:
                yield file, n, start, resolved[1]


def heading_anchors(client: Client, path: Path, prefix: str = "", text: str | None = None) -> dict[int, tuple[str, str]]:
    """{1-based heading line: (anchor, heading text)} for `path`, from the server's own anchor completion. With `text`,
    the server first sees that content for `path` instead of what is on disk. The server caps the list at 50 entries."""
    if text is not None:
        client.notify("textDocument/didOpen", {"textDocument": {"uri": path.as_uri(), "languageId": "markdown",
                                                                "version": 1, "text": text}})
        time.sleep(0.5)  # the server re-indexes an opened document after a 100 ms debounce
    probe = path.parent / ".rumdl-lsp-anchor-probe.md"
    probe_text = f"[x]({path.name}#{prefix}"
    client.notify("textDocument/didOpen", {"textDocument": {"uri": probe.as_uri(), "languageId": "markdown", "version": 1,
                                                            "text": probe_text}})
    result = client.request("textDocument/completion", {"textDocument": {"uri": probe.as_uri()},
                                                        "position": {"line": 0, "character": len(probe_text)}})
    client.notify("textDocument/didClose", {"textDocument": {"uri": probe.as_uri()}})
    if text is not None:
        client.notify("textDocument/didClose", {"textDocument": {"uri": path.as_uri()}})
        time.sleep(0.5)  # let the server re-index the file from disk
    items = result.get("items", []) if isinstance(result, dict) else (result or [])
    anchors = {}
    for item in items:
        anchor = (item.get("detail") or "").lstrip("#") or item.get("insertText", "")
        try:
            anchors[int(item.get("sortText", ""))] = (anchor, item["label"])  # sortText is the heading's line number
        except ValueError:
            anchors[-len(anchors) - 1] = (anchor, item["label"])
    return anchors


def anchor_at(client: Client, path: Path, line: int, text: str | None = None) -> str | None:
    found = heading_anchors(client, path, text=text).get(line)
    if found is None:  # past the 50-entry cap: narrow by the heading's first letters
        heading = (text.splitlines()[line - 1] if text is not None else read_lines(path)[line - 1]).lstrip("# ").lower()
        found = heading_anchors(client, path, prefix=re.sub(r"[^\w-]", "", heading.split(" ")[0])[:3], text=text).get(line)
    return found[0] if found else None


def mentions(root: Path, target: Path, anchor: str | None) -> list[str]:
    """Lines in files that are not Markdown (nav config, HTML, code) naming `target` by its path or any trailing part of it
    with a folder (`guides/cache.md` for `docs/guides/cache.md`, so paths relative to a docs root match), or as a
    published-site URL (`guides/cache/`, `guides/cache.html`), followed by `#anchor` when one is given. The server indexes
    Markdown only; this covers the rest without matching the Markdown it already answered for."""
    rel = target.resolve().relative_to(root.resolve()).as_posix()
    parts = rel.split("/")
    tails = ["/".join(parts[i:]) for i in range(len(parts) - 1)] or [rel]
    forms = set()
    for tail in tails:
        stem = tail[: -len(target.suffix)] if target.suffix else tail
        forms |= {tail, stem + "/", stem + ".html"}
    patterns = sorted(f + "#" + anchor for f in forms) if anchor else sorted(forms)
    end = r"(?![\w-])" if anchor else r"(?![\w])"
    whole = [re.compile(r"(?<![\w.-])" + re.escape(p) + end) for p in patterns]

    def keep(text: str) -> bool:
        return any(w.search(text) for w in whole)

    try:
        cmd = ["git", "grep", "-n", "-I", "-F", "--untracked"] + [x for p in patterns for x in ("-e", p)]
        cmd += ["--", ".", ":(exclude)*.md", ":(exclude)*.markdown"]
        out = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if out.returncode in (0, 1):
            return [h for h in out.stdout.splitlines() if keep(h.split(":", 2)[-1])]
    except OSError:
        pass
    hits = []
    for file in root.rglob("*"):
        if not file.is_file() or file.suffix in (".md", ".markdown") or {".git", "node_modules"} & set(file.parts):
            continue
        try:
            for n, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
                if keep(line):
                    hits.append(f"{file.relative_to(root).as_posix()}:{n}:{line}")
        except (OSError, UnicodeDecodeError):
            continue
    return hits


INLINE_LINK = re.compile(r"!?\[(?:[^\]\\]|\\.)*\]\(([^)\s]*)")


def link_target_column(path: Path, line: int, col: int | None) -> int | None:
    """The 1-based column just inside the `(...)` of the inline link at or covering FILE:LINE:COL, so a position on a
    link's text still reaches the server, which answers only inside the target. None when no link covers the column."""
    text = read_lines(path)[line - 1]
    index = (col or 1) - 1
    for m in INLINE_LINK.finditer(text):
        if m.start() <= index <= m.end() and m.group(1):
            return m.start(1) + 2
    return None


def no_link_note(path: Path, line: int) -> None:
    text = read_lines(path)[line - 1]
    cols = [str(m.start(1) + 2) for m in INLINE_LINK.finditer(text) if m.group(1)]
    where = f"; its inline link targets start at column {', '.join(cols)}" if cols else "; it has no inline link"
    note(f"no link at {path.name}:{line}{where}")


def rename_check(root: Path, path: Path, new_map: dict[int, tuple[str, str]], old_anchors: list[str]) -> None:
    """After a rename is written: every Markdown link to the file, grouped by the heading it now reaches, any that reach
    no heading, and the files outside Markdown that still name an anchor the rename changed. Read from disk, so it sees
    exactly what was written."""
    name = display(path, root)
    by_anchor = {anchor.lower(): (line, heading) for line, (anchor, heading) in new_map.items()}
    groups: dict[str | None, list[str]] = {}
    for file, n, start, frag in links_to(root, path):
        groups.setdefault(frag.lower() or None, []).append(location(file, n, index_to_utf16(read_lines(file)[n], start), root))
    unverified = len(new_map) >= 50  # the server lists at most 50 anchors, so a link past them may look missing
    missing = [] if unverified else [f"{p}  #{f}" for f, places in groups.items() if f and f not in by_anchor for p in places]
    old = ", ".join("#" + a for a in dict.fromkeys(old_anchors))
    named = sorted({hit for a in dict.fromkeys(old_anchors) for hit in mentions(root, path, a)})
    # Totals first, so a reader who sees only part of the check can tell, and still knows what the whole of it found.
    total = sum(len(p) for p in groups.values())
    broken = "anchors not verified" if unverified else f"{len(missing)} to a missing anchor"
    print(f"Check, read back from the files as written: {total} Markdown link(s) to {name}, {broken}; "
          f"{len(named)} line(s) outside Markdown name {old}.")
    for frag, places in sorted(groups.items(), key=lambda g: by_anchor.get(g[0], (0,))[0] if g[0] else -1):
        if frag is None:
            print(f"  {name}: {len(places)} link(s) to the file itself")
        elif frag in by_anchor:
            line, heading = by_anchor[frag]
            print(f"  {name}#{frag}: {len(places)} link(s), reaching \"{heading}\" on line {line}")
        elif unverified:
            print(f"  {name}#{frag}: {len(places)} link(s), to a heading past the first 50")
        else:
            continue
        for place in places:
            print(f"    {place}")
    if unverified:
        print(f"  {name} has 50 or more headings, more than the server lists; run rumdl check to verify the anchors.")
    elif missing:
        print(f"  {len(missing)} Markdown link(s) point at a missing anchor in {name}; fix each:")
        for m in missing:
            print(f"    {m}")
    else:
        print(f"  No Markdown link points at a missing anchor in {name}.")
    if named:
        print(f"  Outside Markdown, these still name {old}; fix or report each:")
        for hit in named:
            print(f"    {hit}")
    else:
        print(f"  No file outside Markdown names {old}.")


def note(message: str) -> None:
    print(f"rumdl_lsp: {message}", file=sys.stderr)


def run(args, client: Client, root: Path) -> int:
    cmd = args.command
    if cmd == "outline":
        path, _, _ = parse_target(args.target)
        result = client.request("textDocument/documentSymbol", doc_params(path))
        print_symbols(result or [], root, path)
        return 0 if result else 1

    if cmd == "headings":
        result = client.request("workspace/symbol", {"query": args.query})
        print_symbols(sorted(result or [], key=lambda s: (s["location"]["uri"], s["location"]["range"]["start"]["line"])),
                      root, None)
        return 0 if result else 1

    if cmd == "anchors":
        # The completions a link to the file would get, asked from a scratch document beside it that is never written.
        path, _, _ = parse_target(args.target)
        anchors = heading_anchors(client, path, prefix=args.prefix or "")
        for line, (anchor, heading) in sorted(anchors.items()):
            print(f"{display(path, root)}:{line}: #{anchor}  {heading}")
        if len(anchors) >= 50:
            note("the server lists at most 50 anchors; pass a prefix to see the rest")
        return 0 if anchors else 1

    if cmd == "references":
        path, line, col = parse_target(args.target)
        params = doc_params(path, line or 1, col)
        if line is None:  # a position on no heading or link asks for every link to the file; line 1 may be the H1
            params["position"] = {"line": 10**6, "character": 0}
        params["context"] = {"includeDeclaration": False}
        found = {(uri_to_path(r["uri"]).resolve(), r["range"]["start"]["line"], r["range"]["start"]["character"])
                 for r in client.request("textDocument/references", params) or []}
        in_code = {f for f in found if in_code_span(*f)}
        found -= in_code
        added = set()
        if col is None:
            anchor = anchor_at(client, path, line) if line is not None else None
            for file, n, start, _ in reference_definitions(root, path, anchor):  # anchor None: any link to the file
                hit = (file.resolve(), n, index_to_utf16(read_lines(file)[n], start))
                if not any(f[:2] == hit[:2] for f in found):
                    added.add(hit)
        for file, n, char16 in sorted(found | added):
            print(location(file, n, char16, root))
        if in_code:
            note(f"left out {len(in_code)} match(es) inside inline code, which are not links")
        if added:
            note(f"added {len(added)} reference definition(s), which the server's index leaves out")
        return 0 if found or added else 1

    if cmd == "mentions":
        # The file may be gone (after a move or delete): checking for leftovers needs only its old path.
        target, _, frag = args.target.partition("#")
        bare = re.sub(r":\d+(:\d+)?$", "", target)
        if Path(bare).is_file():
            path, line, _ = parse_target(target)
        else:
            path, line = Path(bare).resolve(), None
        anchor = frag or (anchor_at(client, path, line) if line else None)
        hits = mentions(root, path, anchor)
        for hit in hits:
            print(hit)
        return 0 if hits else 1

    if cmd == "definition":
        path, line, col = parse_target(args.target, need_col=True)
        result = client.request("textDocument/definition", doc_params(path, line, col))
        retry = None if result else link_target_column(path, line, col)
        if retry and retry != col:
            result = client.request("textDocument/definition", doc_params(path, line, retry))
        if not result:
            no_link_note(path, line)
        if isinstance(result, dict):
            result = [result]
        for loc in result or []:
            uri = loc.get("uri") or loc.get("targetUri")
            rng = loc.get("range") or loc.get("targetSelectionRange")
            print(location(uri_to_path(uri), rng["start"]["line"], rng["start"]["character"], root))
        return 0 if result else 1

    if cmd == "hover":
        path, line, col = parse_target(args.target, need_col=True)
        result = client.request("textDocument/hover", doc_params(path, line, col))
        retry = None if result else link_target_column(path, line, col)
        if retry and retry != col:
            result = client.request("textDocument/hover", doc_params(path, line, retry))
        if not result:
            no_link_note(path, line)
            return 1
        contents = result["contents"]
        print(contents.get("value", contents) if isinstance(contents, dict) else contents)
        return 0

    if cmd == "rename":
        path, line, _ = parse_target(args.target)
        if line is None:
            raise LspError("give the heading's line, as FILE:LINE")
        params = doc_params(path, line, None)
        if not client.request("textDocument/prepareRename", params):
            note(f"{display(path, root)}:{line} is not a heading rumdl can rename")
            return 1
        old_map = heading_anchors(client, path)
        old_anchor = anchor_at(client, path, line)
        result = client.request("textDocument/rename", {**params, "newName": args.new_name})
        edits = {f.resolve(): c for f, c in workspace_edits(result or {}).items()}
        if not edits:
            note("the server refused the rename; it does so when the new text's anchor would collide with another heading in "
                 "the same file. Choose a different name, or rename the other heading first")
            return 1
        def partial_anchor(file: Path, e: dict) -> bool:
            # The server also rewrites the front of a longer anchor that starts with the old one (#setup in #setup-1).
            if file == path.resolve() and e["range"]["start"]["line"] == line - 1:  # the heading itself
                return False
            text = read_lines(file)[e["range"]["end"]["line"]]
            end = utf16_to_index(text, e["range"]["end"]["character"])
            return end < len(text) and (text[end].isalnum() or text[end] in "-_")

        skipped = partial = 0
        for file in list(edits):
            kept = []
            for e in edits[file]:
                if in_code_span(file, e["range"]["start"]["line"], e["range"]["start"]["character"]):
                    skipped += 1
                elif partial_anchor(file, e):
                    partial += 1
                else:
                    kept.append(e)
            edits[file] = kept
        renamed_text = "".join(apply_edits(read_lines(path), edits.get(path.resolve(), [])))
        new_map = heading_anchors(client, path, text=renamed_text)
        new_anchor = new_map.get(line, (None,))[0] or anchor_at(client, path, line, text=renamed_text)

        def add_edit(file: Path, n: int, start: int, end: int, new_text: str) -> bool:
            text = read_lines(file)[n]
            rng = {"start": {"line": n, "character": index_to_utf16(text, start)},
                   "end": {"line": n, "character": index_to_utf16(text, end)}}
            if any(e["range"]["start"] == rng["start"] for e in edits.get(file, [])):
                return False
            edits.setdefault(file, []).append({"range": rng, "newText": new_text})
            return True

        added = 0
        if old_anchor and new_anchor and old_anchor != new_anchor:
            for file, n, start, end in reference_definitions(root, path, old_anchor):
                added += add_edit(file.resolve(), n, start, end, new_anchor)
        elif old_anchor is None or new_anchor is None:
            note("could not read the heading's anchors, so reference definitions were not checked")

        # Renaming one of two same-named headings moves the other's numbered anchor (#setup-1 becomes #setup). The
        # server leaves links to the moved anchor alone; follow them, so each link keeps pointing at the same heading.
        shifted = 0
        for other, (before, _) in old_map.items():
            after = new_map.get(other, (None,))[0]
            if other == line or after is None or after == before:
                continue
            refs = client.request("textDocument/references", {**doc_params(path, other, None),
                                                              "context": {"includeDeclaration": False}}) or []
            for r in refs:
                file, n = uri_to_path(r["uri"]).resolve(), r["range"]["start"]["line"]
                text = read_lines(file)[n]
                pattern = re.compile(re.escape("#" + before) + r"(?=[)\s\"'>]|$)", re.IGNORECASE)
                m = pattern.search(text, utf16_to_index(text, r["range"]["start"]["character"]))
                if m and not in_code_span(file, n, index_to_utf16(text, m.start())):
                    shifted += add_edit(file, n, m.start() + 1, m.end(), after)
            for file, n, start, end in reference_definitions(root, path, before):
                shifted += add_edit(file.resolve(), n, start, end, after)
        if len(old_map) >= 50:
            note("the file has 50 or more headings; anchors past the first 50 were not checked for shifts")
        edits = {f: c for f, c in edits.items() if c}
        for file, changes in sorted(edits.items()):
            old = read_lines(file)
            new = apply_edits(old, changes)
            for n in sorted({c["range"]["start"]["line"] for c in changes}):
                print(f"{display(file, root)}:{n + 1}:")
                print(f"  - {old[n].rstrip()}")
                print(f"  + {new[n].rstrip()}")
            if args.apply:
                with open(file, "w", encoding="utf-8", newline="") as f:
                    f.write("".join(new))
        if skipped:
            note(f"left out {skipped} edit(s) inside inline code, which are not links")
        if partial:
            note(f"left out {partial} edit(s) to a longer anchor that only starts with the old one")
        if added:
            note(f"added {added} edit(s) to reference definitions, which the server's index leaves out")
        if shifted:
            note(f"added {shifted} edit(s) for links to a same-named heading whose numbered anchor the rename moved")
        count = sum(len(c) for c in edits.values())
        verb = "Applied" if args.apply else "Would apply"
        print(f"{verb} {count} edit(s) in {len(edits)} file(s)." + ("" if args.apply else " Add --apply to write them."))
        if args.apply:
            moved = [old_anchor] + [b for o, (b, _) in old_map.items() if o != line and new_map.get(o, (b,))[0] != b]
            rename_check(root, path, new_map, [a for a in moved if a])
        return 0
    raise LspError(f"unknown command {cmd}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 2)[2])
    parser.add_argument("--root", help="workspace root (default: the enclosing git repository, else the current directory)")
    parser.add_argument("--config", help="rumdl config file to use instead of per-directory discovery")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("outline", help="heading tree of one file").add_argument("target", metavar="FILE")
    sub.add_parser("headings", help="search headings across the workspace").add_argument("query")
    p = sub.add_parser("anchors", help="anchors that a link to FILE can use")
    p.add_argument("target", metavar="FILE")
    p.add_argument("prefix", nargs="?", default="")
    sub.add_parser("references", help="links to a heading (FILE:LINE), a link's target (FILE:LINE:COL), or a file (FILE)"
                   ).add_argument("target", metavar="FILE[:LINE[:COL]]")
    sub.add_parser("mentions", help="non-Markdown files that name FILE, or the heading at FILE:LINE, or FILE#anchor"
                   ).add_argument("target", metavar="FILE[:LINE]|FILE#ANCHOR")
    sub.add_parser("definition", help="where the link at FILE:LINE:COL goes").add_argument("target", metavar="FILE:LINE:COL")
    sub.add_parser("hover", help="preview of the link target at FILE:LINE:COL").add_argument("target", metavar="FILE:LINE:COL")
    p = sub.add_parser("rename", help="rename the heading at FILE:LINE and update every link to it")
    p.add_argument("target", metavar="FILE:LINE")
    p.add_argument("new_name", metavar="NEW_TEXT")
    p.add_argument("--apply", action="store_true", help="write the edits (default: preview only)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else find_root(Path.cwd().resolve())
    client = None
    try:
        client = Client(root, args.config)
        client.start(root)
        return run(args, client, root)
    except LspError as e:
        print(f"rumdl_lsp: {e}", file=sys.stderr)
        return 2
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    sys.exit(main())
