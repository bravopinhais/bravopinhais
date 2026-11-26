# Revisão de onboarding e primeiro administrador — Bravo Shadow

## Status

**Revisão documental concluída; nenhuma implementação autorizada ou realizada.** Não foram alterados schemas, serviços, rotas, autenticação, banco, migrations, interface ou o sistema original.

## Conclusão executiva

O desenho de provisionamento fora da API pública é a direção correta, mas ainda não está pronto para execução. Há uma divergência importante entre a política proposta e o contrato atual: o schema e a tabela SQL permitem que um cadastro novo comece como `Ativo`, enquanto os documentos deixam o estado inicial pendente de decisão. Essa decisão precisa ser tomada antes da refatoração.

A recomendação de segurança é que cadastros comuns comecem **sem acesso** (`Inativo`, ou um estado explícito `Pendente` se esse estado for aprovado no contrato). A conta só deve autenticar nas rotas protegidas depois de aprovação administrativa. Isso não altera a regra do primeiro Admin: ele é provisionado separadamente, de forma controlada e fora da API.

## Achados confirmados

### 1. O onboarding atual concede estado ativo por padrão

- `UsuarioInput.status` tem default `Ativo`; `perfil` tem default `Operador`.
- A tabela SQL proposta também define `status default 'Ativo'` e `perfil default 'Operador'`.
- Portanto, omitir esses campos em uma criação atual pode resultar em Operador ativo.
- Os documentos de contrato e refatoração, porém, dizem corretamente que o estado inicial ainda não foi decidido e não deve ser codificado sem aprovação.

**Risco:** se uma futura rota de criação simplesmente reaproveitar o schema ou os defaults atuais, poderá ativar um usuário sem a aprovação de onboarding pretendida.

**Recomendação:** retirar defaults privilegiados/de acesso do contrato público de criação. O servidor deve aplicar explicitamente o estado inicial aprovado. Até a decisão, não implementar a nova rota nem reutilizar o schema legado para cadastro comum.

### 2. A autenticação Google já bloqueia cadastros inativos

A função `principal_from_google_claims` exige `sub`, e-mail não vazio e `email_verified is True`; normaliza o e-mail, exige exatamente um cadastro correspondente e exige `status == "Ativo"`. Cadastro ausente, duplicado ou inativo não recebe principal válido.

Isso dá suporte técnico a um onboarding pendente/inativo, mas a dependência ainda não está ligada às rotas de negócio. O endpoint `/auth/me` usa a fundação de autenticação; os routers de negócio e de usuários continuam sem proteção. Logo, a checagem do status **não torna a API segura enquanto as rotas permanecerem públicas**.

### 3. O backend padrão é memória

`build_storage_services("memory")` cria um repositório de usuários em memória. O modo PostgreSQL exige uma `connection_factory` explícita. O documento de bootstrap já exige corretamente PostgreSQL persistente e recusa memória.

**Recomendação:** o futuro comando de bootstrap deve verificar explicitamente o backend configurado e falhar antes de qualquer operação se não for PostgreSQL de sombra. Não pode aceitar fallback para memória nem conexão remota/produção.

### 4. O primeiro Admin precisa de garantias transacionais mais precisas

O desenho atual exige transação, unicidade e abortar se já houver Admin ativo. O desenho separado de operações atômicas de usuários também prevê bloqueio transacional para operações que afetam Admins.

Antes de implementar o bootstrap, formalizar que:
- a verificação de Admin ativo e a criação ocorrem na mesma transação;
- a serialização usa o mesmo mecanismo de bloqueio adotado pelas futuras alterações de perfil/status;
- o e-mail é normalizado de modo idêntico no comando, schema, autenticação e banco;
- a unicidade é imposta pelo banco e conflitos são tratados sem promover ou reativar registros existentes;
- a segunda execução não altera registros e retorna resultado seguro e explícito;
- qualquer falha faz rollback integral.

O índice SQL atual usa `lower(email)`; o schema Python normaliza com `strip().lower()`. Para defesa consistente contra espaços armazenados por caminhos alternativos, revisar o índice para a mesma normalização, por exemplo `lower(btrim(email))`, antes de criar a migration local.

### 5. O cadastro legado não pode ser exposto

O router atual permite GET de lista/detalhe, POST, PUT e DELETE sem autenticação. O schema aceita `perfil` e `status`; o serviço faz checagem de e-mail separada da gravação; a exclusão é física.

**Recomendação:** não reutilizar esse router como interface de onboarding. Implementar primeiro os contratos separados já propostos: cadastro sem perfil/status, atualização cadastral parcial, administração de perfil/status e desativação lógica. Cada rota deve exigir token Google validado e capacidade específica. Não criar endpoint público de bootstrap.

### 6. Identidade e primeiro acesso

A identidade confiável deve continuar vindo do ID token Google validado no servidor. O cliente não pode definir `perfil`, `status`, `subject` ou o e-mail de identidade por payload. O bootstrap recebe o e-mail explicitamente pelo ambiente controlado, mas a autenticação posterior ainda precisa validar o token Google e encontrar o cadastro interno ativo.

O vínculo atual é por e-mail verificado; não há persistência do `sub` Google no cadastro. Isso é aceitável para a proposta atual somente se a política de troca/recuperação de e-mail for definida e auditada. Não adicionar vínculo por `sub` sem desenhar migração e reconciliação.

## Fluxo recomendado, ainda sujeito à aprovação

1. Preparar ambiente isolado de sombra com PostgreSQL local/homologação privada e credenciais restritas.
2. Aplicar somente migrations revisadas no banco local descartável; não usar projeto remoto ou banco de produção.
3. Executar comando administrativo fora da API com `BRAVO_BOOTSTRAP_ADMIN_EMAIL` explicitamente informado pelo responsável.
4. Normalizar e validar o e-mail; abortar se já existir qualquer Admin ativo ou se o e-mail já estiver cadastrado como Operador/Inativo.
5. Criar exatamente um Admin ativo dentro da transação e registrar evento mínimo de auditoria na mesma transação quando o sink transacional estiver integrado.
6. Remover a variável de bootstrap e impedir reutilização; não persistir segredo em arquivo versionado ou log.
7. Validar login com conta Google correspondente e token real validado no servidor.
8. Criar usuários subsequentes somente pelo fluxo administrativo protegido; mantê-los sem acesso até aprovação, caso essa seja a política aprovada.
9. Liberar acesso às rotas apenas depois de matriz de capacidades aprovada, dependências por rota implementadas e testes 401/403/permitido concluídos.

## Decisões que continuam pendentes

Nenhuma delas é presumida pelo pedido “Seguir”.

1. Cadastro novo começa como `Inativo` ou será criado um estado `Pendente`?
2. Quem pode criar cadastros e quem pode aprovar/ativar?
3. O convite será enviado antes ou depois da criação do cadastro?
4. A criação administrativa exige aprovação adicional ou confirmação?
5. A desativação lógica substitui definitivamente a exclusão física?
6. A política de identidade continuará baseada somente no e-mail Google verificado ou exigirá também persistência do `sub`?
7. A matriz de capacidades e as permissões de Admin/Operador serão aprovadas separadamente.

## Próxima sequência técnica segura

Sem depender dessas decisões, o próximo trabalho seguro é preparar uma lista de verificação de implementação e testes para o comando de bootstrap e para o módulo de usuários, mantendo tudo como desenho. A implementação só começa após aprovação das decisões funcionais, revisão das migrations e ambiente PostgreSQL local isolado.

## Restrições preservadas

- Nenhum código, rota, schema ou banco foi alterado nesta revisão.
- Nenhum usuário ou Admin foi criado.
- Nenhum teste foi executado nesta etapa.
- Nenhuma conexão com banco remoto ou produção foi realizada.
- O login continua baseado em Google/e-mail; nenhuma senha local foi introduzida.
- A tela de login e o `index.html` original permanecem intocados.
