# NeuroForge AI service: implementation handoff

**Workspace layout.** Run Python setup, tests, and scripts from `ai-service/`. Service-relative paths such as `app/` and `scripts/` below refer to that directory. Shared API contracts and saved smoke results are in the repository-level `docs/`.

The current web flow includes password login, HR submission and apply, two distinct approver decisions, an audit trail and employee access refresh. Use the portal walkthrough in [START_HERE.md](../START_HERE.md). The sections below preserve the earlier Python handoff.

The employee portal opens five individual demo apps from **My applications**. Each view follows the same authenticated employee profile through grants and revocations. Nikhitha reports completing the rejection, duplicate-approver, future-date and offboarding checks on her local installation.

Gmail delivery is pending. When HR creates a new pending request, the integration owner should send its request number and review link to the two configured approver addresses after the transaction commits. Record delivery outcomes per recipient so retries avoid duplicate notifications. Verify receipt in both inboxes and opening the request from a signed-out browser. The current login returns to the queue, where the approver can open the request by number.

This is the AI-service handoff as of 2026-11-21. It records implemented behavior
and verified limits, not completion of the Java/React IAM application.

New teammates should first read [START_HERE.md](../START_HERE.md) for tools,
clone/run commands, per-role tasks, key setup, and an AI-assistant starting prompt.
The original developer's Groq key and running localhost server are not shared
by cloning this repository. Manual form use needs no provider key; AI-assisted
use requires a key configured on the server that the teammate is actually using.

## Implemented

- FastAPI Python service with typed JSON validation and interactive API docs.
- LangGraph workflow: Interpret → Retrieve Employee → Compare Permissions → Create Plan.
- Conservative deterministic employee/action/target-role extraction; no API key needed.
- Role-change draft planning, including promotions, demotions, and same-role/no-change cases.
- Offboarding draft planning: revoke all current permissions; grant and retain nothing.
- Read-only mock backend with seven employees (five in Engineering) and four role policies.
- Sorted, deduplicated Grant / Revoke / Retain lists based on actual current mock access.
- Structured effective date, justification, reporting manager, and assignment type fields.
- Explicitly marked message-clause detail extraction, conflict detection, and missing-detail questions.
- Mock manager existence/self-manager checks; invalid field validation.
- Advisory LOW/MEDIUM/HIGH risk suggestions with reasons and versioned demo rules.
- Local request form with employee names, role/offboarding choices, validation, draft preview,
  risk explanations, and activity steps. This is a reference for the team's React implementation.
- Optional AI description-to-form workflow, non-secret provider status, partial
  field prefill, and review-before-final-draft behavior. Manual form entry stays available.
- Optional request title, priority, demo requester reference, and business unit
  metadata. Read-only current role/department fields and mock-only editable demo
  examples make role-change/offboarding demonstrations easy to reproduce.
- Automated tests, dependency versions, current Python OpenAPI export, and proposed Java contract.
- Optional OpenAI Responses API interpreter using strict structured extraction,
  local validation, safe failure responses, and simulated HTTP tests. Live
  provider verification is pending; default requests make no model calls.
  A live synthetic test was attempted; the provider returned HTTP
  429 (rate limited). Successful live extraction still needs verification after
  the API project's limits are resolved. Error categorization is implemented.
- Selectable Groq adapter with strict structured extraction, separate credentials,
  simulated HTTP tests, and setup instructions. A successful live role-change
  smoke test was reported by the user on 2026-11-21: HTTP 200, correct
  EF-1001/MANAGER extraction, correct grant/revoke/retain lists over mock data,
  and questions for the four missing details. Final live regression: all eight
  approved synthetic cases passed after prompt refinement; see live-smoke-results.json.
  The initial run over-clarified one polite request; the refined prompt and
  zero-temperature Groq extraction passed the complete rerun.
- Java HTTP adapter for the proposed endpoints, delegated user-token forwarding,
  typed response validation, safe failure handling, and no mock fallback.
- Explicit reviewed-plan submission with fresh recomputation, version/permission
  snapshot checks, temporary/no-change blocking, and idempotency-key forwarding.
  Only matching PENDING_APPROVAL receipts with 0/2 approvals are accepted.
- Simulated Java integration tests; mock-mode submission remains disabled.
- 68 passing automated tests plus a successful JavaScript syntax check. The
  AI-to-form path was also exercised in the browser on the Groq-enabled server.

## Remaining team integration and policy decisions

- Expand live model-quality testing for new language/domain cases as needed.
- Verify the implemented Java HTTP adapter/submission path against actual teammate
  endpoints, authentication, version checks, persistence, and idempotency behavior.
- Agreed archival semantics. ARCHIVE currently requests clarification rather than revoking access.
- Server-side conversation memory if required. The current form retains extracted
  fields for review; API clients resend complete details. Final multi-service demo
  checks require the Java and React implementations.

The repo is not yet a fully finished integrated agent. Default behavior is
rule-based draft planning over mock records. Optional Groq interpretation has
eight passing live synthetic cases plus simulated tests; employee and policy data
still come from mocks. No approvals or access changes occur.

## Responsibilities for teammates

### Java backend / integration owner

Review `BACKEND_CONTRACT.md`. Implement authoritative employee and role policy
data, authentication/authorization, request persistence, two distinct authenticated
approvals, Gmail notifications, audit evidence, effective-date/application rules,
and permission enforcement. Provide endpoint examples and authentication details
so the implemented Python HTTP adapter can be verified/adapted. Preserve the distinction between
draft generation, request creation, approval, and applying changes.

### React frontend owner

Use `ai-service.openapi.json` for the Python request/response schema. The local
HTML form in `app/static/` demonstrates how to display the draft, required detail
questions, risk suggestion, and activity steps. In the integrated architecture,
React calls Java's authenticated routes; the local form directly calls Python
only for standalone demonstration.

### Policy/demo owner

Confirm complete role permission sets, manager/approver rules, date behavior,
temporary assignment expiry, archival meaning, and demo risk classifications.
Current risk rules are proposed demo heuristics, not an approved security policy.

## Current safeguards and limits

- AI service never applies access changes or approves requests.
- Every plan is DRAFT with two approvals required; mock submission is disabled.
  HTTP submission requires backend-issued caller credentials and fresh validation;
  Java must still authorize, persist, enforce idempotency, and require approvals.
- `details_complete` only reports completion of current request-detail checks.
- No production login, SSO, persistent employee data, audit log, Gmail sending,
  approval execution, external IAM integration, scheduling, or temporary expiry.
- Mock roles treat the report's key permissions as complete policies; separately
  assigned access exceptions are not modeled.
- The local form is served by FastAPI; it is not the final React application.
- No secret is needed for manual mock-mode use; model assistance requires a
  server-side provider key. `.env` and `.venv` are ignored; keys are not committed.

## Run and verify

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8002
```

Open <http://127.0.0.1:8002/> for the form or <http://127.0.0.1:8002/docs>
for API docs. Regenerate the schema with `python scripts/export_openapi.py`.

## Short progress message to share

> Built the NeuroForge FastAPI/LangGraph draft-planning service with a local
> role-change/offboarding form, mock employee/policy lookup, Grant/Revoke/Retain
> calculation, required-detail validation and clarification, advisory risk reasons,
> automated tests, and API handoff documentation. Groq model-assisted role-change
> interpretation and eight synthetic live checks passed after prompt refinement.
> The form supports optional AI prefill, editable mock demo defaults, request
> metadata, and manual review. All 68 automated tests pass. The Java HTTP adapter and explicit
> pending-request submission path are implemented with simulated integration tests;
> live Java compatibility remains pending. Archival policy is undefined and
> temporary expiry is not implemented. Approvals, Gmail, persistence, and applying
> access changes belong to the backend/integration owners.
