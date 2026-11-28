"""Explicit coverage register for the 16 legacy DEFAULT_DATA domains.

This is a status index, not an import allowlist. A contract status never grants
permission to export, transform, or write real user data.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainCoverage:
    legacy_key: str
    contract_kind: str
    status: str
    note: str


DOMAIN_COVERAGE: tuple[DomainCoverage, ...] = (
    DomainCoverage("condominio", "singleton", "manual_source_locator_required",
                   "Objeto único; não é coleção."),
    DomainCoverage("conselheiros", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; exige revisão de privacidade."),
    DomainCoverage("usuarios", "identity", "review_only",
                   "Campos não credenciais observados; vínculo Google e conta interna exigem reconciliação."),
    DomainCoverage("plano_contas", "reference", "review_only",
                   "Campos iniciais observados: id, codigo, nome, tipo."),
    DomainCoverage("financeiro", "specialized", "review_only",
                   "Contrato conservador; reconciliação financeira pendente."),
    DomainCoverage("formas_monetarias", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados."),
    DomainCoverage("contas_bancarias", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; potencial dado financeiro sensível."),
    DomainCoverage("moradores", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; dados pessoais exigem minimização."),
    DomainCoverage("fornecedores", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; possíveis dados pessoais e bancários."),
    DomainCoverage("empregados", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; dados pessoais e trabalhistas."),
    DomainCoverage("categorias", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados."),
    DomainCoverage("estoque", "specialized", "review_only",
                   "Contrato conservador; fotos e movimentos exigem validação."),
    DomainCoverage("acertos_estoque", "specialized", "review_only",
                   "Contrato conservador; referências e saldos exigem reconciliação."),
    DomainCoverage("motivos_acerto_estoque", "reference", "review_only",
                   "Campos iniciais observados: id, nome."),
    DomainCoverage("documentos", "specialized", "review_only",
                   "Contrato conservador; codec e conteúdo binário exigem validação."),
    DomainCoverage("logs", "none", "blocked_no_field_allowlist",
                   "Campos não catalogados; não importar por padrão."),
)


def domain_coverage_by_key() -> dict[str, DomainCoverage]:
    """Return a fresh lookup; the canonical register remains immutable."""
    return {item.legacy_key: item for item in DOMAIN_COVERAGE}
