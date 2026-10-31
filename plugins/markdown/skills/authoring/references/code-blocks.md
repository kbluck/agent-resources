# Code Block Rewrite Examples

Rule: runnable commands, multi-line config, and sample output go in fenced code blocks, always with a language tag. Paths, variable
names, and identifiers inside prose or tables go in inline code.

## Merge Consecutive Commands into One Block

Before, several separate blocks:

````markdown
```bash
ssh svcuser@10.0.0.1
```
```shell
cd /srv/app/containers
docker compose ps
```
````

After, one block:

```shell
ssh svcuser@10.0.0.1
cd /srv/app/containers
docker compose ps
```

Keep blocks separate only when prose between them explains something the reader must do or check before continuing.

## Language Tags

| Content | Tag | Use for |
| :------ | :-- | :------ |
| Shell commands | `shell` | General terminal commands that do not rely on a specific shell |
| Terminal inputs/outputs | `console` | To highlight the prompt ($) and leave output uncolored. |
| POSIX shell script | `sh` | Shell script that is compliant with the generic POSIX shell standards |
| Bash script | `bash` | Shell script that relies on capabilities of the GNU Bash shell |
| zsh script | `zsh` | Shell script that relies on capabilities of the zsh shell |
| YAML config | `yaml` | YAML |
| `.env` or INI | `ini` | INI |
| SQL | `sql` | SQL queries and commands |
| JSON | `json` | JSON without comments |
| JSONC | `jsonc` | JSON with comments |
| Plain text output | `text` | Text that is not code or markup, and should not have syntax highlighting |
| Mermaid diagram | `mermaid` | Mermaid diagrams |

## Missing Language Tag (Anti-Pattern)

Before:

````markdown
```
docker compose ps
```
````

After:

```shell
docker compose ps
```

## Multi-Line Configuration

Before, environment variables as a numbered list:

```markdown
1. APP_PORT=8080
2. APP_ENV=production
3. DB_HOST=10.0.0.1
```

After, as an `ini` code block:

```ini
APP_PORT=8080
APP_ENV=production
DB_HOST=10.0.0.1
```

If each variable also needs a description or default, use a table with the names in inline code instead, and keep a copyable `ini`
block below it if readers will paste the values.
