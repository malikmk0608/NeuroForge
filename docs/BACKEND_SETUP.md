# Connecting the Java backend

The HTTP adapter and submission path are implemented against
`BACKEND_CONTRACT.md`. Automated tests use a simulated Java API. No live Java
backend has been tested; the teammate implementing Java must confirm paths,
field names, token delegation, atomic snapshot checks, and idempotency semantics.

## Default standalone mode

`BACKEND_MODE=mock` (the default) keeps existing sample data and the local form
working. Drafts show `backend_mode: mock`, `ready_for_submission: false`.
`POST /agent/submit` returns 409 `MOCK_SUBMISSION_DISABLED` without persisting
anything. There is no fake approval workflow or in-memory request store.

## HTTP mode

After Java implements the proposed endpoints and user authentication:

```zsh
export BACKEND_MODE=http
export BACKEND_BASE_URL=http://127.0.0.1:8081
python -m uvicorn app.main:app --reload --port 8002
```

Restart is required when changing backend configuration. Keep the Groq settings
from GROQ_SETUP.md if optional model interpretation is needed. No model call
is necessary for structured planning or submission revalidation.

HTTP mode uses these Java paths:

| Operation | Java endpoint |
| --- | --- |
| List employees | GET /api/employees |
| Employee access | GET /api/employees/{employee_code} |
| List role policies | GET /api/roles |
| Role permissions | GET /api/roles/{role}/permissions |
| Create pending request | POST /api/access-requests |

Every Python planning/list/submission call in HTTP mode requires
`Authorization: Bearer <backend-issued user token>`. It is forwarded only to
the configured Java backend, not the model provider. Java validates the token
and requester authority. Python checks the header format but does not validate
JWT signatures itself; a correctly shaped token is not proof of authorization.
The health endpoint makes no backend call and is not an authentication check.

The local HTML form has no login/token flow and is intended for mock mode.
For HTTP integration use authenticated API requests or the team's React → Java
proxy. Do not add a shared privileged token to browser code. No server-owned
service credential is silently substituted for a missing user token.

The adapter accepts local HTTP and remote HTTPS only, verifies certificates,
does not follow redirects, uses a 10-second HTTP timeout per call, and makes no
automatic retries or fallback to mock records. It validates backend JSON, field
types, requested employee identity, requested policy identity, and submission
receipt state. Backend URLs/credentials cannot be supplied through the request
message, model output, or submission JSON.

## Draft snapshot and readiness

Java employee and role responses should include a positive integer `version`.
The draft includes `expected_employee_version` and `expected_policy_version`.
Offboarding uses only employee version and has no target policy.

`ready_for_submission` becomes true only in HTTP mode with complete validated
details, actual changes, versioned records, and no temporary assignment. It
means eligible for submission checks; it never means approved or applied.
Unversioned HTTP records can be displayed in drafts but cannot be submitted.
Temporary assignments remain draft-only until expiry rules are implemented.

## Explicit submission

Generate and review a draft first. Then call Python `POST /agent/submit`:

- Header `Authorization: Bearer <backend-issued user token>`.
- Header `Idempotency-Key: <UUID generated once for this submission>`.
- JSON body `{"plan": <the full reviewed plan object>}`.

Do not send the entire AgentResponse; put its `plan` inside the body. Reuse
the same UUID only when retrying that same submission, including after a
timeout. Generate a new key for a genuinely new or changed request.

The service treats supplied readiness, permissions, roles, risk, and completion
flags as untrusted. It fetches fresh employee, manager, and policy data, recomputes
the permission lists without another model call, rejects incomplete/no-change/
temporary requests, checks reviewed versions and permissions, then posts the
fresh validated payload to Java. A stale or modified reviewed snapshot gets 409
and is not posted. Java must still atomically compare versions at creation and
again enforce reviewed-plan/approval requirements before applying.

Optional `plan.request_context` contains request_title, priority,
requester_reference, and business_unit. Non-default context is forwarded as
an optional object in the Java creation payload. Confirm Java supports these
fields. The requester reference is descriptive only; identity and authority
must still come from the login token. Priority does not override risk or approvals.

Java derives status and approvals. The Python outbound payload contains no
APPROVED/APPLIED instruction, requester override, or approval count. A receipt
is accepted only if it matches the submitted action/employee and reports
PENDING_APPROVAL, required_approvals=2, approved_count=0. A malformed or unexpected
receipt returns 502; creation may already have occurred, so check with Java and
retry only with the same key. Python cannot undo a backend side effect from an
invalid receipt, and it does not claim the submission failed atomically.

Python returns HTTP 200 for a validated receipt, whether Java returned 201 for
first creation or 200 for an idempotent replay. Java owns durable duplicate
prevention. Python does not implement cross-request storage or pretend that
forwarding the key guarantees backend idempotency.

## Failure responses

Errors return `detail` and `code`. Unknown read records stop the planning graph.
Authentication failures stay 401/403; validation and policy rejection stay
400/422; conflicts stay 409; rate limits stay 429; network failure is 503;
timeout is 504; invalid JSON/schema/receipt or unexpected upstream status is 502.
Provider bodies, user tokens, and raw exception text are not exposed.

After a POST timeout, the error explicitly marks creation outcome unconfirmed.
There is no automatic retry that could create duplicate approval requests.

## Tested versus pending

Simulated HTTP tests cover role-change and offboarding submission, employee and
policy reads, token forwarding, missing authorization, required idempotency keys,
backend idempotent replay, stale versions, changed actual access, tampered
permission lists, incomplete details, temporary/no-change blocking, missing
versions, 401/403/409/429/5xx, invalid responses, wrong identities, unexpected
approval states, mock-mode submission blocking, POST timeouts, and redirects.

Still pending: live Java integration, actual login/token delegation, authoritative
manager policy, durable backend idempotency, Gmail delivery, dual approval,
audit persistence, applying access changes, and final multi-service demo.
