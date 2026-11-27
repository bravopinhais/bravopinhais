# Contratos especiais de migração — módulos de maior risco

Data: 27/11/2026  
Branch: bravo-shadow  
Escopo: avaliação estrutural e regras de preservação. Não executa importação, transformação, leitura de arquivos externos ou gravação.

## Resultado geral

Foram definidos contratos especializados para Financeiro, Documentos, Estoque e Acertos de Estoque. Condomínio foi separado como objeto singleton, pois o inventário atual percorre coleções em formato de lista e não consegue localizá-lo sem identificar primeiro o caminho real no snapshot legado.

O avaliador trabalha com nomes exatos. Uma coleção com nome diferente só é considerada mediante mapeamento explícito após confirmação. Os contratos não produzem payload, não preenchem defaults, não convertem valores e não descartam campos adicionais.

## 1. Condomínio — objeto singleton

O Shadow possui um objeto institucional com 17 campos textuais: identificação, endereço, contatos e identificadores de concessionárias (Copel, gás e Sanepar).

**Condição atual:** localização manual da origem necessária. O inventário de coleções não é evidência suficiente para localizar o singleton.

Regras:
- identificar um único objeto de origem; mais de um candidato exige revisão;
- preservar ausência, null e string vazia como estados distintos;
- manter CNPJ, CEP, telefones e códigos como texto, inclusive zeros à esquerda;
- não criar ID, lista ou valores padrão artificiais;
- não inferir equivalências entre nomes de campo.

## 2. Financeiro

Contrato legado observado: id, tipo, planoContaId, historico, valor.

| Campo | Regra especial |
|---|---|
| id | Preservar exatamente como texto |
| tipo | Validar literal Receber/Pagar |
| planoContaId | Opcional; resolver apenas por ID exato |
| historico | Preservar texto; campo obrigatório |
| valor | Origem numérica via JavaScript; conversão para Decimal exige decisão explícita |

**Bloqueios:** um número JSON não comprova que os centavos foram preservados exatamente. Vínculos órfãos ou ambíguos no Plano de Contas exigem revisão. Não inventar vencimento, baixa, parcelas, status ou liquidação: esses campos não constam do contrato legado auditado.

## 3. Documentos

Contrato legado observado: id, pasta, titulo, nomeArquivo, arquivoCompactadoGzip.

O nome do campo não é prova do codec. A auditoria estática identificou uso de pako.deflate/pako.inflate; portanto, não se pode presumir que o conteúdo seja um fluxo Gzip RFC 1952 aceito pelo validador atual do Shadow.

Regras:
- preservar Base64 e bytes comprimidos originais na primeira passagem;
- identificar e validar o codec antes de qualquer descompactação;
- comparar SHA-256 do conteúdo descompactado em ambiente descartável;
- não recompactar, converter ou renomear em lote;
- mapear pasta/categoria somente por correspondência exata e única;
- relatórios não podem expor conteúdo, nomes pessoais ou payload binário.

**Bloqueios:** storage de objetos, limite, MIME, retenção e autorização de download ainda dependem de destino e política aprovados. A lista não deve transportar conteúdo binário integral.

## 4. Estoque e Inventário

Contrato legado observado para cadastro: id, item, quantidade, minimo, maximo, etiqueta, fotoNome, fotoCompactadaGzip.

Regras:
- IDs, etiquetas e unidades permanecem textuais;
- quantidades precisam de conversão controlada para Decimal, sem float intermediário;
- separar saldo cadastrado de histórico de movimentos;
- reconciliar saldo por produto com os movimentos, sem correção automática;
- marca, linha, fabricante e dataCadastro são extensões solicitadas no Shadow, não campos comprovados no cadastro legado auditado.

**Bloqueios:** o legado permite saldo negativo em certos fluxos; Shadow bloqueia saída acima do saldo. Etiquetas duplicadas, limites incoerentes e divergências de saldo precisam de decisão humana. Fotos podem usar o codec deflate do legado, apesar do nome Gzip.

## 5. Acertos de Estoque

Contrato legado observado: id, data, tipo, produtoId, quantidade, motivo.

Regras:
- preservar o texto original da data e versionar qualquer parser;
- validar tipo como Entrada/Saída;
- resolver produtoId por ID exato;
- manter motivo textual; motivoId não consta no registro legado observado;
- reconstruir movimentos em ordem determinística aprovada e comparar saldo calculado ao saldo cadastrado;
- nunca apagar ou reescrever movimentos na migração.

**Bloqueios:** legado permite saldo negativo e exclusão de histórico sem recomposição do saldo; Shadow bloqueia saldo negativo e orienta correção por movimento compensatório. Datas ambíguas e movimentos sem produto correspondente ficam em revisão.

## Estados e interpretação do avaliador

O módulo migration_special_contracts.py avalia presença de coleção, campos obrigatórios, preenchimento parcial, campos extras e tipos observados. Os quatro módulos permanecem em review_required mesmo quando a estrutura coincide, pois ainda há invariantes de domínio que não podem ser comprovadas por uma contagem de campos.

Códigos relevantes:
- source_collection_not_found: coleção não localizada pelo nome confirmado; não se tenta adivinhar alias;
- review_required: existe risco de domínio, integridade, tipo ou campo que exige decisão;
- manual_source_locator_required: Condomínio singleton ainda precisa ser localizado manualmente.

O mapeamento explícito de nomes de coleção é permitido somente depois de confirmar a origem. Não há junção automática de coleções nem transformação de dados.

## Próximas dependências antes de qualquer piloto

1. Localizar e documentar o caminho do objeto singleton de Condomínio.
2. Obter snapshot sintético/anônimo representativo e confirmar nomes reais das coleções.
3. Aprovar estratégia de Decimal e política para valores que não possam ser recuperados com precisão.
4. Identificar codec real dos documentos e fotos por amostras controladas.
5. Definir política de saldo negativo e procedimento de reconciliação de estoque.
6. Validar todas as referências por ID e gerar relatório de órfãos/duplicidades.
7. Só depois especificar o transformador e o serviço transacional de importação.

## Limites desta entrega

- Nenhum dado real foi consultado ou importado.
- Nenhum payload de migração foi gerado.
- Nenhuma transformação, conversão, correção de saldo ou recompactação foi executada.
- Nenhum SQL foi aplicado, banco conectado ou ambiente publicado.
- Testes sintéticos foram adicionados, mas não executados, conforme orientação vigente.
