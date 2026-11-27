# Análise funcional — Empregados

Data da inspeção: 27/11/2026  
Escopo: comparação estática do módulo legado com a branch `bravo-shadow`.

## 1. Comportamento identificado no legado

A tabela apresenta:
- Nome e função/cargo;
- Empresa;
- Endereço;
- Telefone;
- Nome do contato de emergência e telefone;
- Ações de edição e exclusão.

O formulário de inclusão/edição contém sete campos:
1. Nome completo — obrigatório;
2. Função / Cargo — obrigatório;
3. Empresa — opcional;
4. Endereço — opcional;
5. Telefone — opcional;
6. Nome familiar/contato de emergência — opcional;
7. Telefone de emergência — opcional.

Não foi identificada importação de empregados no trecho funcional inspecionado. Também não foram observados campos de salário, documentos pessoais, jornada, datas de admissão/desligamento ou tipo de contrato. Não presumir tais requisitos sem validação funcional.

## 2. Implementação Shadow existente

### Schema
`backend/app/modules/empregados/schemas.py`:
- `nome` e `cargo` com comprimento mínimo 1;
- `empresa`, `endereco`, `telefone`, `contatoEmergenciaNome`, `contatoEmergenciaTel` opcionais;
- remove espaços nas extremidades de strings;
- rejeita campos extras.

### Serviço e persistência
`EmpregadosService` implementa listagem, criação, edição e exclusão sobre repositório. O adapter `PostgresEmpregadosRepository` persiste os sete campos em `bravo_shadow.empregados`. Na edição, atualiza `updated_at` e incrementa `version`.

### API
- `GET /api/v1/empregados` — `empregados:read`;
- `POST /api/v1/empregados` — `empregados:create`;
- `PUT /api/v1/empregados/{item_id}` — `empregados:update`;
- `DELETE /api/v1/empregados/{item_id}` — `empregados:delete`.

A matriz atual concede as quatro capacidades tanto a Admin quanto a Operador. O armazenamento PostgreSQL é registrado em `build_storage_services`.

## 3. Interface criada nesta etapa

A função `empregadosView()` foi adicionada ao frontend Shadow e ligada à navegação `data-module="empregados"`. A tela inclui os sete campos, estrutura de pesquisa, tabela com as colunas do legado e aviso de privacidade.

Todos os controles permanecem desabilitados. Não há chamadas de rede, dados sintéticos ou conexão com API nesta tela. A ativação depende de integração segura da sessão Google/Bearer e de uma API HTTPS em ambiente isolado.

## 4. Riscos e lacunas

1. **Exclusão física:** o service/repositório remove o registro. Não há fluxo de desligamento, arquivamento, retenção ou recuperação.
2. **Referências:** não foi identificada verificação de vínculos antes da exclusão.
3. **Concorrência:** o adapter incrementa `version`, mas o router não exige `If-Match`/ETag nem repassa versão esperada ao service.
4. **Auditoria:** não foi confirmada gravação transacional de eventos de auditoria para CRUD de empregados.
5. **Consulta:** GET lista a coleção inteira, sem filtros ou paginação.
6. **Privacidade:** endereço, telefone e dados do contato de emergência devem ter acesso mínimo, logs sem conteúdo pessoal e retenção definida.
7. **Escopo trabalhista:** não acrescentar salário, documentos, jornada ou dados contratuais sem confirmação do responsável pelo processo.

## 5. Critérios para habilitação futura

- Definir política de desligamento/arquivamento e retenção antes de liberar exclusão;
- confirmar se empregados são referenciados por outros módulos;
- implementar controle de versão concorrente no contrato HTTP;
- registrar operações sensíveis em auditoria apropriada;
- adicionar paginação e filtros quando necessário;
- validar perfil Operador e necessidade de acesso a contatos de emergência;
- concluir integração Google/Bearer com API HTTPS isolada.

## 6. Limites desta entrega

Esta etapa é uma implementação visual e documentação de paridade. Não executou testes, não aplicou SQL, não conectou banco, não publicou frontend/API e não alterou a branch `main` nem dados de produção.
