# Update repo data workflow

The [`update-repodata`](.github/workflows/update-repodata.yml) workflow runs
[`scripts/generate_data.py`](scripts/generate_data.py) on a GitHub-hosted runner, then opens
(or updates) a pull request from the branch `auto/update-repodata` into `master` containing
only the changes under `data/`. Nothing is written to `master` until someone merges that PR.

| Trigger | How |
|---|---|
| Manual | `gh workflow run update-repodata.yml` or **Run workflow** in the Actions tab |
| Trigger file | Push a change to `.trigger` on `master` |
| Schedule | Commented out in the workflow; uncomment `schedule:` to enable |

## GITHUB_TOKEN

### What it is

`GITHUB_TOKEN` is a token GitHub creates automatically at the start of every workflow job. You
never create, store or rotate it.

- **Scope:** only the repository the workflow runs in.
- **Lifetime:** expires when the job finishes (24 hours at most).
- **Permissions:** exactly what the workflow's `permissions:` block grants. Without the block,
  the repository default applies (`read` in this org).
- **Identity:** acts as `github-actions[bot]`, so PRs it opens are authored by the bot.
- **No chaining:** pushes and PRs made with it do not trigger other workflows. This prevents
  workflow loops, but it also means CI (`on: pull_request`) will not run on the data PRs.

`actions/checkout` and `peter-evans/create-pull-request` both use it by default, so the
workflow never references it explicitly.

### How it is allowed in this repo

Two things must both be in place.

**1. Org (or repo) setting: allow Actions to create PRs.** Without this, PR creation fails with
`GitHub Actions is not permitted to create or approve pull requests`.

- Org: **Settings → Actions → General → Workflow permissions →** tick **Allow GitHub Actions to
  create and approve pull requests**.
- The repo has the same setting under its own **Settings → Actions → General**; the org setting
  must allow it first.

Check it with:

```sh
gh api repos/woodez-kubernetes/test-update-repodata/actions/permissions/workflow
# {"default_workflow_permissions":"read","can_approve_pull_request_reviews":true}
```

**2. `permissions:` block in the workflow.** The default token is read-only, so the workflow
grants itself write access:

```yaml
permissions:
  contents: write        # push the auto/update-repodata branch
  pull-requests: write   # open/update the PR
```

### Compared with a personal access token (PAT)

The workflow previously used the org secret `GITOPS_PUSH_TOKEN` and was switched back to
`GITHUB_TOKEN` because the built-in token is safer:

| | `GITHUB_TOKEN` | PAT in a secret (e.g. `GITOPS_PUSH_TOKEN`) |
|---|---|---|
| Created by | GitHub, per job | A person |
| Lifetime | One job | Until it expires or is revoked |
| Repos | This one | Every repo the token can reach |
| Permissions set by | The workflow's `permissions:` block | The token's own settings |
| Acts as | `github-actions[bot]` | The token owner |
| Triggers other workflows | No | Yes |
| If leaked | Effectively useless | Usable as the owner until revoked |

If CI must run on the data PRs, prefer a GitHub App token
(`actions/create-github-app-token`) over a PAT.

## Triggering with the gh client

Run these from inside a clone of the repo, or add
`--repo woodez-kubernetes/test-update-repodata`.

```sh
# Start a run
gh workflow run update-repodata.yml

# Deterministic output: fixed timestamp and seed, so a re-run produces no diff
gh workflow run update-repodata.yml -f noop=true

# Follow the latest run until it finishes
gh run watch $(gh run list -w update-repodata.yml -L1 --json databaseId -q '.[0].databaseId')

# List recent runs (shows trigger event and who started them)
gh run list -w update-repodata.yml

# Show what the run did with the PR (created / updated / none)
gh run view --log $(gh run list -w update-repodata.yml -L1 --json databaseId -q '.[0].databaseId') \
  | grep "PR operation"

# See the data PR and its diff
gh pr list --head auto/update-repodata
gh pr diff auto/update-repodata

# Merge the data PR
gh pr merge auto/update-repodata --merge
```

`gh` needs to be logged in (`gh auth login`) as a user with write access to the repo.

## Triggering with the .trigger file

Pushing a change to `.trigger` on `master` starts the workflow. The file's content does not
matter; it only has to change, so write the current time into it:

```sh
git checkout master && git pull
date -u +%Y-%m-%dT%H:%M:%SZ > .trigger
git commit -am "Trigger data update"
git push
```

What happens next:

1. GitHub sees a push to `master` that touched `.trigger` and starts the workflow.
2. The runner checks out `master` and runs `scripts/generate_data.py` in normal mode
   (the `noop` input exists only for manual runs).
3. The data PR on `auto/update-repodata` is created, or updated if one is already open. Your
   `.trigger` commit is already on `master`, so it is not part of the PR.
4. Merging the data PR changes only `data/`, so it does not start another run.

Notes:

- The change must land on `master`. Editing `.trigger` on another branch does nothing until it
  is merged.
- Workflow pushes to `auto/update-repodata` never match the trigger, so there is no loop.
- Each trigger adds a commit to `master`. If `master` becomes protected, every trigger needs
  its own PR, and `gh workflow run` is the simpler option.
- Changes to `scripts/generate_data.py` do **not** trigger a run. After changing the script,
  trigger it manually or with `.trigger`.
