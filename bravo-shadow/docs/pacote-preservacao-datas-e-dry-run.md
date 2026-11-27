# Pacote de preservação de datas e dry-run — Bravo Shadow

**Branch:** bravo-shadow  
**Escopo:** endurecimento do planejador read-only e interpretação opcional de datas legadas.  
**Status:** código e testes sintéticos adicionados; testes não executados.

## Entregas deste pacote
- `migration_date_parser.py`: parser puro com regras explícitas e versionadas.
- `test_migration_date_parser.py`: casos sintéticos de ISO, pt-BR, calendário inválido, strings vazias e formatos não canônicos.
- Endurecimento do dry-run para aceitar estruturas imutáveis provenientes do leitor de envelope, exigir coleções explicitamente mapeadas e validar snapshots de estado.
- Testes adicionais de imutabilidade do envelope e entradas incompletas.

## Datas: preservação antes de interpretação
O parser mantém `raw_value` exatamente como recebido. Sem regra aprovada, retorna `not_attempted`. Com `iso_ymd_v1`, aceita estritamente AAAA-MM-DD; com `pt_br_dmy_v1`, aceita estritamente DD/MM/AAAA. Calendário impossível, zero padding incorreto ou espaços extras retornam `invalid`; nenhum valor é corrigido automaticamente.

O parser não aceita data sem ano, timestamp, hora ou fuso. Não infere timezone e não substitui o texto original pela data normalizada. A versão da regra precisa constar do mapeamento/manifesto da coleção que vier a utilizá-la.

## Dry-run endurecido
- Canonicalização recursiva de mappings imutáveis e tuplas produzidas pelo envelope reader.
- Coleção ausente no mapeamento explícito gera bloqueio, em vez de ser tratada como lista vazia.
- IDs do snapshot de destino e hashes de proveniência são validados antes da classificação.
- Nenhum payload ou valor de origem é incluído no relatório.

## Limites mantidos
- Não existe adaptador de escrita, endpoint de apply, transação PostgreSQL ou conexão.
- Rollback continua sendo simulação lógica.
- Não foi criado nem executado SQL.
- Não foram importados dados reais nem acessados bancos.
- Os testes não foram executados, conforme orientação atual.

## Próximo marco
Depois de confirmar os contratos e gates de origem, a próxima entrega será o adaptador transacional isolado, inicialmente com doubles sintéticos: uma conexão/unidade de trabalho única para dados funcionais, mapa de proveniência e auditoria de sucesso; falha em qualquer etapa deve reverter tudo. A implementação deverá permanecer desligada da aplicação e de qualquer banco até aprovação explícita e ambiente descartável comprovado.
