"""Non-executable operational runbook for isolated migration homologation.

Produces ordered checkpoints and stop/recovery guidance only. It cannot connect
to a database, execute SQL, approve a batch, or create apply commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.core.migration_homologation_package import (
    SyntheticHomologationPackage,
    verify_homologation_package,
)

RunbookStatus = Literal["blocked", "prepared_not_executable"]

@dataclass(frozen=True, slots=True)
class ExecutionCheckpoint:
    checkpoint_id: str
    phase: str
    objective: str
    entry_conditions: tuple[str, ...]
    evidence_required: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    recovery_action: str

@dataclass(frozen=True, slots=True)
class ExecutionRunbook:
    format_version: int
    runbook_id: str
    package_id: str
    package_hash: str
    environment: str
    status: RunbookStatus
    executable: bool
    approval_required: bool
    checkpoints: tuple[ExecutionCheckpoint, ...]
    global_stop_conditions: tuple[str, ...]
    recovery_policy: tuple[str, ...]

_CHECKPOINTS = (
    ExecutionCheckpoint(
        "PRE-001", "integrity", "Confirmar integridade e identidade do dossiê.",
        ("Dossiê recebido por canal controlado.",),
        ("Hash do pacote validado.", "Sistema, baseline e snapshot conferidos."),
        ("Hash divergente ou origem/baseline desconhecidos.",),
        "Interromper; preservar o pacote original e gerar novo dossiê a partir de snapshot sintético controlado.",
    ),
    ExecutionCheckpoint(
        "PRE-002", "isolation", "Preparar ambiente local descartável e isolado.",
        ("PRE-001 concluído.",),
        ("Ambiente sem rota para produção.", "Credenciais e dados reais ausentes.",
         "Backup descartável e procedimento de descarte documentados."),
        ("Conexão, segredo ou rota de produção detectados.",),
        "Desligar o ambiente, revogar credenciais temporárias e investigar exposição antes de reiniciar.",
    ),
    ExecutionCheckpoint(
        "PRE-003", "schema", "Conferir DDL, adaptador e restrições do banco descartável.",
        ("PRE-002 concluído.",),
        ("DDL revisado sem execução em produção.", "Tabelas, colunas, defaults, NOT NULL e FKs comparados.",
         "Constraints de proveniência e auditoria conferidas."),
        ("Diferença de schema, FK sem mapeamento ou constraint ausente.",),
        "Não aplicar alterações automaticamente; corrigir o desenho, revisar e emitir nova evidência.",
    ),
    ExecutionCheckpoint(
        "PRE-004", "dry_run", "Executar apenas inventário e pré-flight com fixture sintética.",
        ("PRE-003 concluído.",),
        ("Snapshot sintético identificado.", "Manifesto e plano determinísticos.",
         "Contagens de origem, candidatos e plano reconciliadas."),
        ("Candidato ausente/extra, duplicidade, conflito ou bloqueio não explicado.",),
        "Descartar a execução de ensaio, manter snapshot intacto e corrigir mapeamento/fixture.",
    ),
    ExecutionCheckpoint(
        "PRE-005", "review", "Revisão independente dos resultados e critérios de domínio.",
        ("PRE-004 concluído.",),
        ("Conversões e perdas documentadas.", "Referências e exceções aprovadas.",
         "Documentos, estoque e singleton Condomínio revisados."),
        ("Qualquer critério obrigatório pendente ou evidência sem responsável.",),
        "Manter bloqueado; encaminhar a pendência ao responsável e repetir a avaliação.",
    ),
    ExecutionCheckpoint(
        "PRE-006", "approval", "Registrar aprovação formal, específica e limitada ao ensaio sintético.",
        ("PRE-005 concluído.",),
        ("Aprovador identificado e autorizado.", "Batch, manifesto, plano e ambiente vinculados à aprovação.",
         "Escopo restrito ao ambiente descartável local."),
        ("Aprovação ausente, expirada, divergente ou com escopo amplo.",),
        "Não iniciar escrita; solicitar nova aprovação vinculada aos hashes corretos.",
    ),
    ExecutionCheckpoint(
        "PRE-007", "synthetic_apply", "Realizar ensaio transacional somente no banco descartável.",
        ("PRE-006 concluído.",),
        ("Conexão explicitamente local e descartável.", "Autorização persistida e transação atômica.",
         "Auditoria e proveniência conferidas."),
        ("Falha de constraint, autorização, auditoria ou resultado de commit incerto.",),
        "Interromper novas tentativas; em commit incerto, reconciliar batch, proveniência e destino antes de qualquer retry.",
    ),
    ExecutionCheckpoint(
        "PRE-008", "reconcile", "Comparar resultado persistido com o plano e fechar o ensaio.",
        ("PRE-007 concluído.",),
        ("Totais por coleção reconciliados.", "Hashes e vínculos de proveniência conferidos.",
         "Auditoria íntegra e divergências explicadas."),
        ("Qualquer diferença de contagem, hash, vínculo ou auditoria.",),
        "Congelar o ensaio, preservar evidências e investigar; não repetir nem promover dados.",
    ),
    ExecutionCheckpoint(
        "PRE-009", "dispose", "Descartar ambiente e artefatos temporários conforme retenção aprovada.",
        ("PRE-008 concluído e revisão encerrada.",),
        ("Evidências necessárias preservadas sem dados pessoais.", "Credenciais temporárias revogadas.",
         "Ambiente descartável removido e descarte registrado."),
        ("Evidência obrigatória não preservada ou segredo ainda ativo.",),
        "Manter encerramento pendente até comprovar retenção mínima e revogação.",
    ),
)

def build_execution_runbook(
    package: SyntheticHomologationPackage,
) -> ExecutionRunbook:
    """Build a checklist; intentionally never returns an executable plan."""
    if not isinstance(package, SyntheticHomologationPackage):
        raise TypeError("dossiê de homologação inválido.")
    if not verify_homologation_package(package):
        raise ValueError("integridade do dossiê inválida.")
    if package.environment != "shadow-synthetic":
        raise ValueError("o runbook aceita somente o ambiente shadow-synthetic.")
    if package.import_authorized:
        raise ValueError("dossiê com autorização inesperada não é aceito por este preparador.")
    if not package.package_id or not package.package_hash:
        raise ValueError("identidade do dossiê incompleta.")
    return ExecutionRunbook(
        format_version=1,
        runbook_id=f"runbook-{package.package_id}",
        package_id=package.package_id,
        package_hash=package.package_hash,
        environment="local_disposable",
        status="blocked",
        executable=False,
        approval_required=True,
        checkpoints=_CHECKPOINTS,
        global_stop_conditions=(
            "Qualquer acesso ou dependência de produção.",
            "Presença de dados reais ou credenciais de produção.",
            "Divergência entre hashes do pacote, manifesto, plano e autorização.",
            "Critério de aprovação obrigatório pendente.",
            "Resultado de COMMIT desconhecido sem reconciliação.",
            "Falha de integridade referencial, proveniência ou auditoria.",
        ),
        recovery_policy=(
            "Parar a sequência no primeiro bloqueio; não pular checkpoints.",
            "Não repetir automaticamente operações após resultado de commit incerto.",
            "Preservar hashes, códigos de erro e evidências mínimas sem payloads pessoais.",
            "Reconciliar estado persistido antes de qualquer nova tentativa.",
            "Descartar o ambiente descartável somente após preservar evidências aprovadas.",
            "Este runbook não autoriza produção, importação real ou cutover.",
        ),
    )
