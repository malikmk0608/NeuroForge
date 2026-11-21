"""HTTP entry point: run with python -m uvicorn app.main:app --reload --port 8000."""

from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.graph import backend_client, build_graph
from app.http_backend import BackendError, HttpEmployeeBackend
from app.model_interpreter import ModelUnavailable, model_configuration
from app.schemas import AgentRequest, AgentResponse, OffboardRequest, RoleChangeRequest, SubmissionRequest, SubmissionReceipt
from app.submission import submit_reviewed_plan

app = FastAPI(
    title="NeuroForge AI Agent",
    description="Role-change/offboarding drafts and Java request submission. Defaults to read-only mock mode.",
    version="0.13.0",
)

STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")


def get_backend(authorization: Annotated[str | None, Header()] = None):
    if isinstance(backend_client, HttpEmployeeBackend):
        if not authorization or not authorization.startswith("Bearer ") or not authorization[7:].strip():
            raise BackendError("A backend-issued Bearer token is required for HTTP mode.", status_code=401, code="AUTHENTICATION_REQUIRED")
        return backend_client.with_authorization(authorization)
    return backend_client


@app.exception_handler(BackendError)
async def backend_error(request: Request, error: BackendError):
    return JSONResponse(status_code=error.status_code, content={"detail": str(error), "code": error.code})


@app.exception_handler(ModelUnavailable)
async def model_error(request: Request, error: ModelUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.get("/", include_in_schema=False)
async def request_form():
    return FileResponse(STATIC_DIRECTORY / "index.html")


@app.get("/agent/form-options")
async def form_options(backend=Depends(get_backend)):
    return {
        "backend_mode": backend.mode,
        "employees": await backend.list_employees(),
        "roles": [policy.role for policy in await backend.list_role_policies()],
        "model": model_configuration(),
    }


@app.post("/agent/role-change", response_model=AgentResponse)
async def role_change(request: RoleChangeRequest, backend=Depends(get_backend)):
    # The form supplies typed fields. Adapt them to the existing graph so the
    # form and optional natural-language route use identical planning logic.
    return await plan(AgentRequest(
        message=f"Move {request.employee_code} to {request.target_role}",
        details=request.details,
        request_context=request.request_context,
    ), backend)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "neuroforge-ai-agent", "milestone": "ai_assisted_form", "backend_mode": backend_client.mode, "model": model_configuration()}


@app.post("/agent/offboard", response_model=AgentResponse)
async def offboard(request: OffboardRequest, backend=Depends(get_backend)):
    return await plan(AgentRequest(
        message=f"Offboard {request.employee_code}", details=request.details,
        request_context=request.request_context,
    ), backend)


@app.post("/agent/plan", response_model=AgentResponse)
async def plan(request: AgentRequest, backend=Depends(get_backend)):
    result = await build_graph(backend).ainvoke({"message": request.message, "details": request.details, "request_context": request.request_context, "use_model": request.use_model, "activity_steps": []})
    interpretation = result["interpretation"]
    needs_clarification = bool(interpretation.clarification_questions)
    employee = result.get("current_employee")
    if needs_clarification:
        status = "needs_clarification"
        message = "Please answer the clarification questions and resend the complete request."
    elif employee is None:
        status = "employee_not_found"
        message = f"The employee code was not found in the {backend.mode} backend. Verify the code and resend the request."
    elif result.get("plan") is None:
        status = "policy_not_found"
        message = "The target role policy was not found. No access plan was generated."
    else:
        status = "draft_plan_ready"
        message = ("Draft plan generated. Answer plan.clarification_questions and resend the complete request."
                   if not result["plan"].details_complete else
                   "Draft plan and request details are complete. No backend request has been created and no access has changed.")
    return AgentResponse(
        status=status,
        backend_mode=backend.mode,
        message=message,
        interpretation=interpretation,
        extracted_details=result.get("details", request.details),
        current_employee=employee,
        plan=result.get("plan"),
        activity_steps=result["activity_steps"],
    )


@app.post("/agent/submit", response_model=SubmissionReceipt)
async def submit(
    request: SubmissionRequest,
    idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    backend=Depends(get_backend),
):
    return await submit_reviewed_plan(backend, request.plan, idempotency_key)
