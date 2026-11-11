---
name: language-server
description: >
  Answer questions about Python code by meaning, not text, and change it safely, with Pyrefly's language server (the LSP tool, or
  the bundled script). Use it before grep, sed, or reading file after file whenever you need where a name is defined, what type a
  variable has, every usage of a function, method, class, or attribute, every caller of a function, the subclasses or overrides of
  a class or method, what a module defines, or whether something is still used before deleting it. It tells same-named methods on
  different classes apart and follows imports, aliases, and inferred types. Use it to rename a symbol project-wide, move a module
  and rewrite its imports, or extract, inline, or move code, and before changing a signature or base class, even if the user never
  mentions an LSP, Pyrefly, or "find references". Not for running pyrefly check or fixing type errors (use type-checking), adding
  annotations (use type-coverage), or searching strings, comments, docs, and non-Python files.
compatibility: >
  Uses the harness's LSP tool when Pyrefly's server is registered with it. Otherwise runs the bundled scripts/pyrefly_lsp.py, which
  needs Python 3.8+ and Pyrefly (the project's own, on PATH, or through uvx or pipx). Written against Pyrefly 1.4.
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/pyrefly/skills/language-server
  version: 1.0.0
---

# Pyrefly Language Server

Python names are resolved, not spelled: `customer.greeting()` calls `Customer.greeting` because `customer` is a `Customer`, while
`report.greeting()` calls something unrelated. Imports rename things (`import load as fetch`), modules are reached three ways, and
subclasses override without naming their base. Pyrefly's language server type-checks the whole project and knows which `greeting`
each call is; grep knows only the letters. Ask the server first whenever the question is about Python names, before reading files or
grepping, and use it again to check a change.

Grep is still right for what is not a resolved name: strings (`mock.patch("a.b")`, `getattr`), comments, docs, `__all__`, and
non-Python files. After a rename or move the script lists those lines for you.

## Reaching the Server

- **The LSP tool** (Claude Code, Copilot CLI, through the `pyrefly` plugin): quick, read-only, takes a file and a 1-based line and
  character on the name. Type errors for each edited `.py` file arrive by themselves.
- **The bundled script**, for any harness and for everything that edits: `python3 <skill-dir>/scripts/pyrefly_lsp.py COMMAND ...`,
  run inside the project. It waits for the index, prints `FILE:LINE:COL: source line`, and previews edits as a diff until you add
  `--apply`. A position is `FILE:LINE:NAME` (first `NAME` on that line), `FILE:LINE:COL`, or `FILE:LINE` on a `def`/`class` line.

> [!IMPORTANT]
> A freshly started server answers from open files only until its background index is done, and gives no signal. Repeat an LSP tool
> `findReferences`, `incomingCalls`, or `workspaceSymbol` before acting on it; trust it when two calls agree. The script waits.

| Question | Script | LSP tool |
| :------- | :----- | :------- |
| Type, signature, docstring | `hover POS` | `hover` |
| Definition (of the name, of its type) | `definition POS`, `type-definition POS` | `goToDefinition` |
| Every use, project-wide (includes overrides) | `references POS` | `findReferences` |
| Every call, with the enclosing function | `callers POS` | `prepareCallHierarchy` + `incomingCalls` |
| Overrides of a method | `implementations POS` | `goToImplementation` |
| All subclasses or base classes | `subtypes POS`, `supertypes POS` | None |
| What a file defines | `outline FILE` | `documentSymbol` |
| Find a symbol by name | `symbols QUERY` | `workspaceSymbol` |
| Inferred types of unannotated code | `hints FILE[:L1-L2]` | None |
| Rename a symbol everywhere | `rename POS NEW [--apply]` | None |
| Move a module, rewriting imports | `move OLD.py NEW.py [--apply]` | None |
| Refactors and quick fixes at a spot | `actions POS` or `FILE:L1-L2`, then `actions ... N [--apply]` | None |

Exit status 1 means nothing was found, which is an answer: no callers, no subclasses.

## Workflows

**Before changing a signature or base class:** `callers` for every call site, `implementations` and `subtypes` for overrides that
must change in step. Then edit, and run `pyrefly check` (type-checking skill) and the tests.

**Renaming:** preview `rename`, read the diff and the "Still naming" list after it (strings, docs, `__all__`, untyped receivers, and
unrelated symbols that share the name), then `--apply` and fix the leftovers that refer to the renamed symbol. Never follow with a
search-and-replace: it renames the unrelated symbols the server correctly skipped.

**Moving a module:** preview `move`, then `--apply` (uses `git mv` when tracked). The list after the diff names what the server does
not rewrite: `from . import mod`, `from pkg import mod`, dotted uses after `import pkg.mod`, strings, docs, and the moved file's own
relative imports when it changes folder. Package folders cannot be moved; `git mv` them and fix what `pyrefly check` reports.

**Refactoring:** `actions` offers extract variable or helper, introduce parameter, inline variable, move to a new file, extract
superclass, convert module to package, and insert import, depending on the spot. Results are unchecked and names are placeholders
(`extracted_function`): preview, rename, and `pyrefly check` after applying. Fix flagged code instead of taking an ignore comment.

**Diagnostics after an edit** cover only the touched file; `pyrefly check` is the gate before finishing.

## Limits

- Cross-file answers need a project marker (`pyrefly.toml`, `pyproject.toml`, `setup.py`, `mypy.ini`, or `pyrightconfig.json`) and
  cover only files the config includes. Without a Pyrefly config the server indexes just 2,000 files, silently; the script lifts
  that, the LSP tool does not.
- Strings, `getattr`, `__all__`, quoted annotations, and receivers with no known type are not references.
- `incomingCalls` misses calls through `import f as g`; the script's `callers` follows aliases. `outgoingCalls` misses method and
  nested calls: read the body instead.

Setup, editors, settings, and troubleshooting: [references/setup.md](references/setup.md).
