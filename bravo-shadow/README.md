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
- `docs/`: inventário, arquitetura, plano de migração e implantação portátil.

## Estado atual

Fundação da API e contratos dos 15 módulos implementados na sombra. Plano de Contas e Financeiro possuem adaptadores PostgreSQL preparados, mas o runtime permanece em memória por padrão. Ainda não há migration aplicada, driver configurado, conexão Supabase, dados reais ou autenticação Google validada. Consulte `docs/` e `supabase/README.md` para o estado e os limites do piloto.

## Preview visual

O frontend estático é publicado pelo GitHub Pages a partir de `bravo-shadow/frontend/`. Esse preview serve para avaliar layout e navegação; ele não hospeda a API FastAPI e bloqueia chamadas de API quando aberto em `github.io`. A navegação oferece link para pular ao conteúdo, foco visível, foco no título ao trocar de módulo e retorno seguro ao Dashboard para fragmentos inválidos. Mensagens de estado do cadastro de Formas Monetárias também são anunciadas por região acessível `role="status"`. A tabela desse cadastro identifica seu conteúdo com legenda e marca os cabeçalhos de coluna com `scope="col"`. Os botões de edição e exclusão identificam também o nome da forma monetária associada, facilitando o uso com leitor de tela. O campo de multa aplica limites nativos de 0 a 100%, com preenchimento obrigatório e precisão de duas casas decimais. Durante o envio, o botão informa `Salvando...`, fica temporariamente desabilitado e o formulário expõe `aria-busy` até a conclusão. O manipulador também ignora novos eventos de envio enquanto o formulário já está ocupado, evitando requisições duplicadas. A atualização da lista também apresenta `Atualizando...`, impede cliques repetidos e expõe seu estado ocupado. A exclusão confirmada apresenta `Excluindo...`, bloqueia novos cliques durante a operação e sinaliza `aria-busy` até o retorno. A publicação depende de o GitHub Pages estar habilitado com a fonte **GitHub Actions** nas configurações do repositório.

## Execução local

Consulte `backend/README.md` para executar a API diretamente e `docs/implantacao-portatil.md` para construir e executar a interface + API em um container Docker. O pacote portátil usa armazenamento temporário em memória e não deve receber dados reais.

## Regra de promoção

Nada desta versão será promovido ao original sem homologação funcional, validação de dados, revisão de segurança e aprovação explícita.
