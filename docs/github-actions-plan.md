# Git and GitHub Actions workflow for ServerWatch

The test-only [CI workflow](../.github/workflows/ci.yml) is implemented locally.
GitHub runs it after it is published to the repository with Actions enabled.
The first hosted result and branch protection settings are pending. Docker and
EC2 deployment automation are later milestones. The [assignment](assignment-brief.md) requires the native and container demonstrations for VG. Automatic image deployment to EC2 is the separate VG4 bonus.

## How one change travels through the project (Git, GitHub)

1. **Work locally.** Start a short-lived branch from an up-to-date `main`, such as `fix/server-id-errors`. Reproduce the problem with a failing test, change the code, and rerun the test. A local commit records a version on your machine. A push sends it to GitHub.
2. **Open a pull request to main.** Describe the problem, the change and the test result. Each new push to the open PR reruns CI. Review your own diff, including accidental files, and fix failures on that branch. Small commits that each express one change are easier to review and undo. [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) · [Pro Git on contributing and commit guidelines](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project)
3. **Merge after green checks.** For a solo developer, require successful checks on `main` where the repository plan allows it. Leave mandatory second-person reviews off during solo work. Squash merging is a reasonable default for one small PR per change. Delete the merged topic branch. Run CI on the resulting main commit too. Keep one long-lived branch, `main`. Each environment records which commit is deployed. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
4. **Promote the tested version.** Once deployment is available, send the successful main commit to an EC2 test environment, verify it there, then deliberately promote that same version to production. Use the image digest to identify the exact Docker image when containers are introduced. A failed test deployment leaves the previous production version in place.

For example, with a clean, synchronized checkout the local commands for the first step would be:

```bash
git switch main
git pull --ff-only
git switch -c fix/server-id-errors
# Edit the handler and regression test, then run the focused check.
python -m pytest backend/tests/test_errors.py -q
git diff
git add -p
git diff --staged
git commit -m "Explain invalid server IDs in API responses"
git push -u origin fix/server-id-errors
```

Keep existing local commits and work in progress when adopting this workflow. Review any commits already ahead of the remote before publishing a new branch.

## One human working with agents (Git, review)

The human owns the task scope, the decision to publish, and the merge into
`main`. For a human-authored change, review your own diff. For an agent-authored
change, the human reviews the actual diff and CI results before merging.

1. Give each task a short-lived branch. For concurrent agents, give each its
   own worktree and branch. Identify owned files and coordinate shared files
   such as the plan or workflow before editing them.
2. An agent inspects existing changes before starting, keeps commits focused,
   runs the same checks as a human, and reports commands, results and remaining
   gaps. Preserve other contributors' work. Never weaken checks to obtain a pass.
3. When publication is authorized, the PR records the purpose, affected areas,
   and verification. The same jobs run regardless of the author. Agents use
   their assigned identity and do not approve or merge their own changes.
4. The human reviews changes to workflows, test configuration and permissions
   especially carefully because the PR can change the checks themselves.
   Production credentials and deploy permissions are outside the CI job.
   Where supported, require all three checks on main after their first hosted
   run. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)

## Implemented CI workflow (GitHub Actions, Python, TypeScript, Bash)

The workflow lives at `.github/workflows/ci.yml`. Its `on` section selects the events, `jobs` names the independent checks, and each job's `runs-on` selects a runner. The job's `steps` check out the code, install tools and run commands. Use `pull_request` targeting `main` and `push` to `main`. PR checks then run when the PR opens and when new commits arrive. Keep daily development commands in their existing project files so a failed job is reproducible locally. [GitHub Actions workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

| Job | What runs and what it catches |
| --- | --- |
| Backend (Python, Ruff, pytest, PostgreSQL) | Install `backend/requirements-dev.txt`. Run `ruff check backend/app backend/tests`, `ruff format --check backend/app backend/tests`, then `python -m pytest backend/tests tests -q -ra` from the repo root. Put lint first so a syntax or import problem fails quickly. Install PostgreSQL server and client binaries including `initdb`, `pg_ctl`, and `psql`. Run pytest as the ordinary runner user so the existing fixtures create disposable clusters. Check the integration tests actually ran because the fixtures can skip when tools are missing. |
| Dashboard (React, TypeScript) | Use a supported Node version meeting `frontend/package.json` and run `npm ci` inside `frontend/`. Then run `npm run format:check`, `npm run typecheck`, `npm test` and `npm run build`. This catches type errors, UI regressions and build failures on a clean Linux installation. |
| Shell (Bash) | Run `bash -n` on each tracked shell script individually. The Python suite above exercises the bootstrap and verification behavior. Leave real host installation and service restarts for the EC2 rehearsal. |

Run these three jobs in parallel with stable names, job timeouts, and a per-PR concurrency group that cancels superseded test runs. Start with all three jobs on every PR. For required checks, whole-workflow path filters can leave a skipped check pending. Grant CI `contents: read`, give test jobs disposable inputs, and pin actions to reviewed full commit SHAs with a comment identifying the release. [Workflow syntax and filtering](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) · [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)

## Later deployment workflow (Ubuntu, EC2, Docker)

| Environment | What happens there |
| --- | --- |
| Local | Develop and test against the local database. Local and CI tests can run before anyone rents an instance. |
| EC2 test / staging | Deploy the candidate to a rehearsal instance using staging-only settings. Run the existing Ubuntu verifier for native deployment. For Compose, verify container health, database persistence, the expected host identity and a fresh stored measurement. Exercise public `/docs` through Nginx. Store the tested commit and image digest with the workflow run. |
| Production / assessed deployment | Promote the staging-tested digest, apply reviewed migrations, then check public HTTPS, Swagger, health and a fresh measurement. Record the previous digest and database backup. On failure, stop promotion. Roll back the image only if it is compatible with the current schema. Follow the course requirement to create a fresh instance during recording. |

Later, keep delivery in `.github/workflows/deploy.yml`. The first version can use a deliberate manual trigger (`workflow_dispatch`) restricted to the trusted main branch and verify the selected commit passed CI. Build the image once, deploy to staging and gate production on staging success. Use separate GitHub environments named `staging` and `production`, separate credentials and data, and one deployment at a time per target. Environment names alone do not isolate hosts or databases. Rehearsals can be temporary to avoid maintaining two always-on instances. [Deployments and environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

Keep deployment credentials out of PR jobs. Scope write permissions to the job that publishes the image. When deploying over SSH, use a dedicated deploy identity and verify the host key. Check the classroom repository's plan and organization permissions before relying on environment secrets, required reviewers or branch rules. For solo work, a deliberate manual promotion is workable. If the necessary protections are unavailable, keep production deployment manual until an appropriately configured repository is available. [Environment feature availability](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) · [Actions security guidance](https://docs.github.com/en/actions/reference/security/secure-use)

The current CI workflow has read-only repository permissions and three independent
jobs. Docker image publishing, deployment workflows and AWS credentials are deferred.
