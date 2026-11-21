"""Validate a reviewed draft again, then ask Java to persist it for approval."""

from uuid import UUID

from app.graph import build_graph
from app.http_backend import BackendError, HttpEmployeeBackend
from app.schemas import AccessPlan, SubmissionReceipt


async def submit_reviewed_plan(backend, reviewed: AccessPlan, idempotency_key: UUID) -> SubmissionReceipt:
    if not isinstance(backend, HttpEmployeeBackend):
        raise BackendError("Submission is disabled in mock mode. Connect the Java backend first.", status_code=409, code="MOCK_SUBMISSION_DISABLED")
    if reviewed.clarification_questions:
        raise BackendError("Resolve the draft's clarification questions before submission.", status_code=422, code="INCOMPLETE_REQUEST")
    if reviewed.details.assignment_type == "TEMPORARY":
        raise BackendError("Temporary assignments remain draft-only until expiry behavior is implemented.", status_code=422, code="TEMPORARY_ASSIGNMENT_UNSUPPORTED")

    # Do not trust submitted permission lists, readiness flags, risk, or roles.
    # Recompute from fresh backend records without another model call.
    message = (f"Offboard {reviewed.employee_code}" if reviewed.action == "OFFBOARD" else
               f"Move {reviewed.employee_code} to {reviewed.target_role}")
    result = await build_graph(backend).ainvoke({
        "message": message, "details": reviewed.details,
        "activity_steps": [], "use_model": False,
    })
    fresh = result.get("plan")
    if fresh is None:
        raise BackendError("Employee or role policy is no longer available. Generate a new draft.", status_code=409, code="STALE_PLAN")
    if not fresh.details_complete:
        raise BackendError("Required request details or manager validation are incomplete.", status_code=422, code="INCOMPLETE_REQUEST")
    if not fresh.has_changes:
        raise BackendError("The request makes no changes. No approval request was created.", status_code=409, code="NO_CHANGES")
    if not fresh.ready_for_submission:
        raise BackendError("Submission requires versioned backend employee/policy records. Update the backend contract and generate a new draft.", status_code=409, code="VERSION_REQUIRED")
    for field in ("current_role", "expected_employee_version", "expected_policy_version", "permissions"):
        if getattr(fresh, field) != getattr(reviewed, field):
            raise BackendError("The reviewed draft is stale or was modified. Generate and review a new draft before submission.", status_code=409, code="STALE_PLAN")

    payload = {
        "action": fresh.action,
        "employee_code": fresh.employee_code,
        "expected_employee_version": fresh.expected_employee_version,
        "current_role": fresh.current_role,
        "target_role": fresh.target_role,
        **fresh.details.model_dump(mode="json"),
        "proposed_permissions": fresh.permissions.model_dump(),
    }
    if fresh.action == "ROLE_CHANGE":
        payload["expected_policy_version"] = fresh.expected_policy_version
    else:
        payload["assignment_type"] = None
    # Java must atomically recheck versions and derive PENDING_APPROVAL itself.
    # Idempotency and requester authorization are enforced by Java, not a local cache.
    return await backend.create_access_request(payload, str(idempotency_key))
