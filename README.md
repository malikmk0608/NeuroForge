# NeuroForge

NeuroForge manages employee access changes. HR reviews a plan, two different approvers decide, and HR applies the approved change. Employees can watch their permissions change in five demo apps. Spring Boot serves the React portals on port 8081, stores requests and audit events in MySQL, and calls a FastAPI/LangGraph planner on port 8012.

## Set up the team project

| Your starting point | What to do |
| --- | --- |
| New laptop or a copy of the earlier AI-only prototype | Clone this repository. Install the Python dependencies in `ai-service/.venv`, initialize an empty MySQL database from `database/schema.sql` and `database/seed.sql`, build React, package Java, then run `start-portals.py --setup`. [First-time setup](START_HERE.md#first-time-setup) |
| Existing clone with working MySQL portals | Stop the launcher, pull the update, rebuild React and the backend JAR, then start the launcher using your saved service password. The five employee screens use the existing database and accounts. [Update an existing installation](START_HERE.md#update-an-existing-installation) |
| Already installed and built this version | Start the launcher and open the HR, approver, or employee portal. [Start the portals](START_HERE.md#run-the-three-login-portals) |

Each new database generates local passwords for one HR operator, two approvers and seven employee accounts. Manual planning works immediately. For natural-language prefill, set your own Groq key in the launcher terminal. Gmail notification delivery is pending. [Groq setup for the signed-in portal](START_HERE.md#optional-groq-prefill)

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
- Authenticated submission, two-approver voting, an effective-date check on Apply, and a per-request audit timeline in the Java/MySQL portal.
- Employee screens for Code Repository, Project Tracker, Team Directory, HR Portal and Finance & Expense. Each compares the required permission with the signed-in employee's current permissions and refreshes about every seven seconds.

**Validation:** 68 automated tests pass. All eight synthetic live Groq cases passed
in the final run; see [the saved results](docs/live-smoke-results.json). One initial
polite role-change case over-clarified; the prompt was refined and the full suite
rerun successfully. This is a smoke test, not proof of perfect language understanding.

## Run the standalone Python planning form

For a draft-only planner development session, start in `ai-service/`. The team setup above runs the complete signed-in workflow.

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

The portal launcher configures Java and Python together. Backend developers can also run the [directory integration check](backend/README.md#local-directory-integration-check) and consult the [planner-to-Java contract](docs/BACKEND_CONTRACT.md).

## Tests and handoff

Run these planner checks from `ai-service/` with its virtual environment active.

```bash
python -m unittest discover -s tests -v
node --check app/static/app.js
python scripts/export_openapi.py
```

Node builds the React portal and runs the optional standalone JavaScript syntax
check. The Python tests use simulated model and Java responses. The opt-in
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
- Java provides local session login, approval, Apply and persistent audit records. Gmail delivery, production SSO, scheduled Apply and external IAM connectors remain future work.
- Groq free-plan availability/rate limits depend on the account; failures return safe
  messages and the manual form stays available.
