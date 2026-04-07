# Contributing to Autom8x (A8X)

Guidelines for contributing to the n8n automation backend.

## Branching Strategy

| Branch          | Purpose                                    |
|-----------------|--------------------------------------------|
| `main`          | Production-ready code, always deployable   |
| `feature/<name>`| New features and pipelines                 |
| `fix/<name>`    | Bug fixes                                  |
| `refactor/<name>`| Refactoring and tech debt                 |
| `chore/<name>`  | Infra, docs, CI/CD, config changes         |

- Branch from `main`, merge back via PR.
- Keep branches short-lived. One logical change per branch.

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) with these types:

| Type       | When to use                                      |
|------------|--------------------------------------------------|
| `feat`     | New workflow, pipeline, or feature                |
| `fix`      | Bug fix in a workflow or integration              |
| `refactor` | Code/workflow restructuring, no behavior change   |
| `chore`    | Infra, Docker, scripts, config, docs              |
| `prompt`   | LLM prompt template changes (custom type)         |
| `schema`   | JSON schema definition changes (custom type)       |
| `test`     | Adding or updating smoke tests                    |

Format: `<type>(<scope>): <description>`

```
feat(invoice): add multi-page PDF support
prompt(extraction): tighten GL code assignment instructions
schema(output): add tax_breakdown field to line items
chore(docker): bump n8n to 2.8.3
```

## Workflow Development Standards

### No Hardcoded Credentials
- Never put API keys, passwords, or secrets directly in workflow nodes.
- Use n8n's built-in Credentials system for all external service auth.
- Gemini API key goes in `.env.local` / `.env.prod`, never in workflow JSON.

### Node Naming
- Every node must have a descriptive name. No default names like "HTTP Request" or "Code".
- Format: `<Verb> <Object>` — e.g., "Upload PDF to GCS", "Extract Line Items", "Assign GL Codes".
- Error handler nodes: prefix with `Handle Error:`.

### Error Handling
- Every workflow must have an error trigger or try/catch pattern.
- External API calls (Gemini, GCS) must handle failures gracefully.
- Log meaningful error context (input file name, client ID, error message).

### Workflow Exports
- Export workflows to `workflows/exports/`.
- Naming: `<domain>-<action>-<version>.json` (e.g., `invoice-process-v2.json`).
- Strip credentials from exports before committing.

## PR Checklist

Before opening a PR, verify:

- [ ] Branch follows naming convention (`feature/`, `fix/`, `refactor/`, `chore/`)
- [ ] Commits follow Conventional Commits format
- [ ] No hardcoded credentials or API keys in any file
- [ ] No `.env`, `.env.local`, `.env.prod`, or `secrets/*.json` files staged
- [ ] Workflow nodes have descriptive names (no defaults)
- [ ] Error handling is present for external API calls
- [ ] Workflow exports are credential-stripped
- [ ] `./scripts/smoke-cleanup.sh` passes locally
- [ ] Docker image builds successfully (`docker compose build --no-cache`)
- [ ] PR description explains what changed and why

## Secrets Policy

**Never commit secrets.** The following are gitignored and must stay that way:

| Path / Pattern        | Contains                          |
|-----------------------|-----------------------------------|
| `.env`                | Should not exist (use .env.local) |
| `.env.local`          | Local dev environment variables   |
| `.env.prod`           | Production environment variables  |
| `secrets/`            | GCP service account JSON keys     |
| `data/`               | SQLite DB, encrypted credentials  |

If you accidentally commit a secret:
1. Rotate the credential immediately.
2. Use `git filter-branch` or BFG Repo-Cleaner to purge from history.
3. Force-push the cleaned history.
4. Notify the team.

## Upgrading Pinned GitHub Actions

Third-party Actions in `.github/workflows/` are pinned to full commit SHAs instead of version tags.

To upgrade an action to a newer version:

1. Go to the action's releases page on GitHub
2. Find the new version tag you want
3. Resolve the tag to a commit SHA:
   ```
   git ls-remote https://github.com/<owner>/<repo>.git refs/tags/<version>
   ```
4. Update the `uses:` line with the new SHA
5. Update the inline version comment to match
