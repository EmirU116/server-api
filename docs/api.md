# ServerWatch API specification

Status: all four APIs are implemented, including persistent incident CRUD.
HTTP contract and isolated PostgreSQL persistence tests cover the endpoints. See
[local setup](../README.md#local-backend-setup-python-fastapi) for the current
startup and test commands.

## Conventions

- Base path: `/api/v1`.
- Scope: one monitored server. Metrics and incidents belong to the server returned
  by `GET /server`.
- Requests and responses use JSON, except successful deletion, which has no body.
- Send `Content-Type: application/json` for requests with a body.
- Timestamps use RFC 3339 with a timezone; normalize stored and returned values to
  UTC, for example `2026-11-15T12:00:00Z`.
- Metric and incident IDs are server-generated UUIDs. Server identity and the
  health lookup use the same configured positive numeric server ID. Reject unknown input fields.
- Health is public and reveals only operational status. All other endpoints
  require `Authorization: Bearer <token>`. Readers can read; collectors can post
  metrics; administrators can create, update, and delete incidents. Credential
  provisioning is outside this contract; never commit or log real tokens.
- Unsupported methods return `405 Method Not Allowed` with an `Allow` header.

## Endpoint overview

| API | Method | Path | Purpose | Success |
| --- | --- | --- | --- | --- |
| Health | GET | `/health?server_id=1` | Current server health | 200 or 503 |
| Metrics | GET | `/metrics` | Read stored server statistics | 200 |
| Metrics | POST | `/metrics` | Store a metric sample | 201 |
| Server | GET | `/server` | Read server identity and OS information | 200 |
| Incidents | POST | `/incidents` | Create an incident | 201 |
| Incidents | GET | `/incidents` | List incidents | 200 |
| Incidents | GET | `/incidents/{incident_id}` | Read one incident | 200 |
| Incidents | PATCH | `/incidents/{incident_id}` | Update selected incident fields | 200 |
| Incidents | DELETE | `/incidents/{incident_id}` | Delete an incident | 204 |

Paths in the table are relative to `/api/v1`. PATCH supplies the update operation
for full incident CRUD; PUT is not part of this contract.

## Health API

### `GET /health`

Return the current health of the monitored server and the API's required
dependencies. Require the query parameter `server_id`, for example
`GET /api/v1/health?server_id=1`. Accept no request body or other query parameters.
Use lightweight checks
with bounded timeouts; do not perform a lengthy metric collection on each call.
This is a readiness check, not a historical metrics endpoint.

Server ID validation and lookup rules:

- Convert the ID using Python's `int()` and require a value of at least `1`.
  Negative numbers, zero, blank values, decimals, nonnumeric text, and repeated
  `server_id` parameters return `400 Bad Request`. Integer formatting accepted
  by `int()` (such as surrounding whitespace or a leading plus) is accepted.
  There is no application-specific 19-digit or 64-bit limit; values that Python
  cannot convert to an integer return `400`.
- A missing required `server_id` returns `422 Unprocessable Content`.
- A valid ID without a registered server returns `404 Not Found` before probes run.
- Currently only the local server is registered, with numeric ID `1`. This lookup
  does not add remote-server probing or a server registration API.

Healthy response (`200 OK`):

```json
{
  "server_id": 1,
  "status": "healthy",
  "checked_at": "2026-11-15T12:00:00Z",
  "checks": {
    "server": "up",
    "database": "up"
  }
}
```

If a required check fails or times out, return `503 Service Unavailable` and
a readiness report with `status: "unhealthy"`, each failed check marked `"down"`,
and a public `message`. For example, a database timeout produces `Database readiness check timed out.` A missing configuration or a probe exception has its own reason. The healthy report omits the message.
Health must still respond if the database is unavailable. Do not expose internal
addresses, exception messages, or credentials. CPU, memory, and disk measurements
belong to the metrics API.

### Current implementation limits

The health route is public and GET-only, rejects bodies/unknown query parameters, and
sets `Cache-Control: no-store`. Independent asynchronous probes run concurrently
with a 150 ms timeout each. Tests inject probes and a fixed UTC clock to
verify healthy, failed, exception, and timeout behavior.

Response-time target: most requests should complete within 150–200 ms under
normal conditions (95th percentile below 200 ms). Each probe has a 150 ms budget
and runs concurrently, leaving approximately 50 ms for request handling. A
timed-out probe is marked `down` and produces a structured `503`, even if the
dependency might otherwise succeed later. This is a performance target, not a
hard deadline: network delay, scheduling, heavy load, or probes that block the
event loop or suppress cancellation can exceed it. Future database probes must
use nonblocking I/O, respect cancellation, and fit this budget.

Local tests measure the 95th percentile of 20 warmed-up requests for both
healthy and unconfigured-database responses. Additional tests verify default
timeouts return `503` within 200 ms and cancel slow server/database probes,
including when both are slow. These tests do not establish deployed latency;
deployment requires measurement through the actual proxy and network.

The default server probe proves that the local API process can respond. It does
not inspect a remote host or report OS resource measurements. The application
database probe executes asynchronous PostgreSQL `SELECT 1` when configured.
Without credentials, or on connection/query failure or timeout, it reports
`database: down` and returns `503`. A successful query allows `200`.
See [local PostgreSQL setup](local-postgresql.md). Metrics and incidents use explicit Alembic migrations. If the entire API host
is offline, no response can be sent; the frontend handles connection failure.
A failed probe means unhealthy or unreachable, not that the server ID is absent.

## Metrics API

Implemented with SQLAlchemy/PostgreSQL and an explicit Alembic upgrade. See
[local metrics setup](local-postgresql.md#enable-metrics-storage-python-postgresql-alembic).
GET requires the reader token; POST requires a distinct collector token. Both
support environment and `_FILE` configuration. A valid token for the other role
returns `403`; missing role configuration fails closed with `503`. Admin credentials are implemented for incident writes; production scheduling remains pending. A simple local test
collector now POSTs real host samples (see [local development](local-development.md)).
Schema/connection failures
return `503`; unexpected failures return sanitized `500`.

The initial fields cover host statistics, not arbitrary application measurements.
The server ID comes from configuration and is stored internally on every sample;
it cannot be supplied in a POST body or GET query. Changing the configured ID
selects that server's history. The server/time uniqueness index also supports
filtered history reads. SQLAlchemy handles transactions and pooled connections;
database work runs in worker threads to keep the API event loop responsive.

### `POST /metrics`

Store one sample submitted by the authorized collector. This endpoint records
measurements; it does not change the server's CPU, memory, or disk configuration.

Request:

```json
{
  "collected_at": "2026-11-15T12:00:00Z",
  "cpu_percent": 27.5,
  "memory_percent": 61.2,
  "disk_percent": 43.8,
  "uptime_seconds": 86400
}
```

| Field | Type | Validation |
| --- | --- | --- |
| `collected_at` | datetime | Required, timezone-aware; cannot be in the future |
| `cpu_percent` | number | Required, finite, from 0 through 100 |
| `memory_percent` | number | Required, finite, from 0 through 100 |
| `disk_percent` | number | Required, finite, from 0 through 100 |
| `uptime_seconds` | integer | Required, 0–9223372036854775807 (PostgreSQL BIGINT) |

Reject strings or booleans in numeric fields. Historical samples are allowed.
Use API receipt time when checking whether a timestamp is in the future; collectors
must keep their clocks synchronized.

Return `201 Created` with the submitted fields and a generated `id`:

```json
{
  "id": "bf7dc095-3ee2-4ae1-9de7-a5eb8cadf8e9",
  "collected_at": "2026-11-15T12:00:00Z",
  "cpu_percent": 27.5,
  "memory_percent": 61.2,
  "disk_percent": 43.8,
  "uptime_seconds": 86400
}
```

Treat the collection timestamp as unique for this server. Repeated submissions
with the same timestamp return `409 Conflict` without creating another row.

### `GET /metrics`

Return stored samples, newest collection time first, with ID ascending as a
tiebreaker. An empty collection returns `200 OK`, not `404`.

Optional query parameters:

| Parameter | Default | Validation / behavior |
| --- | --- | --- |
| `limit` | 50 | Integer, 1–100 |
| `offset` | 0 | Integer, 0–9223372036854775807 |
| `start` | Unset | Timezone-aware datetime; inclusive lower collection time |
| `end` | Unset | Timezone-aware datetime; inclusive upper collection time |

If both time bounds are provided, require `start <= end`. Invalid parameters
return `422`. To retrieve the latest stored sample, use `GET /metrics?limit=1`.
This reads stored data and does not trigger a new measurement.

Response shape (each item has the fields shown in the POST response):

```json
{
  "items": [],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

`total` is the number of matching records before pagination.

## Server API

### `GET /server`

Return identity and operating system information only. Accept an optional
`server_id` query parameter, for example `GET /api/v1/server?server_id=1`.
When omitted, return the configured local server. Use the same positive integer
validation as health: conversion with `int()`, minimum `1`, no duplicate values.
Accept no request body or other query parameters. Metric values and incident
records are served by their own APIs. Selection does not add remote probing or
registration of additional servers.

Response (`200 OK`):

```json
{
  "id": 1,
  "name": "ServerWatch production server",
  "hostname": "serverwatch-01",
  "os_type": "Linux",
  "os_name": "Ubuntu",
  "os_version": "24.04",
  "architecture": "x86_64"
}
```

The example values are illustrative. Read actual host information from the
configured monitored server; a container's hostname or OS must not accidentally
be reported as the host's identity. `id` is stable across restarts; `name` is a
configured display name. Defaults are ID `1` and name `ServerWatch server`;
configure them with `SERVERWATCH_SERVER_ID` and `SERVERWATCH_SERVER_NAME`.
Health uses that same configured ID. Return `503` if server information is unavailable.
There are no server creation, update, or deletion endpoints in this scope.

Implemented error handling:

| Situation | Response |
| --- | --- |
| Valid reader token and complete host metadata | `200` |
| Invalid, zero, negative, or repeated `server_id` | `400` |
| Valid `server_id` is not registered | `404` |
| Missing, wrong, or non-Bearer credentials | `401`, with `WWW-Authenticate: Bearer` |
| Unknown query parameters or a request body | `422` (after authentication) |
| Unsupported HTTP method | `405`, with `Allow: GET` |
| Unreadable/incomplete host metadata or detected container without host source | `503` |
| Reader credential is unconfigured and a bearer token is supplied | `503`, fail closed |
| Unexpected application failure | Sanitized `500` |

This endpoint selects the one configured server by default or by matching its ID.
Unknown IDs return `404` before metadata is read. A missing metadata source for a
known server is `503`, not `404`. Normal unknown routes still return `404`.
Responses contain only the documented identity fields and disable caching.

Reader authentication uses one configured read-only bearer token, not a user
account or a complete role system. Supply `SERVERWATCH_READER_TOKEN` locally or
`SERVERWATCH_READER_TOKEN_FILE` for a protected mounted file (file takes precedence).
Missing credentials never make the endpoint public. Blank/whitespace-containing
tokens and unreadable secret files prevent startup with a sanitized error.
No real token is created or committed by this implementation. Collector
permissions are implemented for metrics POST; admin permissions are implemented for incident writes.

Native host metadata comes from Python's `platform` module; Linux distribution
name/version come from `freedesktop_os_release()`. Common container markers are
rejected to avoid reporting a container as the host. This is not exhaustive
container detection. WSL reports its Linux environment, not the Windows host;
future container deployment needs an explicitly supplied host metadata source.
No database, shell commands, SSH, or cloud requests are needed.

### Testing the server endpoint

Recommended and implemented approach: test the service with fixed metadata, then
test HTTP behavior using FastAPI TestClient. Patch the OS metadata source so a
Windows developer and Linux CI receive the same test results; do not assert that
the test machine is Ubuntu or require a live EC2 instance.

- Service tests: configured ID/name, Linux distribution extraction, non-Linux
  metadata, and rejecting container metadata as host identity.
- HTTP tests: exact `200` fields and stable identity across requests; no metric
  or incident fields; optional matching IDs give `200`, invalid/duplicate IDs
  give `400`, and unknown IDs give `404` without reading host metadata;
  `401` for invalid credentials; `422` for unsupported input;
  `405` for unsupported methods; `503` for missing/unreadable metadata and missing
  credential configuration; sanitized `500` for unexpected bugs.
- Configuration/security tests: invalid server settings, token file precedence,
  hidden token representation, invalid tokens, and unreadable files. Use dummy
  credentials and temporary test files exclusively.
- Deployment smoke test still needed: verify the reported ID, hostname, and OS
  against the actual native EC2 host, and later the container host metadata source.

This test selection is our project recommendation based on official guidance:
[FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/),
[dependency overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/),
and [Python platform metadata](https://docs.python.org/3/library/platform.html).
Dependency overrides can isolate service/auth dependencies; source patching is
used here to also exercise the real service and authentication code.

## Incident API

Incidents record server errors, outages, or other operational problems. Records
remain stored until explicitly deleted, including after resolution. This API
supports recording incidents; automatic incident detection is separate work.

Implemented with PostgreSQL. Apply migrations through `0004_incident_triggers` with the existing
upgrade command before testing; see [local incident setup](local-postgresql.md#enable-incident-storage-python-postgresql).
GET uses the reader token. POST/PATCH/DELETE require a distinct
`SERVERWATCH_ADMIN_TOKEN` or `SERVERWATCH_ADMIN_TOKEN_FILE` (file takes precedence).
Roles are separate: the admin token does not grant reader or collector access.
A recognized token for another role returns 403, missing/invalid credentials
return 401, and an unconfigured required role returns 503. Duplicate role tokens,
blank tokens, or unreadable configured secret files prevent startup safely.

All operations disable caching. POST/PATCH require JSON and reject query
parameters. GET-by-ID and DELETE reject query parameters and bodies; list GET
accepts only the documented filters and pagination, once each. Missing tables,
connection failures, pool/lock timeouts return sanitized 503; unexpected failures
return sanitized 500. Writes are transactional; updates/deletes lock their record
so concurrent changes cannot corrupt status/resolution consistency. Concurrent
edits serialize, with the last successful edit to a field taking effect.

The React dashboard reads incidents with the reader token and uses the separate
admin token to save changes. Planned records store a scenario and response steps.

### `POST /incidents`

Request:

```json
{
  "title": "Disk usage above threshold",
  "description": "Root filesystem usage exceeded the configured threshold.",
  "severity": "warning",
  "occurred_at": "2026-11-15T12:00:00Z"
}
```

| Input field | Validation |
| --- | --- |
| `title` | Required string; trim whitespace; 1–200 characters; no null characters |
| `description` | Required string; trim whitespace; 1–5000 characters; no null characters |
| `severity` | Required enum: `info`, `warning`, `critical` |
| `occurred_at` | Required field. Send a timezone-aware datetime for an actual incident, or `null` to save a plan. A datetime cannot be in the future. |
| `trigger` | Optional rule with `metric` (`cpu`, `memory`, `storage`, or `gpu`), `threshold_percent` (0–100), and `duration_seconds` (whole number, 5–600). Send `null` in PATCH to remove it. |

The dashboard compares stored samples at or above the threshold. A matching
rule highlights a plan for manual review. GPU rules can be saved, and their
readings stay unavailable until GPU collection is implemented.

Return `201 Created`, a `Location: /api/v1/incidents/{incident_id}` header, and the
complete record:

```json
{
  "id": "d2860789-521f-4747-b072-ba9fd104ba54",
  "title": "Disk usage above threshold",
  "description": "Root filesystem usage exceeded the configured threshold.",
  "severity": "warning",
  "status": "open",
  "occurred_at": "2026-11-15T12:00:00Z",
  "created_at": "2026-11-15T12:01:00Z",
  "updated_at": "2026-11-15T12:01:00Z",
  "resolved_at": null
}
```

The API generates the ID, timestamps, and initial status. A null occurrence
starts as `planned`, and a dated occurrence starts as `open`. Editing a plan
without changing its status leaves the occurrence blank. Changing its status to
`open`, `investigating`, or `resolved` records the current time as the occurrence.
Clients cannot
set these fields on creation. Separate reports may describe the same problem;
incident creation does not deduplicate on title.

### `GET /incidents`

Return `items`, `total`, `limit`, and `offset`, using the same pagination rules as
metrics. Each item is a complete incident record. Sort by `created_at` descending,
then ID ascending. Empty results return `200` with `items: []` and `total: 0`.

Optional filters: `status` (`planned`, `open`, `investigating`, `resolved`) and `severity`
(`info`, `warning`, `critical`). Apply supplied filters together before counting
and pagination. Invalid filters return `422`.

### `GET /incidents/{incident_id}`

Return the complete record with `200 OK`. A valid UUID that does not exist returns
`404 Not Found`; a malformed UUID returns `422 Unprocessable Entity`.

### `PATCH /incidents/{incident_id}`

Accept one or more of `title`, `description`, `severity`, and `status`. Reuse the
creation constraints for title, description, and severity. Status must be `open`,
`investigating`, or `resolved`. Omitted fields keep their current values; explicit
nulls, empty objects, and unknown or read-only fields return `422`.

```json
{
  "status": "resolved",
  "description": "Removed old logs and confirmed normal disk usage."
}
```

All transitions between the three valid statuses are allowed. When moving into
`resolved`, set `resolved_at` to current UTC time. When reopening to `open` or
`investigating`, clear it. Updating an already resolved record without changing
its status preserves its existing resolution time. Set `updated_at` on every
successful update and return the complete record with `200 OK`.

Validate the entire change before writing; invalid input must not partially
update a record. Missing incidents return `404`.

### `DELETE /incidents/{incident_id}`

Permanently remove the record and return `204 No Content` with no response body.
A subsequent read or delete returns `404`. A malformed ID returns `422`. Do not
accept a request body or query parameters.

## Validation and error-handling rules

**Required for every operation and every handled error code.** The public response
must explain why the operation failed. Include the violated input rule, required
role, missing resource or failed dependency when known. Use a field detail when
the schema can identify the field. For unknown internal failures, state that
server-side processing failed and keep technical diagnostics private. Verify
the public reason through the affected endpoint. This rule covers framework
routing, authentication, schema validation, reads, writes and deletes.

Every endpoint accepting input must validate its body, path, and query parameters
before performing side effects. Reject unexpected query parameters and request
bodies on endpoints that do not support them.

| Status | Meaning |
| --- | --- |
| 400 | Malformed JSON; invalid or repeated `server_id` on health or server |
| 401 | Missing or invalid credentials; include `WWW-Authenticate: Bearer` |
| 403 | Authenticated caller lacks the required permission |
| 404 | No matching registered server, incident, or route |
| 405 | Method is not supported |
| 409 | Duplicate metric collection timestamp |
| 415 | Request body uses an unsupported content type |
| 422 | Valid JSON with invalid fields, types, constraints, path, or query values |
| 500 | Unexpected internal error |
| 503 | Required dependency or server information is unavailable |

Use a consistent error response for all errors except the health check's
structured unhealthy response:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "body.cpu_percent",
        "message": "Input should be less than or equal to 100"
      }
    ]
  }
}
```

For example, the response above applies to a CPU percentage of 101. On health
and server lookups, `error.message` directly explains a rejected ID:

| Request input | Status | Explanation returned |
| --- | --- | --- |
| `server_id=-1` or `server_id=0` | 400 | server_id must be at least 1. |
| `server_id=abc` | 400 | server_id must be a whole number. |
| `server_id=1&server_id=2` | 400 | Supply server_id exactly once. |
| Omitted on health | 422 | `details` identifies `query.server_id` and says the field is required. |
| Valid ID with no registered server | 404 | No server is registered with this ID. |

| Operation or failure | What the caller learns |
| --- | --- |
| Any protected read or write (401, 403) | A Bearer credential is missing or malformed, the token is unrecognized, or the operation needs a different named role. A missing server-side role configuration returns 503. |
| Unknown path or unsupported method (404, 405) | The path has no matching route, or the route does not support the method. A 405 preserves the framework's Allow header. HEAD responses follow HTTP bodyless semantics. |
| Metric or incident POST, incident PATCH (400, 415, 422) | Invalid JSON syntax, the required JSON media type, or the field and rule that failed. An empty PATCH identifies the requirement to supply at least one change. |
| Metric POST (409), metrics GET (422) | The collection timestamp already exists for this server, or a filter is repeated, incorrectly formatted or out of order. |
| Incident detail GET, PATCH or DELETE (404, 422) | No record exists with that ID, or the path ID must be a UUID. Successful DELETE remains an empty 204. |
| Server identity and database operations (503) | The native identity source is unavailable or incomplete, storage is unconfigured, a required schema object is missing, a lock or timeout prevented completion, or PostgreSQL failed to complete the operation. Each reason reflects evidence from the failing check. |
| Unexpected processing failure (500) | The server encountered an internal failure while processing the request. A response that fails output validation identifies the server-side schema mismatch. Raw exception details stay private. |

Use stable machine-readable codes, for example `not_found`, `conflict`,
`internal_error`, and `service_unavailable`. Use `details: []` when no field-level
information applies. Do not echo submitted credentials or sensitive values.
FastAPI's default error format differs: implementation must normalize framework
validation and HTTP errors to this contract, including malformed JSON as `400`.

Catch expected domain and persistence errors explicitly. Roll back failed
transactions and avoid partial writes. Log unexpected failures internally with
sanitized context; return a generic `500` message without stack traces, SQL,
connection strings, or secrets. Do not turn failures into successful empty data.

## Required tests

Write backend unit tests under `backend/tests/` using `pytest`, plus API contract
tests using FastAPI's test client when the backend is implemented. Unit tests
should isolate services using injected repositories, clocks, and health probes.
API tests should verify routing, validation, serialization, and error translation.

| Area | Required coverage |
| --- | --- |
| Health | Valid registered ID and healthy probes give `200`; invalid IDs give `400`; unknown IDs give `404`; missing ID gives `422`; failed/exception/timed-out probes give `503`; unexpected bugs give sanitized `500` |
| Metrics creation | Valid creation; 0 and 100 boundaries; missing fields; negative, over-100, nonfinite, boolean and string values; invalid/future timestamps; duplicate timestamp |
| Metrics reading | Empty results; latest sample; ordering; pagination and bounds; time filters; reversed time range |
| Server | Expected identity fields; actual host metadata source; unavailable source returns `503` |
| Incident creation/read | Valid creation and generated fields; list/get; filters; pagination; empty results; invalid UUID and missing record |
| Incident validation | Blank/oversized text; invalid severity/status; missing fields; explicit nulls; future timestamps; unknown/read-only fields |
| Incident updates | Partial update preserves omitted fields; empty update rejected; resolution/reopening timestamps; invalid update leaves data unchanged |
| Incident deletion | `204` has no body; deleted record cannot be read; repeated delete gives `404` |
| Shared behavior | Authentication and permissions; `405` and `Allow`; malformed JSON; wrong content type; unsupported inputs; consistent errors |
| Failure handling | Repository failure rolls back; unavailable dependency gives `503`; unexpected failures give sanitized `500` |

Use fixed clocks for time assertions and isolated fixtures for each test. Tests
must not call a live EC2 instance or production database. Add separate persistence
integration tests against an isolated database for constraints, transaction
rollback, and CRUD persistence. The foundation has executable shared-error and
configuration tests. Run
`python -m pytest backend/tests -q` after installing development dependencies.
Metrics endpoint and PostgreSQL persistence coverage are implemented. Integration
tests use a private temporary PostgreSQL cluster and skip if server tools are
unavailable. Incident tests cover CRUD, filtering, resolution/reopening, rollback,
server isolation, safe storage failures, and upgrading an existing metrics schema.

## Code comments and multiline explanations

- Use docstrings to explain each route/service's purpose, inputs, return value,
  and important error behavior.
- Add comments explaining intent, assumptions, and non-obvious decisions,
  especially health checks, timestamp rules, transaction handling, and incident
  status transitions.
- Use multiline docstrings for explanations spanning several steps. Use multiline
  formatting for long signatures, calls, conditions, and data structures.
- Keep explanations accurate as behavior changes; avoid comments that simply
  repeat an obvious line of code.

Illustrative service documentation (not an implementation):

```python
def update_incident(incident_id, changes, repository, clock):
    """Update the supplied fields of an existing incident.

    Validate all changes before persistence. Use the injected clock to manage
    resolution timestamps consistently and keep time-dependent tests repeatable.
    Raise a domain not-found error when the incident does not exist.
    """
    # Preserve resolution time when editing an already resolved incident.
    # Clear it when reopening so the timestamp reflects the current status.
    ...
```
