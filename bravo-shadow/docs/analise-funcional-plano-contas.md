# Análise funcional — Plano de Contas

Data: 2026-11-27  
Escopo: comparação estática do fluxo legado, router/schema/service e repositório PostgreSQL Shadow.

## Fluxo legado identificado

A tela `renderPlanoContasView` apresenta uma tabela com:
- Código;
- Nome da Conta;
- Tipo;
- Ações de editar e excluir.

O formulário de inclusão/edição contém:
- Código, obrigatório (exemplo visual no legado: `1.3`);
- Nome da conta, obrigatório;
- Tipo: Receita ou Despesa, com Despesa como valor inicial.

O registro legado tem `id, codigo, nome, tipo`. O salvamento insere ou substitui o registro na coleção `db.plano_contas`. A lista é apresentada por código no fluxo Shadow, mantendo os mesmos campos de negócio.

## Contrato backend Shadow

Prefixo: `/api/v1/plano-contas`.

| Método | Rota | Capacidade | Observação |
|---|---|---|---|
| GET | `/api/v1/plano-contas` | `plano_contas:read` | Lista ordenada por código |
| POST | `/api/v1/plano-contas` | `plano_contas:create` | Cria conta e retorna ETag |
| PUT | `/api/v1/plano-contas/{id}` | `plano_contas:update` | Exige If-Match e versão esperada |
| DELETE | `/api/v1/plano-contas/{id}` | `plano_contas:delete` | Verifica vínculo financeiro |

Schema:
- `codigo`: obrigatório, 1–30 caracteres;
- `nome`: obrigatório, 2–160 caracteres;
- `tipo`: somente `Receita` ou `Despesa`;
- `id` e `version`: metadados do registro.

O serviço normaliza espaços externos, rejeita valores vazios e verifica duplicidade de código sem diferenciar maiúsculas/minúsculas. O repositório PostgreSQL também converte violação de unicidade em conflito HTTP 409.

## Integração com Financeiro e DRE

- O Financeiro permite informar `planoContaId`; o vínculo é opcional no schema atual.
- A camada de serviço do Plano de Contas recebe verificador de referências financeiras.
- A exclusão é recusada se houver títulos vinculados; se o verificador não estiver configurado, a exclusão retorna indisponibilidade em vez de prosseguir.
- A persistência PostgreSQL também trata violação de chave estrangeira como conflito.
- A DRE legada agrupa valores por conta e separa Receita de Despesa. Não foi acrescentada regra contábil nova nesta etapa.

## Autorização e concorrência

- Admin possui leitura e operações CRUD conforme capacidades.
- Operador possui somente `plano_contas:read`.
- A atualização exige `If-Match` e usa compare-and-swap no repositório para detectar edição concorrente.
- A criação e a edição possuem verificação de código duplicado; a constraint PostgreSQL é a proteção final contra corrida.
- Não foi confirmada auditoria transacional específica das operações CRUD neste serviço.

## Estrutura visual criada

- Formulário com código, nome e tipo.
- Tabela com código, nome, tipo e coluna de ações prevista.
- Campos de pesquisa por código/nome e filtro por tipo.
- Área explicativa sobre vínculo com Financeiro, DRE, ETag e exclusão protegida.

A tela não executa chamadas nem permite gravações enquanto a sessão Google não estiver integrada e o frontend não enviar o ID token como Bearer. Nenhum dado de exemplo é exibido.

## Lacunas do contrato observado

1. Não há hierarquia pai/filho nem código de conta pai.
2. Não há distinção entre contas sintéticas e analíticas.
3. Não há centro de custo, grupo, subgrupo ou nível contábil adicional.
4. Não há campo de conta ativa/inativa.
5. Não há trilha de auditoria transacional específica para criar, editar e excluir.
6. O vínculo Financeiro é opcional; a regra de obrigatoriedade precisa ser confirmada com o legado antes de alterar.
7. Não há paginação ou filtro server-side no endpoint de listagem.

## Próximos passos

1. Confirmar se o uso real do Plano de Contas no Bravo depende de hierarquia ou apenas dos três campos observados.
2. Integrar sessão Google e cliente HTTP autenticado, incluindo tratamento de ETag/If-Match.
3. Revisar auditoria transacional e política de retenção antes de habilitar alterações.
4. Homologar vínculo Financeiro e totais da DRE com dados sintéticos.
5. Definir paginação e busca caso o volume real de contas justifique.

## Situação

- [x] Campos e fluxo legado identificados.
- [x] Rotas, schema, validação e persistência inspecionados.
- [x] Vínculos financeiros e bloqueio de exclusão confirmados no serviço.
- [x] ETag/If-Match e controle de concorrência confirmados.
- [x] Tela Shadow criada sem dados simulados e sem requests.
- [ ] Confirmar necessidade de hierarquia.
- [ ] Auditoria transacional de CRUD.
- [ ] Integração Google/Bearer e homologação isolada.

**Status: cadastro simples de contas gerenciais mapeado; não presumir hierarquia contábil ainda não existente no contrato.**
