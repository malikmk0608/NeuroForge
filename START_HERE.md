# Start here: run NeuroForge locally

Use this guide for the signed-in HR, approver and employee portals. All terminal blocks below start in the repository root (`NeuroForge-EL`) unless the step says otherwise. Each laptop runs its own local database.

## First-time setup

### 1. Install the tools and get the project

Install Git, Python 3.13 or 3.14, MySQL Server 8 with the `mysql` command-line client, a Java 21 JDK, Maven 3.6.3 or newer, and Node.js 22.12+ with npm (Node 24 also works). Set `JAVA_HOME` to your installed JDK directory. In a new terminal, check `java -version`, `mvn -v`, `mysql --version`, `node -v` and `npm -v`. Maven should report Java 21 or newer.

```bash
git clone https://github.com/pabbisettynikhitha2007-ctrl/NeuroForge-EL.git
cd NeuroForge-EL
```

If you already cloned this repository, open its root folder. If you previously used the AI-only repository, clone this one alongside it.

### 2. Install the Python planner

On Windows, use PowerShell. Substitute `-3.13` if that is the Python version you installed.

```powershell
py -3.14 -m venv ai-service/.venv
.\ai-service\.venv\Scripts\python.exe -m pip install -r ai-service/requirements.lock.txt
```

On macOS/Linux, use your installed Python 3.13 or 3.14 executable.

```bash
python3.13 -m venv ai-service/.venv
ai-service/.venv/bin/python -m pip install -r ai-service/requirements.lock.txt
```

### 3. Initialize MySQL once

Start MySQL Server on port 3306. From the repository root, run `mysql -u root -p` and enter the MySQL administrator password set on **this** laptop. At the `mysql>` prompt, run the following on a **fresh database**. If `neuroforge` already exists, check its tables and data before continuing. An existing seeded portal uses the update instructions below.

```sql
CREATE DATABASE neuroforge CHARACTER SET utf8mb4;
USE neuroforge;
SOURCE database/schema.sql
SOURCE database/seed.sql
SELECT department, COUNT(*) AS employees FROM employee GROUP BY department;
EXIT
```

The initial counts are Engineering **5**, Finance **1**, and HR **1**. In MySQL Workbench, you can instead select the new schema, use **File > Open SQL Script**, and execute `schema.sql` followed by `seed.sql`.

### 4. Build the signed-in frontend and backend

From the repository root, run these commands in order. Continue to the next command after the preceding one succeeds. Maven copies the compiled React assets into the JAR.

```bash
npm --prefix frontend install
npm --prefix frontend run build
mvn -f backend/pom.xml package
```

Expect `BUILD SUCCESS` and `backend/target/backend-0.1.0.jar`. The JAR, `frontend/dist`, installed dependencies and local credentials are generated on each laptop.

### 5. Provision accounts and start the portals

On Windows:

```powershell
.\ai-service\.venv\Scripts\python.exe .\backend\scripts\start-portals.py --setup
```

On macOS/Linux:

```bash
ai-service/.venv/bin/python backend/scripts/start-portals.py --setup
```

Enter your **MySQL administrator** username and password. Save the generated **MySQL service password** for `neuroforge_portal` and the individual **Web login** passwords privately. Setup prints web passwords when it first assigns them. Use the appropriate credential for each prompt:

| Where | Account |
| --- | --- |
| First-time provisioning | MySQL administrator, usually `root` |
| Launcher on subsequent starts | MySQL service account `neuroforge_portal` |
| Browser | `hr.operations`, `department.approver`, `security.approver`, or an employee from `EF-1001` to `EF-1007`, each with its own web password |

Setup starts the app immediately. After `Started NeuroForgeApplication`, open [the portal](http://localhost:8081). Leave the launcher terminal open. It runs both Spring Boot and the planner. Press **Ctrl+C** there to stop them.

## Update an existing installation

Use these steps for an ordinary clone of this repository with a working seeded portal. Run `git status` and save local work before updating. Stop the existing launcher with **Ctrl+C** so Maven can replace the JAR. From the repository root:

```powershell
git pull --ff-only origin main
.\ai-service\.venv\Scripts\python.exe -m pip install -r ai-service/requirements.lock.txt
npm --prefix frontend install
npm --prefix frontend run build
mvn -f backend/pom.xml package
.\ai-service\.venv\Scripts\python.exe .\backend\scripts\start-portals.py
```

On macOS/Linux, use `ai-service/.venv/bin/python` for both Python commands and `backend/scripts/start-portals.py` for the launcher path. The five employee screens require a frontend and JAR rebuild. Existing portal installations use the same schema, employee records and passwords. Skip the SQL scripts and first-time provisioning for this update.

## Run the three login portals

For everyday starts, run just the launcher from the repository root:

```powershell
.\ai-service\.venv\Scripts\python.exe .\backend\scripts\start-portals.py
```

On macOS/Linux run `ai-service/.venv/bin/python backend/scripts/start-portals.py`. Enter the saved `neuroforge_portal` service password. The portal opens at [localhost:8081](http://localhost:8081). The [planner health endpoint](http://127.0.0.1:8012/health) should report `backend_mode: http`.

### Verify a role change

1. Sign in as `hr.operations`. Choose **Create access request**. For a fresh seed, select Ananya (`EF-1005`), target role **MANAGER**, today's effective date, Priya (`EF-1002`) as manager, **Permanent**, and a business justification. On a used database, choose an employee who is currently an Engineer.
2. Choose **Generate access plan**, then **Submit for approval**. Note the request number and **0/2** progress.
3. Sign in as `department.approver`, open the request and approve it. Repeat with `security.approver`. At **2/2** the request is approved.
4. In a separate browser profile, sign in as the affected employee and open **My applications > Code Repository**. It should still show **Access granted**.
5. As HR, choose **Apply change**. Within about seven seconds, the employee's open Code Repository should show **Access denied**. Open **Team Directory** to see **Access granted**. Review the actors and timestamps in the HR request's activity list.

Employee accounts can open **Code Repository, Project Tracker, Team Directory, HR Portal, and Finance & Expense**. HR Portal displays the employee's own record. The other four use sample app content.

## Optional Groq prefill

Manual form entry works as soon as the portals start. For **Describe the request > Use AI to fill form**, use your own Groq key on the machine running the planner. Stop the launcher, then set the variables in the terminal you will restart it from. In Windows PowerShell, run this line on its own and paste the key at the hidden prompt:

```powershell
$groqSecret = Read-Host 'Groq API key' -AsSecureString
```

When the PowerShell prompt returns:

```powershell
$env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', $groqSecret).Password.Trim()
Remove-Variable groqSecret
$env:LLM_PROVIDER = 'groq'
$env:GROQ_MODEL = 'openai/gpt-oss-20b'
.\ai-service\.venv\Scripts\python.exe .\backend\scripts\start-portals.py
```

On macOS/Linux, set the three environment variables using the hidden-input instructions in [Groq setup](docs/GROQ_SETUP.md), then run the **portal launcher** in that same terminal. For the integrated app, the launcher starts the planner on 8012.

Open the [health endpoint](http://127.0.0.1:8012/health) and look for `"provider":"groq"` and `"configured":true`. To verify a live call, sign in as HR, enter **Move EF-1006 to MANAGER** for a seeded Engineer, and click **Use AI to fill form**. Successful prefill selects the employee and target role. A new terminal needs the variables set again.

## Development and handoff

| Task | How to run or verify it |
| --- | --- |
| React development | Leave the integrated launcher running. In another terminal at the repository root run `npm --prefix frontend run dev`. Open the URL printed by Vite. It proxies portal calls to Java on 8081. |
| Python planner tests | Run from `ai-service/` using `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. |
| Standalone planner development | From `ai-service/` use its virtual environment to run `python -m uvicorn app.main:app --reload --port 8002`. This opens the draft-only form. |
| Java directory integration | Follow the [directory check](backend/README.md#local-directory-integration-check). The signed-in portal gets its credentials through the launcher. |
| Gmail integration owner | Connect a committed pending request to email delivery for both approvers. Verify both inboxes receive the same request number and review link. Gmail delivery is pending; the current portal works independently. |

See the [handoff](docs/HANDOFF.md), [AI API schema](docs/ai-service.openapi.json), [Java contract](docs/BACKEND_CONTRACT.md), and [project instructions](AGENTS.md) before changing shared API fields. Each teammate uses their own GitHub access and local credentials.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Only the old employee cards appear | Stop the launcher, build React first, run Maven package, restart, and refresh port 8081. |
| MySQL reports error 1045 | For `--setup`, use the administrator password. For everyday starts, verify the service credential with `mysql -h 127.0.0.1 -u neuroforge_portal -p -D neuroforge -e "SELECT COUNT(*) FROM employee;"`. |
| Java reports `UnsupportedClassVersionError` | Point `JAVA_HOME` and the terminal's Java path at the installed JDK. Check both `java -version` and the Java version shown by `mvn -v`. |
| Port 8012 or 8081 is in use | Return to the earlier launcher's terminal and press Ctrl+C before starting another copy. |
| Groq configured but prefill fails | Read the message on the form. A rejected key needs a valid key in the launcher terminal and a restart. A rate-limit message requires waiting or using the manual form. |
| A teammate opens localhost and sees a different database | Each laptop's localhost serves that laptop's installation. Use separate browser profiles on the same machine for a shared local demo. |
