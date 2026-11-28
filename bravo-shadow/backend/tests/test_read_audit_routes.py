from fastapi.testclient import TestClient

from app.core.authentication import get_current_principal
from app.core.authorization import AuthenticatedPrincipal
from app.main import create_app
from app.modules.usuarios.schemas import UsuarioInput


class ReadAuditSink:
    def __init__(self, fail=False):
        self.events = []
        self.fail = fail

    def append(self, event):
        if self.fail:
            raise RuntimeError("private audit backend detail")
        self.events.append(event)


def build_client():
    application = create_app(storage_backend="memory")

    async def admin():
        return AuthenticatedPrincipal(
            subject="google-test-subject",
            email="admin@example.com",
            profile="Admin",
            account_status="Ativo",
        )

    application.dependency_overrides[get_current_principal] = admin
    return application, TestClient(application)


def test_sensitive_catalog_and_user_reads_are_audited_without_payload():
    application, client = build_client()
    services = application.state.services
    modules = [
        (services.fornecedores, "/api/v1/fornecedores", "fornecedores:list", "fornecedor"),
        (services.empregados, "/api/v1/empregados", "empregados:list", "empregado"),
        (services.contas_bancarias, "/api/v1/contas-bancarias", "contas_bancarias:list", "conta_bancaria"),
        (services.conselheiros, "/api/v1/conselheiros", "conselheiros:list", "conselheiro"),
        (services.usuarios, "/api/v1/usuarios", "usuarios:list", "usuario"),
    ]
    sinks = []
    for service, _, _, _ in modules:
        sink = ReadAuditSink()
        service.audit_sink = sink
        sinks.append(sink)

    for _, path, _, _ in modules:
        response = client.get(path)
        assert response.status_code == 200

    for (_, _, action, entity_type), sink in zip(modules, sinks):
        assert len(sink.events) == 1
        event = sink.events[0]
        assert (event.action, event.entity_type, event.entity_id) == (action, entity_type, None)
        assert event.actor_subject == "google-test-subject"
        assert event.request_id
        assert not hasattr(event, "payload")
        assert not hasattr(event, "email")

    user = services.usuarios.create(
        UsuarioInput(email="morador@example.com", nome="Pessoa", cargo="Conselho")
    )
    user_sink = sinks[-1]
    response = client.get(f"/api/v1/usuarios/{user.id}")
    assert response.status_code == 200
    detail_event = user_sink.events[-1]
    assert detail_event.action == "usuarios:read"
    assert detail_event.entity_type == "usuario"
    assert detail_event.entity_id == user.id


def test_sensitive_read_routes_fail_closed_when_audit_sink_fails():
    application, client = build_client()
    services = application.state.services
    services.fornecedores.audit_sink = ReadAuditSink(fail=True)
    services.empregados.audit_sink = ReadAuditSink(fail=True)
    services.contas_bancarias.audit_sink = ReadAuditSink(fail=True)
    services.conselheiros.audit_sink = ReadAuditSink(fail=True)
    services.usuarios.audit_sink = ReadAuditSink(fail=True)

    for path in (
        "/api/v1/fornecedores",
        "/api/v1/empregados",
        "/api/v1/contas-bancarias",
        "/api/v1/conselheiros",
        "/api/v1/usuarios",
    ):
        response = client.get(path)
        assert response.status_code == 503
        assert "private audit backend detail" not in response.text

    detail = client.get("/api/v1/usuarios/id-inexistente")
    assert detail.status_code == 503
    assert "private audit backend detail" not in detail.text
