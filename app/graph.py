"""Interpret a request, stopping early when clarification is required."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.backend import EmployeeBackend, create_configured_backend
from app.clarification import missing_detail_questions
from app.detail_extractor import extract_details
from app.interpreter import interpret_message
from app.model_interpreter import interpret_with_model
from app.planner import compare_permission_sets
from app.risk import suggest_risk
from app.schemas import AccessPlan, ActivityStep, Employee, Interpretation, PermissionChanges, RequestDetails, RequestContext


class AgentState(TypedDict):
    # State is the information passed from one node to the next.
    message: str
    activity_steps: list[ActivityStep]
    interpretation: Interpretation
    current_employee: Employee | None
    permission_changes: PermissionChanges | None
    plan: AccessPlan
    details: RequestDetails
    detail_issues: list[str]
    use_model: bool
    expected_policy_version: int | None
    backend_mode: str
    request_context: RequestContext


async def interpret(state: AgentState) -> dict:
    structured = state.get("details", RequestDetails())
    if state.get("use_model", False):
        interpretation, details, issues = await interpret_with_model(state["message"], structured)
        method = "model-assisted extraction with local validation"
    else:
        action_message, details, issues = extract_details(state["message"], structured)
        interpretation = interpret_message(action_message)
        method = "deterministic rules"
    needs_clarification = bool(interpretation.clarification_questions)
    return {
        "interpretation": interpretation,
        "details": details,
        "detail_issues": issues,
        "activity_steps": [ActivityStep(
            node="interpret",
            status="needs_clarification" if needs_clarification else "completed",
            message=("More information is required before employee lookup."
                     if needs_clarification else f"Extracted the requested action and employee details using {method}."),
        )],
    }


def route_after_interpret(state: AgentState) -> str:
    return END if state["interpretation"].clarification_questions else "retrieve_employee"


def route_after_retrieval(state: AgentState) -> str:
    return "compare_permissions" if state["current_employee"] else END


def route_after_comparison(state: AgentState) -> str:
    return "create_plan" if state["permission_changes"] is not None else END


def create_plan(state: AgentState) -> dict:
    employee = state["current_employee"]
    changes = state["permission_changes"]
    target_role = state["interpretation"].target_role
    action = state["interpretation"].action
    assert employee is not None and changes is not None and action is not None
    details = state.get("details", RequestDetails())
    missing, questions = missing_detail_questions(details, action)
    questions.extend(state.get("detail_issues", []))
    has_changes = bool(changes.grant or changes.revoke or employee.role != target_role)
    ready = bool(
        state.get("backend_mode") == "http" and not questions and has_changes
        and employee.version is not None
        and (action == "OFFBOARD" or state.get("expected_policy_version") is not None)
        and details.assignment_type != "TEMPORARY"
    )
    plan = AccessPlan(
        employee_code=employee.employee_code,
        request_context=state.get("request_context", RequestContext()),
        action=action,
        current_role=employee.role,
        target_role=target_role,
        expected_employee_version=employee.version,
        expected_policy_version=state.get("expected_policy_version"),
        permissions=changes,
        has_changes=has_changes,
        risk_suggestion=suggest_risk(action, changes, has_changes),
        details=details,
        missing_details=missing,
        clarification_questions=questions,
        details_complete=not questions,
        ready_for_submission=ready,
    )
    return {
        "plan": plan,
        "activity_steps": [*state["activity_steps"], ActivityStep(
            node="create_plan", status="completed",
            message=("Created a draft plan. Request details need clarification; nothing has been submitted, approved, or applied."
                     if questions else "Created a draft with complete request details. Nothing has been submitted, approved, or applied."),
        )],
    }


def build_graph(backend: EmployeeBackend):
    async def compare_permissions(state: AgentState) -> dict:
        employee = state["current_employee"]
        target_role = state["interpretation"].target_role
        assert employee is not None
        if state["interpretation"].action == "OFFBOARD":
            policy_version = None
            changes = compare_permission_sets(employee.permissions, [])
            comparison_message = "Offboarding draft: revoke all current permissions, with no grants or retained access."
        else:
            assert target_role is not None
            policy = await backend.get_role_policy(target_role)
            policy_version = policy.version if policy else None
            changes = compare_permission_sets(employee.permissions, policy.permissions) if policy else None
            comparison_message = (f"Compared actual current permissions with the target role's {backend.mode} policy."
                                  if policy else "Target role policy was not found. No plan was generated.")
        return {
            "permission_changes": changes,
            "expected_policy_version": policy_version,
            "activity_steps": [*state["activity_steps"], ActivityStep(
                node="compare_permissions", status="completed" if changes is not None else "not_found",
                message=comparison_message,
            )],
        }

    async def retrieve_employee(state: AgentState) -> dict:
        code = state["interpretation"].employee_code
        assert code is not None  # Interpretation routing has already checked this.
        employee = await backend.get_employee(code)
        details = state.get("details", RequestDetails())
        detail_issues = list(state.get("detail_issues", []))
        if employee and details.manager:
            if details.manager == code:
                detail_issues.append("The employee cannot be their own manager. Provide a different manager employee code.")
            elif await backend.get_employee(details.manager) is None:
                detail_issues.append(f"The manager employee code was not found in the {backend.mode} backend. Provide an existing employee code.")
        return {
            "current_employee": employee,
            "backend_mode": backend.mode,
            "detail_issues": detail_issues,
            "activity_steps": [
                *state["activity_steps"],
                ActivityStep(
                    node="retrieve_employee",
                    status="completed" if employee else "not_found",
                    message=(f"Retrieved {code} and current permissions from the {backend.mode} backend."
                             if employee else f"Employee {code} was not found in the {backend.mode} backend. Verify the employee code."),
                ),
            ],
        }

    workflow = StateGraph(AgentState)
    workflow.add_node("interpret", interpret)
    workflow.add_node("retrieve_employee", retrieve_employee)
    workflow.add_node("compare_permissions", compare_permissions)
    workflow.add_node("create_plan", create_plan)

    workflow.add_edge(START, "interpret")
    workflow.add_conditional_edges("interpret", route_after_interpret, ["retrieve_employee", END])
    workflow.add_conditional_edges("retrieve_employee", route_after_retrieval, ["compare_permissions", END])
    workflow.add_conditional_edges("compare_permissions", route_after_comparison, ["create_plan", END])
    workflow.add_edge("create_plan", END)
    return workflow.compile()


backend_client = create_configured_backend()
agent_graph = build_graph(backend_client)
