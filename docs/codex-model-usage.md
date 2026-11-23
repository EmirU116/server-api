# Codex model usage for ServerWatch

Use **GPT-6.2 Sol at medium effort** for ordinary implementation and debugging. Match the model to the uncertainty and impact of the task. A one-line change to database permissions can warrant more reasoning than a larger documentation edit.

## Choose a model

| Model | Starting effort, when available | ServerWatch scenarios |
|---|---|---|
| **GPT-6 Luna** (`gpt-6-luna`) | Low | Fix a known Markdown link, update a test assertion with an explicit expected value, or summarize a short CI log. |
| **GPT-6.2 Sol** (`gpt-6.2-sol`) | Medium | Fix a FastAPI validation bug with a reproducible test, change a React component and its tests, or update a Compose setting with a known cause. Low is enough for localized, predictable edits. |
| **GPT-6.1 Terra** (`gpt-6.1-terra`) | Low or medium | Inspect a dashboard screenshot for clipped labels, compare chart layouts, or review browser behavior when the client provides the required tools. |
| **GPT-6.2 Astra** (`gpt-6.2-astra`) | High | Trace an intermittent failure across Nginx, FastAPI and PostgreSQL, reason through an Alembic migration and rollback, or review changes to authentication boundaries or deployment permissions. |

If a listed model is unavailable, choose an available model with a similar role. Sol at low effort is a practical fallback for focused edits, and Sol at high effort can take on complex work when Astra is unavailable. These are project starting points. Available models and effort levels depend on the client and workspace. [OpenAI model catalog](https://learn.chatgpt.com/docs/models#recommended-models)

## Escalate when the evidence changes

- Raise reasoning effort when the model has the relevant evidence but needs to reconcile competing explanations or check more edge cases.
- Switch to Astra when a targeted attempt leaves the cause unclear across components, or start there when the change affects access controls, persistent data or deployment recovery. Carry forward the relevant files, failing command, observed error, and hypotheses already ruled out.
- When evidence is missing, collect the smallest useful reproduction, test output or configuration excerpt before retrying. Keep ServerWatch approval gates and verification requirements at every model tier. [Agent instructions](../AGENT.md)

## Spend fewer tokens

- Give the goal, relevant paths, expected behavior and verification target in the first prompt. For example, “In `frontend/src/components/ResourceChart.tsx`, reproduce the reported label clipping, preserve the data and polling behavior, and run the focused component test.”
- Search for the affected symbols and read the relevant sections of their files and project guides. Include the failing assertion and nearby log lines when sharing output. Redact credentials and other secrets.
- Start with the closest test or validation command, then run broader checks when the change crosses a component boundary or the repository requires them. Ask for a short summary of changes, checks and unresolved issues.
- Keep related follow-ups in the same conversation. Start a fresh task for unrelated work. If a long investigation needs a handoff, carry over a short summary of decisions, changed files, test results and open questions.
- Compare token usage across similar completed tasks, including retries and rework. Credits per token and total token usage are separate measures. The CLI's `/status` shows session configuration and token usage. [Codex CLI commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)

## Apply the choice in Codex

In the Codex CLI, use `/model` to choose an available model and reasoning effort, or start a session with `codex -m gpt-6.2-sol`. Use the model picker in other clients when available. The guide provides selection advice. A session's model is controlled by the client or its configuration. [Codex CLI commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)

This repository uses `AGENT.md`. To have Codex discover it automatically, add `"AGENT.md"` to `project_doc_fallback_filenames` in your Codex configuration, preserving any existing entries. Start a new session after changing the configuration. You can also point Codex to `AGENT.md` explicitly in your prompt. [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md#customize-fallback-filenames)
