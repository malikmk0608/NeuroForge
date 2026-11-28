"""Run the local authenticated portals against the existing seeded MySQL database."""
import argparse
import getpass
import hashlib
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
APP_USER = "neuroforge_portal"
CREATE_SERVICE = "CREATE USER IF NOT EXISTS 'neuroforge_portal'@'localhost' IDENTIFIED BY RANDOM PASSWORD;"
TABLE_RIGHTS = {
    "app_user": "SELECT", "role_policy": "SELECT", "role_permission": "SELECT",
    "employee": "SELECT, UPDATE", "employee_permission": "SELECT, INSERT, DELETE",
    "access_request": "SELECT, INSERT, UPDATE", "audit_log": "SELECT, INSERT",
    "request_approval": "SELECT, INSERT",
}


def grants():
    return [f"GRANT {rights} ON neuroforge.{table} TO 'neuroforge_portal'@'localhost';"
            for table, rights in TABLE_RIGHTS.items()]


def set_missing_password(user, digest):
    return (f"UPDATE neuroforge.app_user SET password_hash='{digest}' "
            f"WHERE username=CONVERT(UNHEX('{user.encode().hex()}') USING utf8mb4) "
            "AND password_hash IS NULL;")


def password_hash(password):
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000, dklen=32)
    return (salt + derived).hex()


def setup():
    admin = input("Local MySQL administrator username [root]: ").strip() or "root"
    env = dict(os.environ, MYSQL_PWD=getpass.getpass(f"MySQL password for {admin} (typing is hidden): "))
    def sql(statement):
        result = subprocess.run(["mysql", "--protocol=TCP", "-h", "127.0.0.1", "-P", "3306",
                                 "-u", admin, "-N", "-B", "--raw", "neuroforge"],
                                env=env, input=statement, text=True, capture_output=True)
        if result.returncode:
            error = next((line for line in result.stderr.splitlines() if line.startswith("ERROR ")),
                         result.stderr.strip() or f"MySQL exited with status {result.returncode}.")
            if error.startswith("ERROR 1045 "):
                error += f"\nCheck the MySQL administrator credentials for {admin}."
            raise SystemExit(error)
        return result.stdout.strip()
    # RANDOM PASSWORD returns a credential only when MySQL actually creates the account.
    created = sql(CREATE_SERVICE)
    db_password = created.split("\t")[2] if created else None
    if db_password:
        print("Save this MySQL service password privately for future starts:", db_password, flush=True)
    for statement in grants():
        sql(statement)
    accounts = sql("SELECT username FROM app_user WHERE password_hash IS NULL ORDER BY username;").splitlines()
    for user in accounts:
        password = secrets.token_urlsafe(16)
        # Use hex for the SQL value so a username can never become SQL syntax.
        count = sql(set_missing_password(user, password_hash(password)) + " SELECT ROW_COUNT();")
        if count == "1":
            print(f"Web login   {user:<22} {password}")
    return db_password


def workbench_setup():
    users = ["hr.operations", "department.approver", "security.approver",
             *(f"EF-{code}" for code in range(1001, 1008))]
    passwords = {user: secrets.token_urlsafe(16) for user in users}
    hashes = {user: password_hash(password) for user, password in passwords.items()}
    statements = [CREATE_SERVICE, *grants(), "START TRANSACTION;",
                  *(set_missing_password(user, hashes[user]) for user in users), "COMMIT;"]
    with tempfile.TemporaryDirectory(prefix="workbench-", dir=ROOT / "backend/target") as folder:
        script = Path(folder) / "setup-portals.sql"
        script.write_text("\n".join(statements) + "\n", encoding="utf-8")
        print("In your connected MySQL Workbench administrator session, choose File > Open SQL Script.")
        print("Paste this full file path:", script)
        print("Run the whole script with the plain lightning bolt. Save the generated service password")
        print("from the CREATE USER result grid. An existing service account uses its saved password.")
        while True:
            password = getpass.getpass("After the script finishes, enter the neuroforge_portal service password: ")
            result = subprocess.run(["mysql", "--protocol=TCP", "-h", "127.0.0.1", "-P", "3306", "-u", APP_USER,
                                     "-N", "-B", "neuroforge"], env=dict(os.environ, MYSQL_PWD=password),
                                    input="SELECT username,password_hash FROM app_user;", text=True, capture_output=True)
            if result.returncode:
                print(result.stderr.strip(), file=sys.stderr)
                print("Check the Workbench Action Output and service password, then retry. Ctrl+C cancels.")
                continue
            saved = dict(line.split("\t", 1) for line in result.stdout.splitlines())
            if any(saved.get(user) in (None, "NULL") for user in users):
                print("Some seeded logins are still missing passwords. Check the script's Action Output and run it to completion.")
                continue
            for user in users:
                if saved[user] == hashes[user]:
                    print(f"Web login   {user:<22} {passwords[user]}")
            return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--setup", action="store_true", help="Provision missing portal accounts in the seeded database")
    mode.add_argument("--workbench-setup", action="store_true", help="Provision the seeded logins through your connected Workbench administrator session")
    args = parser.parse_args()
    java_dir = Path(os.environ.get("JAVA_HOME") or Path.home() / ".jdks" / "openjdk-25")
    java = str(java_dir / "bin" / "java.exe") if (java_dir / "bin" / "java.exe").is_file() else shutil.which("java")
    python = ROOT / "ai-service/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    jar = ROOT / "backend/target/backend-0.1.0.jar"
    if not java or not jar.is_file() or not python.is_file():
        sys.exit("Build the backend with the React frontend and install the AI-service environment first.")
    for port in (8012,8081):
        with socket.socket() as probe:
            try: probe.bind(("127.0.0.1",port))
            except OSError: sys.exit(f"Port {port} is already in use. Stop the earlier portal run before restarting.")
    password = setup() if args.setup else None
    if args.workbench_setup:
        password = workbench_setup()
    password = password or getpass.getpass("MySQL password for neuroforge_portal: ")
    java_env = dict(os.environ, DB_USER=APP_USER, DB_PASSWORD=password,
                    DB_URL="jdbc:mysql://127.0.0.1:3306/neuroforge", PORTAL_PLANNER_URL="http://127.0.0.1:8012")
    ai_env = dict(os.environ, BACKEND_MODE="http", BACKEND_BASE_URL="http://127.0.0.1:8081")
    for key in ("DB_USER","DB_PASSWORD","MYSQL_PWD"):
        ai_env.pop(key,None)
    processes = []
    try:
        processes.append(subprocess.Popen([str(python),"-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8012"],
                                          cwd=ROOT/"ai-service",env=ai_env))
        processes.append(subprocess.Popen([java,"-jar",str(jar)],env=java_env))
        print("Open http://localhost:8081 when Spring Boot reports Started.", flush=True)
        while all(p.poll() is None for p in processes):
            time.sleep(1)
        sys.exit("A portal service stopped. See its startup message above.")
    except KeyboardInterrupt:
        pass
    finally:
        for p in processes:
            if p.poll() is None: p.terminate()
        for p in processes: p.wait()


if __name__ == "__main__":
    main()

