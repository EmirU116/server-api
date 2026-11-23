# Git and GitHub Actions workflow for ServerWatch

The test-only [CI workflow](../.github/workflows/ci.yml) is implemented locally.
GitHub runs it after it is published to the repository with Actions enabled.
CD is an opt-in workflow for the container deployment. Its first hosted
deployment is pending. The [assignment](assignment-brief.md) requires the native
and container demonstrations for VG. Automatic image deployment to EC2 is the
separate VG4 bonus.

## How one change travels through the project (Git, GitHub)

1. **Work locally.** Start a short-lived branch from an up-to-date `main`, such as `fix/server-id-errors`. Reproduce the problem with a failing test, change the code, and rerun the test. A local commit records a version on your machine. A push sends it to GitHub.
2. **Open a pull request to main.** Describe the problem, the change and the test result. Each new push to the open PR reruns CI. Review your own diff, including accidental files, and fix failures on that branch. Small commits that each express one change are easier to review and undo. [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) · [Pro Git on contributing and commit guidelines](https://git-scm.com/book/en/v2/Distributed-Git-Contributing-to-a-Project)
3. **Merge after green checks.** For a solo developer, require successful checks on `main` where the repository plan allows it. Leave mandatory second-person reviews off during solo work. Squash merging is a reasonable default for one small PR per change. Delete the merged topic branch. Run CI on the resulting main commit too. Keep one long-lived branch, `main`. Each environment records which commit is deployed. [GitHub branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
4. **Promote the tested version.** Send the successful main commit to an EC2 staging environment. Once the workflow verifies staging, you can promote the same image digests to production. A failed test deployment leaves the previous production version in place.

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

## Opt-in deployment workflow (GitHub Actions, Compose, EC2)

[ServerWatch delivery](../.github/workflows/deploy.yml) is manually triggered
from the Actions tab on `main`. It checks that the exact commit passed main CI,
builds and publishes API and web images to GHCR for Linux x86-64, then deploys
those digests to staging. If you select **promote**, the same digests proceed
to production after staging passes and the production environment gate opens.
CI on pull requests and pushes continues to run independently.
[GitHub deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)

### One-time preparation (Ubuntu, Docker, GitHub)

1. On each target, install Docker Engine with the Compose plugin, Git, Bash,
   curl, Python 3, util-linux, and OpenSSH tools with `ssh-keygen -Y verify`
   support. Use two Linux identities. The trusted
   Compose operator (example `swoperator`) owns `~/serverwatch`, the host
   Compose configuration, secrets, and Git/GHCR read credentials. The CI SSH
   account (example `swdeploy`) has a locked password, no Docker group or
   daemon access, and no general sudo access. For an existing stack, keep the
   existing operator to preserve file ownership and use a separate SSH account.
   When repurposing an old CI account, remove its Docker group and broad sudo
   grants, and end old sessions that still have the previous permissions.
2. As the operator, clone the repository to `~/serverwatch` and follow the
   [Compose setup guide](docker-deployment.md). Run `compose_host.sh prepare`
   ahead of the first release, including on an existing volume. Set the host
   environment and the exact lowercase GHCR release base (omit `-api`/`-web`).

   ```bash
   install -d -m 700 "$HOME/.config/serverwatch-delivery"
   umask 077
   printf '%s\n' staging > "$HOME/.config/serverwatch-delivery/environment"
   printf '%s\n' ghcr.io/OWNER/REPOSITORY > "$HOME/.config/serverwatch-delivery/repository"
   ```

   Replace `OWNER/REPOSITORY` with the lowercase GitHub owner and repository.
   Use `production` on the production host. Keep staging and production
   volumes and secrets independent.
3. Generate a dedicated Ed25519 release signing key for each environment
   outside the checkout, using `ssh-keygen -t ed25519 -N '' -f /private/path/release-signing-key`.
   Use a private directory and keep the signing key separate from the SSH
   login key. As the host administrator, install the reviewed scripts from
   the checkout, install the CI login public key, and pin the release signing
   public key alongside the scripts.

   ```bash
   sudo install -d -m 0755 /usr/local/libexec/serverwatch /etc/ssh/serverwatch
   sudo install -o root -g root -m 0755 scripts/deployment/{deploy_ssh_entry,deploy_compose,compose_host}.sh /usr/local/libexec/serverwatch/
   sudo install -o root -g root -m 0644 serverwatch-ci.pub /etc/ssh/serverwatch/swdeploy
   # Use production and its corresponding public key on the production host.
   printf 'staging namespaces="serverwatch-release-v1" %s\n' "$(cat /private/path/release-signing-key.pub)" |
       sudo install -o root -g root -m 0644 /dev/stdin /usr/local/libexec/serverwatch/release-signers
   sudo visudo -f /etc/sudoers.d/serverwatch-deploy
   ```

   Enter this single sudoers rule. The final `""` allows only a call with no
   arguments.

   ```sudoers
   swdeploy ALL=(swoperator) NOPASSWD:NOSETENV: /usr/local/libexec/serverwatch/deploy_ssh_entry.sh ""
   ```

   Add the following account block to the **end** of `/etc/ssh/sshd_config`.
   Set Bash as the login shell for `swdeploy` so sshd can run the
   forced command. The key file and installed scripts must stay writable only
   by root.

   ```sshconfig
   Match User swdeploy
       AuthorizedKeysFile /etc/ssh/serverwatch/swdeploy
       AuthenticationMethods publickey
       DisableForwarding yes
       PermitTTY no
       PermitUserRC no
       ForceCommand /usr/bin/printf '%s\n' "$SSH_ORIGINAL_COMMAND" | /usr/bin/sudo -n -H -u swoperator /usr/local/libexec/serverwatch/deploy_ssh_entry.sh
   ```

   Run `sudo sshd -t` before `sudo systemctl reload ssh` and keep your existing
   administrator session open. Check `id swdeploy`, Docker socket access, and
   `sudo -l -U swdeploy` from the administrator session. From the key holder,
   try `ssh -T swdeploy@HOST id` with the pinned host key. It must return the
   ServerWatch rejection. Check that forwarding is denied, then run an approved
   staging release. Keep the former unrestricted configuration disabled.
4. In GitHub, configure the `staging` and (if used) `production`
   environments. Restrict both to `main`. Enable production promotion only
   after configuring required reviewers and disabling protection-rule bypass
   for production. For each environment set the variables `DEPLOY_HOST`
   and `DEPLOY_USER`, and the secrets `DEPLOY_SSH_KEY` (dedicated deploy
   identity) and `DEPLOY_KNOWN_HOSTS` (a verified OpenSSH known-hosts entry
   matching the host variable) and `DEPLOY_RELEASE_SIGNING_KEY` (the release
   signing private key corresponding to the host's pinned public key). Store
   the signing key only as an environment-scoped GitHub Actions secret.
   Verify the host key independently before
   adding it. The runner needs an approved SSH route to EC2. If your
   instance only permits your own IP, use a trusted runner with a fixed
   allowlisted IP. Set the repository variable
   `SERVERWATCH_DEPLOY_RUNNER` to its dedicated runner label. Restrict that
   runner to trusted workflows so pull-request code cannot use it. Leave
   delivery disabled until a route is available.

### Release verification and recovery (GitHub Actions, Docker, PostgreSQL)

Once GitHub's environment rules pass, the deployment job signs the environment,
commit SHA, and exact API and web digest references built by the publish job.
The forced command requires this signature. The installed script checks the
host environment and image repository, then verifies the exact record against
the pinned signing key before fetching Git or invoking Docker. It checks main
ancestry and loads the Compose manifest from the selected commit on
`origin/main` and leaves the checkout and host secret files in place.
It pulls the two application digests, waits for startup and migrations,
then checks loopback health and Swagger on the port from the host Compose file. Keep Nginx as the public entry
point and verify public access and fresh host measurements separately.

Update the installed host scripts and pin the signing key before running the
updated workflow. Previously signed records can be retried for the same
environment and exact release while their signing key is trusted and their
commit is reachable from main.

Before enabling production promotion, take and verify a database backup.
If deployment fails, the job stops and leaves the last successful marker in
`~/.config/serverwatch-delivery/last-success`. A successful update also saves
the previous marker as `previous-success`. Review the Compose logs and
database state before retrying. Use the previous manifest and digests for
recovery only after checking compatibility with the migrated schema and database roles. An
unsuccessful rollout can leave some services updated. Use care when choosing
between repairing the rollout and restoring from a verified backup.
