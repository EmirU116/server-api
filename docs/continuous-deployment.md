# Continuous deployment to EC2 (VG4 bonus)

After CI passes on `main`, GitHub Actions builds the Docker images of that
exact commit, pushes them to GitHub Container Registry (GHCR) and starts them
in the Compose stack on EC2. This is the optional VG4 bonus from the
[assignment](assignment-brief.md). The manual native and Compose deployments
in the [EC2 guide](ec2-manual-setup.md) and [Compose guide](docker-deployment.md)
are still required and come first.

## How a change reaches the server

```text
push to main
  └─ ServerWatch CI (ci.yml): backend, dashboard and Bash checks
       └─ passed → ServerWatch deploy (deploy.yml)
            ├─ images: build api + web, tag both with the commit SHA, push to GHCR
            └─ deploy: ssh deploy-key → EC2 runs deploy_image.sh <SHA>
                 ├─ git fast-forwards ~/serverwatch to that commit (must be on main)
                 ├─ compose pull api web  (ghcr.io/<owner>/<repo>/{api,web}:<SHA>)
                 ├─ compose up -d --no-build --wait  (migrate runs before the API)
                 ├─ health check through the Compose web container
                 └─ records the SHA in ~/.config/serverwatch-delivery/deployed-commit
```

| Part | File | Job |
| --- | --- | --- |
| Workflow | [`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml) | Runs after a green CI run for a push to `main`, or by hand (**Run workflow**). |
| Deploy script | [`scripts/deployment/deploy_image.sh`](../scripts/deployment/deploy_image.sh) | Runs on EC2. Only deploys commits on `origin/main`, refuses a checkout with local edits, and fails if the new containers are unhealthy. |
| Key setup | [`scripts/deployment/authorize_deploy_key.sh`](../scripts/deployment/authorize_deploy_key.sh) | Adds GitHub's public key to `authorized_keys` with `restrict,command="…deploy_image.sh …"`. |

Why it is built this way:

- **The images are tagged with the commit SHA**, not `latest`, so the server
  runs exactly the code CI tested, and the tag shows which version runs.
- **GitHub's SSH key can only deploy.** `restrict` turns off shells, port
  forwarding and terminals, and `command=` replaces whatever GitHub sends with
  `deploy_image.sh`. GitHub only chooses the commit, and the script accepts
  nothing but a 40-character SHA that is already on `main`.
- **The server's host key is pinned** in a GitHub secret, so the runner refuses
  to deploy to anything pretending to be your instance.
- **One deploy at a time.** The workflow's concurrency group queues deploys
  and never cancels one halfway through.
- **Off unless switched on.** Automatic deploys run only while the repository
  variable `SERVERWATCH_DEPLOY_ENABLED` is `true`, so pushes don't fail while
  the instance is stopped.

## Set it up (once per instance)

Start from an instance where `setup.sh` has run and
`bash scripts/deployment/compose_host.sh start` has started Compose once.

1. **Create a key pair for GitHub on your own computer.** It is separate from
   your personal SSH key, and has no passphrase because a robot uses it.

   ```bash
   ssh-keygen -t ed25519 -N '' -C github-deploy -f ~/.ssh/serverwatch_github_deploy
   scp ~/.ssh/serverwatch_github_deploy.pub ubuntu@ELASTIC_IP:~/
   ```

2. **Authorize it on EC2** as the user who runs Compose. Use the address GitHub
   will connect to (the Elastic IP, or the domain):

   ```bash
   bash ~/serverwatch/scripts/deployment/authorize_deploy_key.sh ~/serverwatch_github_deploy.pub ELASTIC_IP
   ```

   It prints the four values for step 3.

3. **Add the repository secrets** in GitHub under **Settings → Secrets and
   variables → Actions → Secrets**:

   | Secret | Value |
   | --- | --- |
   | `SERVERWATCH_DEPLOY_HOST` | The Elastic IP or domain from step 2. |
   | `SERVERWATCH_DEPLOY_USER` | The Compose user, for example `ubuntu`. |
   | `SERVERWATCH_DEPLOY_SSH_KEY` | The whole **private** key file `~/.ssh/serverwatch_github_deploy`. |
   | `SERVERWATCH_DEPLOY_KNOWN_HOSTS` | The `known_hosts` line the script printed. |

   Under **Variables**, add `SERVERWATCH_DEPLOY_ENABLED` = `true`.

4. **Allow SSH from GitHub.** GitHub's hosted runners connect from many
   changing addresses, so the security group's SSH rule must allow
   `0.0.0.0/0` on port 22 while you use automatic deploys. Password logins are
   off on Ubuntu's EC2 images, so only listed keys get in. Narrow the rule to
   your own IP again when you are done.

5. **Run the first deploy by hand:** **Actions → ServerWatch deploy → Run
   workflow** on `main`.

6. **Make the two packages public (first deploy only).** GHCR creates them as
   private, so the first pull fails with "Check that both GHCR packages are
   public". On GitHub open your profile → **Packages** → `<repo>/api` →
   **Package settings** → **Change visibility** → **Public**, do the same for
   `<repo>/web`, then rerun the workflow. The repository is public, so this
   exposes nothing new, and EC2 needs no registry password.

## Check and use it

```bash
cat ~/.config/serverwatch-delivery/deployed-commit       # SHA running in Compose
bash ~/serverwatch/scripts/deployment/compose_host.sh ps # image tags per service
```

On GitHub, **Actions → ServerWatch deploy** shows each run's two jobs and the
script's `[DEPLOY]` and `[PASS]` lines.

The deploy also writes the image tags into
`~/.config/serverwatch-delivery/compose.env`, so later manual commands such as
`compose_host.sh down` and `up -d --wait` keep the deployed version.
`compose_host.sh start` rebuilds from the checkout instead, which holds the same
commit.

The deploy updates the **Compose** stack (web on `127.0.0.1:8080`). The public
site serves the native API until you point the HTTPS block at port 8080, as
described in the [Compose guide](docker-deployment.md).

To roll back, revert the bad commit on `main` (`git revert`) and push. CI tests
the revert and the workflow deploys it like any other change.

## Stopping and new instances

- Stopping for the day: set `SERVERWATCH_DEPLOY_ENABLED` to `false` (or delete
  it) and narrow SSH again.
- New instance: repeat steps 2–5. The host, host key and maybe the user change,
  so update the secrets. The packages stay public.
- Remove access: delete the deploy-key line from `~/.ssh/authorized_keys` on
  the server and the secrets on GitHub.
