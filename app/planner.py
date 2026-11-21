"""Permission arithmetic: no model calls, approvals, or access mutations."""

from app.schemas import PermissionChanges


def compare_permission_sets(current: list[str], target: list[str]) -> PermissionChanges:
    current_set = set(current)
    target_set = set(target)
    return PermissionChanges(
        grant=sorted(target_set - current_set),
        revoke=sorted(current_set - target_set),
        retain=sorted(current_set & target_set),
    )
