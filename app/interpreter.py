"""Conservative rules for a first set of role-change sentences, without an LLM.

These role names come from the report, not from a backend policy lookup.
Extraction does not establish that an employee exists or a role is authorized.
"""

import re

from app.schemas import Interpretation

EMPLOYEE_CODE = re.compile(r"\bEF[-\s]?(\d{4})\b", re.IGNORECASE)
CHANGE_VERB = re.compile(r"\b(move|promote|demote|upgrade|downgrade|transfer|change|switch|assign|make)\b", re.IGNORECASE)
TARGET_ROLE = re.compile(
    r"\b(?:to|as)\s+(?:(?:an?|the)\s+)?(?:(?:new|role\s+of)\s+)?"
    r"(engineer|manager|hr|finance)\b|"
    r"\bmake\s+EF[-\s]?\d{4}\s+(?:(?:an?|the)\s+)?(engineer|manager|hr|finance)\b",
    re.IGNORECASE,
)
UNSUPPORTED_CONTEXT = re.compile(
    r"\b(not|never|unless|if|don['’]?t|shouldn['’]?t|do\s+not|how|explain|hypothetical|archive|onboard|terminate|delete|revoke|remove)\b",
    re.IGNORECASE,
)


def interpret_message(message: str) -> Interpretation:
    result = Interpretation()
    codes = sorted({f"EF-{match}" for match in EMPLOYEE_CODE.findall(message)})
    if len(codes) == 1:
        result.employee_code = codes[0]
    elif not codes:
        result.clarification_questions.append("What is the employee code, for example EF-1001?")
    else:
        result.clarification_questions.append("Please request a change for one employee at a time.")

    # Do not guess the meaning of conditional, negative, or other lifecycle requests.
    if UNSUPPORTED_CONTEXT.search(message):
        result.clarification_questions.append(
            "Please state one direct role-change or offboarding request without conditions. Other lifecycle actions are not supported yet."
        )
        return result

    if re.search(r"\b(offboard|deactivate)\b", message, re.IGNORECASE):
        if CHANGE_VERB.search(message) or re.search(r"\b(engineer|manager|hr|finance)\b", message, re.IGNORECASE):
            result.clarification_questions.append("Please request either offboarding or a role change, one action at a time.")
        elif re.fullmatch(r"\s*(?:please\s+)?(?:offboard|deactivate)\s+(?:employee\s+)?EF[-\s]?\d{4}[.!]?\s*", message, re.IGNORECASE):
            result.action = "OFFBOARD"
        else:
            result.clarification_questions.append("Please use a direct offboarding request, for example: Offboard EF-1001.")
        return result

    if CHANGE_VERB.search(message):
        result.action = "ROLE_CHANGE"
    else:
        result.clarification_questions.append(
            "Are you requesting a role change? For example: Move EF-1001 to MANAGER."
        )

    roles = {
        (match.group(1) or match.group(2)).upper()
        for match in TARGET_ROLE.finditer(message)
    }
    # A sentence naming multiple roles may describe a source role or alternatives.
    # Ask instead of incorrectly treating a source role as the target.
    mentioned_roles = {
        role.upper()
        for role in re.findall(r"\b(engineer|manager|hr|finance)\b", message, re.IGNORECASE)
    }
    if len(roles) == 1 and len(mentioned_roles) == 1:
        result.target_role = roles.pop()
    elif len(mentioned_roles) > 1:
        result.clarification_questions.append(
            "Please specify just the target role, for example: Move EF-1001 to MANAGER."
        )
    else:
        result.clarification_questions.append(
            "What is the target role? Use 'to ENGINEER', 'to MANAGER', 'to HR', or 'to FINANCE'."
        )
    return result
