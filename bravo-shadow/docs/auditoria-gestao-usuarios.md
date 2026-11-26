# Auditoria — Gestão de Usuários

## Fonte e escopo
Inspeção estática do `index.html` na branch `upgrade/project-hardening`, blob `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. Nenhuma credencial, hash ou registro de usuário do HTML foi copiado para a sombra.

## Estrutura encontrada no original
A coleção é `db.usuarios`. Os objetos padrão legados contêm `id`, `usuario`, `nome`, `email`, `cargo`, `loja`, `perfil`, `status`, `primeiroAcesso` e `senhaHash`. Os registros padrão incluem credenciais de exemplo embutidas no código; não foram reproduzidos.

A listagem exibe login/usuário, nome, e-mail, loja/unidade e cargo/perfil. A edição cadastra login, nome, e-mail, loja e cargo; o cargo também é copiado para `perfil`. O cadastro define `status: Ativo`. A tela não apresenta controles claros para alterar status ou perfil de forma independente.

O HTML contém fluxo de senha temporária no cadastro, redefinição administrativa e armazenamento local em `senhaHash`. Esse comportamento é legado e está em desacordo com o requisito vigente do Bravo: identificação pela conta Google/e-mail, sem senha local tradicional. Nenhuma dessas rotinas foi migrada.

## Contrato da API sombra
- `id`: identificador interno gerado no backend.
- `email`: identidade de vínculo do perfil; normalizada para minúsculas e espaços externos removidos.
- `nome`, `loja`, `cargo`: dados do perfil.
- `perfil`: `Admin` ou `Operador`.
- `status`: `Ativo` ou `Inativo`.

E-mail duplicado é rejeitado (HTTP 409). Campos não previstos, incluindo senha/hash, são rejeitados pelo schema (HTTP 422). O contrato é uma modelagem inicial de perfil, não uma implementação de autenticação ou autorização.

## Rotas
- `GET /api/v1/usuarios`
- `GET /api/v1/usuarios/{id}`
- `POST /api/v1/usuarios`
- `PUT /api/v1/usuarios/{id}`
- `DELETE /api/v1/usuarios/{id}`

## Limites e decisões pendentes
- Armazenamento temporário em memória; reiniciar a API apaga os perfis.
- Nenhuma integração com Google, Supabase Auth, tokens ou claims.
- Nenhuma política de autorização efetiva; o campo `perfil` ainda é apenas metadado.
- Antes de ativar o módulo, validar no servidor o token do provedor Google já adotado pelo ambiente ativo e vincular o e-mail verificado ao perfil.
- Definir matriz de permissões por módulo/ação, proteção contra autoexclusão do último administrador, auditoria de alterações e políticas RLS.
- Não importar os registros padrão com credenciais do HTML. Migração de perfis deverá ser saneada e aprovada.

## Testes
Foram escritos testes para normalização e unicidade do e-mail, consulta, edição, exclusão e rejeição de campos de senha. Ainda não foram executados.
