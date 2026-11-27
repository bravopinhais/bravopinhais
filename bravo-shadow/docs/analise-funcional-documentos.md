# Análise funcional — Gestão de Documentos

Data da inspeção: 2026-11-27  
Escopo: comparação estática do renderizador legado e dos contratos Shadow. Nenhum arquivo real foi lido, importado ou enviado.

## Fluxo observado no sistema legado

O módulo **Documentos Gzip** apresenta uma tabela com pasta, título, nome do arquivo e ações. Para cada registro, o legado oferece:

- inserir documento;
- editar título/pasta e substituir o arquivo;
- visualizar o arquivo;
- baixar o arquivo original;
- excluir documento;
- selecionar a pasta a partir das categorias cadastradas (com opções padrão quando não há categorias).

O registro legado usa os campos `id`, `pasta`, `titulo`, `nomeArquivo` e `arquivoCompactadoGzip`. O navegador compacta o arquivo em Gzip e mantém o conteúdo codificado em Base64. Na edição, se não houver novo arquivo selecionado, o conteúdo e o nome anteriores são preservados. A visualização e o download descompactam o conteúdo antes de abrir/baixar.

## Contrato atualmente existente no Shadow

- `GET /api/v1/documentos`: lista documentos.
- `GET /api/v1/documentos/{id}`: consulta um documento.
- `POST /api/v1/documentos`: cria documento.
- `PUT /api/v1/documentos/{id}`: substitui os metadados/conteúdo do documento.
- `DELETE /api/v1/documentos/{id}`: exclui documento.
- Capacidades: `documentos:read`, `documentos:create`, `documentos:update`, `documentos:delete`.
- Contrato de entrada: `pasta`, `categoriaId` opcional, `titulo`, `nomeArquivo`, `arquivoCompactadoGzip`.
- Quando `categoriaId` é informado, o serviço valida a categoria e usa o nome da categoria como pasta.
- O repositório PostgreSQL atual armazena `arquivo_compactado_gzip` diretamente na linha do documento.

## Diferenças e lacunas identificadas

1. A tela Shadow recém-criada é apenas estrutura visual; não consulta nem grava documentos.
2. O cliente ainda não implementa compressão Gzip/Base64, descompressão, visualização ou download.
3. O backend aceita uma string não vazia para o conteúdo compactado, mas o contrato inspecionado não define limite explícito de tamanho nem validação de assinatura/formato Gzip.
4. Não há validação de MIME/tipo real, extensão permitida, nome seguro, proteção contra conteúdo malicioso ou política de retenção documentada.
5. Não há serviço de armazenamento externo, URLs assinadas, upload/download em streaming, gestão de arquivos órfãos ou otimização de armazenamento.
6. Armazenar Base64/Gzip em uma coluna de banco aumenta o volume por causa da codificação e não equivale a storage de objetos.
7. A API lista o conteúdo completo no contrato atual; antes de habilitar listagem em escala, separar metadados de conteúdo binário e evitar transportar todos os arquivos no endpoint de lista.
8. A relação de categoria é opcional no schema, enquanto o legado grava o nome da pasta. É necessário manter compatibilidade de leitura e decidir como tratar categorias renomeadas/excluídas sem perder a identificação histórica.

## Sequência segura para concluir o módulo

1. Definir limites de tamanho, tipos aceitos e política de nomes; rejeitar conteúdo que não seja Gzip válido e Base64 canônico.
2. Definir armazenamento de objetos gratuito/compatível com as restrições do projeto, sem serviço pago ou publicação não aprovada. Se não houver destino aprovado, manter upload bloqueado.
3. Separar metadados do conteúdo; a listagem deve retornar metadados e tamanho/hash, não o conteúdo integral.
4. Criar endpoints específicos de upload/download com autorização por documento, streaming, cabeçalhos seguros e sem URLs públicas permanentes.
5. Definir estratégia de visualização por MIME com sandbox e fallback de download.
6. Definir reconciliação de referências, limpeza de órfãos e auditoria antes de qualquer exclusão física.
7. Implementar cliente Gzip, progresso, cancelamento, estados de erro e preservação do arquivo existente durante edição.
8. Comparar os resultados com o legado em ambiente descartável e só depois considerar aceite funcional.

## Situação

- [x] Renderizador legado e ações de documentos inspecionados estaticamente.
- [x] Contrato e rotas Shadow inspecionados.
- [x] Tela inicial Shadow criada com formulário, filtros e tabela, sem ações ativas.
- [x] Limitações atuais explicitadas na interface e no README.
- [ ] Validação robusta de arquivo e limites de tamanho.
- [ ] Estratégia de armazenamento de objetos aprovada e implementada.
- [ ] Upload/download/visualização integrados.
- [ ] Auditoria e reconciliação de arquivos órfãos.
- [ ] Homologação funcional e aceite.

**Não é aceite de paridade:** o módulo permanece incompleto. Nenhum arquivo real foi importado e nenhum teste foi executado nesta etapa.
