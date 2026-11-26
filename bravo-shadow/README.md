# Bravo Shadow

Versão paralela do Bravo, criada para evolução arquitetural gradual e homologação antes de qualquer substituição do sistema original.

## Princípios

- O sistema original permanece na branch `upgrade/project-hardening` e não é alterado por este projeto.
- Esta branch (`bravo-shadow`) é o ambiente independente de construção.
- Nenhuma gravação será feita no banco de produção durante desenvolvimento e testes.
- A interface preservará a identidade do Bravo: modo noturno fixo, grafite/carvão, texto claro e acento verde-azulado, com acabamento mais refinado.
- A autenticação Google/e-mail existente será tratada como integração a preservar; não será reintroduzido login por senha local.
- Migração por capacidade/módulo, com testes de equivalência, rastreabilidade e plano de reversão.

## Estrutura

- `backend/`: API Python com FastAPI.
- `frontend/`: futura interface web unificada.
- `docs/`: inventário, arquitetura e plano de migração.

## Estado atual

Fundação inicial criada. A API expõe apenas um endpoint de saúde; ainda não há conexão com Supabase, dados reais, autenticação ou operações de negócio. Isso é intencional até a conclusão do inventário e da definição dos contratos.

## Execução local

Consulte `backend/README.md`. Não configure credenciais de produção neste ambiente.

## Regra de promoção

Nada desta versão será promovido ao original sem homologação funcional, validação de dados, revisão de segurança e aprovação explícita.
