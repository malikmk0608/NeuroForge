"""Read-only sample backend. This does not call the Java service.

The graph calls get_employee rather than reading sample records itself.
Later, an HTTP client can implement the same interface using the agreed API.
Never silently substitute mock data when a real backend fails.
"""

from typing import Protocol

from app.schemas import Employee, RolePolicy


class EmployeeBackend(Protocol):
    mode: str
    async def get_employee(self, employee_code: str) -> Employee | None: ...
    async def get_role_policy(self, role: str) -> RolePolicy | None: ...
    async def list_employees(self) -> list[Employee]: ...
    async def list_role_policies(self) -> list[RolePolicy]: ...


class MockEmployeeBackend:
    mode = "mock"
    def __init__(self):
        # Synthetic employees copied from the project report.
        employees = [
            Employee(
                employee_code="EF-1001", name="Aarav Sharma", department="Engineering",
                role="ENGINEER", permissions=["GIT_READ", "GIT_WRITE", "JIRA_EDIT", "VPN_ACCESS"],
            ),
            Employee(
                employee_code="EF-1002", name="Priya Patel", department="Engineering",
                role="MANAGER", permissions=["TEAM_DIRECTORY", "REPORT_VIEW", "JIRA_EDIT", "VPN_ACCESS"],
            ),
            Employee(
                employee_code="EF-1003", name="Rohan Mehta", department="HR",
                role="HR", permissions=["EMPLOYEE_DIRECTORY", "HRIS_READ", "HRIS_EDIT"],
            ),
            Employee(
                employee_code="EF-1004", name="Sneha Reddy", department="Finance",
                role="FINANCE", permissions=["ERP_READ", "EXPENSE_APPROVE", "REPORT_VIEW"],
            ),
        ]
        for code, name in [
            ("EF-1005", "Ananya Rao"),
            ("EF-1006", "Kabir Shah"),
            ("EF-1007", "Diya Menon"),
        ]:
            employees.append(Employee(
                employee_code=code, name=name, department="Engineering", role="ENGINEER",
                permissions=list(employees[0].permissions),
            ))
        self._employees = {employee.employee_code: employee for employee in employees}
        # Prototype assumption: the report's listed key permissions are treated
        # as complete role policies. Teammates must confirm these before integration.
        self._policies = {
            "ENGINEER": RolePolicy(role="ENGINEER", permissions=["GIT_READ", "GIT_WRITE", "JIRA_EDIT", "VPN_ACCESS"]),
            "MANAGER": RolePolicy(role="MANAGER", permissions=["TEAM_DIRECTORY", "REPORT_VIEW", "JIRA_EDIT", "VPN_ACCESS"]),
            "HR": RolePolicy(role="HR", permissions=["EMPLOYEE_DIRECTORY", "HRIS_READ", "HRIS_EDIT"]),
            "FINANCE": RolePolicy(role="FINANCE", permissions=["ERP_READ", "EXPENSE_APPROVE", "REPORT_VIEW"]),
        }

    async def get_employee(self, employee_code: str) -> Employee | None:
        employee = self._employees.get(employee_code)
        # Return a copy so callers cannot modify the underlying sample record.
        return employee.model_copy(deep=True) if employee else None

    async def get_role_policy(self, role: str) -> RolePolicy | None:
        policy = self._policies.get(role)
        return policy.model_copy(deep=True) if policy else None

    async def list_employees(self) -> list[Employee]:
        return [employee.model_copy(deep=True) for employee in self._employees.values()]

    async def list_role_policies(self) -> list[RolePolicy]:
        return [policy.model_copy(deep=True) for policy in self._policies.values()]


def create_configured_backend() -> EmployeeBackend:
    import os
    from app.http_backend import HttpEmployeeBackend

    mode = os.getenv("BACKEND_MODE", "mock").strip().lower()
    if mode == "mock":
        return MockEmployeeBackend()
    if mode == "http":
        return HttpEmployeeBackend(os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8081"))
    raise ValueError("BACKEND_MODE must be mock or http.")
