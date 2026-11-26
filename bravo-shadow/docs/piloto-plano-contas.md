# Piloto 01 — Plano de Contas

## Objetivo

Validar a arquitetura frontend/API e as regras básicas do primeiro domínio migrado, mantendo o original intacto.

## Contrato implementado

Base: `/api/v1/plano-contas`

### Modelo

- `id`: identificador gerado pelo serviço.
- `codigo`: texto obrigatório, 1–30 caracteres.
- `nome`: texto obrigatório, 2–160 caracteres.
- `tipo`: somente `Receita` ou `Despesa`.

Campos extras são rejeitados. Espaços periféricos são removidos na validação.

### Operações

| Método | Rota | Resultado esperado |
|---|---|---|
| GET | `/api/v1/plano-contas` | Lista ordenada por código |
| POST | `/api/v1/plano-contas` | Cria; retorna 201 |
| PUT | `/api/v1/plano-contas/{id}` | Atualiza; retorna 200 |
| DELETE | `/api/v1/plano-contas/{id}` | Exclui; retorna 204 |

### Regras e erros

- Código não pode ser duplicado (comparação sem diferenciar maiúsculas/minúsculas): HTTP 409.
- Registro inexistente em edição/exclusão: HTTP 404.
- Payload inválido: HTTP 422 via validação FastAPI/Pydantic.

## Limites conhecidos

- Armazenamento em memória; dados se perdem ao reiniciar o processo.
- Sem integração com Supabase ou com o frontend.
- Sem autenticação/autorização; manter o serviço restrito ao ambiente local de desenvolvimento.
- Não há ainda regra de impacto em lançamentos financeiros que referenciem a conta.
- A regra de unicidade precisa ser comparada com dados reais e importações existentes antes de ser adotada em produção.

## Testes automatizados preparados

- Criar e listar.
- Rejeitar código duplicado.
- Atualizar.
- Excluir.
- Rejeitar tipo inválido.

Os testes foram adicionados ao repositório, mas ainda precisam ser executados em ambiente Python para confirmar o resultado runtime.

## Próximas validações

1. Instalar dependências e executar `pytest`.
2. Executar API local e validar OpenAPI/HTTP.
3. Revisar regra de unicidade e normalização de códigos com o inventário real.
4. Definir persistência sombra isolada, migrações e transações.
5. Definir autenticação Google/e-mail e autorização antes de expor a API fora do ambiente local.
6. Integrar a tela do Plano de Contas ao endpoint somente depois dessas validações.
7. Comparar resultados e fluxos com o original, sem escrita no banco de produção.
