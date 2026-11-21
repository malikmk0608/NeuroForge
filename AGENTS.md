# NeuroForge repository instructions

Read `START_HERE.md` and `docs/HANDOFF.md` before implementing changes.
The user may assign a teammate's role in the current chat; work on that role's
scope while preserving the existing AI-service contract. This repository is an
AI-service handoff, not a completed Java/React IAM application.

## Current implementation

- Python 3.13 / FastAPI service; `app/main.py` exposes the actual routes.
- LangGraph nodes in `app/graph.py`: interpretation, employee retrieval,
  permission comparison, and draft creation.
- `app/model_interpreter.py` optionally calls Groq or OpenAI. Default requests
  are deterministic; explicit `use_model: true` enables the configured provider.
- `app/backend.py` has four synthetic employees and mock role policies.
  `app/http_backend.py` targets the proposed Java API, with no mock fallback.
- `app/submission.py` revalidates reviewed plans and asks Java to persist a
  PENDING_APPROVAL request; it does not approve or apply changes.
- `app/static/` is the local reference form, not the final React frontend.

## Architecture and ownership

React calls authenticated Java routes; Java delegates AI planning to Python.
Python reads employee/policy data and creates requests through Java's API.
The standalone Python form calls Python directly only for local demonstration.
No Java backend, React application, MySQL schema, or employee demo applications
are currently implemented in this repository.

Java/integration owns login, requester authorization, manager eligibility,
request persistence, two distinct approvals, Gmail, audit evidence, effective-date
enforcement, idempotency, and applying permissions. The React owner builds HR,
approver, employee, progress, and demo-application screens using those APIs.

## Preserve these boundaries

- AI only interprets and proposes. Permission differences are computed with Python
  sets; do not let a model invent the authoritative grant/revoke/retain lists.
- Every actual change requires two approvals enforced by Java. Risk and priority
  never reduce that requirement. Draft creation is separate from submission and apply.
- The requester reference is untrusted metadata; authenticated identity comes
  from the backend-validated caller token.
- HTTP submission recomputes against fresh records and compares reviewed versions
  and permissions. Java must also perform atomic version checks and durable idempotency.
- Defaults stay mock and read-only. Never silently use mock data after an HTTP failure.
- Never hard-code, print, commit, or place provider keys, Java tokens, Gmail app
  passwords, database passwords, or GitHub tokens in frontend code or docs.
- `.env.example` documents settings only. The app does not automatically load `.env`.
- ARCHIVE remains clarification-only until the team defines retention/access rules.
  Temporary access remains draft-only until expiry behavior exists.
- The report's key permissions are currently assumed to be complete role policies.
  Confirm exception handling with the backend owner before actual enforcement.

## Integration references

- `docs/BACKEND_CONTRACT.md`: proposed Java endpoints and JSON shapes.
- `docs/BACKEND_SETUP.md`: HTTP mode, caller-token forwarding, version checks,
  submission payload, and failure behavior.
- `docs/ai-service.openapi.json`: exported actual Python API contract.
- `docs/GROQ_SETUP.md`: server-side model configuration; keys are not in Git.
- `docs/live-smoke-results.json`: eight passing synthetic Groq smoke cases from
  the handoff run, not a guarantee of arbitrary-language correctness.

Before changing API fields, agree on the change with the affected owner, update
the relevant adapter/tests/docs, and regenerate the OpenAPI export. Do not
implement a second independent AI planning workflow in Java or React.

## Verification

From the repository root with dependencies installed:

```bash
python -m unittest discover -s tests -v
node --check app/static/app.js
python scripts/export_openapi.py
```

Node is optional for the Python service; the syntax command needs it. Automated
tests use simulated provider/Java responses, not external calls. The opt-in live
smoke runner uses Groq and synthetic mock records only; inspect its cases and
obtain the user's authorization before external calls. Never claim live Java
integration, approvals, email, or enforcement were verified using mock tests.

For new Java/React work, add the chosen build/run/test commands and configuration
examples to `START_HERE.md` and update the handoff as behavior changes.
