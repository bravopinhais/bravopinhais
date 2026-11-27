from types import SimpleNamespace

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import (
    AuthenticatedPrincipal,
    require_capability_dependency,
)


def make_principal(profile: str = "Admin") -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject="google-test-subject",
        email="teste@example.com",
        profile=profile,
        account_status="Ativo",
    )


def build_test_client(principal: AuthenticatedPrincipal | None = None, audit_sink=None) -> TestClient:
    application = FastAPI()
    application.state.services = SimpleNamespace(audit_sink=audit_sink)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = "req_test_authorization"
        return await call_next(request)

    router = APIRouter()

    async def fake_authentication() -> AuthenticatedPrincipal:
        if principal is None:
            raise HTTPException(status_code=401, detail="Token obrigatório.")
        return principal

    application.dependency_overrides[get_current_principal] = fake_authentication

    @router.get(
        "/protected",
        dependencies=[Depends(require_capability_dependency("financeiro:read"))],
    )
    async def protected_resource():
        return {"ok": True}

    application.include_router(router)
    return TestClient(application)


def test_protected_route_returns_401_without_identity():
    response = build_test_client().get("/protected")
    assert response.status_code == 401


def test_protected_route_returns_403_for_operator_until_matrix_is_approved():
    response = build_test_client(make_principal("Operador")).get("/protected")
    assert response.status_code == 403


def test_protected_route_returns_403_for_admin_until_matrix_is_approved():
    response = build_test_client(make_principal("Admin")).get("/protected")
    assert response.status_code == 403


def test_protected_route_rejects_unknown_capability_even_for_admin():
    application = FastAPI()
    router = APIRouter()

    async def authenticated_admin() -> AuthenticatedPrincipal:
        return make_principal("Admin")

    application.dependency_overrides[get_current_principal] = authenticated_admin

    @router.get(
        "/protected-unknown",
        dependencies=[Depends(require_capability_dependency("financeiro:superuser"))],
    )
    async def protected_unknown():
        return {"ok": True}

    application.include_router(router)
    response = TestClient(application).get("/protected-unknown")
    assert response.status_code == 403


class RecordingAuditSink:
    def __init__(self, *, fail=False):
        self.events = []
        self.fail = fail

    def append(self, event):
        if self.fail:
            raise RuntimeError("audit unavailable")
        self.events.append(event)


def test_authenticated_permission_denial_is_audited_without_personal_payload():
    sink = RecordingAuditSink()
    principal = make_principal("Admin")

    response = build_test_client(principal, sink).get("/protected")

    assert response.status_code == 403
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.actor_subject == principal.subject
    assert event.action == "financeiro:read"
    assert event.entity_type == "authorization"
    assert event.entity_id is None
    assert event.outcome == "denied"
    assert event.request_id == "req_test_authorization"
    assert not hasattr(event, "email")


def test_audit_failure_does_not_turn_permission_denial_into_success():
    sink = RecordingAuditSink(fail=True)

    response = build_test_client(make_principal("Admin"), sink).get("/protected")

    assert response.status_code == 403



def build_failure_client(monkeypatch, sink):
    from app import main as main_module
    from app.main import create_app

    monkeypatch.setattr(
        "app.core.authorization.ROLE_CAPABILITIES",
        {"Admin": frozenset({"dashboard:read"}), "Operador": frozenset()},
    )
    application = create_app(storage_backend="memory")
    application.state.services = SimpleNamespace(audit_sink=sink)
    application.dependency_overrides[get_current_principal] = lambda: make_principal()

    @application.get(
        "/test-unexpected-failure",
        dependencies=[Depends(require_capability_dependency("dashboard:read"))],
    )
    def unexpected_failure():
        raise RuntimeError("sensitive database detail must not be returned")

    return TestClient(application, raise_server_exceptions=False)


def test_unexpected_authenticated_failure_is_audited_with_minimal_fields(monkeypatch):
    sink = RecordingAuditSink()
    client = build_failure_client(monkeypatch, sink)

    response = client.get("/test-unexpected-failure")

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno do servidor."
    assert "sensitive database detail" not in response.text
    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.actor_subject == "google-test-subject"
    assert event.action == "http:unhandled_exception"
    assert event.entity_type == "request"
    assert event.entity_id is None
    assert event.outcome == "failure"
    assert event.request_id == response.headers["X-Request-ID"]
    assert not hasattr(event, "email")


def test_audit_sink_failure_does_not_expose_original_exception(monkeypatch):
    sink = RecordingAuditSink(fail=True)
    client = build_failure_client(monkeypatch, sink)

    response = client.get("/test-unexpected-failure")

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno do servidor."
    assert "sensitive database detail" not in response.text
