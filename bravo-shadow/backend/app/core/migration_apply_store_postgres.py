"""Concrete PostgreSQL store for the opt-in Bravo Shadow migration apply unit.

All SQL uses the caller-owned transaction connection. Target table and column
identifiers come exclusively from the static allowlist below; record values
are always bound parameters. This adapter is not wired to application routes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.migration_source_records_postgres import (
    PostgresSourceRecordStore,
    SourceRecordLink,
)
from app.core.migration_transaction import MigrationApplyCommand


# Only columns present in the reviewed Shadow SQL draft are accepted.
# Identifiers are constants, never derived from a record or request.
TARGET_COLUMNS: dict[str, tuple[str, ...]] = {
    "formas_monetarias": ("id", "nome", "multa_pct"),
    "plano_contas": ("id", "codigo", "nome", "tipo"),
    "financeiro": ("id", "tipo", "plano_conta_id", "historico", "valor"),
    "moradores": ("id", "bloco", "apartamento", "nome", "email", "telefone", "cpf", "pet_nome", "vaga_garagem"),
    "fornecedores": ("id", "cnpj", "razao_social"),
    "empregados": ("id", "nome", "cargo", "empresa", "endereco", "telefone", "contato_emergencia_nome", "contato_emergencia_tel"),
    "contas_bancarias": ("id", "banco", "saldo"),
    "condominio": ("id", "nome", "cnpj", "razaoSocial", "endereco", "bairro", "cidade", "uf", "cep", "telefone", "email", "copelBloco1", "copelBloco2", "copelBloco3", "copelBloco4", "copelAreasComuns", "gasSalao", "sanepar"),
    "conselheiros": ("id", "nome", "cargo", "BlocoAp", "telefone"),
    "usuarios": ("id", "email", "nome", "loja", "cargo", "perfil", "status"),
    "estoque": ("id", "item", "quantidade", "minimo", "maximo", "etiqueta", "foto_nome", "foto_compactada_gzip", "marca", "linha", "fabricante", "data_cadastro", "setor", "unidade", "valor_unitario", "status", "cor", "foto_path"),
    "categorias": ("id", "nome"),
    "motivos_acerto": ("id", "nome"),
    "documentos": ("id", "pasta", "categoria_id", "titulo", "nome_arquivo", "arquivo_compactado_gzip"),
    "acertos_estoque": ("id", "data", "tipo", "produto_id", "quantidade", "motivo", "motivo_id"),
}


class MigrationApplyStorePostgres:
    """Implements MigrationApplyStore without owning connection lifecycle."""

    def __init__(self) -> None:
        self._provenance = PostgresSourceRecordStore()

    @staticmethod
    def _cursor(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if connection is None or not callable(getattr(connection, "cursor", None)):
            raise TypeError("conexão PostgreSQL do chamador obrigatória.")
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            return cursor
        except BaseException:
            try:
                cursor.close()
            except BaseException:
                pass
            raise

    def lock_source_identity(
        self, connection: Any, source_system: str, source_collection: str, legacy_id: str
    ) -> None:
        values = (source_system, source_collection, legacy_id)
        if any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError("identidade de origem incompleta.")
        # Length-prefix framing avoids ambiguous concatenation of identity parts.
        lock_key = "".join(f"{len(v)}:{v}" for v in values)
        cursor = self._cursor(
            connection,
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"bravo-shadow:migration-source:{lock_key}",),
        )
        cursor.fetchone()
        cursor.close()

    def find_source_link(
        self, connection: Any, source_system: str, source_collection: str, legacy_id: str
    ) -> tuple[str, str] | None:
        cursor = self._cursor(
            connection,
            """SELECT source_record_hash, destination_id
               FROM bravo_shadow.migration_source_records
               WHERE source_system = %s AND source_collection = %s AND legacy_id = %s
               FOR UPDATE""",
            (source_system, source_collection, legacy_id),
        )
        row = cursor.fetchone()
        cursor.close()
        if row is None:
            return None
        if not isinstance(row, (tuple, list)) or len(row) != 2:
            raise RuntimeError("registro de proveniência armazenado inválido.")
        return row[0], row[1]

    def target_id_exists(self, connection: Any, target_collection: str, destination_id: str) -> bool:
        columns = TARGET_COLUMNS.get(target_collection)
        if columns is None:
            raise ValueError("coleção de destino não permitida.")
        cursor = self._cursor(
            connection,
            f'SELECT 1 FROM bravo_shadow."{target_collection}" WHERE id = %s LIMIT 1',
            (destination_id,),
        )
        found = cursor.fetchone() is not None
        cursor.close()
        return found

    def insert_target(
        self, connection: Any, target_collection: str, destination_id: str, payload: dict[str, Any]
    ) -> None:
        allowed = TARGET_COLUMNS.get(target_collection)
        if allowed is None:
            raise ValueError("coleção de destino não permitida.")
        if not isinstance(payload, dict):
            raise TypeError("payload de destino deve ser objeto.")
        unknown = set(payload) - set(allowed)
        if unknown:
            raise ValueError("payload contém campos não permitidos: " + ", ".join(sorted(unknown)))
        supplied_id = payload.get("id")
        if supplied_id is not None and supplied_id != destination_id:
            raise ValueError("ID do payload diverge do destino autorizado.")
        values_by_column = dict(payload)
        values_by_column["id"] = destination_id
        names = [name for name in allowed if name in values_by_column]
        if not names:
            raise ValueError("payload de destino vazio.")
        identifiers = ", ".join(f'"{name}"' for name in names)
        placeholders = ", ".join(["%s"] * len(names))
        values = tuple(values_by_column[name] for name in names)
        cursor = self._cursor(
            connection,
            f'INSERT INTO bravo_shadow."{target_collection}" ({identifiers}) VALUES ({placeholders})',
            values,
        )
        cursor.close()

    def insert_source_link(self, connection: Any, command: MigrationApplyCommand) -> None:
        self._provenance.record(
            connection,
            SourceRecordLink(
                source_system=command.source_system,
                source_collection=command.source_collection,
                legacy_id=command.legacy_id,
                destination_collection=command.target_collection,
                destination_id=command.destination_id,
                source_record_hash=command.source_record_sha256,
                batch_id=command.batch_id,
            ),
        )

    def insert_success_event_authenticated(
        self,
        connection: Any,
        command: MigrationApplyCommand,
        destination_id: str,
        actor_subject: str,
        request_id: str | None,
    ) -> None:
        if not isinstance(actor_subject, str) or not actor_subject.strip():
            raise ValueError("ator autenticado obrigatório.")
        if request_id is not None and (
            not isinstance(request_id, str) or not request_id.strip()
        ):
            raise ValueError("request_id inválido.")
        cursor = self._cursor(
            connection,
            """INSERT INTO bravo_shadow.audit_events
               (event_id, occurred_at, actor_subject, action, entity_type,
                entity_id, outcome, request_id)
               VALUES (%s, %s, %s, %s, %s, %s, 'success', %s)""",
            (
                str(uuid4()),
                datetime.now(timezone.utc),
                actor_subject.strip(),
                "migration.apply.record",
                command.target_collection,
                destination_id,
                request_id,
            ),
        )
        cursor.close()
