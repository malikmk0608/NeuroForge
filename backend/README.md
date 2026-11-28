# MySQL directory and portal service

For the packaged HR, approver and employee interface, use [the portal setup and login walkthrough](../START_HERE.md#run-the-three-login-portals). The read-only directory integration check below can still use its original MySQL reader account.

## Initialize a fresh local database

Start the MySQL client from the repository root using an authorized MySQL account. The client prompts privately for the password.

```powershell
mysql -u root -p
```

```sql
CREATE DATABASE neuroforge CHARACTER SET utf8mb4;
USE neuroforge;
SOURCE database/schema.sql;
SOURCE database/seed.sql;
SELECT department, role, COUNT(*) FROM employee GROUP BY department, role;
```

Use these scripts once on an empty database. Avoid rerunning them on existing IAM data. The seed contains seven employees, seven employee identities, two approver identities and one HR operator identity. The identities have no seeded passwords. The four engineers report to Priya Patel. Each employee starts with a copy of their role's permissions.

## Run and verify

These commands are for the standalone directory API. The [signed-in portals](../START_HERE.md#first-time-setup) have their own local session login and launcher. For a standalone directory run, use Maven 3.6.3+ and a JDK supporting Java 21. Configure DB_USER and DB_PASSWORD privately for a database account with SELECT privileges. DB_URL defaults to jdbc:mysql://127.0.0.1:3306/neuroforge. IAM_ISSUER is the trusted OpenID Connect issuer URL for external caller tokens. Supply it and a valid access token for audience neuroforge and scope iam.plan to exercise that API.

```powershell
cd backend
mvn package
mvn spring-boot:run
```

From a separate PowerShell session with a privately configured delegated token:

```powershell
$headers = @{ Authorization = "Bearer $env:NEUROFORGE_ACCESS_TOKEN" }
Invoke-RestMethod http://127.0.0.1:8081/api/employees -Headers $headers
Invoke-RestMethod http://127.0.0.1:8081/api/employees/EF-1005 -Headers $headers
Invoke-RestMethod http://127.0.0.1:8081/api/roles/MANAGER/permissions -Headers $headers
```

For standalone Python HTTP mode set BACKEND_MODE=http and BACKEND_BASE_URL=http://127.0.0.1:8081 before starting FastAPI. Include the same Authorization header in the request to FastAPI. The portal launcher supplies the HTTP-mode settings and Java delegates signed-in planner calls. Request creation, approval and Apply are available through the portal. Gmail delivery is pending.

## Local directory integration check

With the JAR built, Node 22+, JAVA_HOME, DB_USER and DB_PASSWORD set, run `node .\scripts\check-directory.mjs` from backend. This starts a temporary backend on a loopback port, exercises anonymous and signed directory requests against MySQL, lists the returned employees, then stops the test process. It supplies an ephemeral local test issuer for this child process only. Testing user login with the team's real issuer is separate.
