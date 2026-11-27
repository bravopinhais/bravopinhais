# Análise funcional — Contas Bancárias / Caixa

Data: 2026-11-27  
Escopo: inspeção estática do módulo legado e dos contratos Shadow. Nenhum dado bancário foi consultado.

## Fluxo legado identificado

A tela apresenta uma lista com:
- Banco;
- Saldo;
- ações de edição e exclusão.

O formulário de inclusão/edição contém:
- Banco (texto obrigatório);
- Saldo Inicial (R$), numérico com duas casas.

O módulo é um cadastro simples. A inspeção não encontrou fluxo de extrato, lançamentos, transferências, conciliação ou fechamento de caixa dentro desta tela.

## Contrato backend Shadow existente

| Método | Rota | Capacidade | Resultado |
|---|---|---|---|
| GET | `/api/v1/contas-bancarias` | `contas_bancarias:read` | Lista contas |
| POST | `/api/v1/contas-bancarias` | `contas_bancarias:create` | Cria conta |
| PUT | `/api/v1/contas-bancarias/{id}` | `contas_bancarias:update` | Atualiza conta |
| DELETE | `/api/v1/contas-bancarias/{id}` | `contas_bancarias:delete` | Exclui fisicamente |

Schema:
- `id`: identificador interno;
- `banco`: texto obrigatório, removendo espaços externos;
- `saldo`: Decimal, até 14 dígitos e duas casas, default 0,00.

O adapter PostgreSQL persiste apenas `id, banco, saldo`. Não há número de agência/conta, tipo, instituição codificada, moeda, data-base ou referência a movimentações.

## Autorização atual

- Admin: todas as capacidades explícitas do catálogo, incluindo leitura e CRUD de contas bancárias.
- Operador: somente `contas_bancarias:read`.
- A autorização é aplicada no backend por rota; esconder ou desabilitar controles no frontend não substitui a proteção.

## Estrutura visual criada

- Identificação da conta e saldo informado;
- formulário inicial com os dois campos existentes;
- tabela de contas cadastradas;
- aviso que diferencia saldo informado de saldo conciliado;
- lista das capacidades e recursos ainda não implementados.

Os controles continuam desabilitados até existir sessão Google integrada e API HTTPS Shadow isolada. A tela não executa requests nem exibe registros fictícios.

## Lacunas e riscos

1. **Saldo manual não é saldo bancário real.** O valor não é derivado de lançamentos nem validado contra extrato.
2. **Sem histórico.** A atualização substitui banco/saldo e não mantém histórico de saldos ou alterações de negócio específico.
3. **Sem vínculo financeiro.** Títulos a pagar/receber não referenciam conta bancária.
4. **Exclusão física.** O serviço verifica existência, mas não verifica referências; a rota DELETE pode remover o cadastro. Não habilitar até política de retenção e integridade ser definida.
5. **Sem auditoria de negócio.** O serviço/repositório atual não recebe audit sink nem registra evento transacional para CRUD.
6. **Sem controle de concorrência.** A atualização não usa ETag/If-Match nem versão esperada no contrato público.
7. **Sem operações de caixa.** Não há entradas, saídas, transferências, conciliação, fechamento ou comprovantes.

## Próximos passos

1. Confirmar se o legado possui outros fluxos de movimentação de caixa fora da tela de cadastro.
2. Definir identificadores bancários e regras de unicidade, sem exigir dados que o legado não usa.
3. Modelar movimentos imutáveis de entrada, saída e transferência, se confirmados como escopo.
4. Definir conciliação, saldo inicial por data, fechamento e estorno com trilha de auditoria.
5. Relacionar títulos financeiros a contas e formas monetárias, preservando integridade e regras de baixa.
6. Adicionar versionamento otimista e auditoria transacional.
7. Proteger exclusão por referências e preferir inativação quando compatível com as regras.
8. Integrar a tela somente após autenticação Google e API HTTPS Shadow independente.

## Situação

- [x] Campos e tabela do legado identificados.
- [x] Contrato de API, persistência e permissões inspecionados.
- [x] Tela Shadow própria adicionada sem dados simulados.
- [x] Limites de saldo e riscos de exclusão documentados.
- [ ] Auditoria transacional e controle de concorrência.
- [ ] Integridade referencial e inativação.
- [ ] Movimentações, transferências e conciliação (a confirmar no legado).
- [ ] Integração autenticada e homologação isolada.

**Status: cadastro bancário básico mapeado; não equivale a caixa ou conciliação bancária.** Nenhum teste foi executado.
