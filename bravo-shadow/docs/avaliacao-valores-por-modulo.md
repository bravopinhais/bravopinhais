# Avaliação de valores por registro e módulo

O avaliador `migration_special_value_assessment.py` conecta os contratos de alto risco aos validadores de tipos sem transformar o registro.

| Módulo | Verificações por registro |
|---|---|
| Financeiro | Literal Receber/Pagar, precisão/escala SQL e bloqueio de precisão não comprovada em número JSON |
| Documentos | Base64 estrito, identificação Deflate/Gzip, limites e integridade do fluxo |
| Estoque | Quantidade/minimo/maximo, escala 3, sinal não negativo e revisão de conversão |
| Acertos | Entrada/Saída, quantidade positiva, escala 3 e data/hora com fuso |

O retorno contém somente código e mensagem de ocorrência, nunca o valor de origem. O objeto de entrada não é alterado. Mesmo quando a forma do valor é válida, o status não autoriza gravação: mapeamento, proveniência, reconciliação referencial e aprovação de migração continuam obrigatórios.

Os números legados são inspecionados sem arredondamento. Financeiro permanece bloqueado para precisão monetária não comprovada; quantidades numéricas requerem regra aprovada para conversão Decimal. Datas fora de ISO 8601 com fuso permanecem em revisão, sem presumir timezone.

Testes sintéticos escritos e não executados. Nenhum dado real foi lido, nenhum banco foi conectado e nenhuma importação foi iniciada.
