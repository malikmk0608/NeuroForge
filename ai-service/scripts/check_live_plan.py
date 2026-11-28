"""Check a draft against the local seeded database through the authenticated API."""
import os
import sys
from datetime import date

import httpx
from fastapi.testclient import TestClient

from app.main import app


def main():
    headers = {"Authorization": "Bearer " + sys.stdin.read().strip()}
    employee_url = os.environ["BACKEND_BASE_URL"] + "/api/employees/EF-1005"
    before = httpx.get(employee_url, headers=headers).raise_for_status().json()
    with TestClient(app) as client:
        response = client.post("/agent/plan", headers=headers, json={
            "message": "Move EF-1005 to MANAGER",
            "details": {
                "effective_date": date.today().isoformat(),
                "manager": "EF-1002",
                "assignment_type": "PERMANENT",
                "justification": "Leading the engineering team.",
            },
        })
    result = response.raise_for_status().json()
    assert result["backend_mode"] == "http" and result["status"] == "draft_plan_ready"
    plan = result["plan"]
    assert plan["employee_code"] == "EF-1005" and plan["current_role"] == "ENGINEER"
    assert plan["target_role"] == "MANAGER" and plan["status"] == "DRAFT"
    assert plan["required_approvals"] == 2 and plan["ready_for_submission"]
    assert plan["expected_employee_version"] == before["version"]
    assert plan["expected_policy_version"] is not None
    expected = {"grant": ["REPORT_VIEW", "TEAM_DIRECTORY"], "revoke": ["GIT_READ", "GIT_WRITE"],
                "retain": ["JIRA_EDIT", "VPN_ACCESS"]}
    for change, permissions in expected.items():
        assert sorted(plan["permissions"][change]) == permissions, change
    after = httpx.get(employee_url, headers=headers).raise_for_status().json()
    assert after == before, "Employee changed during the draft check"
    print("PASS: EF-1005 Engineer to Manager draft matched all six permissions. Employee unchanged.")


if __name__ == "__main__":
    main()
