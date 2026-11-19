---
name: explain-api-errors
description: Require safe, specific public reasons when adding, modifying or reviewing ServerWatch API errors for any HTTP operation, including framework, authentication, health and persistence failures.
---

# Explain every handled API failure

Trace each operation through its router, auth dependencies, schema, service, global handlers and consuming client. Include errors produced before the route runs and after it returns. Compare distinct causes that share a status.

Every handled failure must tell the caller what failed. Identify the field and violated rule for bad inputs, the missing resource or role for lookup or permission errors, and the failed dependency or check for availability errors. Give a corrective action when it is known. For an unexpected exception, explain that processing failed inside the server. Only claim a timeout, schema problem or configuration issue when code can establish it.

Use the existing public error envelope and stable codes. Set application-owned messages with PublicHTTPError and schema-specific reasons with PublicInputError. Preserve protocol headers, bodyless HEAD semantics, and the health readiness response. Never forward raw exception text, SQL, credentials, unrecognized field names, request values or infrastructure paths.

Exercise the real HTTP operation. Assert the status and reason or field details, including distinct causes with the same status, safe fallbacks and relevant headers. Check the consuming client retains the public explanation. Update docs/api.md and its examples with every material change to error behavior.
