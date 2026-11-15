---
name: sync-agent-docs
description: Keep ServerWatch AGENT.md references and instructions aligned when documentation is added, moved, renamed, deleted, or materially changes project requirements. Use during relevant documentation tasks or when explicitly asked to synchronize agent guidance.
---

# Synchronize agent documentation

Maintain the repository-root `AGENT.md` as a concise entry point to project
documentation. This repository uses the singular filename `AGENT.md`; update it
in place rather than creating a competing `AGENTS.md`.

## Workflow

1. Read `AGENT.md` and the affected documentation. Inspect current files and Git
   diffs, including untracked documents; preserve unrelated user changes.
   Discover guides under `docs/` and elsewhere, including `README.md`. Exclude
   placeholders, generated artifacts, and skill internals from the guide index.
2. For each new guide, add a relative Markdown link and when-to-read description
   to the documentation reference table. For moves, renames, and deletion,
   repair references throughout `AGENT.md`; remove obsolete instructions without
   inventing replacement requirements.
3. For material changes, update stale summaries, task routing, and instructions.
   Material changes affect API contracts, architecture, security, folder
   ownership, development/testing requirements, deployment, or demo constraints.
   Document length alone is not a trigger. Typo and formatting fixes require no
   instruction edits unless they repair references.
4. Keep detailed requirements in their owning documents and link to them instead
   of copying entire sections. Distinguish proposed requirements from implemented
   behavior. Respect explicit user decisions. Report unresolved conflicts rather
   than silently inventing a requirement or weakening an approval rule.
5. Verify that local links resolve, the reference table covers current project
   guides, and summaries agree with their sources. Run `git diff --check` scoped
   to the changed files. Report references or rules changed and any unresolved
   conflicts; preserve unrelated pre-existing changes.

Perform synchronization during authorized documentation tasks without separate
confirmation. This skill guides agents during their work; it does not install
a background file watcher, Git hook, or continuous synchronization service.
