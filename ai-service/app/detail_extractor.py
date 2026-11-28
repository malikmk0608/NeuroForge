"""Extract explicitly marked detail clauses; this is not general NLP.

Semicolons/newlines separate fields. Structured and textual values must agree.
"""

import re

from pydantic import ValidationError

from app.schemas import RequestDetails

LABELS = [
    ("effective_date", r"(?:effective\s+date\s*:|effective\s+on\s+)"),
    ("justification", r"(?:justification\s*:|because\s+)"),
    ("manager", r"manager\s*(?::|\s)\s*"),
    ("assignment_type", r"assignment\s+type\s*(?::|\s)\s*"),
]


def extract_details(message: str, structured: RequestDetails) -> tuple[str, RequestDetails, list[str]]:
    values = structured.model_dump()
    issues = []
    action_clauses = []
    extracted = {}

    def collect(field: str, raw: str):
        raw = raw.strip()
        if field == "manager":
            match = re.fullmatch(r"EF[-\s]?(\d{4})", raw, re.IGNORECASE)
            raw = f"EF-{match[1]}" if match else raw
        if field == "assignment_type":
            raw = raw.upper()
        try:
            value = getattr(RequestDetails(**{field: raw}), field)
        except ValidationError:
            issues.append(f"The {field} in your message is invalid. Please correct it using the documented format.")
            return
        if field in extracted and extracted[field] != value:
            issues.append(f"Your message contains conflicting {field} values. Please provide one value.")
        extracted[field] = value

    for clause in re.split(r"[;\n]", message):
        clause = clause.strip()
        if not clause:
            continue
        for field, label in LABELS:
            match = re.fullmatch(label + r"(.*)", clause, re.IGNORECASE)
            if match:
                collect(field, match[1])
                break
        else:
            # Also accept a date attached to the action clause itself.
            match = re.search(r"\beffective\s+on\s+(.+)$", clause, re.IGNORECASE)
            if match:
                collect("effective_date", match[1])
                clause = clause[:match.start()].strip()
            action_clauses.append(clause)

    for field, value in extracted.items():
        if values[field] is not None and values[field] != value:
            issues.append(f"The {field} in your message conflicts with details.{field}. Please make them agree.")
        elif values[field] is None:
            values[field] = value

    return "; ".join(action_clauses), RequestDetails(**values), issues
