# Política central de autorização — Bravo Shadow

## Escopo desta entrega

`authorization.py` contém um catálogo de capacidades e uma função de decisão
pura. Ela não valida tokens Google, não consulta o cadastro de usuários e não
foi conectada aos routers. Não representa autenticação pronta para produção.

## Contrato de confiança

`AuthenticatedPrincipal` só pode ser criado por uma camada de autenticação
futura depois de:

1. validar criptograficamente o token Google no servidor;
2. conferir emissor, audiência, expiração e sujeito;
3. resolver o sujeito/e-mail no cadastro interno;
4. confirmar que o usuário está ativo;
5. obter perfil e status da fonte confiável, nunca do corpo enviado pelo browser.

Não instanciar esse objeto a partir de campos enviados pelo cliente.

## Política atual

- `Admin`: recebe as capacidades administrativas enumeradas em
  `ROLE_CAPABILITIES`, respeitando as invariantes de histórico de estoque.
- `Operador`: nenhuma capacidade concedida enquanto a matriz funcional não
  for aprovada.
- Perfil desconhecido, usuário inativo, identidade ausente ou capacidade
  desconhecida: negar.
- A API responde 403 para uma decisão de autorização negada. A futura camada
  de autenticação deverá responder 401 quando não houver identidade válida.
- `GET /api/v1/health` continua público e fora deste catálogo.

## Invariantes

- Não existe capacidade para editar ou excluir movimentos de estoque.
- Alterar saldo após histórico continua sujeito às regras transacionais do
  repositório de estoque.
- Esta política não substitui validações de integridade, auditoria ou RLS.
- O perfil Admin não deve ser aceito apenas porque o navegador o enviou.
- A matriz de Operador deve ser aprovada antes de conceder qualquer capacidade.

## Integração futura

Cada endpoint deverá declarar explicitamente a capacidade exigida por meio de
dependências FastAPI centrais. A integração deve ocorrer somente após definir
e testar a validação do token Google e o vínculo com o cadastro interno.


## Dependência FastAPI reutilizável — preparada

```python
from fastapi import Depends
from app.core.authorization import require_capability_dependency

@router.get("/exemplo")
def listar_exemplo(
    principal = Depends(require_capability_dependency("financeiro:read")),
):
    ...
```

A fábrica `require_capability_dependency` combina a identidade
validada por `get_current_principal` com a verificação da capacidade
solicitada. Ela retorna o principal autenticado para uso opcional no handler.

A fábrica não foi aplicada aos routers de negócio nesta etapa. Portanto, não
interpretar a existência dessa função como proteção HTTP já ativada. A
integração por rota depende da aprovação da matriz funcional e deverá ser
acompanhada de testes HTTP positivos e negativos.
