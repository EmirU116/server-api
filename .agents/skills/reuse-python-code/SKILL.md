---
name: reuse-python-code
description: Extract duplicate Python behavior when editing ServerWatch backend routes, schemas, or Python scripts. Use when multiple callers implement the same validation or operation.
---

# Reuse Python behavior

Trace each caller and its tests first. Compare accepted inputs, error codes, validation order, side effects and async behavior. Two similar-looking checks may enforce different contracts, such as a repeated server ID (400) and a repeated list filter (422).

For shared backend behavior, use the single module `backend/app/reusable.py`. Import existing helpers directly and keep endpoint-specific decisions at their call sites. Keep standalone Python scripts usable with their documented interpreter and dependencies. When a helper is shared only by scripts, reuse its owning module if one already exists. Keep frontend helpers in their own frontend module if the policy is later extended to that stack. This workflow currently covers Python.

Describe when each extracted helper applies in a concise docstring. Write direct unit tests for successful and failing inputs and run the existing caller tests. Check that public API responses, OpenAPI parameters and command-line entry points retain their behavior. A new helper should replace actual duplication and make the callers easier to read.
