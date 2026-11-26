# Proposta de catálogo granular de capacidades — Bravo Shadow

## Status e limites

Documento de desenho técnico para revisão. **Não aprovado e não aplicado**.

- Não altera código, routers, serviços, schemas, banco ou interface.
- Não concede permissões a Admin ou Operador.
- Não transforma o perfil do cadastro em prova de identidade.
- As rotas de negócio continuam sem proteção HTTP; a API não deve ser exposta publicamente nem receber dados reais.
- O login continua baseado em identidade Google validada no servidor; não criar senha local.

## Objetivo

Substituir permissões genéricas que misturam operações diferentes por capacidades específicas por ação e por risco. A autorização deve ser verificada no backend em cada endpoint; esconder botões na interface não é controle de segurança.

## Catálogo proposto

Os nomes abaixo são sugestões canônicas. Antes da implementação, devem ser comparados com os endpoints e contratos finais.

| Domínio | Capacidades propostas | Observações |
|---|---|---|
| Condomínio | condominio:read, condominio:update | Não há criação/exclusão no contrato atual. |
| Conselho | conselheiros:read, create, update, delete | Separar consulta e manutenção. |
| Plano de Contas | plano_contas:read, create, update, delete | Exclusão continua sujeita a referências financeiras. |
| Financeiro | financeiro:read, create, update, delete | Não presumir aprovação, liquidação ou conciliação: esses fluxos não estão definidos no modelo atual. |
| Formas Monetárias | formas_monetarias:read, create, update, delete | Configuração de apoio. |
| Contas Bancárias | contas_bancarias:read, create, update, delete | Saldo informado manualmente; não equivale a conciliação bancária. |
| Moradores | moradores:read, create, update, delete, import | Importação em lote é uma ação distinta. A leitura deve ser tratada como dado pessoal restrito. |
| Fornecedores | fornecedores:read, create, update, delete | Dados cadastrais/fiscais. |
| Empregados | empregados:read, create, update, delete | Dados pessoais e funcionais. |
| Categorias | categorias:read, create, delete | Ajustar o catálogo se o endpoint ganhar edição. |
| Motivos de estoque | motivos_estoque:read, create, delete | Ajustar o catálogo se o endpoint ganhar edição. |
| Produtos em estoque | estoque:read, estoque:create, estoque:update_metadata, estoque:delete | update_metadata não autoriza alteração de quantidade/saldo. Exclusão respeita histórico e integridade. |
| Movimentos de estoque | acertos_estoque:read, acertos_estoque:create | Sem update/delete. Correção futura por movimento compensatório, se o fluxo for aprovado. |
| Documentos | documentos:read, create, update, delete | Leitura e download devem ser protegidos; não registrar conteúdo em logs. |
| Dashboard | dashboard:read | Sem endpoint de agregação confirmado; capacidade inerte até endpoint protegido e testes. |
| Relatórios/DRE | relatorios:read | Sem endpoint de agregação confirmado; capacidade inerte até endpoint protegido e testes. |
| Usuários — consulta | usuarios:read | Lista/detalhe restritos; avaliar se consultas precisam ser separadas por escopo. |
| Usuários — cadastro | usuarios:create, usuarios:update_data | Somente dados cadastrais não privilegiados. Não aceitar perfil/status como campos livremente editáveis. |
| Usuários — administração | usuarios:update_profile, usuarios:update_status, usuarios:deactivate | Ações separadas e altamente restritas. Sem autoalteração, autoelevação ou remoção do último Admin. |
| Auditoria | auditoria:read | Consulta de eventos separada de gestão de usuários e de dashboard. Sem editar/excluir eventos pela API. |

## Regras de domínio que não podem ser substituídas por permissões

1. Uma capacidade autoriza tentar a ação; as regras do serviço e as restrições do banco continuam obrigatórias.
2. Alterar metadados de produto não pode alterar quantidade.
3. Movimentos de estoque permanecem imutáveis; não criar capacidade de edição/exclusão.
4. Exclusão de Plano de Contas deve continuar bloqueada quando houver referência financeira.
5. Importação de moradores exige capacidade própria e validação do lote.
6. Operações administrativas de usuários exigem regras contextuais além da capacidade estática.
7. Dashboard e DRE não podem apresentar dados demonstrativos como dados reais nem converter ausência/falha de API em saldo zero.
8. Eventos de auditoria não devem conter e-mail, nome, CPF, telefone, endereço, token, senha, conteúdo documental, payload ou valor financeiro.

## Matriz de perfis — deliberadamente não preenchida

| Capacidade / grupo | Admin | Operador |
|---|---|---|
| Consultas operacionais | Aguardando aprovação | Aguardando aprovação |
| Cadastros e manutenção operacional | Aguardando aprovação | Aguardando aprovação |
| Lançamentos financeiros | Aguardando aprovação | Aguardando aprovação |
| Dados pessoais de moradores/empregados | Aguardando aprovação | Aguardando aprovação |
| Importação de moradores | Aguardando aprovação | Aguardando aprovação |
| Movimentos de estoque | Aguardando aprovação | Aguardando aprovação |
| Administração de usuários | Aguardando aprovação | Negar por padrão até decisão explícita |
| Consulta de auditoria | Aguardando aprovação | Aguardando aprovação |
| Dashboard e relatórios | Aguardando endpoint e aprovação | Aguardando endpoint e aprovação |

“Aguardando aprovação” significa negar por padrão na implementação. Esta tabela não concede nenhuma permissão.

## Regras contextuais obrigatórias para gestão de usuários

- O usuário não altera o próprio perfil nem o próprio status.
- Não permitir que um usuário se promova a Admin.
- Não permitir desativar ou remover o último Admin ativo.
- A criação inicial do primeiro Admin permanece fora de endpoint público, por bootstrap controlado no ambiente local isolado.
- Perfil e status vêm do cadastro interno confiável, nunca do token ou payload do navegador.
- Alterações de perfil/status devem gerar evento de auditoria na mesma transação da alteração.

## Sequência segura de implementação futura

1. Revisar e aprovar os nomes canônicos deste catálogo.
2. Aprovar separadamente a matriz Admin/Operador e as regras de acesso a dados pessoais.
3. Ajustar schemas e serviços de usuários para separar dados cadastrais de perfil/status.
4. Implementar testes unitários da política, incluindo negação por capacidade desconhecida.
5. Proteger cada rota com identidade Google validada e capacidade específica.
6. Testar HTTP 401, 403, sucesso autorizado, conta inativa e regras contextuais.
7. Integrar auditoria atomicamente nas operações críticas.
8. Só depois validar o modo PostgreSQL local com roles/RLS e considerar qualquer publicação controlada.

## Próximo bloqueio de decisão

A implementação não deve avançar para atribuição de capacidades aos perfis sem aprovação explícita da matriz Admin/Operador. Enquanto isso, o trabalho seguro é revisão estática, testes isolados e preparação de ambiente local; não ativar routers nem conectar dados reais.
