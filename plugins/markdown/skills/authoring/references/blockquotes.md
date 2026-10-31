# Blockquote Rewrite Examples

Rule: warnings, cautions, important caveats, tips, core principles, and sources go in blockquotes, not mixed into ordinary lists.

## Every Kind

A warning, for a mistake that causes data loss or an outage:

> [!WARNING] Do not edit the rendered config files on the remote host. The next automation run overwrites them.

A caution, for an action that cannot be undone:

> [!CAUTION] `docker compose down -v` deletes the named volumes, including the database. There is no undo.

An important note, for a limitation that is easy to miss:

> [!IMPORTANT] The init container exits after initialization. This is expected, not an error.

A note, for background:

> [!NOTE] The playbook renders the config from templates in `roles/app/templates/`.

A tip, for a shortcut:

> [!TIP] To restart a single service temporarily, run `docker compose up -d <service>`. There is no need to rerun the whole
> playbook.

A core principle, as a bare blockquote:

> The core principle: automation converges the state; a manual change is only a temporary workaround, not a fix.

A KB article source header:

> Source: [Official deployment guide](https://example.com/deploy)

In a real document these sit next to the steps they qualify, separated by ordinary text rather than stacked one after another.

## Before and After

Before, caveats mixed into a list:

```markdown
Notes:

1. Do not edit the remote config files directly, they get overwritten.
2. The init container exiting is normal.
3. For a temporary restart use docker compose up -d <service>.
```

After, with the one critical limitation as a blockquote and the remaining caveats as a table:

> [!WARNING] Do not edit the rendered config files on the remote host. The next automation run overwrites them.

| Behavior | Explanation |
| :------- | :---------- |
| Init container exits on its own | Expected; it exits once initialization finishes |
| Restarting a single service | `docker compose up -d <service>`; no need to rerun the whole flow |

The heading "Notes" is also gone: the warning sits next to the step it applies to, and the table goes under a descriptive heading
such as "Container Behavior".

## Fallback When Alerts Do Not Render

If the repository already uses bold-label callouts, or the target renderer shows `[!WARNING]` as literal text, use this form
instead:

```markdown
> **Warning:** Do not edit the rendered config files on the remote host. The next automation run overwrites them.
```
