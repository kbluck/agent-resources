# IDE Spelling Checks

How to get spelling findings from an IDE through its MCP server, and how to set the IDE up when the findings do not come through.
Each IDE section was tested against the version it names; check the tool list and settings of the version in front of you, since
both change between releases.

## Contents

- [JetBrains IDEs](#jetbrains-ides)
- [VS Code](#vs-code)

## JetBrains IDEs

Tested with PyCharm 2026.2 and its built-in MCP server. Other IntelliJ-based IDEs (IntelliJ IDEA, WebStorm, Rider, RustRover, CLion)
share the same spelling inspection and MCP tools.

### Tools

| Tool | Call |
| :--- | :--- |
| `get_file_problems` | One file, with `errorsOnly` set to `false` |
| `lint_files` | Several files at once; `min_severity` accepts only `warning` or `error`, and defaults to `warning` |

Both take paths relative to the project root. When the IDE has several projects open, or not the one you are working in, pass
`projectPath`; if the project is not open at all, ask the user to open it. Spelling findings come back as weak warnings with the
description `Typo: In word '...'`.

Files written outside the IDE (from a shell) can take a while to reach the IDE, and until then the tools may report them as empty or
missing. Files written through the IDE's own tools (`create_new_file`, `apply_patch`) are seen at once.

### Inspection Settings

The tools leave out every finding below Weak warning, and the Spelling inspection often sits lower, at Typo or Style suggestion. The
inspection is Settings, Editor, Inspections, Proofreading, Spelling, with the ID `SpellCheckingInspection`. Its options decide which
text is checked:

| Setting | Effect on what the tools return |
| :------ | :------------------------------ |
| Severity below Weak warning | No spelling findings at all |
| Weak warning, Process comments on | Misspellings in code comments |
| Weak warning, Process code on as well | Misspellings in Markdown text as well; with Process code off, Markdown text is not checked |
| Process literals off | No findings in docstrings or other strings |

Read the settings from the project's inspection profile, `.idea/inspectionProfiles/Project_Default.xml`, in the
`SpellCheckingInspection` entry. If the severity is too low or a kind of text you edited is switched off, suggest the change to the
user rather than making it, since the profile is shared project configuration.

### Markdown Without Noise in Code

Process code also spell-checks identifiers, which floods code files with findings for names such as `utcnow`. To check Markdown text
without that noise, suggest giving the inspection a scope of its own for Markdown files:

1. Under Settings, Appearance & Behavior, Scopes, add a scope named `Markdown` with the pattern `file:*.md||file:*/*.md`. The
   `*/*.md` part matches files in any folder but not at the project root, so `*.md` is needed too. The scope is saved in
   `.idea/scopes/Markdown.xml`.
2. On the Spelling inspection, add the `Markdown` scope above Everything else, at Weak warning with Process code on. Leave Process
   code off for Everything else.

In the profile, the result looks like this. The `<scope>` element holds its own options, and the options after it apply everywhere
else:

```xml
<inspection_tool class="SpellCheckingInspection" enabled="true" level="WEAK WARNING" enabled_by_default="true" editorAttributes="TYPO">
  <scope name="Markdown" level="WEAK WARNING" enabled="true" editorAttributes="TYPO">
    <option name="processCode" value="true" />
    <option name="processLiterals" value="true" />
    <option name="processComments" value="true" />
  </scope>
  <option name="processCode" value="false" />
  <option name="processLiterals" value="false" />
  <option name="processComments" value="true" />
</inspection_tool>
```

### Project Dictionary

Words the team has accepted are in `.idea/dictionaries/project.xml`, one `<w>` element each:

```xml
<component name="ProjectDictionaryState">
  <dictionary name="project">
    <words>
      <w>Databento</w>
    </words>
  </dictionary>
</component>
```

Do not "correct" a word listed there. To add an exception the user has agreed to, add a `<w>` entry in alphabetical order, or let
the user apply the "Save to project-level dictionary" quick-fix on the flagged word.

### Variety Checks

The Spelling inspection's dictionary accepts both American and British spellings, so it passes `colour` and `color` alike. The
variety check comes from the Style inspection of the Natural Languages plugin (`GrazieStyle`, under Proofreading, Style), which
checks text against the English variety chosen under Settings, Editor, Natural Languages. With American English chosen and Style at
Weak warning, the tools flagged British spellings in Markdown paragraphs and code comments alike:

| Flagged | Description returned |
| :------ | :------------------- |
| behaviour, colour | British roots ending with '-our' usually have '-or' in American English |
| organise | American English uses '-iz-' in suffixes |
| analyser | American English uses '-yz-' in suffixes |
| centre, theatre | American English uses '-er' instead of '-re' |
| travelled, cancelled | American English does not double '-l-' in suffixes |
| grey, licence, defence | American English uses 'gray', 'license', 'defense' |
| paediatric | American English uses '-e-' instead of '-ae-' in some words of Greek and Latin origin |

`catalogue` was not flagged, since American English accepts it too. Like Spelling, Style is often set to Style suggestion, below
what the tools return; suggest raising it to Weak warning. Results also took longer than the spelling findings to appear in one
test, so recheck a file whose first result looks too clean.

Style does not check text inside Markdown table cells: `behaviour` in a paragraph was flagged, and the same word in a table cell of
another file was not. The cause is in the plugin's source: its Markdown text extractor (`MarkdownTextExtractor` in
`plugins/grazie/markdown` of `JetBrains/intellij-community`) hands only paragraphs and heading text to the grammar and style checks,
and a table cell is neither. Text in list items and blockquotes is parsed as paragraphs, so it is checked. Check table cells
yourself, for instance with the marker patterns in SKILL.md.

When the IDE's language is the other variety from the project's, these findings are wrong for the project. Keep the words and
suggest the user set the IDE's English variety to the project's. American English is the variety tested here; British English should
flag American spellings the same way, but check that before relying on it.

### Limits

Spelling missed `teh` in testing. A clean result means no flagged words, not perfect spelling.

## VS Code

Claude Code's IDE integration offers `getDiagnostics` for a file. VS Code has no spell checker of its own: spelling findings come
only from an installed extension, most often Code Spell Checker (cspell), which reports them as "Unknown word" diagnostics. Its
language and accepted words come from `cspell.json` or from `cSpell.language` and `cSpell.words` in `.vscode/settings.json`. Not yet
tested here.
