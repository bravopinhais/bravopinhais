# Análise funcional — Formas Monetárias

Data: 2026-11-27  
Escopo: comparação estática do legado, schema/serviço/router Shadow, persistência e autorização.

## Fluxo identificado no legado

A tela lista:
- Nome;
- Multa (%);
- ações de editar e excluir.

O formulário de inclusão/edição contém:
- Nome da forma monetária, obrigatório;
- Multa (%), numérica, passo 0,01, valor inicial 2,00.

O legado mantém a lista em `db.formas_monetarias`; cria ou substitui pelo identificador e remove pelo fluxo genérico de exclusão. O código observado não aplica regra explícita de unicidade de nome, nem apresenta campos de bandeira, taxa de adquirência, prazo de recebimento, conta de destino ou integração de gateway.

## Contrato backend Shadow

Prefixo: `/api/v1/formas-monetarias`.

| Método | Rota | Capacidade |
|---|---|---|
| GET | `/api/v1/formas-monetarias` | `formas_monetarias:read` |
| POST | `/api/v1/formas-monetarias` | `formas_monetarias:create` |
| PUT | `/api/v1/formas-monetarias/{id}` | `formas_monetarias:update` |
| DELETE | `/api/v1/formas-monetarias/{id}` | `formas_monetarias:delete` |

Schema:
- `id`: identificador;
- `nome`: texto obrigatório, espaços externos removidos;
- `multaPct`: percentual entre 0 e 100, até duas casas decimais; default 2,00.

A API valida os campos e usa Decimal para verificar a escala do percentual antes de armazenar o valor como float. O repositório PostgreSQL persiste `id, nome, multa_pct`.

## Autorização

- Admin: leitura e CRUD conforme capacidades cadastradas.
- Operador: somente `formas_monetarias:read`.
- As rotas aplicam a dependência de capacidade no backend.

## Persistência e riscos observados

- O serviço recebe um repositório; existe adapter PostgreSQL.
- O modo de armazenamento padrão é memória, com perda dos dados quando o processo reinicia.
- PostgreSQL depende de configuração explícita e de conexão isolada.
- O CRUD atual não recebe audit sink; não foi confirmada auditoria transacional de inclusão, edição ou exclusão.
- A exclusão é física e o serviço não verifica referências a formas monetárias em títulos/cobranças.
- O contrato não define uso efetivo de `multaPct` no cálculo de juros/encargos do Financeiro.
- O modelo não contém taxas de cartão, adquirente, prazo de liquidação, bandeira, conta bancária de destino ou conciliação.

## Correção de segurança aplicada no frontend

A versão anterior fazia chamadas à API com `fetch` sem encaminhar `Authorization: Bearer`. Isso não atende à autenticação Google exigida pelo backend. Para impedir tentativas não autenticadas e evitar aparentar integração pronta:

- os campos e o botão estão desabilitados;
- a lista não tenta carregar dados;
- os handlers de criar/editar/excluir e os requests associados foram removidos;
- a tela explica os pré-requisitos de integração.

Nenhuma chamada é disparada e nenhum registro fictício é mostrado. A tela só deverá ser reativada quando o bootstrap Google fornecer um ID token válido e o cliente enviar esse token em todas as requisições, com tratamento de expiração e sessão encerrada.

## Próximos passos

1. Integrar o cliente com a sessão Google e centralizar requisições autenticadas com Bearer token.
2. Selecionar PostgreSQL isolado e aplicar migration revisada; não usar memória para dados persistentes.
3. Definir auditoria transacional para criação, alteração e exclusão.
4. Definir proteção contra exclusão quando a forma estiver referenciada; preferir inativação se compatível com o legado.
5. Confirmar a regra de negócio da multa: quando se aplica, base de cálculo, arredondamento, isenções, teto e interação com juros.
6. Homologar os resultados comparando registros sintéticos com o comportamento legado.

## Situação

- [x] Campos e regras de validação mapeados.
- [x] Rotas e capacidades identificadas.
- [x] Adapter PostgreSQL existente identificado.
- [x] Chamada frontend sem Bearer removida do caminho operacional; tela bloqueada preventivamente.
- [ ] Integração Google e requests autenticados.
- [ ] Persistência PostgreSQL isolada e migration aplicada.
- [ ] Auditoria transacional e integridade referencial.
- [ ] Regra de multa homologada com Financeiro.

**Status: backend CRUD existente; frontend bloqueado por segurança até autenticação. Paridade funcional ainda não concluída.**
