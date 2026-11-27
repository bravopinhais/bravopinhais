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

O frontend estático é publicado pelo GitHub Pages a partir de `bravo-shadow/frontend/`. Esse preview serve para avaliar layout e navegação; ele não hospeda a API FastAPI e bloqueia chamadas de API quando aberto em `github.io`. A interface respeita a preferência do sistema por movimento reduzido, reduzindo transições e animações para usuários que ativaram essa opção. A navegação oferece link para pular ao conteúdo, foco visível, foco no título ao trocar de módulo e retorno seguro ao Dashboard para fragmentos inválidos. Mensagens de estado do cadastro de Formas Monetárias também são anunciadas por região acessível `role="status"`. A tabela desse cadastro identifica seu conteúdo com legenda e marca os cabeçalhos de coluna com `scope="col"`. Os botões de edição e exclusão identificam também o nome da forma monetária associada, facilitando o uso com leitor de tela. O campo de multa aplica limites nativos de 0 a 100%, com preenchimento obrigatório e precisão de duas casas decimais. O aviso sobre armazenamento temporário é associado programaticamente ao formulário por `aria-describedby`, tornando o limite do ambiente perceptível também para tecnologias assistivas. Durante o envio, ações de edição, exclusão e atualização da lista também ficam bloqueadas para evitar concorrência entre operações e mudanças inesperadas no formulário. Se uma atualização detectar que o registro aberto para edição já não existe, o formulário é limpo e a edição obsoleta é cancelada, evitando tentar salvar uma referência removida. Ao atualizar manualmente a lista durante uma edição, o formulário cancela a edição anterior e informa o usuário, evitando salvar dados que podem ter ficado desatualizados. Se uma atualização posterior falhar e já houver uma lista carregada, a interface mantém os registros visíveis e avisa que são os últimos dados carregados e podem estar desatualizados, em vez de substituir a tabela por uma mensagem vazia. Enquanto essa lista estiver marcada como potencialmente desatualizada, as ações de edição e exclusão ficam bloqueadas até uma atualização bem-sucedida, evitando operar sobre referências antigas. Ao iniciar uma edição, a região de status anuncia o nome do registro e orienta a salvar ou cancelar, sem depender apenas da mudança visual dos botões. Durante o envio, o botão informa `Salvando...`, fica temporariamente desabilitado e o formulário expõe `aria-busy` até a conclusão. Após salvar, a interface distingue a confirmação da gravação do resultado da atualização da lista: se a gravação funcionar, mas a consulta de atualização falhar, informa que o registro foi salvo e orienta usar `Atualizar`, sem apresentar o salvamento como falho. O manipulador também ignora novos eventos de envio enquanto o formulário já está ocupado, evitando requisições duplicadas. Ao abrir novamente o módulo Formas Monetárias, o estado de edição anterior é descartado, pois a tela é reconstruída; isso evita que um formulário novo tente atualizar silenciosamente um registro antigo. Ao entrar em edição, a interface oferece `Cancelar edição`; cancelar restaura o formulário sem enviar alterações à API e devolve o foco ao campo de nome. A tecla `Escape` também cancela a edição, exceto enquanto um envio está em andamento; nesse estado, o cancelamento é bloqueado para evitar divergência entre a tela e a operação pendente. A atualização da lista também apresenta `Atualizando...`, impede cliques repetidos e expõe seu estado ocupado. A exclusão confirmada apresenta `Excluindo...`, bloqueia novos cliques durante a operação e sinaliza `aria-busy` até o retorno. Se a exclusão for concluída, mas a atualização da lista falhar, a interface informa os dois resultados separadamente e orienta usar `Atualizar`. Após a operação, o foco é direcionado à região de status acessível para que o resultado fique perceptível também na navegação por teclado. A publicação depende de o GitHub Pages estar habilitado com a fonte **GitHub Actions** nas configurações do repositório.

## Homologação local sintética

A fixture controlada está em `backend/fixtures/migration_homologation_synthetic.json`. O teste `backend/tests/test_migration_homologation_fixture.py` verifica a avaliação integrada sem expor valores dos registros. Para preparar o PostgreSQL local descartável, consulte `docs/guia-homologacao-gratuita.md` e `scripts/homologar-local.sh`. O script recria somente o banco local configurado; nunca executar em ambiente com dados úteis. Nenhum banco hospedado, importação ou deploy é necessário ou autorizado nesta etapa.

## Execução local

Consulte `backend/README.md` para executar a API diretamente e `docs/implantacao-portatil.md` para construir e executar a interface + API em um container Docker. O pacote portátil usa armazenamento temporário em memória e não deve receber dados reais.

## Regra de promoção

Nada desta versão será promovido ao original sem homologação funcional, validação de dados, revisão de segurança e aprovação explícita.
