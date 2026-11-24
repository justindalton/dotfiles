# GitHub CLI / API Notes For `babysit-pr`

## Primary commands used

### PR metadata

- `gh pr view --json number,url,state,mergedAt,closedAt,headRefName,headRefOid,baseRefName,baseRefOid,headRepository,headRepositoryOwner`

Used to resolve PR number, URL, branch, head/base SHA, and closed/merged state.

### PR checks summary

- `gh pr checks --json name,state,bucket,link,workflow,event,startedAt,completedAt`

Used to compute pending/failed/passed counts and whether the current CI round is terminal.

### Workflow runs for head SHA

- `gh api repos/{owner}/{repo}/actions/runs -X GET -f head_sha=<sha> -f per_page=100`

Used to discover failed workflow runs and rerunnable run IDs.

### Failed log inspection

- `gh run view <run-id> --json jobs,name,workflowName,conclusion,status,url,headSha`
- `gh api repos/{owner}/{repo}/actions/runs/{run_id}/jobs -X GET -f per_page=100`
- `gh api repos/{owner}/{repo}/actions/jobs/{job_id}/logs > /tmp/codex-gh-job-{job_id}-logs.zip`
- `gh run view <run-id> --log-failed`

Used by Codex to classify branch-related vs flaky/unrelated failures. Prefer the direct job log endpoint as soon as a job has failed because `gh run view --log-failed` may not produce failed-job logs until the overall workflow run completes.

### Retry failed jobs only

- `gh run rerun <run-id> --failed`

Reruns only failed jobs (and dependencies) for a workflow run.

## Review-related endpoints

- Issue comments on PR:
  - `gh api repos/{owner}/{repo}/issues/<pr_number>/comments?per_page=100`
- Inline PR review comments:
  - `gh api repos/{owner}/{repo}/pulls/<pr_number>/comments?per_page=100`
- Review submissions:
  - `gh api repos/{owner}/{repo}/pulls/<pr_number>/reviews?per_page=100`

The watcher paginates all three endpoints. Author `type: Bot` and the `[bot]`
login suffix identify agent feedback, so new bot identities do not require an
allow-list. REST `pull_request_review_id` is a review submission ID, not an
inline thread ID. The watcher therefore makes best-effort GraphQL
`PullRequest.reviewThreads` queries and associates REST comment database IDs
with the returned thread node ID, resolution state, and follow-ups. If that
optional enrichment fails or a comment is unmapped, it remains unresolved.
Bodies and content fingerprints are retained in the atomic watcher state file.
Informational bot chatter is retained but does not create an actionable review
action; substantive or ambiguous bot content remains pending for triage.

## JSON fields consumed by the watcher

### `gh pr view`

- `number`
- `url`
- `state`
- `mergedAt`
- `closedAt`
- `headRefName`
- `headRefOid`
- `baseRefName`
- `baseRefOid`

### `gh pr checks`

- `bucket` (`pass`, `fail`, `pending`, `skipping`)
- `state`
- `name`
- `workflow`
- `link`

### Actions runs API (`workflow_runs[]`)

- `id`
- `name`
- `status`
- `conclusion`
- `html_url`
- `head_sha`

The watcher persists the last observed base SHA, outstanding rebase requests, and
explicit base/head acknowledgement. It emits an immediate `rebase_pr` action for
`DIRTY`/conflicted merge state, and retains requests for base movement or the
configured open-PR cadence until acknowledged. Rebase execution is deliberately
outside the watcher: fetch the remote base, rebase the PR head, resolve conflicts,
test as warranted, push with `--force-with-lease`, then run
`gh_pr_watch.py --pr auto --ack-rebase --base-sha <current-base-sha> --head-sha <pushed-head-sha>`.
`ready_to_merge` is suppressed until that acknowledgement matches the current PR.

### Actions run jobs API (`jobs[]`)

- `id`
- `name`
- `status`
- `conclusion`
- `html_url`
