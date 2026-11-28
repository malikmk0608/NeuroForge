# NeuroForge

**Workspace layout.** Run Python setup, tests, and scripts from `ai-service/`. Service-relative paths such as `app/` and `scripts/` below refer to that directory. Shared API contracts and saved smoke results are in the repository-level `docs/`.

The React portals support HR submission, two independent approver decisions, HR apply, and employee access updates against MySQL. Spring Boot serves the signed-in application and calls the FastAPI planner. Follow [the portal setup and walkthrough](START_HERE.md#run-the-three-login-portals) to provision local logins and verify a change. The standalone Python planning form is also available.

**Teammates: begin with [START_HERE.md](START_HERE.md).** It covers
prerequisites, Windows/macOS/Linux setup, private Groq configuration, each role's
next tasks, and a prompt for continuing with an AI coding assistant.
Repository-level [AGENTS.md](AGENTS.md) records the architecture and implementation boundaries.

## What is working

- Role-change planning, including promotions, demotions, and no-change requests.
- Offboarding plans that revoke all current permissions.
- Sorted Grant / Revoke / Retain lists calculated with Python set operations.
- Required effective date, justification, reporting manager, and assignment-type checks.
- Explicit missing-detail questions and conflict detection.
- Advisory risk suggestions with clear reasons; every change still requires two approvals.
- Groq-powered interpretation with strict structured output and local validation;
  OpenAI remains an optional alternative.
- Local request form with employee names, draft review, risk reasons, and activity steps.
- Editable mock defaults, request title,
  priority, requester reference, business unit, and read-only employee role/department.
- Optional **Describe the request → Use AI to fill form** workflow. The model fills
  the form; the requester reviews it and completes missing details before generating
  the final draft. Regular form entry needs no model key.
- Java HTTP adapter and explicit pending-request submission interface, tested against
  simulated Java responses. Real Java integration is pending the backend team.

**Validation:** 68 automated tests pass. All eight synthetic live Groq cases passed
in the final run; see [the saved results](docs/live-smoke-results.json). One initial
polite role-change case over-clarified; the prompt was refined and the full suite
rerun successfully. This is a smoke test, not proof of perfect language understanding.

## Start locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m uvicorn app.main:app --reload --port 8002
```

Open [the request form](http://127.0.0.1:8002/) or
[interactive API docs](http://127.0.0.1:8002/docs). On Windows, activate with
`.venv\Scripts\activate` instead. Python 3.13 is the tested version.

Port 8002 is used for this local handoff to avoid the earlier demo server on 8000.
The service can use port 8000 when it is free. Use the same port in the browser as
in the server command. Different server processes have different key environments.

Mock mode prefills an editable role-change request automatically. Choose the
request type and edit its details as needed. Demo effective dates
use the next weekday in Asia/Kolkata; no date scheduling or approval is performed.
The requester reference is labeled demo text and never supplies authentication.
HTTP mode does not auto-populate synthetic demo values.

Default `BACKEND_MODE=mock` uses seven synthetic employees and never submits,
approves, applies, or persists access changes. No API key is required for manual
form entry or deterministic planning. The local form has no production login.

## Where the Groq key is used

The key stays in the server environment. Selecting **Use AI to fill form** sends
only the description and supplied request details to the configured provider.
Groq extracts fields into typed JSON. Backend lookup and permission calculation
then run in Python. No employee database records or policy tables are added to
the model input, and no tools or permission-changing authority are given to it.

The regular **Generate access plan** form button sends typed fields and makes no
model call. API clients can explicitly select the model with `use_model: true`.
The form shows whether the current server has a provider configured; configuration
is not a guarantee of provider availability. Review extracted fields before continuing.

Follow [Groq setup](docs/GROQ_SETUP.md) to enter the key privately, or
[OpenAI setup](docs/MODEL_SETUP.md) for that alternative. Never commit real keys;
`.env.example` documents variable names, `.env` is ignored, and automatic `.env`
loading is not implemented. Provider selection is explicit; no silent fallback occurs.

## Workflow and ownership

```text
Interpret → Retrieve Employee → Compare Permissions → Create Plan
```

The graph stops when the requested employee/action/role needs clarification or a
record/policy is missing. Once intent is clear, missing request metadata can still
be shown alongside a draft. `extracted_details` supports partial form prefill.

Java owns authentication, authorization, employee/policy data, request persistence,
idempotency, two distinct approvals, Gmail, audit records, and applying changes.
In the integrated application, React calls authenticated Java routes that delegate
planning to Python. The standalone form directly calls Python only for this demo.

## API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Service status, backend mode, non-secret model configuration |
| GET | `/agent/form-options` | Employee/role choices and non-secret model configuration |
| POST | `/agent/role-change` | Typed employee_code, target_role, and details → draft |
| POST | `/agent/offboard` | Typed employee_code and details → offboarding draft |
| POST | `/agent/plan` | Message, optional details, and use_model flag → interpretation/draft |
| POST | `/agent/submit` | Revalidate reviewed plan and ask Java to persist PENDING_APPROVAL |

Example typed request to `/agent/role-change`:

```json
{
  "employee_code": "EF-1001",
  "target_role": "MANAGER",
  "request_context": {
    "request_title": "Engineering leadership transition",
    "priority": "NORMAL",
    "requester_reference": "HR Operations (demo)",
    "business_unit": "Engineering"
  },
  "details": {
    "effective_date": "2026-11-23",
    "justification": "Leading the engineering team.",
    "manager": "EF-1002",
    "assignment_type": "PERMANENT"
  }
}
```

Employee EF-1001 currently has the ENGINEER role. This draft grants REPORT_VIEW
and TEAM_DIRECTORY, revokes GIT_READ and GIT_WRITE, and retains JIRA_EDIT and
VPN_ACCESS. No current access changes while generating it.

`request_context` is optional descriptive metadata preserved in the draft.
Priority is urgency, independent of the computed risk suggestion. On HTTP
submission, non-default context is forwarded to Java as `request_context`;
Java must support this optional object and still derive the authenticated
requester from the token rather than `requester_reference`.

For message input, `/agent/plan` accepts:

```json
{
  "message": "Could you give EF-1001 the MANAGER role?",
  "use_model": true
}
```

This calls the configured provider. `use_model` defaults to false; rule-based
input supports direct role changes and offboarding. Details can be structured or
explicitly marked clauses, such as `effective date: 2026-11-23; manager: EF-1002`.
Names alone and ambiguous relative dates require clarification.

## Java integration and submission

The default mock service has submission disabled. In HTTP mode, each list/planning/
submission call requires a backend-issued Bearer token forwarded to Java. Drafts
need complete details, actual changes, supported assignment types, and versioned
records before becoming eligible for submission.

`POST /agent/submit` takes `{"plan": <reviewed plan>}` and an `Idempotency-Key`
UUID header. It fetches fresh records and recomputes the plan without another
model call. Stale/modified permissions or versions, incomplete details, no-change
requests, and temporary assignments are blocked. Java must enforce authorization,
atomic version checks, and durable idempotency itself. Only a matching
PENDING_APPROVAL receipt with zero of two approvals is accepted.

See [backend setup](docs/BACKEND_SETUP.md) and the
[proposed Java contract](docs/BACKEND_CONTRACT.md). The live Java service has not
been tested; actual endpoint compatibility remains the team's integration task.

## Tests and handoff

```bash
python -m unittest discover -s tests -v
node --check app/static/app.js
python scripts/export_openapi.py
```

Node is only needed for this optional JavaScript syntax check, not for running
the app. Automated tests make no external model or Java API calls. The opt-in
`python scripts/live_smoke.py --run` sends eight synthetic fixtures to Groq through
the local mock server. Without `--run`, it only prints the cases.

- [Handoff and progress message](docs/HANDOFF.md): completed work and teammate responsibilities.
- [Current API schema](docs/ai-service.openapi.json): generated from actual Python code.
- [Groq setup](docs/GROQ_SETUP.md) and [OpenAI setup](docs/MODEL_SETUP.md): private local configuration.
- [Backend setup](docs/BACKEND_SETUP.md) and [contract proposal](docs/BACKEND_CONTRACT.md): integration requirements.

## Limits the team must know

- ARCHIVE asks for clarification because record-retention/access semantics are undefined.
- No server-side conversation history. The browser keeps extracted fields for the
  current form; API clients resend complete request details.
- TEMPORARY is metadata only and remains draft-only until expiry is implemented.
- The report's key permission lists are treated as complete role policies. Exceptions
  and separately granted entitlements are not modeled; confirm these with the backend team.
- Risk classifications are demo heuristics, not an approved enterprise security policy.
- No production SSO, persistent audit log, Gmail sending, approval UI, scheduling,
  real IAM connectors, or permission application is implemented in this AI service.
- Groq free-plan availability/rate limits depend on the account; failures return safe
  messages and the manual form stays available.
