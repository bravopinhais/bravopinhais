# Contrato de gestão de usuários — Bravo Shadow

## Status

**Implementação parcial em Shadow; ainda não integrada às rotas.** Os schemas separados e seus testes unitários existem, mas o serviço e os endpoints continuam usando o contrato legado. Não altera autenticação, permissões, interface ou dados. A matriz de permissões e o fluxo de entrada de novos usuários continuam pendentes de aprovação.

## Situação encontrada

- `UsuarioInput` mistura dados cadastrais (`email`, `nome`, `loja`, `cargo`) com campos privilegiados (`perfil`, `status`).
- O mesmo schema é usado em criação e atualização integral.
- O router de usuários já exige dependências de autenticação e capacidades específicas (`usuarios:read/create/update/delete`). A matriz atual mantém as capacidades de Admin/Operador fechadas, e os testes verificam 401 sem identidade e 403 para ambos os perfis.
- Os testes atuais verificam o bloqueio das rotas sem autenticação e para os perfis ainda sem capacidades aprovadas.
- O serviço em memória é isolado por instância, mas não é persistente.

## Separação de contratos proposta

### 1. Dados cadastrais

O `UsuarioCadastroInput` contém apenas `email`, `nome`, `loja` e `cargo`; rejeita campos extras e normaliza e-mail/textos. O `UsuarioDadosCadastraisUpdateInput` permite apenas `nome`, `loja` e `cargo`, sem troca de e-mail ou status, e exige ao menos um campo não vazio. Ambos têm testes unitários. Esses schemas ainda não substituem `UsuarioInput` nas rotas.

### 2. Criação administrativa

A criação de um usuário deve ser uma operação administrativa protegida por capacidade explícita. O payload cadastral não escolhe o perfil nem o status. O servidor aplica os valores iniciais definidos pela política aprovada.

**Ponto ainda não decidido:** se o cadastro novo começa como `Ativo` ou `Inativo/Pendente`, e se haverá convite/aprovação antes do primeiro acesso. Não codificar um padrão até essa regra ser aprovada.

### 3. Alteração cadastral

A alteração comum deve aceitar apenas campos cadastrais permitidos e tratar atualização parcial de forma explícita. Não deve permitir trocar e-mail de identidade sem um fluxo próprio de reconciliação com a conta Google.

### 4. Alteração administrativa

Perfil e status devem ficar em uma operação/schema separado, protegido por capacidade administrativa. A operação deve validar valores no servidor, impedir autoelevação, impedir que a conta autenticada altere o próprio perfil/status, proteger o último Admin ativo, registrar auditoria mínima e usar transação e controle de concorrência no PostgreSQL.

### 5. Consulta e exclusão

Listagem e detalhe são privados. Exclusão não deve ser um CRUD irrestrito: avaliar desativação lógica como padrão, preservar histórico e impedir a remoção do último Admin ativo. A decisão entre exclusão lógica e física depende da política de retenção e deve ser aprovada antes da implementação.

## Regras invariáveis

- A identidade vem de Google ID token validado no servidor; nunca de `email`, `perfil` ou `status` enviados pelo cliente.
- O e-mail autenticado deve ser verificado e corresponder a exatamente um cadastro interno ativo.
- Falha ou ambiguidade resulta em negação, nunca em perfil padrão privilegiado.
- Nenhuma rota de negócio ou de usuários deve ser liberada operacionalmente antes da configuração Google validada e da aprovação explícita das capacidades; as dependências de proteção já estão no router, mas a matriz permanece fechada.
- O bootstrap do primeiro Admin permanece fora da API pública e segue `provisionamento-primeiro-admin.md`.
- Não introduzir login por senha local.

## Sequência segura de implementação

1. Aprovar matriz de capacidades e regra de onboarding (estado inicial do usuário).
2. Implementar schemas separados e testes unitários de rejeição de campos privilegiados.
3. Implementar operações de usuário com autorização explícita, proteção do último Admin e auditoria.
4. Atualizar testes de API para exigir token válido e testar 401/403/permitido.
5. Validar concorrência e persistência em PostgreSQL local descartável.
6. Fazer revisão de segurança de todas as rotas antes de qualquer deploy privado.

## Fora do escopo desta etapa

Nenhuma rota foi alterada ou exposta, nenhum usuário foi criado, nenhuma migration foi gerada e nenhum banco foi conectado. Os testes foram adicionados ao CI, mas o resultado da execução precisa ser confirmado para o commit mais recente. A tela de login permanece como está, conforme o planejamento de redesenhá-la posteriormente.