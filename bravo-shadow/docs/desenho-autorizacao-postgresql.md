# Desenho de autorização PostgreSQL — Bravo Shadow

## Status e limites

Este documento é uma proposta de desenho, não uma migration e não autoriza ativar o modo PostgreSQL. Nenhuma role, policy, grant ou banco foi criado ou alterado.

O SQL de referência mantém o schema `bravo_shadow` fora da Data API, habilita RLS nas 15 tabelas e revoga grants das roles padrão. O backend usa uma conexão PostgreSQL direta via Psycopg; a autenticação Google/e-mail ocorre na aplicação e não é substituída por esta role técnica.

## Objetivos

- Usar identidade PostgreSQL exclusiva para o backend Bravo Shadow, separada de `anon`, `authenticated`, `service_role` e do superusuário.
- Não conceder `BYPASSRLS`, superuser ou propriedade das tabelas à credencial de execução da API.
- Manter o schema `bravo_shadow` não exposto pela Data API.
- Conceder somente `USAGE` no schema e privilégios de tabela/sequence estritamente necessários.
- Exigir policies RLS explícitas para a identidade de execução; GRANT sem policy não libera linhas.
- Não permitir que a role da API altere ou apague o histórico de `acertos_estoque`.
- Não confundir o perfil funcional salvo em `usuarios.perfil` com autorização de banco ou autorização por usuário.

## Identidade proposta — ainda não implementada

Separar conceitualmente duas roles:

1. Uma role proprietária/de implantação, usada somente em operações controladas de migration local. Não deve ser usada pela API.
2. Uma role de execução da API, sem superuser, sem `BYPASSRLS`, sem propriedade de tabelas e com senha/segredo mantido somente no ambiente backend.

A forma exata de associação entre uma role de login e uma role de grupo sem login deve ser validada na instância PostgreSQL local, incluindo `current_user`, `session_user`, herança de membership e aplicação de policies `TO`. Não presumir que uma configuração de membership funciona sem teste. Não gravar credenciais no frontend, no repositório ou em arquivos versionados.

## Matriz preliminar de privilégios por tabela

A matriz reflete as operações observadas nos adaptadores PostgreSQL atuais. É um ponto de partida para revisão, não um conjunto de GRANTs pronto para execução.

| Tabela | SELECT | INSERT | UPDATE | DELETE | Observação |
|---|---:|---:|---:|---:|---|
| `formas_monetarias` | Sim | Sim | Sim | Sim | CRUD do catálogo |
| `plano_contas` | Sim | Sim | Sim | Sim | Exclusão deve respeitar FK de lançamentos |
| `financeiro` | Sim | Sim | Sim | Sim | Atualização usa controle de versão |
| `estoque` | Sim | Sim | Sim | Sim | Alteração de saldo protegida após existir histórico |
| `acertos_estoque` | Sim | Sim | **Não** | **Não** | Histórico imutável; movimentos são INSERT |
| `categorias` | Sim | Sim | Sim | Sim | Exclusão respeita FK de documentos |
| `motivos_acerto` | Sim | Sim | Sim | Sim | Exclusão respeita FK de movimentos |
| `documentos` | Sim | Sim | Sim | Sim | Conteúdo ainda armazenado no formato legado |
| `moradores` | Sim | Sim | Sim | Sim | Dados pessoais; acesso somente pelo backend |
| `fornecedores` | Sim | Sim | Sim | Sim | Cadastro |
| `empregados` | Sim | Sim | Sim | Sim | Dados pessoais; acesso somente pelo backend |
| `contas_bancarias` | Sim | Sim | Sim | Sim | Saldo cadastral; não representa conciliação |
| `condominio` | Sim | Sim | Sim | Não | Adaptador atual não expõe delete |
| `conselheiros` | Sim | Sim | Sim | Sim | Cadastro |
| `usuarios` | Sim | Sim | Sim | Sim | Perfil de aplicação; não autentica nem autoriza sozinho |

O backend PostgreSQL instancia adaptadores para os 14 módulos com repositório próprio. Por isso, não é correto conceder permissões somente ao piloto financeiro e depois ligar o modo PostgreSQL globalmente.

## Modelo RLS a validar

Para a primeira homologação local, o modelo mais simples é uma policy explícita por tabela para a role técnica da API, com operações limitadas à matriz acima. Como a API conecta com uma identidade técnica compartilhada, essas policies representam confiança no backend, não autorização individual dos moradores/operadores.

Requisitos obrigatórios:

- Policies explicitamente direcionadas à role técnica; não usar policies abertas a `PUBLIC`, `anon` ou `authenticated`.
- Para tabelas sem segregação por condomínio/usuário implementada, deixar claro que o backend é o perímetro de autorização e não expor o schema pela Data API.
- Não habilitar políticas de UPDATE/DELETE para `acertos_estoque`.
- Testar também acesso negado: sem role, role errada, sem GRANT, sem policy e tentativa de UPDATE/DELETE no histórico.
- Testar as operações de FK: impedir excluir plano de contas, categoria, motivo ou produto quando existirem referências.
- Garantir que a role de execução não consiga criar/alterar tabelas, policies, schemas, roles ou funções privilegiadas.
- Avaliar privilégios de funções, sequences e objetos futuros separadamente; não conceder `ALL PRIVILEGES ON ALL TABLES` ou `ALL ON SCHEMA` por conveniência.

## Limite de autorização individual

O vínculo Google/e-mail e a validação de token devem ser verificados pelo backend antes de executar operações. A tabela `usuarios` é apenas um cadastro de perfil e não comprova que a requisição pertence ao titular do e-mail. O backend ainda precisa validar o token de identidade, mapear o sujeito autenticado ao perfil ativo e aplicar permissões funcionais por endpoint.

Até essa camada existir e ser testada, não considerar a autorização individual pronta para uso real. Não introduzir senha local tradicional.

## Plano de validação local

1. Preparar Supabase CLI e Docker em ambiente de desenvolvimento isolado.
2. Gerar migration com `supabase migration new`; não criar timestamp manualmente.
3. Criar as roles e policies somente na migration local revisada, com owner separado da role da API.
4. Aplicar em stack local descartável e inspecionar `pg_roles`, `pg_policies`, grants e privilégios efetivos.
5. Conectar com a role técnica e provar CRUD permitido em cada tabela.
6. Provar que a role não acessa objetos fora de `bravo_shadow`, não altera schema/roles/policies e não executa DDL.
7. Provar que UPDATE e DELETE em `acertos_estoque` falham mesmo quando tentados diretamente.
8. Provar que `anon`, `authenticated` e `service_role` não ganham acesso às tabelas privadas.
9. Reiniciar API e banco local e confirmar persistência, isolamento e falhas fechadas.
10. Só então considerar habilitar `BRAVO_STORAGE_BACKEND=postgres` na sombra.

## Decisões pendentes antes da migration

- Definir nomes finais das roles de implantação e execução.
- Confirmar comportamento de membership/inheritance e policies `TO` com testes na versão PostgreSQL usada pela stack local.
- Revisar se a matriz CRUD reflete todos os caminhos HTTP e tarefas administrativas.
- Projetar a autorização funcional por usuário/perfil na API; a role técnica compartilhada não substitui esse controle.
- Revisar política de backup, rotação de segredo, logs e recuperação.

## Estado confirmado nesta etapa

- Nenhuma migration criada.
- Nenhuma role ou policy criada.
- Nenhuma conexão ou alteração em banco remoto.
- O backend deve permanecer no modo padrão `memory` até os critérios de aceite serem cumpridos.
