# Table Rewrite Examples

Rule: when items have two or more attributes, need comparing, form a mapping, or describe states, use a table.

## Contents

- [Variable list](#variable-list)
- [Service endpoints](#service-endpoints)
- [Design details](#design-details)
- [Expected states](#expected-states)
- [CI results](#ci-results)

## Variable List

Before:

```markdown
1. `app_image_name`
2. `app_image_tag`
3. `db_encryption_key` (Vault)
4. `app_user_password` (Vault)
```

After:

| Variable | Type | Description |
| :------- | :--- | :---------- |
| `app_image_name` | string | Docker image name |
| `app_image_tag` | string | Docker image tag |
| `db_encryption_key` | Vault | Database encryption key |
| `app_user_password` | Vault | Application user password |

## Service Endpoints

Before:

```markdown
1. Web UI: `http://10.0.0.1:8080`
2. Health: `http://10.0.0.1:8080/health`
```

After:

| Service | URL | Description |
| :------ | :-- | :---------- |
| Web UI | `http://10.0.0.1:8080` | Browser interface |
| Health | `http://10.0.0.1:8080/health` | Health check endpoint |

## Design Details

Before:

```markdown
1. DB: `appdb`
2. User: `app_user`
3. Privileges: `public` schema `ALL`
4. DB owner: `app_user`
5. Schema owner: `app_user`
```

After:

| Item | Value |
| :--- | :---- |
| Database | `appdb` |
| User | `app_user` |
| Schema privileges | `public` ALL (including future tables) |
| DB owner | `app_user` |
| Schema owner | `app_user` |

## Expected States

Before:

```markdown
1. `app-web`: `Up (healthy)`
2. `app-worker`: `Up (healthy)`
3. `app-redis`: `Up (healthy)`
```

After:

| Container | Expected state |
| :-------- | :------------- |
| `app-web` | `Up (healthy)` |
| `app-worker` | `Up (healthy)` |
| `app-redis` | `Up (healthy)` |

## CI Results

Before:

```markdown
1. lint: pass
2. unit-test: pass (1m 23s)
3. build: pass (4m 07s)
4. deploy-staging: pass
```

After:

| Job | Status | Duration |
| :-- | :----: | -------: |
| lint | pass | |
| unit-test | pass | 1m 23s |
| build | pass | 4m 07s |
| deploy-staging | pass | |
