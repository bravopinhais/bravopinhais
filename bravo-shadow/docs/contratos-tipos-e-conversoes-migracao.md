# Contratos de tipos e conversões da migração

**Estado:** validadores puros implementados; testes sintéticos escritos e não executados.

## Decimais
- Exigem texto decimal; floats e inteiros JSON são recusados para evitar aceitar aproximações binárias sem decisão.
- Conversão usa Decimal sem arredondamento implícito.
- Precisão, escala e sinal são parâmetros por campo.
- Financeiro e contas bancárias usam numeric(14,2) no DDL; estoque e movimentos usam numeric(14,3).
- Valores financeiros legados originados em Number/parseFloat não comprovam exatidão decimal. Exigem relatório de diferença e regra aprovada.

## Datas
- data_cadastro do estoque: DATE, texto canônico YYYY-MM-DD.
- data dos acertos: TIMESTAMPTZ, ISO 8601 com offset ou Z obrigatório.
- Data sem fuso fica em revisão; não assumir fuso local nem reescrever o texto original.

## Literais
- Financeiro: Receber/Pagar.
- Movimentos: Entrada/Saída.
- Comparação exata, sem normalizar caixa, acentos ou aliases.

## Documentos e fotos
- Base64 estrito; reconhecimento de zlib-wrapped deflate (pako.deflate legado) e Gzip.
- Limites configuráveis para bytes codificados e descompactados.
- Resultado contém codec, tamanhos e SHA-256 do conteúdo descompactado; nunca retorna conteúdo.
- Preservar bytes/Base64 originais na primeira passagem. Não recomprimir nem migrar automaticamente para Storage.
- MIME, antivírus, retenção e autorização de download permanecem pendentes.

## Limites e próximos bloqueios
Os validadores ainda precisam ser ligados aos campos concretos dos contratos, sem inferir aliases ou transformar payloads. Testes não executados. Nenhum SQL aplicado, banco conectado ou dado importado.
