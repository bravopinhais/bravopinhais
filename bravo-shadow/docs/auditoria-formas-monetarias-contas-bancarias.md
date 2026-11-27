# Auditoria de Formas Monetárias e Contas Bancárias

## Fonte
Inspeção estática de `index.html` na branch `upgrade/project-hardening`, blob `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. Foram examinadas as funções de listagem, modal, gravação e ocorrências de `db.formas_monetarias` e `db.contas_bancarias` no arquivo completo.

## Formas Monetárias

Coleção: `db.formas_monetarias`.

Campos gravados:
- `id`: preservado na edição; novo registro recebe `fm_` + timestamp.
- `nome`: texto obrigatório pelo atributo HTML `required`.
- `multaPct`: número decimal, `step=0.01`; valor inválido/vazio é convertido para zero na gravação.

Comportamento:
- Novo cadastro apresenta multa padrão de 2,0%.
- Cadastro e edição substituem o objeto por ID ou adicionam ao array.
- Exclusão usa `excluirRegistro`, sem regra de integridade específica.
- A coleção aparece somente no próprio módulo durante a inspeção estática. Não foi encontrado consumo de `multaPct` no cálculo dos títulos financeiros nem associação entre uma forma monetária e um título.
- Não foram encontrados campos de juros, desconto, periodicidade, meio de pagamento, taxa ou identificador externo.

## Contas Bancárias / Caixa

Coleção: `db.contas_bancarias`.

Campos gravados:
- `id`: preservado na edição; novo registro recebe `cb_` + timestamp.
- `banco`: texto obrigatório pelo atributo HTML `required`.
- `saldo`: campo numérico decimal com `step=0.01`; valor inválido/vazio é convertido para zero na gravação.

Comportamento:
- Novo cadastro apresenta saldo inicial padrão 0.
- Cadastro e edição substituem o objeto por ID ou adicionam ao array.
- Exclusão usa `excluirRegistro`, sem regra específica.
- A tela mostra o texto do banco e o saldo informado.
- Não há campos de agência, número de conta, tipo de conta, titular, identificador bancário, data de referência ou histórico de movimentações.
- Não foi encontrada integração entre essa coleção e os títulos de `db.financeiro`; o formulário financeiro não possui campo de conta bancária.
- O saldo exibido não é calculado a partir de lançamentos nem conciliado com extrato. É um valor cadastrado manualmente.

## Regras de paridade na sombra
- Formas Monetárias: preservar `id`, `nome` e `multaPct`, com padrão de 2.0 para novo cadastro.
- Contas Bancárias: preservar `id`, `banco` e `saldo`, com padrão 0.0.
- Não inventar vínculo entre forma monetária, conta bancária e título financeiro.
- Não chamar o saldo cadastrado de saldo conciliado ou saldo calculado.
- Não impor unicidade ou novas regras de sinal sem decisão funcional e análise dos dados existentes. Na interface sombra já havia limite de multa entre 0% e 100%, com precisão de duas casas decimais; a API agora aplica a mesma faixa e precisão no servidor e rejeita valores não finitos, para que chamadas diretas não contornem a validação visual.
- A API sombra já oferece CRUD em memória para ambos os cadastros; não existe integração com Supabase nem frontend conectado.

## Limitações
Auditoria estática. Não foram executados fluxos na aplicação nem consultados registros reais. A persistência em memória da sombra é temporária e será substituída por repositório de homologação após definição de persistência e estratégia de migração.
