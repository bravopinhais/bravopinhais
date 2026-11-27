# Matriz de permissões — Bravo Shadow

**Aprovada pelo responsável do sistema em 27/11/2026.** Esta matriz vale somente para o ambiente Shadow e é aplicada no backend por capacidade, independentemente da visibilidade dos botões da interface.

## Administrador (Admin)

Acesso a todas as capacidades registradas em `CAPABILITIES`, incluindo:
- Gerenciar usuários e perfis: consultar, cadastrar, alterar, excluir e desativar.
- Alterar configurações do condomínio e cadastros estruturais.
- Criar, alterar e excluir planos de contas, formas monetárias, contas bancárias, categorias e motivos de estoque.
- Executar todas as operações dos módulos financeiros, estoque, moradores, fornecedores, empregados, documentos e relatórios.

## Operador

Acesso à rotina operacional, sem administração de usuários ou alteração de configurações.

| Módulo | Permissões do Operador |
|---|---|
| Dashboard | Consultar |
| Financeiro | Consultar, criar, alterar e excluir lançamentos |
| Moradores | Consultar, cadastrar, alterar, excluir e importar |
| Fornecedores | Consultar, cadastrar, alterar e excluir |
| Empregados | Consultar, cadastrar, alterar e excluir |
| Estoque | Consultar, cadastrar, alterar e excluir itens |
| Acertos de estoque | Consultar e registrar acertos |
| Documentos | Consultar, cadastrar, alterar e excluir |
| Relatórios | Consultar |
| Condomínio | Somente consultar |
| Conselheiros | Somente consultar |
| Plano de contas | Somente consultar |
| Formas monetárias | Somente consultar |
| Contas bancárias | Somente consultar |
| Categorias | Somente consultar |
| Motivos de acerto | Somente consultar |
| Usuários e perfis | Sem acesso |

## Regras de segurança

- O perfil e o status são lidos do cadastro interno Bravo após validação server-side do ID token Google.
- Somente usuário com status `Ativo` pode acessar.
- Perfil desconhecido, capacidade não cadastrada, usuário inativo ou identidade inválida resulta em negação.
- Toda rota de negócio exige identidade Google e uma capacidade explícita. A rota `/api/v1/auth/me` apenas confirma a identidade.
- A API é a fonte de verdade: esconder uma opção na interface não substitui autorização no servidor.
- Os acertos de estoque são operações registradas; não há permissão de edição/exclusão de movimentos na matriz.
- A matriz foi aprovada para implementação e testes no Shadow. Não autoriza migração, publicação, conexão com dados reais nem alteração do sistema original.

## Implementação

A matriz está em `backend/app/core/authorization.py`, nas constantes `ADMIN_CAPABILITIES`, `OPERATOR_CAPABILITIES` e `ROLE_CAPABILITIES`. Os testes de política e HTTP estão em `backend/tests/test_authorization_policy.py` e `backend/tests/test_authorization_http.py`.
