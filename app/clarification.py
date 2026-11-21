"""Explain which structured request details are still required."""

from app.schemas import RequestDetails

DETAIL_QUESTIONS = {
    "effective_date": "On what date should the change take effect? Provide YYYY-MM-DD.",
    "justification": "What is the business justification for this change?",
    "manager": "What is the manager's employee code, for example EF-1002?",
    "assignment_type": "Is this assignment PERMANENT or TEMPORARY?",
}


def missing_detail_questions(details: RequestDetails, action: str = "ROLE_CHANGE") -> tuple[list[str], list[str]]:
    required = [field for field in DETAIL_QUESTIONS if action != "OFFBOARD" or field != "assignment_type"]
    missing = [field for field in required if getattr(details, field) is None]
    return missing, [DETAIL_QUESTIONS[field] for field in missing]
