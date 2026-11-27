from __future__ import annotations

from fastapi import HTTPException, status

from app.core.audit import AuditEvent
from app.core.authorization import AuthenticatedPrincipal
from .schemas import ModuloEstado


MODULES = (
    ("dashboard", "Dashboard Executivo", "Gestão"),
    ("condominio", "Dados do Condomínio", "Cadastros"),
    ("plano_contas", "Plano de Contas", "Financeiro"),
    ("financeiro", "Pagar / Receber", "Financeiro"),
    ("formas_monetarias", "Formas Monetárias", "Financeiro"),
    ("contas_bancarias", "Contas Bancárias", "Financeiro"),
    ("relatorios", "DRE & Relatórios", "Gestão"),
    ("moradores", "Moradores & Unidades", "Cadastros"),
    ("fornecedores", "Fornecedores", "Cadastros"),
    ("empregados", "Empregados", "Cadastros"),
    ("estoque", "Estoque & Fotos", "Estoque"),
    ("acerto_estoque", "Acerto de Estoque", "Estoque"),
    ("compras_consumo", "Compras x Consumo", "Estoque"),
    ("categorias", "Pastas", "Documentos"),
    ("documentos", "Documentos Gzip", "Documentos"),
    ("configuracoes", "Configurações", "Sistema"),
    ("usuarios", "Utilizadores", "Sistema"),
)
MODULE_BY_KEY = {item[0]: item for item in MODULES}


class ConfiguracoesService:
    def __init__(self, repository, audit_sink=None):
        self.repository = repository
        self.audit_sink = audit_sink

    def list_modules(self) -> list[ModuloEstado]:
        saved = self.repository.list_states()
        return [
            ModuloEstado(
                chave=key, nome=name, grupo=group,
                ativo=saved.get(key, True),
            )
            for key, name, group in MODULES
        ]

    @staticmethod
    def _validate_admin(actor: AuthenticatedPrincipal) -> None:
        if (
            not isinstance(actor, AuthenticatedPrincipal)
            or actor.account_status != "Ativo"
            or actor.profile != "Admin"
            or not actor.subject.strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Somente Admin ativo pode alterar configurações.",
            )

    def set_module(
        self, key: str, enabled: bool, *, actor: AuthenticatedPrincipal,
        request_id: str | None = None,
    ) -> ModuloEstado:
        self._validate_admin(actor)
        if key not in MODULE_BY_KEY:
            raise HTTPException(status_code=404, detail="Módulo não encontrado.")
        if key == "configuracoes" and not enabled:
            raise HTTPException(
                status_code=409,
                detail="O módulo Configurações deve permanecer ativo.",
            )
        if not callable(getattr(self.repository, "set_state_audited", None)):
            raise HTTPException(
                status_code=503,
                detail="Persistência administrativa auditada indisponível.",
            )
        if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(
                status_code=503,
                detail="Auditoria persistente indisponível.",
            )
        event = AuditEvent(
            actor_subject=actor.subject.strip(),
            action="configuracoes:alterar_modulo",
            entity_type="modulo",
            entity_id=key,
            outcome="success",
            request_id=request_id,
        )
        self.repository.set_state_audited(
            key, enabled, event=event, audit_sink=self.audit_sink
        )
        name, group = MODULE_BY_KEY[key][1], MODULE_BY_KEY[key][2]
        return ModuloEstado(chave=key, nome=name, grupo=group, ativo=enabled)

    def apply_bulk(
        self, action: str, *, actor: AuthenticatedPrincipal,
        request_id: str | None = None,
    ) -> list[ModuloEstado]:
        self._validate_admin(actor)
        if action not in ("ativar_todos", "desativar_operacionais"):
            raise HTTPException(status_code=422, detail="Ação em massa inválida.")
        if not callable(getattr(self.repository, "set_states_audited", None)):
            raise HTTPException(status_code=503, detail="Persistência administrativa auditada indisponível.")
        if not callable(getattr(self.audit_sink, "append_in_transaction", None)):
            raise HTTPException(status_code=503, detail="Auditoria persistente indisponível.")
        enabled = action == "ativar_todos"
        changes = {
            key: (True if enabled else False)
            for key, _, _ in MODULES
            if enabled or key != "configuracoes"
        }
        events = [
            AuditEvent(
                actor_subject=actor.subject.strip(),
                action="configuracoes:alteracao_em_massa",
                entity_type="modulo",
                entity_id=key,
                outcome="success",
                request_id=request_id,
            )
            for key in changes
        ]
        self.repository.set_states_audited(
            changes, events=events, audit_sink=self.audit_sink
        )
        return self.list_modules()
