"""Explainable prototype heuristics, not an enterprise risk policy.

Evaluate the proposed change, not the employee's personal characteristics.
These suggestions never change the two-approval requirement.
"""

from app.schemas import PermissionChanges, RiskSuggestion

SENSITIVE_GRANTS = {"HRIS_READ", "HRIS_EDIT", "ERP_READ", "EXPENSE_APPROVE"}
KNOWN_PERMISSIONS = SENSITIVE_GRANTS | {
    "GIT_READ", "GIT_WRITE", "JIRA_EDIT", "VPN_ACCESS", "TEAM_DIRECTORY",
    "REPORT_VIEW", "EMPLOYEE_DIRECTORY",
}


def suggest_risk(action: str, changes: PermissionChanges, has_changes: bool) -> RiskSuggestion:
    if action == "OFFBOARD":
        return RiskSuggestion(level="HIGH", reasons=[
            "Offboarding proposes removing all current access and can disrupt the employee's ability to work.",
        ])
    if not has_changes:
        return RiskSuggestion(level="LOW", reasons=["The requested role and permissions already match current access."])

    reasons = []
    sensitive = sorted(set(changes.grant) & SENSITIVE_GRANTS)
    unknown = sorted(set(changes.grant) - KNOWN_PERMISSIONS)
    if sensitive:
        reasons.append("New HR or financial access is proposed: " + ", ".join(sensitive) + ".")
    if unknown:
        reasons.append("New permissions have no classification in the demo risk rules: " + ", ".join(unknown) + ".")
    if reasons:
        return RiskSuggestion(level="HIGH", reasons=reasons)

    if changes.grant:
        reasons.append(f"The request grants {len(changes.grant)} additional permission(s).")
    if changes.revoke:
        reasons.append(f"The request revokes {len(changes.revoke)} permission(s), which may affect ongoing work.")
    if not reasons:
        reasons.append("The role changes even though its permission set matches current access.")
    return RiskSuggestion(level="MEDIUM", reasons=reasons)
