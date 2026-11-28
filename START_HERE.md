# Start here: continuing NeuroForge

Use these steps to run the Java, MySQL, FastAPI and React workflow locally.

## Run the three login portals

With the existing seeded MySQL database, run this from the repository root in PowerShell:

```powershell
cd backend
..\ai-service\.venv\Scripts\python.exe .\scripts\start-portals.py --setup
```

Setup prompts for a local MySQL administrator. It creates the database service account `neuroforge_portal`, grants it table-specific access, and generates distinct web passwords for seeded users who still need one. Save the displayed credentials privately. Existing web passwords and employee records are preserved. The earlier `neuroforge_reader` account can continue running the directory checks.

Open http://localhost:8081 after Spring Boot starts. The packaged React interface and Java session endpoints share this address. The launcher starts a separate HTTP-mode FastAPI planner on loopback port 8012. Leave this terminal open during the demo. On subsequent starts omit `--setup` and supply the MySQL service password when prompted.

1. Sign in as `hr.operations`. Choose **Create access request**, select Ananya (`EF-1005`), Manager, Priya (`EF-1002`), Permanent, and a justification. Choose today's effective date for immediate application after approval. Generate the plan, then choose **Submit for approval** and note the request number.
2. Sign in as `department.approver`, open that number and approve. Sign in as `security.approver` and approve it again. Each person can decide once. A rejection closes the request.
3. Sign in as `EF-1005` before Apply. Ananya still has her original role even at Approved 2/2. Use a separate browser profile to keep her session open while HR works.
4. In Ananya's **My applications**, open **Code Repository**. Leave it open in her browser profile. As HR, reopen the approved request and choose **Apply change**. The employee page refreshes every seven seconds. Check that Code Repository now shows **Access denied** and that the sample files disappear. Follow **My access** and open **Team Directory** to see **Access granted**. The HR request detail records who submitted, decided and applied it.

Each employee application has a bookmarkable address under `/#apps/`, shows the signed-in employee and compares current permissions with its required permission. Code Repository, Project Tracker, Team Directory, and Finance & Expense use sample workspace content. HR Portal displays the signed-in employee's own directory record. For a local walkthrough after frontend edits, rebuild the frontend, repackage the JAR with the commands below, and restart the portal launcher.

For a fresh checkout or after editing React, build the frontend first, then package the backend. The JAR includes the built frontend:

```powershell
cd frontend
npm install
npm run build
cd ..\backend
mvn package
```

## Database and Java directory

Use [the database and backend setup](backend/README.md) to initialize an empty MySQL 8 database and run the Java 21 directory API. The seed has seven employees, including four engineers reporting to one Engineering manager.

## Current workspace

Run all Python commands below from `ai-service/` (first run `cd ai-service` from the repository root). Shared contracts and smoke evidence remain in root `docs/`.

The React HR request page lives in `frontend/`. From a second terminal at the repository root:

```powershell
cd frontend
npm install
npm run build
npm run dev
```

Open the local URL printed by Vite. With the portal launcher running, Vite forwards signed-in portal requests to Java on port 8081. Use an employee account to preview the five application screens after a frontend edit. The separate draft form at `/planner` uses a standalone Python service on port 8002.

## Read in this order

1. This guide: prerequisites, first run, and role-specific starting tasks.
2. `docs/HANDOFF.md`: what is implemented, tested, simulated, and still pending.
3. `AGENTS.md`: project boundaries for an AI coding assistant.
4. `docs/BACKEND_CONTRACT.md` and `docs/BACKEND_SETUP.md`: backend owner/integration work.
5. `docs/ai-service.openapi.json`: actual Python routes and JSON fields for integration.

## Prerequisites by role

| Work | Install/configure | Not needed to start |
| --- | --- | --- |
| Run the existing AI service/form/tests | Git, Python 3.13 with pip and venv, browser; internet to install dependencies | Java, MySQL, Node, Groq key |
| Use AI description-to-form or model-assisted API requests | The above plus an available Groq account/key, outbound HTTPS, GROQ environment variables | OpenAI account/key when Groq is selected |
| Build final React frontend | Git, Node.js/npm compatible with the chosen Vite version, React/Vite/TypeScript/Tailwind project setup | A Groq key in browser code; Java/MySQL can initially be mocked |
| Build Java backend | Git, Java 21 JDK, chosen Spring Boot build setup/Maven or Gradle wrapper, MySQL and local DB configuration | A model key for backend business logic and approval work |
| Integrate Gmail and approvals | Running Java service, seeded HR/two distinct approver accounts, a sender's Gmail app-password configuration where supported | Gmail secrets in Python/frontend/Git |
| Edit code with an AI assistant | Repository access, access to that coding tool, and the role prompt below | Our chat history or our personal API keys |

Node is only needed for frontend development or the optional JavaScript syntax
check. The React planner requires Node and npm. The standalone reference form is served by FastAPI without npm.
Login, request processing, Gmail sending,
and the remaining React screens are not supplied by this AI-service repository;
their owners must implement/document them.

## Repository access

Clone with:

```bash
git clone https://github.com/malikmk0608/NeuroForge.git
cd NeuroForge
```

For a private repository, the owner must grant teammates access. To push changes,
teammates need collaborator/write access or should use a fork and pull request.
Each teammate authenticates to GitHub with their own account. GitHub credentials
and Groq API keys are different and should not be exchanged through repository files.

Create separate work branches for backend/frontend/integration. Merge changes
through reviewed pull requests and pull main before starting new work. Preserve
the existing Python service while adding other parts in clearly named directories
under `backend/` and `frontend/`.

## First run: macOS/Linux

From the ai-service directory, with Python 3.13 installed:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload --port 8002
```

If `python3` already points to Python 3.13, it can replace `python3.13` above.
Run `python --version` after activating the environment to check the interpreter.

## First run: Windows PowerShell

From the ai-service directory, with Python 3.13 and the Python launcher installed:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8002
```

These commands use the environment's interpreter directly; PowerShell script
activation and execution-policy changes are not required. The handoff was tested
on macOS/Python 3.13; the Windows instructions still need verification on a teammate's machine.

Open <http://127.0.0.1:8002/> and <http://127.0.0.1:8002/docs> on that same machine.
Manual form entry and planning work without a provider key. The AI section stays
unavailable until the local server has a provider configured. The handoff has
68 passing automated tests; future feature changes may legitimately add tests.

## Groq keys: what each teammate needs

The original Groq key was entered privately in the author's terminal environment.
It was not committed, and cloning the repository will not provide it. Closing
that terminal or using a different one can require configuring it again.

For AI testing on their own machine, teammates should create their own key at
<https://console.groq.com/keys> and follow `docs/GROQ_SETUP.md`. They do not need to
replace the model client or write new extraction logic. Current settings are:

```text
LLM_PROVIDER=groq
GROQ_API_KEY=<their private key, configured server-side>
GROQ_MODEL=openai/gpt-oss-20b
BACKEND_MODE=mock
```

The `openai/` model-name prefix does not mean the key is an OpenAI key; requests
go to Groq. `.env.example` has blank placeholders only. Copying it to `.env`
alone does not configure this application because automatic dotenv loading is
not implemented. Export the variables before starting the server.

A frontend developer using only typed form requests needs no Groq key. If the
team later uses one shared backend deployment, only its operator configures the
server-side model key; browser users do not receive it. The current localhost
server is not a shared remote deployment and is not reachable from a friend's
computer using their own `127.0.0.1` address.

Using an AI coding assistant is separate: that assistant's subscription or API
access does not automatically configure the NeuroForge application's Groq key.

## What the Java backend owner should do first

1. Run the Python service in mock mode and review a role-change/offboarding draft.
2. Read `docs/BACKEND_CONTRACT.md` and confirm/adapt the proposed read/create endpoints
   and JSON shapes before frontend and backend implementations diverge.
3. Seed the four report employees and role policies; provide positive integer
   employee/policy versions. Treat currently listed permissions as a policy assumption
   to confirm, including behavior for exceptional/non-role entitlements.
4. Implement login/requester authorization, manager eligibility, request persistence,
   backend-derived PENDING_APPROVAL status, idempotency, and atomic version checks.
5. Add two distinct approver accounts and authenticated approval/rejection. Approval
   count is backend state, not a value trusted from Python or React.
6. Add Gmail notifications, audit evidence, separate authorized Apply, and real
   enforcement in the employee/demo apps. The AI service never applies permissions.
7. Verify the existing HTTP adapter against the real endpoints. Update adapter,
   contract, and tests together if Java uses different paths/field names.

The Python HTTP adapter is implemented and simulated tests pass. Real Java
compatibility, persistence, token handling, Gmail, and approval/apply behavior
are not yet verified. See `docs/BACKEND_SETUP.md` for caller-token forwarding.

## What the React frontend owner should do first

1. Run the local form as a behavioral reference; do not treat its static HTML as
   a completed React frontend.
2. Read the generated Python OpenAPI schema. Preserve typed forms, optional AI
   prefill, required-detail questions, draft review, permission lists, risk reasons,
   activity steps, and the distinction between priority and suggested risk.
3. Build the HR/Admin console, approver console, four employee views, request
   progress, and five demo apps: repository, project tracker, team directory,
   HR portal, and finance/expenses.
4. Agree authenticated Java proxy routes with the backend owner. In the final
   architecture React calls Java, and Java delegates planning to Python. The
   standalone reference form's direct Python calls are not the final login flow.
5. Display real Java request IDs and states. Do not fabricate approvals or label a
   DRAFT as submitted. Show permission changes on employee views only after Apply.

No provider key, Java privileged token, database password, or Gmail app password
belongs in client-side JavaScript or Vite-exposed environment variables.

## What the integration/demo owner should do first

- Agree service URLs and how a Java-authenticated request delegates its identity
  to Python. Suggested local ports: React 5173, Java 8081, AI 8002; port 8000 may
  replace 8002 if that is what the team configures. Use matching URLs everywhere.
- Seed one HR account, two distinct approvers, and the four employees. Reporting
  manager and approver are separate concepts.
- Configure Java's MySQL connection and Gmail sender/app password privately.
- Verify the full flow: form/AI draft → explicit request creation → 0/2 → 1/2 →
  2/2 → APPROVED → authorized Apply → employee access updated → audit evidence.
- Verify denied access, rejection, stale plans, duplicate submissions, expired
  login, unavailable backend, and notification/application failure states.
- Decide onboarding support, archival/retention semantics, temporary expiry,
  future-date scheduling, self-approval, and policy exceptions before implementing
  those behaviors. Current AI planning supports role changes/offboarding;
  onboarding/archival requests ask for clarification.

## Paste this into an AI coding assistant

Replace the bracketed role/task with the teammate's actual responsibility:

> I am continuing NeuroForge from this repository. My role is [Java backend /
> React frontend / integration], and my task is [specific task]. First read
> AGENTS.md, START_HERE.md, docs/HANDOFF.md, README.md, and the relevant API
> contract/setup documents. Inspect the current source and tests before editing.
> Explain what already works, what is mocked, and what my role still needs to
> implement. Preserve the existing Python AI planner and its JSON contracts;
> do not rebuild it independently or bypass Java's two distinct approvals.
> Never request or commit real API keys. Work in small verified steps, explain
> changes, and update the handoff and integration docs as my part is completed.

An assistant may not automatically read AGENTS.md; this prompt explicitly points
it to the files. Repository instructions do not replace reading/testing the code.

## Troubleshooting first run

| Symptom | Check |
| --- | --- |
| Port already in use | Use another port and open that same port in the browser |
| AI says not configured | Set variables in the terminal that starts the server, then restart it |
| Groq 401/429 | Check that developer's key, model access, account quota/rate limits; use the manual form meanwhile |
| 422 from an API call | Match the endpoint's schema: message/use_model go to /agent/plan, typed fields to /agent/role-change |
| HTTP mode requires token | Use the backend-issued user Bearer token; the standalone form has no production login flow |
| Submission disabled | This is intentional in mock mode; connect a versioned/authenticated Java backend |
| Friend cannot access the author's localhost | Clone/run locally or agree on a properly deployed shared service later |

The original Groq and GitHub tokens are not prerequisites to share. Repository
access, installed tools, per-developer local settings, and an agreed integration
contract are the prerequisites to continuing the work.
