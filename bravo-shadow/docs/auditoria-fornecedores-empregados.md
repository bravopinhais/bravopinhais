# Auditoria de Fornecedores e Empregados

## Fonte
Inspeção estática do index.html na branch upgrade/project-hardening, blob 873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c. Nenhuma alteração foi feita no original.

## Fornecedores

Coleção: db.fornecedores.

Campos gravados:
- id: preservado ao editar; novo registro usa prefixo for_ e timestamp.
- cnpj: obrigatório no formulário (required), armazenado como texto sem normalização ou validação de dígitos.
- razaoSocial: obrigatório no formulário (required).

A listagem exibe CNPJ, razão social e ações de edição/exclusão. A gravação reconstrói o objeto com os três campos e substitui por ID ou adiciona ao array. Exclusão usa excluirRegistro, sem verificação de vínculos.

Não foram observados campos de nome fantasia, endereço, inscrição estadual, contato, e-mail, telefone ou status.

## Empregados

Coleção: db.empregados.

Campos gravados:
- id: preservado ao editar; novo registro usa prefixo emp_ e timestamp.
- nome: obrigatório no formulário.
- cargo: obrigatório no formulário.
- empresa: opcional.
- endereco: opcional.
- telefone: opcional.
- contatoEmergenciaNome: opcional.
- contatoEmergenciaTel: opcional.

A listagem exibe nome/cargo, empresa, endereço, telefone e contato de emergência. A gravação reconstrói o objeto com os sete campos e substitui por ID ou adiciona ao array. Exclusão usa excluirRegistro, sem confirmação de vínculos específicos além da confirmação genérica.

Não foram observados CPF, RG, data de nascimento, salário, admissão, demissão, jornada, documentos pessoais ou vínculo com folha de pagamento.

## Regras para paridade na sombra
- Preservar exatamente os campos observados e as obrigatoriedades acima.
- Não validar CNPJ matematicamente nem normalizar telefone sem decisão de produto.
- Não introduzir dados pessoais sensíveis que não existam no formulário.
- Não criar vínculo presumido entre empregado e fornecedor, empresa ou condomínio.
- Não adicionar validação de unicidade, formatos ou limites de tamanho não presentes no original.
- O CRUD inicial da sombra usa memória temporária e não está conectado ao frontend nem a banco.

## Limitações
Auditoria estática. Não foram executados formulários no browser nem consultados dados reais do Supabase. O conteúdo histórico pode conter propriedades extras; a rotina de edição observada reconstrói o objeto e descarta propriedades que não constem do formulário.
