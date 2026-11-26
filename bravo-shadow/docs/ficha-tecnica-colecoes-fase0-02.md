# Ficha técnica de coleções — Fase 0 (lote 02)

## Objetivo e limites

Comparação de leitura entre o legado e o Shadow para Financeiro, Formas Monetárias e Contas Bancárias. Nenhum dado real foi consultado, extraído ou migrado.

## Baseline

- Legado: `upgrade/project-hardening/index.html`.
- SHA observado: `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.
- Armazenamento legado: objeto JSON `payload` em `public.condominio_dados`, registro `principal`.
- Shadow: branch `bravo-shadow`.

## 1. Financeiro

### Legado observado

Coleção `db.financeiro[]`. Campos gravados no formulário:
- `id`: string; novos IDs usam prefixo `fin_` e timestamp.
- `tipo`: `Receber` ou `Pagar`.
- `planoContaId`: string; pode ficar vazio.
- `historico`: texto obrigatório.
- `valor`: número decimal (interface usa `parseFloat`, fallback zero).

A tela apresenta tipo, conta vinculada, histórico e valor. Permite criar, editar e excluir. A referência à conta é resolvida por `planoContaId`; quando não existe correspondência, mostra “Não vinculada”.

### Shadow observado

- Schema `FinanceiroInput`: `tipo` limitado a `Receber`/`Pagar`; `planoContaId` string opcional com default vazio; `historico` obrigatório e aparado; `valor` Decimal com até 14 dígitos e 2 casas.
- Modelo de saída inclui `id` e `version`.
- API: GET/POST/PUT/DELETE em `/api/v1/financeiro`; PUT usa `If-Match`/ETag.
- Serviço/repositório tem verificação de referência ao Plano de Contas e controle de versão.

### Diferenças e riscos

- Não há campos explícitos de competência, vencimento, pagamento/recebimento, baixa, situação, parcela, forma monetária ou conta bancária no contrato observado.
- Não é possível reconstruir com segurança relatórios por período, inadimplência, títulos liquidados ou conciliação bancária a partir desses cinco campos.
- Não converter valor em ponto flutuante durante a transformação; usar decimal exato e validar escala.
- Preservar títulos sem plano associado; não inventar vínculo.
- Validar se existem propriedades extras nos dados históricos antes de aplicar schema estrito.

### Aceite futuro

1. Reconciliar total de títulos, IDs, tipos e soma decimal por tipo.
2. Relatar IDs duplicados, tipos desconhecidos, valores inválidos e referências órfãs.
3. Fazer round-trip preservando ID, histórico, tipo, valor e planoContaId.
4. Testar concorrência/ETag e restrição de exclusão de contas referenciadas em PostgreSQL local.
5. Não declarar o módulo apto a relatórios por período sem fonte confiável para datas e situação.

## 2. Formas Monetárias

### Legado observado

Coleção `db.formas_monetarias[]`:
- `id`: string; novos IDs usam prefixo `fm_`.
- `nome`: texto obrigatório.
- `multaPct`: número; novo registro inicia com 2.0; gravação usa `parseFloat` com fallback zero.

A tela mostra nome e multa percentual e permite criar, editar e excluir.

### Shadow observado

- Schema `FormaMonetariaInput`: `nome` obrigatório, aparado; `multaPct` float com default 2.0.
- Modelo inclui `id`.
- API GET/POST/PUT/DELETE em `/api/v1/formas-monetarias`.

### Diferenças e riscos

- O fluxo legado analisado não mostra associação da forma monetária a um título financeiro, nem regra de cálculo/uso da multa.
- Não presumir que `multaPct` seja juros, desconto ou multa efetivamente aplicada sem confirmar regra de negócio.
- Float pode introduzir diferenças de representação; avaliar Decimal e escala após confirmar precisão esperada.
- Validar valores negativos, limites percentuais e precisão com o responsável pelo negócio; não inventar restrições.

### Aceite futuro

1. Preservar IDs, nome e percentual sem arredondamento silencioso.
2. Relatar valores nulos, texto inesperado e percentuais fora do intervalo a ser aprovado.
3. Testar round-trip e comportamento de atualização/exclusão.
4. Confirmar se há vínculo funcional com Financeiro em outro fluxo ou se a coleção é apenas cadastro de parâmetros.

## 3. Contas Bancárias

### Legado observado

Coleção `db.contas_bancarias[]`:
- `id`: string; novos IDs usam prefixo `cb_`.
- `banco`: texto obrigatório.
- `saldo`: número decimal; formulário solicita “Saldo Inicial (R$)” e grava `parseFloat` com fallback zero.

A tela mostra banco e saldo e permite criar, editar e excluir. Não foi observado campo de agência, número da conta, tipo, titular, data-base ou vínculo com lançamentos financeiros.

### Shadow observado

- Schema `ContaBancariaInput`: `banco` obrigatório e aparado; `saldo` Decimal com até 14 dígitos e 2 casas, default 0.00.
- Modelo inclui `id`.
- API GET/POST/PUT/DELETE em `/api/v1/contas-bancarias`.

### Diferenças e riscos

- O saldo é cadastrado manualmente como saldo inicial; não há reconciliação, extrato ou movimentação bancária observada.
- Não há relação explícita entre `contas_bancarias` e `financeiro`; não inferir associação.
- Não apresentar esse saldo como saldo conciliado ou atualizado automaticamente.
- Preservar saldo como decimal exato e manter valores negativos se existirem até validar regra de negócio.
- Confirmar se a coleção representa contas bancárias distintas ou apenas pares banco/saldo.

### Aceite futuro

1. Reconciliar quantidade, IDs, bancos e saldos com precisão decimal.
2. Detectar IDs duplicados, banco vazio e valores inválidos sem descartar registros silenciosamente.
3. Testar round-trip com saldos positivos, zero e negativos (se encontrados).
4. Confirmar com o negócio se serão necessários agência, conta, titular, tipo e data-base numa fase futura; não adicionar esses campos ao legado sem decisão.

## 4. Riscos transversais

- Os três módulos estão dentro do mesmo payload JSON no legado; a transformação deve ser feita por snapshot consistente e com checksum/contagem, não por cópias parciais improvisadas.
- Os IDs legados devem ser preservados para rastreabilidade.
- A presença de um endpoint no Shadow não comprova paridade operacional nem segurança: rotas comerciais ainda aguardam a etapa transversal de autenticação/autorização.
- Os campos atualmente ausentes não podem ser fabricados a partir de suposições ou valores de demonstração.
- Nenhum módulo deve ser cortado do legado até reconciliação, aceite e rollback testado.

## 5. Evidências consultadas

Legado: `renderFinanceiroView`, `renderModalNovoTitulo`, `salvarModalFinanceiro`, `renderFormasMonetariasView`, `renderModalFormaMonetaria`, `salvarModalFormaMonetaria`, `renderContasBancariasView`, `renderModalContaBancaria`, `salvarModalContaBancaria`.

Shadow:
- `backend/app/modules/financeiro/schemas.py` e `router.py`.
- `backend/app/modules/formas_monetarias/schemas.py` e `router.py`.
- `backend/app/modules/contas_bancarias/schemas.py` e `router.py`.

**Limite:** documentação de leitura. Nenhuma migração, carga, alteração de banco, API, interface ou legado foi realizada. Testes de integração PostgreSQL não foram executados.
