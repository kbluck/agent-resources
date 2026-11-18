---
name: english-spelling
description: >
  Read this before writing or editing English prose in a project: a README, docs/ page, CONTRIBUTING, or other Markdown document, or
  comments and docstrings in source code, even if no one mentions spelling. It settles whether the project spells in American or
  British English (color or colour, analyze or analyse, canceled or cancelled, Oxford -ize) from what the user or project says,
  spell-checker settings (cspell, typos, codespell, EditorConfig), the spelling already in use, and the locale. It keeps new text in
  that variety, brings stray spellings into line, and, when an IDE is connected through MCP (JetBrains or VS Code), checks the IDE's
  spelling inspections on edited files and suggests dictionary exceptions for correct words it flags. Also use it when the user asks
  which English a project uses, wants US and UK spelling converted or made consistent, or an IDE or spell checker flags a word. Not
  for translation, grammar, renaming identifiers or UI strings, or Markdown lint (use the formatting skill).
license: MIT
metadata:
  author: Kevin J Bluck <kbluck@users.noreply.github.com>
  copyright: Copyright © 2026 Kevin J. Bluck
  repository: https://github.com/kbluck/agent-resources
  url: https://github.com/kbluck/agent-resources/tree/main/plugins/markdown/skills/english-spelling
  version: 1.0.0
---

# English Spelling

A project's prose should use one variety of English spelling throughout. A reader notices `color` in one paragraph and `colour` in
the next, and the mix makes a document look unedited even when every word is spelled correctly. American English (en-US) and British
English (en-GB) differ in a few hundred common words, nearly all by regular patterns, so the work is mostly deciding which variety
the project uses and then applying the patterns consistently.

Use this skill for prose a person reads: Markdown documents, and comments and docstrings in source code. Decide the variety once per
project, before you write, and keep to it.

## Deciding the Variety

Work down this list and stop at the first signal that decides it. Signals higher in the list describe the project; lower ones
describe the person or machine that happens to be working on it.

| Order | Signal | Where to look |
| :---- | :----- | :------------ |
| 1 | Someone said so | The user's request; `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, a style guide, or your memory of the user's preferences |
| 2 | Spell-checker or editor settings committed to the project | See [Settings that name a variety](#settings-that-name-a-variety) |
| 3 | The spelling the project already uses | Its Markdown, docs, and comments; see [Sampling existing prose](#sampling-existing-prose) |
| 4 | Who the project is for | The organization's country, a `.co.uk` or `.com.au` homepage, dates written day-first, prices in pounds |
| 5 | The developer's settings | IDE natural-language settings, then the operating system locale; see [Local settings](#local-settings) |
| 6 | Nothing decides it | Use American English, the variety of most software documentation and of nearly every API name |

A few judgments the order does not settle:

- **Contributing to someone else's project.** Their variety wins over the user's own. A British developer sending a patch to an
  American project writes `color` in the docs.
- **Established project against local settings.** Prose already written in one variety outweighs an en-GB laptop. Local settings
  decide only for a new project, or when existing prose is too thin or too mixed to call.
- **A clear majority.** Call it from the existing prose when one variety leads about three to one over a dozen or more marker words.
  A closer split is a mixed project: decide from signals 4 to 6, then offer to standardize (see
  [Standardizing existing text](#standardizing-existing-text)).
- **Oxford spelling.** British English written with `-ize` (`organize`, `recognize`) but every other British form (`colour`,
  `centre`, `analyse`) is a consistent style called Oxford spelling (en-GB-oxendict), not a mix. Keep its `-ize`. For the same
  reason, `-ize` alone is weak evidence of American spelling; `-our`, `-re`, `-yse`, and doubled `-ll-` are the telling markers.

When you inferred the variety rather than being told, say which one you chose and why in your reply, in one sentence, so the user
can correct it. Offer to record the choice where the next writer will find it: a line in `AGENTS.md` or `CONTRIBUTING.md`, or a
spell-checker setting. A recorded choice ends the guessing for every later session.

### Settings That Name a Variety

| File | Setting | Example |
| :--- | :------ | :------ |
| `cspell.json`, `.cspell.json`, `cspell.config.yaml` | `language` | `"language": "en-GB"` |
| `.vscode/settings.json` | `cSpell.language` | `"cSpell.language": "en-GB"` |
| `_typos.toml`, `typos.toml`, `.typos.toml` | `locale` under `[default]` | `locale = "en-gb"`; `en` alone accepts both |
| `.editorconfig` | `spelling_language` | `spelling_language = en-US` |
| `.pre-commit-config.yaml`, `setup.cfg`, `pyproject.toml` | codespell `builtin` | `en-GB_to_en-US` means the project is American |
| `.vale.ini` | `BasedOnStyles` | `Google` or `Microsoft`: both house style guides use American spelling |
| LaTeX sources | `babel` option | `british` or `UKenglish`; `american` or `USenglish` |
| HTML pages and site generator config | `lang`, `languageCode`, `defaultLocale` | `en-GB`; a bare `en` says nothing |

### Sampling Existing Prose

Count marker words in the prose, using `git grep` because it runs the same way in every shell. These patterns leave out `-ize` and
`-ise` on purpose (see Oxford spelling, above):

```bash
git grep -I -i -c -w -E '((colour|behaviour|favour|neighbour)[a-z]*|(honour|labour)(s|ed|ing|able)?|(centre|metre|litre|fibre)s?|analys(e|ed|es|ing)|catalogues?|defence|offence|licence|grey|(travell|cancell|labell|modell)(ed|ing|er|ers))' -- '*.md' '*.rst' '*.txt'
git grep -I -i -c -w -E '((color|behavior|favor|neighbor)[a-z]*|(honor|labor)(s|ed|ing|able)?|(center|fiber)(s|ed)?|analyz(e|ed|es|ing)|catalogs?|defense|offense|gray|(travel|cancel|label|model)(ed|ing|er|ers))' -- '*.md' '*.rst' '*.txt'
```

The first line counts lines with British markers per file, the second American ones; swap `-c` for `-o` to list the words. Add the
project's source extensions (`'*.py'`, `'*.ts'`) to sample comments, then look at the hits before trusting the totals: code blocks,
CSS `color`, API names, and vendored or generated files count toward American without saying anything about the prose. Leave them
out of the tally.

### Local Settings

These describe the developer, not the project (signal 5 above).

| Source | How to read it |
| :----- | :------------- |
| JetBrains IDEs | Settings, Editor, Natural Languages lists the languages the IDE checks, such as English (GB); it is stored per IDE, not in the project, and plain English is no signal |
| VS Code user settings | `cSpell.language` in the user `settings.json` |
| macOS | `defaults read -g AppleLocale`, such as `en_GB` |
| Linux, BSD, and other Unix | `LC_ALL`, `LC_MESSAGES`, or `LANG`, such as `en_AU.UTF-8` |
| Windows | `Get-Culture` in PowerShell, such as `en-GB` |

Canadian, Australian, New Zealand, Irish, Indian, and South African English all spell close to British, with local differences
(Canadian English uses `-ize`, `-our`, and `-re` together, and often American `tire` and `curb`). Map them to British unless the
project names the specific variety.

## Writing in the Variety

Most differences follow a handful of patterns. Learn the patterns and the exceptions that both varieties share, and you will rarely
need the word lists.

| Pattern | American | British | Same in both, so never change |
| :------ | :------- | :------ | :---------------------------- |
| `-or` and `-our` | color, behavior, honorable | colour, behaviour, honourable | error, mirror, author, actor; humorous, honorary (British drops the `u` before `-ous`, `-ary`, `-ation`) |
| `-er` and `-re` | center, fiber, theater | centre, fibre, theatre | acre, massacre, ogre; meter as a measuring device (thermometer) |
| `-ize` and `-ise` | organize, recognize | organise, recognise (organize in Oxford spelling) | advertise, advise, comprise, compromise, exercise, revise, supervise; size, seize, capsize |
| `-yze` and `-yse` | analyze, paralyze | analyse, paralyse (in Oxford spelling too) | |
| Doubled `l` before a vowel suffix | canceled, labeling, modeled, traveler | cancelled, labelling, modelled, traveller | compelled, patrolling, rebellion (stress on the last syllable) |
| Single `l` in the root | fulfill, enroll, skillful, installment | fulfil, enrol, skilful, instalment | |
| `-og` and `-ogue` | catalog, analog | catalogue, analogue | dialogue (conversation), dialog box, monologue, prologue, epilogue |
| `ae` and `oe` | anemia, pediatric, maneuver | anaemia, paediatric, manoeuvre | encyclopedia and medieval are now usual in both |
| `-ense` and `-ence` nouns | defense, offense, license (noun) | defence, offence, licence (noun) | difference, presence, reference; license as a verb in British too |
| Noun `-ice`, verb `-ise` | practice (noun and verb) | practice (noun), practise (verb) | advice and advise differ in both |
| Silent `e` before a suffix | aging, judgment, likable | ageing, judgement, likeable | judgment in British legal writing |
| Single words | gray, aluminum, check (bank), tire, program | grey, aluminium, cheque, tyre, programme (but a computer program) | disk for computer storage |

Read [references/spelling-rules.md](references/spelling-rules.md) for the full word lists under each pattern and for the irregular
words. Read it before converting a document or standardizing a project, when a word fits no pattern above, and before "correcting" a
word you are unsure of, since many words are spelled the same in both varieties.

## Text Never to Respell

Spelling applies to prose only. Change any of the following and you break code, links, or meaning:

- **Code.** Identifiers, keywords, API, function, and parameter names, CSS properties (`color`, `text-align: center`), config keys,
  CLI flags, and environment variables, whether in a source file, inline code, or a fenced block. A comment that names a code symbol
  keeps the symbol's spelling: "Set `colour_map` to the color scheme" in an American project.
- **String literals in code.** User-facing messages are behavior and may be translation keys or asserted by tests. Change them only
  when the user asks.
- **Names.** Proper nouns, product and organization names, and titles of works: Centers for Disease Control, the Labour Party,
  Visual Studio Code's Color Theme, the MIT License, Royal Society of Chemistry.
- **Quotations and citations.** Quoted text keeps its original spelling.
- **Addresses and paths.** URLs, file and directory names (`LICENSE`), and anchors. A heading's anchor comes from its text, so
  respelling a heading breaks every link to it; rename it with the `rumdl-language-server` skill, which updates the links too.
- **Text the project does not own.** Vendored and generated files, license texts and legal notices, test fixtures and snapshots, and
  the release notes of past versions.

## Checking with the IDE

An IDE's spelling inspection catches misspellings that pattern knowledge misses, and it checks the exact files you changed. When an
MCP server connects you to the user's IDE, ask it for the inspection results on every file whose prose you wrote or edited, after
you finish editing and before you report back. Look at the tool list for such a server before assuming there is none.

| IDE connection | Tool to call |
| :------------- | :----------- |
| JetBrains MCP server (built into IntelliJ-based IDEs) | `get_file_problems` with `errorsOnly` set to `false`, or `lint_files` |
| Claude Code's IDE integration (VS Code, JetBrains) | `getDiagnostics` for the file |
| Another IDE MCP server | Whatever tool it offers for a file's problems, inspections, or diagnostics |

Read [references/ide-spelling.md](references/ide-spelling.md) for the IDE in front of you before you rely on its results. An IDE's
inspection settings often keep spelling findings below what its MCP tools return, or leave Markdown text unchecked, so an empty
result may mean the check never ran. The reference says how to tell, which settings to suggest, and where the IDE keeps its project
dictionary.

The IDE check does not replace your own. Its spelling dictionary accepts both varieties; JetBrains IDEs flag the wrong variety only
through their style inspections, and only for the variety the IDE is set to, which may not be the project's. A clean result means no
flagged words, not perfect spelling. When the IDE cannot report spelling for the files you edited, say so in your reply rather than
calling them clean, and run the project's own command-line spell checker (cspell, typos, codespell) on them if it configures one.

Evaluate each flagged word, from the IDE or a spell checker, on its own. The IDE's dictionary is not always right, and it may even
be set to the other variety:

| The flag is | Action |
| :---------- | :----- |
| A real misspelling | Fix it |
| An off-variety spelling | Fix it to the project's variety |
| A project-variety spelling flagged because the IDE checks the other variety | Keep the word. Suggest the user set the IDE's language to the project's variety (see [Local settings](#local-settings)), which clears every such flag at once |
| A correct word the dictionary lacks: a name, product, acronym, or technical term | Keep the word. Suggest adding it as an exception (see below) |
| A code symbol written as plain prose | Put it in inline code, `like_this`; most spell checkers skip code spans |
| Deliberate text: a quotation, a title, a name with its own spelling | Keep it as written. Suggest an exception if the word recurs |

Suggest exceptions rather than adding them yourself, since they change project configuration that other contributors share. Name
each word and where it would go, then add it if the user agrees:

| Checker | Where exceptions go |
| :------ | :------------------ |
| JetBrains IDEs | A `<w>word</w>` entry in the project dictionary, `.idea/dictionaries/project.xml` |
| cspell, including VS Code's Code Spell Checker | `words` in `cspell.json`, or `cSpell.words` in `.vscode/settings.json` |
| typos | `[default.extend-words]` in `_typos.toml`, mapping the word to itself |
| codespell | `ignore-words-list` in its configuration |

Prefer the project-level dictionary over a personal one, so the exception reaches everyone who opens the project.

## Standardizing Existing Text

Bring existing text into the project's variety. A mixed project keeps getting more mixed, because each writer copies whatever
spelling is nearest.

| Situation | Action |
| :-------- | :----- |
| Text you write or rewrite | Always in the project's variety |
| Other prose in a file you are editing | Fix the off-variety spellings in that file too, and say so in your reply; the change is small and easy to review |
| Files you are not otherwise touching | Report what you found, such as "12 British spellings in 5 files under `docs/`", and offer a project-wide pass |
| The user asks for a project-wide pass | Do it as its own commit, apart from any other change, so it is easy to review and revert |
| A hotfix, or a diff that must stay minimal | Leave other text alone and mention it instead |

For a project-wide pass:

1. Find candidates with the patterns from [Sampling existing prose](#sampling-existing-prose), extended from the word lists in the
   reference, limited to prose files and comments.
2. Review every hit in context and change it by hand or with a targeted edit. A blind search-and-replace rewrites code, URLs, names,
   and quotations (see [Text never to respell](#text-never-to-respell)).
3. Rename headings with the `rumdl-language-server` skill so links follow.
4. Run the project's linters and tests, and the `formatting` skill on changed Markdown, since a respelled word can change line
   lengths and table widths.
5. Offer to record the variety, as in [Deciding the variety](#deciding-the-variety), so the project stays consistent.

## Done Criteria

- You know which variety the project uses and why, and said so in your reply if you inferred it.
- New and rewritten prose uses that variety, and words the varieties share are unchanged (no `advertize`, no `errour`).
- No code, string literal, name, quotation, URL, path, or text the project does not own was respelled.
- Off-variety spellings in the files you edited are fixed, and any elsewhere are reported with an offer to standardize them.
- If an IDE was reachable through MCP, every spelling flag in the files you edited is fixed or explained, with any exceptions
  suggested to the user.
