"""Specialized, conservative migration contracts for high-risk Bravo modules.

These contracts describe observed legacy shapes and Shadow constraints. They
are assessment-only: no transformation, defaults, payload construction, or I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from app.core.migration_source_inventory import SourceInventory


@dataclass(frozen=True, slots=True)
class SpecialField:
    name: str
    observed_type: str
    required: bool = True
    shadow_type: str | None = None
    notes: str = ""


@dataclass(frozen=True, slots=True)
class SpecialCollectionContract:
    key: str
    source_collection: str
    domain: str
    fields: tuple[SpecialField, ...]
    invariants: tuple[str, ...]
    blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialCollectionAssessment:
    key: str
    source_collection: str
    domain: str
    status: str
    record_count: int | None
    missing_required: tuple[str, ...]
    partially_populated: tuple[str, ...]
    unexpected_fields: tuple[str, ...]
    type_mismatches: tuple[str, ...]
    review_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SpecialContractReport:
    assessments: tuple[SpecialCollectionAssessment, ...]
    unassessed_domains: tuple[str, ...]


# Names and shapes below come from the static legacy audit, not from guesses
# about alternate collection names. Exact-name mapping is intentional.
SPECIAL_COLLECTION_CONTRACTS: tuple[SpecialCollectionContract, ...] = (
    SpecialCollectionContract(
        key="financeiro",
        source_collection="financeiro",
        domain="Financeiro",
        fields=(
            SpecialField("id", "string"),
            SpecialField("tipo", "string", notes="Literal legado: Receber/Pagar."),
            SpecialField("planoContaId", "string", required=False,
                         notes="Vínculo opcional; vazio/nulo exige revisão semântica."),
            SpecialField("historico", "string"),
            SpecialField("valor", "number", shadow_type="Decimal",
                         notes="Legado usa Number/parseFloat; não presumir centavos exatos."),
        ),
        invariants=(
            "Preservar ID legado como texto, inclusive zeros à esquerda.",
            "Aceitar apenas os tipos Receber e Pagar após validação explícita.",
            "Resolver planoContaId somente por ID exato; referências ausentes ou órfãs vão para revisão.",
            "Converter valor para Decimal apenas com regra de arredondamento aprovada e relatório de perda.",
            "Não interpretar soma de títulos como saldo bancário ou liquidação.",
        ),
        blockers=(
            "Valores JSON numéricos não comprovam preservação decimal exata.",
            "Vínculos do Plano de Contas precisam ser reconciliados antes da gravação.",
            "Não há no contrato legado auditado datas, baixa, status ou parcelas a inferir.",
        ),
    ),
    SpecialCollectionContract(
        key="documentos",
        source_collection="documentos",
        domain="Documentos",
        fields=(
            SpecialField("id", "string"),
            SpecialField("pasta", "string"),
            SpecialField("titulo", "string"),
            SpecialField("nomeArquivo", "string"),
            SpecialField("arquivoCompactadoGzip", "string",
                         notes="Base64 de bytes comprimidos; o legado auditado usa pako.deflate/inflate."),
        ),
        invariants=(
            "Preservar Base64 original e bytes comprimidos sem recompactar na primeira passagem.",
            "Decodificar Base64 estritamente e validar o fluxo comprimido com codec identificado.",
            "Comparar SHA-256 do conteúdo descompactado antes/depois em ambiente descartável.",
            "Preservar nome e pasta legados; mapear categoria apenas por correspondência exata e única.",
            "Relatar somente contagens, tamanhos e hashes; nunca conteúdo ou dados pessoais.",
        ),
        blockers=(
            "O nome arquivoCompactadoGzip não prova que os bytes sejam Gzip RFC 1952.",
            "O legado observado usa zlib/deflate; não assumir compatibilidade com o validador Gzip atual do Shadow.",
            "Storage de objetos, limites, MIME, retenção e autorização de download ainda precisam de destino aprovado.",
        ),
    ),
    SpecialCollectionContract(
        key="estoque",
        source_collection="estoque",
        domain="Estoque e Inventário",
        fields=(
            SpecialField("id", "string"),
            SpecialField("item", "string"),
            SpecialField("quantidade", "number", shadow_type="Decimal"),
            SpecialField("minimo", "number", required=False, shadow_type="Decimal"),
            SpecialField("maximo", "number", required=False, shadow_type="Decimal"),
            SpecialField("etiqueta", "string", required=False),
            SpecialField("fotoNome", "string", required=False),
            SpecialField("fotoCompactadaGzip", "string", required=False),
        ),
        invariants=(
            "Preservar ID, etiqueta e unidade de medida como texto.",
            "Converter quantidades com Decimal e regra explícita de até três casas no Shadow.",
            "Manter separadas quantidades de cadastro e movimentações históricas.",
            "Conferir saldo final por produto contra a soma reconstruída dos movimentos, sem corrigir automaticamente.",
            "Campos marca, linha, fabricante e dataCadastro são extensões Shadow; não são campos observados no cadastro legado auditado.",
        ),
        blockers=(
            "Legado permite saldo negativo por fluxo de acerto; Shadow bloqueia saída acima do saldo.",
            "Foto pode usar codec legado deflate apesar do nome Gzip; não reprocessar sem identificar codec.",
            "Etiqueta duplicada, limites incoerentes e divergência de saldo exigem revisão.",
        ),
    ),
    SpecialCollectionContract(
        key="acertos_estoque",
        source_collection="acertos_estoque",
        domain="Acertos de Estoque",
        fields=(
            SpecialField("id", "string"),
            SpecialField("data", "string", notes="Preservar texto original; parsing é versionado."),
            SpecialField("tipo", "string", notes="Literal legado: Entrada/Saída."),
            SpecialField("produtoId", "string"),
            SpecialField("quantidade", "number", shadow_type="Decimal"),
            SpecialField("motivo", "string"),
        ),
        invariants=(
            "Preservar data original e só interpretar formatos previamente aprovados.",
            "Resolver produtoId por ID exato; referências ausentes permanecem em revisão.",
            "Preservar motivo como texto; motivoId não existe no registro legado observado.",
            "Reconstruir movimentos em ordem determinística aprovada e comparar saldo calculado ao saldo cadastrado.",
            "Nunca apagar ou reescrever movimento; divergências exigem decisão explícita e trilha.",
        ),
        blockers=(
            "Legado permite saldo negativo e exclusão de histórico sem recompor saldo.",
            "Shadow exige saldo não negativo e correção por movimento compensatório.",
            "A ordenação temporal pode ser ambígua se datas legadas não incluírem fuso/horário consistente.",
        ),
    ),
)


# Condomínio is a singleton object in Shadow, not an array collection in the
# legacy audit. It cannot be measured by SourceInventory's collection scanner.
CONDOMINIO_SINGLETON_CONTRACT = {
    "domain": "Condomínio",
    "source_shape": "singleton_object",
    "target_fields": (
        "nome", "cnpj", "razaoSocial", "endereco", "bairro", "cidade", "uf",
        "cep", "telefone", "email", "copelBloco1", "copelBloco2",
        "copelBloco3", "copelBloco4", "copelAreasComuns", "gasSalao", "sanepar",
    ),
    "rules": (
        "Localizar o objeto singleton real no snapshot; não fabricar coleção nem ID.",
        "Preservar valores textuais e zeros à esquerda de CNPJ, CEP, telefone e identificadores de unidades.",
        "Distinguir campo ausente, null e string vazia; não preencher defaults durante a migração.",
        "Validar cardinalidade singleton e exigir revisão se houver mais de um objeto candidato.",
    ),
    "status": "manual_source_locator_required",
}


def _type_compatible(observed: tuple[tuple[str, int], ...], expected: str) -> bool:
    types = {name for name, count in observed if count > 0}
    if expected == "number":
        return types.issubset({"number"})
    return types.issubset({expected})


def assess_special_contracts(
    inventory: SourceInventory,
    *,
    source_to_target: Mapping[str, str] | None = None,
) -> SpecialContractReport:
    """Assess observed source shape only; all domain-specific blockers remain."""
    mapping = dict(source_to_target or {})
    by_name = {item.name: item for item in inventory.collections}
    assessments: list[SpecialCollectionAssessment] = []
    assessed_names: set[str] = set()

    for contract in SPECIAL_COLLECTION_CONTRACTS:
        source_name = mapping.get(contract.source_collection, contract.source_collection)
        source = by_name.get(source_name)
        if source is None:
            assessments.append(SpecialCollectionAssessment(
                key=contract.key,
                source_collection=source_name,
                domain=contract.domain,
                status="source_collection_not_found",
                record_count=None,
                missing_required=tuple(field.name for field in contract.fields if field.required),
                partially_populated=(),
                unexpected_fields=(),
                type_mismatches=(),
                review_reasons=("A coleção não foi localizada pelo nome confirmado; não inferir aliases.",),
            ))
            continue

        assessed_names.add(source_name)
        source_fields = {field.name: field for field in source.fields}
        expected_fields = {field.name for field in contract.fields}
        missing = tuple(sorted(
            field.name for field in contract.fields
            if field.required and field.name not in source_fields
        ))
        partial = tuple(sorted(
            field.name for field in contract.fields
            if field.name in source_fields
            and source_fields[field.name].records_present < source.records_total
        ))
        unexpected = tuple(sorted(set(source_fields) - expected_fields))
        mismatches = tuple(sorted(
            field.name for field in contract.fields
            if field.name in source_fields
            and not _type_compatible(source_fields[field.name].value_types, field.observed_type)
        ))
        reasons = list(contract.blockers)
        if source.records_total == 0:
            reasons.append("Coleção vazia: não comprova compatibilidade nem integridade.")
        if source.invalid_records or source.records_missing_id or source.duplicate_ids:
            reasons.append("Há registros inválidos, IDs ausentes ou IDs duplicados.")
        if missing:
            reasons.append("Campos obrigatórios ausentes.")
        if partial:
            reasons.append("Há campos parcialmente preenchidos.")
        if unexpected:
            reasons.append("Campos adicionais não podem ser descartados sem decisão.")
        if mismatches:
            reasons.append("Tipos observados divergem do formato legado esperado.")
        status = "review_required" if reasons or missing or partial or unexpected or mismatches else "shape_matches_review_required"
        assessments.append(SpecialCollectionAssessment(
            key=contract.key,
            source_collection=source_name,
            domain=contract.domain,
            status=status,
            record_count=source.records_total,
            missing_required=missing,
            partially_populated=partial,
            unexpected_fields=unexpected,
            type_mismatches=mismatches,
            review_reasons=tuple(reasons),
        ))

    return SpecialContractReport(
        assessments=tuple(assessments),
        unassessed_domains=("Condomínio: objeto singleton exige localização manual fora do inventário de coleções.",),
    )


# Auxiliary collections have smaller observed shapes, but they are not yet
# package allowlists and therefore remain assessment-only.
AUXILIARY_COLLECTION_CONTRACTS: tuple[SpecialCollectionContract, ...] = (
    SpecialCollectionContract(
        key="formas_monetarias",
        source_collection="formas_monetarias",
        domain="Configuração financeira",
        fields=(
            SpecialField("id", "string"),
            SpecialField("nome", "string"),
            SpecialField("multaPct", "number", required=False),
        ),
        invariants=(
            "Preservar IDs e nomes como texto.",
            "Validar multaPct apenas após confirmar unidade, escala e regra de aplicação.",
            "Não presumir que ausência de multaPct equivale a zero.",
        ),
        blockers=(
            "A escala e a semântica de multaPct ainda exigem confirmação funcional.",
            "Contrato ainda não está integrado ao leitor de pacote como allowlist.",
        ),
    ),
    SpecialCollectionContract(
        key="motivos_acerto_estoque",
        source_collection="motivos_acerto_estoque",
        domain="Configuração de estoque",
        fields=(
            SpecialField("id", "string"),
            SpecialField("nome", "string"),
        ),
        invariants=(
            "Preservar ID e nome como texto.",
            "Não substituir o texto motivo dos movimentos legados por motivoId sem mapeamento exato e aprovado.",
        ),
        blockers=(
            "A coleção de motivos não altera o contrato legado de acertos_estoque, que armazena motivo como texto.",
            "Contrato ainda não está integrado ao leitor de pacote como allowlist.",
        ),
    ),
    SpecialCollectionContract(
        key="categorias",
        source_collection="categorias",
        domain="Organização de documentos",
        fields=(
            SpecialField("id", "string"),
            SpecialField("nome", "string"),
        ),
        invariants=(
            "Preservar ID e nome como texto.",
            "Relacionar pasta textual de documentos somente por correspondência exata e única.",
        ),
        blockers=(
            "Documentos legados armazenam pasta como texto, não como categoriaId.",
            "Contrato ainda não está integrado ao leitor de pacote como allowlist.",
        ),
    ),
)


def assess_auxiliary_contracts(
    inventory: SourceInventory,
    *,
    source_to_target: Mapping[str, str] | None = None,
) -> SpecialContractReport:
    """Assess simple auxiliary collection shapes without declaring import readiness."""
    mapping = dict(source_to_target or {})
    by_name = {item.name: item for item in inventory.collections}
    assessments: list[SpecialCollectionAssessment] = []

    for contract in AUXILIARY_COLLECTION_CONTRACTS:
        source_name = mapping.get(contract.source_collection, contract.source_collection)
        source = by_name.get(source_name)
        if source is None:
            assessments.append(SpecialCollectionAssessment(
                key=contract.key,
                source_collection=source_name,
                domain=contract.domain,
                status="source_collection_not_found",
                record_count=None,
                missing_required=tuple(field.name for field in contract.fields if field.required),
                partially_populated=(),
                unexpected_fields=(),
                type_mismatches=(),
                review_reasons=("Coleção auxiliar não localizada pelo nome confirmado.",),
            ))
            continue

        source_fields = {field.name: field for field in source.fields}
        expected_fields = {field.name for field in contract.fields}
        missing = tuple(sorted(
            field.name for field in contract.fields
            if field.required and field.name not in source_fields
        ))
        partial = tuple(sorted(
            field.name for field in contract.fields
            if field.name in source_fields
            and source_fields[field.name].records_present < source.records_total
        ))
        unexpected = tuple(sorted(set(source_fields) - expected_fields))
        mismatches = tuple(sorted(
            field.name for field in contract.fields
            if field.name in source_fields
            and not _type_compatible(source_fields[field.name].value_types, field.observed_type)
        ))
        reasons = list(contract.blockers)
        if source.records_total == 0:
            reasons.append("Coleção vazia: não comprova compatibilidade nem integridade.")
        if source.invalid_records or source.records_missing_id or source.duplicate_ids:
            reasons.append("Há registros inválidos, IDs ausentes ou IDs duplicados.")
        if missing:
            reasons.append("Campos obrigatórios ausentes.")
        if partial:
            reasons.append("Há campos parcialmente preenchidos.")
        if unexpected:
            reasons.append("Campos adicionais exigem decisão explícita.")
        if mismatches:
            reasons.append("Tipos observados divergem do formato esperado.")
        assessments.append(SpecialCollectionAssessment(
            key=contract.key,
            source_collection=source_name,
            domain=contract.domain,
            status="review_required",
            record_count=source.records_total,
            missing_required=missing,
            partially_populated=partial,
            unexpected_fields=unexpected,
            type_mismatches=mismatches,
            review_reasons=tuple(reasons),
        ))

    return SpecialContractReport(
        assessments=tuple(assessments),
        unassessed_domains=(
            "Coleções auxiliares: avaliação estrutural preliminar; allowlists do pacote e validação semântica ainda pendentes.",
        ),
    )


def assess_all_collection_contracts(
    inventory: SourceInventory,
    *,
    source_to_target: Mapping[str, str] | None = None,
) -> SpecialContractReport:
    """Return one structural report for all currently catalogued collections.

    This is still assessment-only. It does not validate arbitrary record values,
    build package allowlists, or grant import readiness.
    """
    special = assess_special_contracts(inventory, source_to_target=source_to_target)
    auxiliary = assess_auxiliary_contracts(inventory, source_to_target=source_to_target)
    return SpecialContractReport(
        assessments=special.assessments + auxiliary.assessments,
        unassessed_domains=special.unassessed_domains + auxiliary.unassessed_domains,
    )
