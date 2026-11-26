# Auditoria de Condomínio & Conselho

## Fonte
Inspeção estática de `index.html` na branch `upgrade/project-hardening`, blob `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O original não foi alterado.

## Dados institucionais — `db.condominio`

O modelo padrão contém:
- `nome`, `cnpj`, `razaoSocial`
- `endereco`, `bairro`, `cidade`, `uf`, `cep`
- `telefone`, `email`
- `copelBloco1`, `copelBloco2`, `copelBloco3`, `copelBloco4`
- `copelAreasComuns`, `gasSalao`, `sanepar`

A tela atual permite editar apenas nome, CNPJ, telefone, e-mail, quatro unidades Copel dos blocos, Copel áreas comuns, registro de gás do salão e matrícula Sanepar. Os campos institucionais de razão social e endereço existem no modelo padrão, mas não aparecem como editáveis nessa tela.

Nenhum campo possui atributo HTML `required` ou validação específica na tela. O salvamento atual altera os campos visíveis em `db.condominio`, chama `salvarDados(db)` e mantém os demais campos do objeto.

A função de salvamento pressupõe que `db.condominio` exista. O modelo padrão fornece o objeto; restaurações/importações antigas sem essa chave podem causar falha.

## Corpo diretivo — `db.conselheiros`

Campos:
- `id`: preservado na edição; novo usa prefixo `cons_` e timestamp.
- `nome`: obrigatório no formulário.
- `cargo`: obrigatório no formulário; padrão inicial `Síndico`.
- `BlocoAp`: opcional.
- `telefone`: opcional.

A tabela exibe nome, cargo e bloco/apartamento; telefone é capturado e armazenado, mas não exibido na tabela. Cadastro, edição e exclusão genérica; sem regras específicas de integridade ou unicidade.

## CRUD inicial na sombra
- `GET/PUT /api/v1/condominio`: leitura e atualização parcial do objeto institucional.
- `GET/POST /api/v1/conselheiros`
- `PUT/DELETE /api/v1/conselheiros/{id}`

A atualização institucional mescla somente os campos enviados para preservar propriedades existentes que não estejam presentes no formulário atual. O serviço em memória não contém os valores de exemplo do original e não se conecta à produção.

## Cuidados
- Não copiar valores de exemplo, contatos, e-mails ou identificadores do condomínio original para a sombra.
- Não presumir que conselheiro seja usuário do sistema ou morador cadastrado.
- Não inferir permissões, mandato, datas, documentos ou relações não existentes no formulário.
- Dados pessoais do corpo diretivo exigirão controle de acesso e proteção na persistência futura.

## Limitações
Auditoria estática; sem execução de formulários no navegador, sem leitura de dados reais do Supabase e sem testes executados nesta etapa.
