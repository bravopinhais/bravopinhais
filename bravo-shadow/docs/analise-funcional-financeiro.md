# Análise funcional — Financeiro: Contas a Pagar / Receber

Data: 2026-11-27  
Fonte funcional: inspeção estática do módulo financeiro no legado e dos contratos backend da branch `bravo-shadow`. Nenhuma conta ou título real foi consultado.

## Fluxo observado no sistema original

A tela apresenta uma tabela com:
- tipo do título (Receber ou Pagar);
- conta do Plano de Contas (código e nome, ou indicação de não vinculada);
- histórico;
- valor;
- ações para editar e excluir.

O formulário de inclusão/edição contém:
- tipo: Receber ou Pagar;
- vínculo opcional com uma conta do Plano de Contas;
- histórico obrigatório;
- valor numérico com duas casas decimais.

Ao salvar, o legado inclui/atualiza o registro na coleção financeira e redesenha a tela. A exclusão é acionada pela ação global de exclusão do módulo.

## Contrato backend Shadow existente

| Método | Rota | Capacidade | Resultado |
|---|---|---|---|
| GET | `/api/v1/financeiro` | `financeiro:read` | Lista títulos |
| POST | `/api/v1/financeiro` | `financeiro:create` | Cria título |
| PUT | `/api/v1/financeiro/{id}` | `financeiro:update` | Atualiza com `If-Match` |
| DELETE | `/api/v1/financeiro/{id}` | `financeiro:delete` | Exclui fisicamente |

### Campos e validações

- `tipo`: literal `Receber` ou `Pagar`.
- `planoContaId`: string opcional; a referência é validada pelo vínculo no PostgreSQL.
- `historico`: obrigatório, normalizado e não pode ficar vazio.
- `valor`: Decimal com até 14 dígitos e 2 casas.
- `version`: controle otimista de concorrência; a edição exige versão atual via ETag/If-Match.

O repositório PostgreSQL mantém valores como Decimal, aplica FK da conta do plano e faz compare-and-swap para a edição. O endpoint de listagem atual não possui filtros, paginação ou ordenação parametrizada.

## Estrutura visual criada nesta etapa

- Formulário com tipo, conta do Plano, histórico e valor.
- Tabela com tipo, conta, histórico, valor e coluna de ações.
- Estrutura de pesquisa e filtro por tipo, ainda desabilitada porque a API não oferece esses parâmetros.
- Avisos explícitos sobre campos não existentes no contrato.
- Indicação de controle de versão na edição.

A interface não está ligada ao Google Identity Services e não realiza requests. Todos os controles permanecem desabilitados até haver uma API HTTPS Shadow isolada e sessão validada. Não há dados fictícios.

## Lacunas funcionais importantes para paridade completa

O contrato financeiro atual é menor do que um contas a pagar/receber completo. Não há campos nem regras documentadas no módulo para:
- emissão, competência e vencimento;
- data e valor efetivamente pagos/recebidos;
- pagamentos parciais, saldo em aberto e quitação;
- baixa, estorno, cancelamento ou renegociação;
- recorrência, parcelamento e rateio;
- fornecedor, morador/unidade, documento ou comprovante vinculados;
- forma monetária, conta bancária e conciliação;
- juros, multa, desconto e encargos;
- filtros por período, status, conta e contraparte;
- alertas de vencimento, atraso e inadimplência;
- histórico de alterações e trilha de auditoria do título.

Esses itens não foram adicionados por inferência: precisam ser confrontados com os fluxos do sistema atual antes de definir o modelo de dados.

## Riscos e decisões técnicas

1. A rota DELETE executa exclusão física. A interface não deve habilitar essa ação até a política de confirmação, retenção e auditoria ser definida.
2. O serviço atual permite listagem integral; com crescimento de títulos, é necessário paginação e filtros no backend.
3. O backend tem armazenamento em memória por padrão. O PostgreSQL só é usado com configuração explícita; ainda não há ambiente Shadow hospedado.
4. A auditoria de operações financeiras deve ser transacional e registrar ator, ação, entidade e resultado sem incluir dados sensíveis no log.
5. O controle ETag/If-Match protege atualizações concorrentes, mas precisa ser mantido no cliente futuro.
6. A vinculação de conta é opcional no schema; é necessário confirmar se o legado permite títulos sem plano e como isso afeta DRE.
7. Não se deve interpretar a soma de títulos como saldo bancário, fluxo de caixa ou valor efetivamente realizado.

## Próximos passos

1. Comparar o fluxo financeiro completo do legado (incluindo rotinas externas ao render da tabela) para levantar baixa, edição, exclusão, filtros e relatórios.
2. Definir modelo de título com datas, status e pagamentos, se confirmados no legado.
3. Implementar filtros/paginação e agregações no PostgreSQL.
4. Adicionar auditoria transacional para criação, edição e exclusão.
5. Definir política de exclusão (preferencialmente lógica quando compatível) e retenção.
6. Integrar com Plano de Contas, Formas Monetárias, Contas Bancárias e DRE sem duplicar regras.
7. Só então habilitar formulário, consulta e ações após autenticação Google e API HTTPS isolada.

## Situação

- [x] Fluxo básico de tabela e formulário legado identificado.
- [x] Contrato e capacidades backend existentes inspecionados.
- [x] Tela Shadow estruturada, sem dados simulados.
- [x] Limites de API e riscos de exclusão documentados.
- [ ] Auditoria financeira transacional.
- [ ] Paginação, filtros e agregações.
- [ ] Fluxo completo de vencimentos, baixas e pagamentos (a confirmar no legado).
- [ ] Integração autenticada e persistência hospedada.
- [ ] Homologação e paridade funcional.

**Status: primeira estrutura funcional mapeada; módulo Financeiro ainda não concluído nem conectado.** Nenhum teste foi executado nesta etapa.
