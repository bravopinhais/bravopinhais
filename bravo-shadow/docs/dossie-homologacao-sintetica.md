# Dossiê de homologação sintética

## Objetivo

O módulo `migration_homologation_package.py` transforma o resultado do pré-homologador integrado em um dossiê imutável e verificável. Ele registra identidade do snapshot por hash, versão do avaliador, contagens agregadas, rastreabilidade dos verificadores e critérios formais ainda pendentes.

## Conteúdo e rastreabilidade

- Identificação: sistema de origem, baseline, hash SHA-256 do snapshot, ambiente e versão do avaliador.
- Inventário: somente nomes de coleções e quantidades agregadas.
- Trilha: inventário, compatibilidade, referências, contratos especializados e valores.
- Bloqueios: códigos agregados do pré-homologador.
- Aprovação: dez critérios explícitos, todos iniciados como `pending`.

Não são incluídos payloads, nomes de pessoas, valores de campos, IDs de registros ou conteúdo de documentos. O hash do snapshot é fornecido pelo chamador; este módulo não afirma ter recalculado ou validado o conteúdo original.

## Fixture de referência

A fixture versionada `backend/fixtures/migration_homologation_synthetic.json` contém apenas registros inventados para exercitar as referências confirmadas entre Financeiro e Plano de Contas e entre Acertos de Estoque e Estoque. O teste `backend/tests/test_migration_homologation_fixture.py` verifica o pré-flight agregado e a ausência de valores/IDs no relatório. A fixture não representa dados reais nem constitui autorização de aplicação.

## Integridade

O pacote usa serialização JSON canônica e SHA-256. `verify_homologation_package` detecta alterações nos campos cobertos pelo hash. `serialize_homologation_package` produz JSON determinístico.

## Critérios formais

A aprovação depende de confirmação da origem, mapeamentos, conversões, referências, localizador singleton do Condomínio, segurança de documentos, regras de estoque, compatibilidade do DDL, segurança/auditoria/reversão e aprovação formal do responsável.

## Limite de autorização

`import_authorized` é sempre `false`. Os critérios são sempre emitidos como `pending`; este gerador não recebe nem registra assinaturas ou aprovações. Mesmo um relatório sem pendências não autoriza importação. Nenhum banco, arquivo, rede, SQL ou dado real é acessado.

Testes sintéticos foram adicionados, mas não executados.
