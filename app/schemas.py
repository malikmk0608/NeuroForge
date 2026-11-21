"""Validated JSON inputs and outputs for the API."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RequestContext(BaseModel):
    """Descriptive request metadata; never an authenticated actor or approval."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    request_title: str = Field(default="Employee access change", min_length=1, max_length=160)
    priority: Literal["LOW", "NORMAL", "HIGH"] = "NORMAL"
    requester_reference: str | None = Field(default=None, min_length=1, max_length=160)
    business_unit: str | None = Field(default=None, min_length=1, max_length=120)


class RequestDetails(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    effective_date: date | None = Field(default=None, description="Requested date, YYYY-MM-DD. Scheduling is not implemented yet.")
    justification: str | None = Field(default=None, min_length=1, max_length=1000)
    manager: str | None = Field(default=None, pattern=r"^EF-\d{4}$", description="Manager employee code, for example EF-1002.")
    assignment_type: Literal["PERMANENT", "TEMPORARY"] | None = None


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    details: RequestDetails = Field(default_factory=RequestDetails)
    request_context: RequestContext = Field(default_factory=RequestContext)
    use_model: bool = Field(default=False, description="Explicitly use the configured OpenAI or Groq interpreter. Sends this message and supplied details to that provider; requires server-side configuration.")


class RoleChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_code: str = Field(pattern=r"^EF-\d{4}$")
    target_role: Literal["ENGINEER", "MANAGER", "HR", "FINANCE"]
    details: RequestDetails = Field(default_factory=RequestDetails)
    request_context: RequestContext = Field(default_factory=RequestContext)


class OffboardRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_code: str = Field(pattern=r"^EF-\d{4}$")
    details: RequestDetails = Field(default_factory=RequestDetails)
    request_context: RequestContext = Field(default_factory=RequestContext)


class ActivityStep(BaseModel):
    node: str
    status: Literal["completed", "needs_clarification", "not_found", "not_implemented"]
    message: str


class Interpretation(BaseModel):
    action: Literal["ROLE_CHANGE", "OFFBOARD"] | None = None
    employee_code: str | None = None
    target_role: Literal["ENGINEER", "MANAGER", "HR", "FINANCE"] | None = None
    clarification_questions: list[str] = Field(default_factory=list)


class Employee(BaseModel):
    employee_code: str
    name: str
    department: str
    role: str
    permissions: list[str]
    version: int | None = Field(default=None, ge=1, strict=True)


class RolePolicy(BaseModel):
    role: str
    permissions: list[str]
    version: int | None = Field(default=None, ge=1, strict=True)


class PermissionChanges(BaseModel):
    grant: list[str]
    revoke: list[str]
    retain: list[str]


class RiskSuggestion(BaseModel):
    level: Literal["LOW", "MEDIUM", "HIGH"]
    reasons: list[str]
    advisory_only: Literal[True] = True
    rules_version: Literal["demo-v1"] = "demo-v1"


class AccessPlan(BaseModel):
    status: Literal["DRAFT"] = "DRAFT"
    employee_code: str
    request_context: RequestContext = Field(default_factory=RequestContext)
    action: Literal["ROLE_CHANGE", "OFFBOARD"]
    current_role: str
    target_role: Literal["ENGINEER", "MANAGER", "HR", "FINANCE"] | None
    expected_employee_version: int | None = Field(default=None, ge=1, strict=True)
    expected_policy_version: int | None = Field(default=None, ge=1, strict=True)
    permissions: PermissionChanges
    has_changes: bool
    risk_suggestion: RiskSuggestion
    required_approvals: Literal[2] = 2
    ready_for_submission: bool = False
    details: RequestDetails
    details_complete: bool
    missing_details: list[str]
    clarification_questions: list[str]

    @model_validator(mode="after")
    def check_action_target(self):
        if self.action == "ROLE_CHANGE" and self.target_role is None:
            raise ValueError("Role changes require a target role.")
        if self.action == "OFFBOARD" and self.target_role is not None:
            raise ValueError("Offboarding must not have a target role.")
        return self


class SubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan: AccessPlan


class SubmissionReceipt(BaseModel):
    request_id: str = Field(min_length=1, max_length=200)
    action: Literal["ROLE_CHANGE", "OFFBOARD"]
    employee_code: str = Field(pattern=r"^EF-\d{4}$")
    status: Literal["PENDING_APPROVAL"]
    required_approvals: Literal[2]
    approved_count: Literal[0]


class AgentResponse(BaseModel):
    status: Literal["draft_plan_ready", "employee_not_found", "policy_not_found", "needs_clarification"]
    message: str
    backend_mode: Literal["mock", "http"] = "mock"
    interpretation: Interpretation
    extracted_details: RequestDetails = Field(default_factory=RequestDetails)
    current_employee: Employee | None = None
    plan: AccessPlan | None = None
    activity_steps: list[ActivityStep]
