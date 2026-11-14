---
name: secure-repo-secrets
description: Review or fix ServerWatch secret handling when adding credentials, configuration, authentication, containers, monitoring, or deployment. Use for repository secret audits and suspected leaks, following docs/SECRETS_MANAGEMENT.md.
---

# Secure repository secrets

Read `docs/SECRETS_MANAGEMENT.md` from the repository root before acting. Treat it as the project's reference for storage, password handling, deployment, and recovery. Resolve its example `serverwatch/` paths against the actual repository root. If the guide is unavailable, report that limitation and avoid guessing production settings.

## Scope and discovery

Inspect relevant tracked code, configuration, templates, workflows, ignore rules, and Docker build contexts. Use file names and Git tracking metadata first; do not open real `.env` files, secret directories, private keys, or other credential stores without explicit approval. Respect section 10 of the guide: real secrets must not be read, printed, copied, exposed, uploaded, committed, rotated, or deleted without explicit approval. An ordinary code change does not authorize a production credential operation.

For an authorized audit, use an available secret scanner with redacted output. Do not install or upload repository contents to a scanning service implicitly. Include tracked files and the intended staged changes; examine history only within the audit's authorized scope. Never print matching lines or raw scanner output that could contain values. Report paths, line numbers when safe, credential categories, and remediation status only. If a value is encountered accidentally, stop propagating it and treat it as a suspected exposure.

## Implement secure storage

- Local development: load credentials from an ignored `.env`; commit only harmless placeholders in `.env.example`.
- EC2: use protected file-backed Compose secrets under `/run/secrets/`, granting each service only the secrets it needs. These files are not automatically encrypted at rest. Use restrictive ownership and permissions compatible with the runtime user; never use `chmod 777` to fix access.
- Implement application support for `NAME_FILE` explicitly, with environment fallback for local use. Fail safely when required secrets are missing, without including their values in errors.
- Keep host monitoring API keys in protected files, outside scripts and crontabs. Authenticate metrics submissions and avoid logging API-key headers or webhook URLs.
- CI/CD: reference GitHub Actions secrets. Prefer OIDC and narrowly scoped IAM roles for AWS access; do not introduce long-lived access keys unnecessarily. Ordinary deployments must preserve production secret files.
- Keep students' SSH private keys on their own computers; only public keys belong in `authorized_keys`. Keep TLS private keys in Certbot-managed storage. Deployment private keys belong in an approved secret store, never source control.
- User login passwords: persist salted password hashes using Argon2id or another appropriate password hashing algorithm. Database connection passwords must remain available through the secret store; do not confuse them with login password hashes.

Ensure `.gitignore` excludes actual secret files, including `.env`, `.env.*` (with an exception for `.env.example`), `secrets/`, and relevant private-key formats. Public keys are not private credentials. Check already tracked paths separately: ignore rules do not untrack files or remove history. Keep secrets out of Docker build contexts with appropriate `.dockerignore` rules; never bake them into image layers, build arguments, or committed configuration. Avoid logging credentials, connection strings, authorization headers, or full webhook URLs.

## Suspected exposure

Follow section 9 of the guide. Explain that revocation or rotation is needed; removing a file or rewriting history does not invalidate a credential. Prepare safe code and template fixes using placeholders. Before accessing real values or changing credential stores, request the explicit approval required by section 10, citing the guide and specifying the action. Coordinate dependent service updates and reloads when authorized. Do not rewrite Git history, force-push, change IAM/SSH settings, or modify production secrets as an incidental fix.

## Verification and report

Use dummy credentials for validation. Verify relevant ignore rules (for example with `git check-ignore`), tracked file status, build-context exclusions, configuration behavior, and redacted scan findings where available. Check that missing secrets fail safely and required mounted files remain readable by the intended service user. Inspect staged changes before any authorized commit.

Report what was checked, safe fixes made, unresolved findings, and any approval needed. Clearly distinguish a limited code review from a full repository/history scan. Never claim secrets are absent or securely stored without supporting checks. This skill guides agent behavior; it does not provide continuous enforcement or replace a configured CI scanner.
