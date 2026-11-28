"""Java API adapter for the proposed contract, with no mock fallback or retries."""

from urllib.parse import quote, urlsplit

import httpx
from pydantic import TypeAdapter, ValidationError

from app.schemas import Employee, RolePolicy, SubmissionReceipt


class BackendError(Exception):
    def __init__(self, message: str, *, status_code: int = 502, code: str = "BACKEND_ERROR"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class HttpEmployeeBackend:
    mode = "http"

    def __init__(self, base_url: str, *, authorization: str | None = None, transport=None):
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("BACKEND_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment.")
        if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Use HTTPS for non-local backend connections.")
        self.base_url = base_url.rstrip("/")
        self.authorization = authorization
        self.transport = transport

    def with_authorization(self, authorization: str):
        return HttpEmployeeBackend(self.base_url, authorization=authorization, transport=self.transport)

    async def _request(self, method: str, path: str, *, payload=None, idempotency_key=None, allow_not_found=False):
        if not self.authorization or not self.authorization.startswith("Bearer ") or not self.authorization[7:].strip():
            raise BackendError("A backend-issued Bearer token is required for HTTP mode.", status_code=401, code="AUTHENTICATION_REQUIRED")
        headers = {"Authorization": self.authorization}
        if idempotency_key:
            headers["Idempotency-Key"] = str(idempotency_key)
        try:
            async with httpx.AsyncClient(timeout=10.0, transport=self.transport, follow_redirects=False) as client:
                response = await client.request(method, f"{self.base_url}{path}", headers=headers, json=payload)
            if allow_not_found and response.status_code == 404:
                return None
            if response.status_code not in ({200, 201} if method == "POST" else {200}):
                status = response.status_code
                messages = {
                    400: "The backend rejected the request fields.",
                    401: "The backend rejected or expired the caller's login token.",
                    403: "The backend denied this caller's access.",
                    404: "The backend resource or proposed endpoint was not found.",
                    409: "The backend detected a stale plan or conflicting submission. Refresh the draft; reuse the same idempotency key only for the same submission.",
                    422: "The backend rejected the request under its validation or policy rules.",
                    429: "The backend rate-limited this request. Retry later.",
                }
                raise BackendError(messages.get(status, "The backend is unavailable or returned an unexpected status."),
                                   status_code=status if status in messages else 502, code=f"BACKEND_HTTP_{status}")
            return response.json()
        except BackendError:
            raise
        except httpx.TimeoutException:
            suffix = " Creation outcome is unconfirmed; retry only with the same idempotency key." if method == "POST" else ""
            raise BackendError("The backend request timed out." + suffix, status_code=504, code="BACKEND_TIMEOUT") from None
        except httpx.RequestError:
            raise BackendError("Unable to connect securely to the backend. No mock data was substituted.", status_code=503, code="BACKEND_UNAVAILABLE") from None
        except (ValueError, TypeError):
            raise BackendError("The backend returned invalid JSON. For submission, check the outcome before retrying with the same idempotency key.", code="INVALID_BACKEND_RESPONSE") from None

    @staticmethod
    def _validate(model, data):
        try:
            return TypeAdapter(model).validate_python(data)
        except (ValidationError, ValueError, TypeError):
            raise BackendError("The backend response does not match the agreed API contract. For submission, verify the request outcome before retrying with the same key.", code="INVALID_BACKEND_RESPONSE") from None

    async def get_employee(self, employee_code: str) -> Employee | None:
        data = await self._request("GET", f"/api/employees/{quote(employee_code, safe='')}", allow_not_found=True)
        if data is None:
            return None
        employee = self._validate(Employee, data)
        if employee.employee_code != employee_code:
            raise BackendError("The backend returned the wrong employee.", code="INVALID_BACKEND_RESPONSE")
        return employee

    async def get_role_policy(self, role: str) -> RolePolicy | None:
        data = await self._request("GET", f"/api/roles/{quote(role, safe='')}/permissions", allow_not_found=True)
        if data is None:
            return None
        policy = self._validate(RolePolicy, data)
        if policy.role != role:
            raise BackendError("The backend returned the wrong role policy.", code="INVALID_BACKEND_RESPONSE")
        return policy

    async def list_employees(self) -> list[Employee]:
        return self._validate(list[Employee], await self._request("GET", "/api/employees"))

    async def list_role_policies(self) -> list[RolePolicy]:
        return self._validate(list[RolePolicy], await self._request("GET", "/api/roles"))

    async def create_access_request(self, payload: dict, idempotency_key: str) -> SubmissionReceipt:
        receipt = self._validate(SubmissionReceipt, await self._request(
            "POST", "/api/access-requests", payload=payload, idempotency_key=idempotency_key,
        ))
        if receipt.action != payload["action"] or receipt.employee_code != payload["employee_code"]:
            raise BackendError("The backend receipt does not match this submission. Check the outcome before retrying with the same key.", code="INVALID_BACKEND_RESPONSE")
        return receipt
