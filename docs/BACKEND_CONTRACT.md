# NeuroForge: proposed Java ↔ AI integration contract

**Status: proposal for teammate review.** The URLs and backend responses below
are to be implemented by Java. The Python HTTP adapter now targets this
proposal and has simulated HTTP tests; live Java verification is pending.
Current Python endpoints are in `ai-service.openapi.json`; default lookups
still use `MockEmployeeBackend`. See BACKEND_SETUP.md for explicit HTTP mode.

## Responsibility split

| Component | Owns |
| --- | --- |
| React | Employee selection, request fields, draft display, progress display |
| Java / Spring Boot | Login, requester authorization, employee records, role policies, request persistence, two distinct approvals, notifications, audit, applying access changes |
| Python / FastAPI / LangGraph | Interpretation, missing-detail questions, permission comparison, structured draft planning; later, authorized request creation through Java |

The local HTML form calls Python directly only to demonstrate the AI service.
For the integrated architecture in the project report, React calls Java;
Java authenticates/authorizes the user and delegates planning to Python.
Python calls Java's employee and policy endpoints. These data endpoints must
not delegate back to Python, which would create a request loop.

```text
React request form
    -> Java authenticated planning route (proxy URL to be agreed)
        -> Python POST /agent/role-change or /agent/offboard
            -> Java employee / role policy endpoints
        <- structured draft
    <- draft for review

Explicit request submission (implemented adapter; Java integration pending)
    -> Java creates PENDING_APPROVAL request
    -> Java notifies two approvers
    -> two authenticated decisions
    -> APPROVED
    -> authorized HR applies the approved plan
    -> APPLIED
```

Generating a draft never creates an access request. `details_complete: true`
does not mean approved, authorized, submitted, or ready to execute. Current
Mock drafts always have `ready_for_submission: false`. Authenticated HTTP-mode
drafts can become ready after detail, change, and version checks; this is not
approval or proof that a request has been created.

## Proposed Java endpoints

Development base URL: `http://127.0.0.1:8081`. All data is JSON with snake_case
field names. If the existing Java API uses camelCase or an envelope, implement
the translation in the Python HTTP adapter after agreeing on actual examples.

| Method | Proposed path | Successful response |
| --- | --- | --- |
| GET | `/api/employees` | 200, array of employee records |
| GET | `/api/employees/{employee_code}` | 200, one employee; 404 if unknown |
| GET | `/api/roles` | 200, array of role policies |
| GET | `/api/roles/{role}/permissions` | 200, one role policy; 404 if unknown |
| POST | `/api/access-requests` | 201, persisted request in PENDING_APPROVAL |

Authentication is required on Java endpoints. The integrated Python client
must use an agreed server-side credential/delegated identity mechanism and
must not receive credentials from model output or message text. Backend
authorization uses a verified requester identity; a caller-supplied `actor_id`
or plain requester header is not trusted. Exact JWT/session delegation and
proxy route design remain integration decisions, not implemented features.

### Employee record

```json
{
  "employee_code": "EF-1001",
  "name": "Aarav Sharma",
  "department": "Engineering",
  "role": "ENGINEER",
  "permissions": ["GIT_READ", "GIT_WRITE", "JIRA_EDIT", "VPN_ACCESS"],
  "version": 1
}
```

`permissions` must contain the employee's actual current permissions, not a
fresh copy of their nominal role policy. `version` is a proposed addition for
detecting stale plans; it is supported as an optional positive integer by the
Python Employee model. It is required for HTTP submission. Agree on matching
version handling in Java before enabling request submission.

The list endpoint returns the same record shape in an array. The prototype
has seven synthetic employees; pagination/search can be added by agreement.
The manager picker uses employee codes, with display names for convenience.
Java must validate reporting-manager eligibility, not merely existence.

### Role policy

```json
{
  "role": "MANAGER",
  "permissions": ["TEAM_DIRECTORY", "REPORT_VIEW", "JIRA_EDIT", "VPN_ACCESS"],
  "version": 1
}
```

Supported role names currently are ENGINEER, MANAGER, HR, FINANCE. `version`
is supported as an optional positive integer in Python and required for
role-change submission. Java must implement it consistently. Changing the
role catalog requires updating Python's typed role choices too.

Policy assumption requiring agreement: a role change replaces the employee's
permission set with the target role's complete permission set. The report's
"key permissions" are currently treated as complete sets. Exceptions and
separately granted entitlements are not modeled. Do not enable real execution
until the team has agreed how these should be preserved or revoked.

### Create a role-change request

Request header: `Idempotency-Key: <stable UUID for this submission>`.

The following is a **proposed Java submission payload**, not the payload accepted
by the current Python `/agent/role-change` draft endpoint:

```json
{
  "action": "ROLE_CHANGE",
  "employee_code": "EF-1001",
  "expected_employee_version": 1,
  "expected_policy_version": 1,
  "current_role": "ENGINEER",
  "target_role": "MANAGER",
  "effective_date": "2026-11-23",
  "justification": "Taking responsibility for the engineering team.",
  "manager": "EF-1002",
  "assignment_type": "PERMANENT",
  "proposed_permissions": {
    "grant": ["REPORT_VIEW", "TEAM_DIRECTORY"],
    "revoke": ["GIT_READ", "GIT_WRITE"],
    "retain": ["JIRA_EDIT", "VPN_ACCESS"]
  }
}
```

Java derives the initial status, required approvals, requester, approvers, and
timestamps server-side. Python cannot provide approval counts or request an
APPROVED/APPLIED status. Java rechecks current employee data, policy, proposed
permission differences, manager eligibility, requester authorization, and date
rules before persisting the request. A stale snapshot produces 409 and requires
a fresh plan; never silently approve a different plan.

Optional request context is now supported by the Python form and draft schema:

```json
{
  "request_context": {
    "request_title": "Engineering leadership transition",
    "priority": "NORMAL",
    "requester_reference": "HR Operations (demo)",
    "business_unit": "Engineering"
  }
}
```

Java should accept this optional object alongside the submission fields above.
Python forwards it when context differs from its defaults; otherwise it omits
the object for compatibility. Priority is LOW/NORMAL/HIGH urgency, not a risk
classification. `requester_reference` is untrusted descriptive text, never
the authenticated requester, an actor override, or approval evidence. Java
must continue deriving identity from the validated login token.

Proposed 201 response:

```json
{
  "request_id": "AR-000001",
  "action": "ROLE_CHANGE",
  "employee_code": "EF-1001",
  "status": "PENDING_APPROVAL",
  "required_approvals": 2,
  "approved_count": 0
}
```

On retry with the same key and identical payload, return the same request
(200 is acceptable). The same key with a different payload returns 409.
This prevents duplicate requests after network timeouts. If creation succeeds
but notification delivery fails, retain the created request and retry email
delivery separately. Do not create another request merely to retry an email.

### Create an offboarding request

Use the same Java creation endpoint and authentication/idempotency rules:

```json
{
  "action": "OFFBOARD",
  "employee_code": "EF-1001",
  "expected_employee_version": 1,
  "current_role": "ENGINEER",
  "target_role": null,
  "effective_date": "2026-11-23",
  "justification": "Employee departure.",
  "manager": "EF-1002",
  "assignment_type": null,
  "proposed_permissions": {
    "grant": [],
    "revoke": ["GIT_READ", "GIT_WRITE", "JIRA_EDIT", "VPN_ACCESS"],
    "retain": []
  }
}
```

Java must validate that all actual current permissions are included in revoke.
Offboarding still starts at PENDING_APPROVAL and requires two distinct
authenticated approvers. Draft planning does not delete an account or archive
employee records. Account disablement and archival/retention behavior need
separate agreement. Do not interpret ARCHIVE as OFFBOARD automatically.

## Error behavior

Proposed Java error body:

```json
{
  "code": "EMPLOYEE_NOT_FOUND",
  "message": "The employee code was not found.",
  "request_id": null
}
```

| HTTP | Meaning / Python behavior when HTTP integration is added |
| --- | --- |
| 400 / 422 | Invalid fields or unsupported policy; return actionable feedback |
| 401 | Authentication required or credential expired; do not retry as anonymous |
| 403 | Caller lacks authority; do not create or modify anything |
| 404 | Employee or role policy missing; stop draft/submission |
| 409 | Stale plan or conflicting idempotency payload; refresh or correct |
| 429 | Rate limited; communicate retry guidance |
| 5xx / network timeout | Backend unavailable; never substitute mock data or claim success |

Current Python validation uses FastAPI's HTTP 422 body and draft outcome
statuses such as `employee_not_found`. The HTTP backend client now implements
safe error translation; actual Java compatibility remains unverified.

## Approval and application requirements owned by Java

- Two distinct authenticated approvers; repeated approval by one account does
  not increase the count. Agree whether requesters may approve their own requests.
- Decisions are bound to the exact reviewed request/permission snapshot.
  Editing that snapshot invalidates approvals.
- After both approvals, status becomes APPROVED. Applying is a separate,
  authorized HR action, as specified in the demonstration flow.
- Apply validates the effective date and detects changes since review. If
  employee permissions or policy changed, require a fresh plan and approvals.
- Persist permission changes and request outcome transactionally. Record
  failures truthfully rather than displaying APPLIED after partial execution.
- Log requester, approvers, timestamps, decisions, approved snapshot, and
  application outcome in the backend's audit system.

These are integration requirements, not guarantees supplied by current Python
code. Gmail notifications, approval UI, and audit persistence belong to Java.

## Decisions to confirm with the backend teammate

1. Existing endpoint URLs, authentication/delegation, and exact JSON field names.
2. Whether listed role permissions are complete, and how access exceptions work.
3. Employee/policy versioning and snapshot validation at submission and apply.
4. Approver assignment and self-approval policy; reporting manager is not
   automatically an approver.
5. Date/timezone rules, past dates, future-dated apply behavior, and temporary
   access. Python currently records TEMPORARY metadata without expiry. Until
   execution/expiry rules exist, reject temporary submission or keep it draft-only.
6. Archival semantics and record retention separately from permission revocation.

## Integration checks after Java is available

Verify a successful role-change draft and offboarding draft against real Java
read endpoints; unknown employee, expired login, forbidden requester, backend
timeout, and malformed backend responses; stale version rejection; duplicate
submission yielding one request; initial approval count 0/2; no permission
mutation before two distinct approvals and authorized apply.

Until that integration passes, keep the default standalone service in mock
mode with submission disabled; use HTTP mode only for explicit integration testing.
