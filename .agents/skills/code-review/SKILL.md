---
name: code-review
description: Conduct a senior engineering review of ServerWatch. Use when the user says code-review or requests an evidence-based review of the project, a diff, a path, or a deployment workflow.
---

# ServerWatch code review

Use `code-review` for the whole project or `code-review <scope>` for a diff,
commit, path, or topic. Start from the current working tree unless a revision
is specified. Review is read-only unless the user also asks for fixes.

- Read the repository instructions and relevant guides. Use the assignment
  brief to check G/VG and distinguish implementation from demonstrated evidence.
- Trace normal and failed operations across boundaries, including fresh setup,
  reruns, upgrades, and data persistence. Prioritize issues users can encounter.
- Review credentials, permissions, network exposure, dependencies, and
  recovery. Follow the repository secrets management skill. Review tracked
  configuration without opening private secrets or changing live services.
- Run targeted local checks. Note where tests use mocks, omit normal entry points,
  or need live EC2 evidence. Check documentation commands against implementation.
- Flag duplication only when it causes divergence or a concrete maintenance cost.

Report findings by severity with a file and line, the triggering condition,
the user impact, and a focused fix. State which checks ran, what remains
unverified, and when there are no actionable findings.
