# Adaptador de persistência do histórico de revisão — Shadow

## Objetivo

Definir uma porta de armazenamento para o histórico humano de revisão de lotes,
com uma implementação em memória segura para desenvolvimento e testes.

## Contrato

- O histórico permanece vinculado ao `batch_id` e ao `manifest_hash`.
- Cada revisão é um evento novo; eventos anteriores nunca são editados ou removidos.
- `expected_version` implementa controle otimista por decisão.
- A validação da versão e a inclusão do evento ocorrem sob a mesma trava no
  adaptador em memória.
- Um mesmo `batch_id` não pode ser reutilizado com outro hash de manifesto.
- Identificadores de evento são únicos dentro do ledger.
- As escolhas registradas continuam sendo decisões humanas; nenhuma escolha
  executa importação, resolve conflito automaticamente ou altera o manifesto.

## Limites da implementação atual

`InMemoryReviewLedgerStore` é volátil: os registros desaparecem ao reiniciar
o processo e não são compartilhados entre instâncias/servidores. Portanto, não
é persistência durável nem adequada para produção.

A implementação PostgreSQL deverá preservar a mesma interface sem confiar em
travas de processo: deve usar transação no banco, restrição única para evento,
vínculo de lote/manifesto e atualização concorrente condicionada à versão
esperada (ou bloqueio de linha). O evento e o avanço da versão devem ser
atômicos. RLS, papéis e permissões continuam bloqueadores e precisam de desenho
e aprovação próprios antes de qualquer DDL ou conexão.

## Segurança e escopo

- Somente a branch `bravo-shadow`.
- Nenhum acesso a banco, Supabase hospedado ou dados reais.
- Nenhuma alteração em `index.html` original.
- Nenhuma escrita dupla, importação ou cutover.
- Testes adicionados; execução ainda não confirmada.
