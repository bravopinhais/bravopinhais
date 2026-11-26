# Auditoria de Gestão de Documentos

## Fonte e preservação
Inspeção estática de `index.html` na branch `upgrade/project-hardening`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. O original permanece intacto.

## Contrato observado (`db.documentos`)
Cada documento é gravado com exatamente estes campos:
- `id`: `doc_` + timestamp.
- `pasta`: texto com o nome da categoria/pasta.
- `titulo`: obrigatório na interface.
- `nomeArquivo`: nome original do arquivo selecionado.
- `arquivoCompactadoGzip`: conteúdo compactado, codificado em Base64.

A pasta é armazenada pelo nome, não por ID. As opções vêm de `db.categorias`; se não houver categorias, a interface oferece Geral, Assembleias, Financeiro e Manutenção. A exclusão de uma categoria não atualiza os documentos que já guardam seu nome.

## Operações existentes
- Listagem mostra pasta, título e nome do arquivo.
- Inserção exige arquivo e título.
- Edição permite manter o arquivo existente ou selecionar outro; se nenhum novo arquivo for escolhido, o conteúdo anterior é preservado.
- Visualização descompacta o conteúdo e chama o visualizador genérico.
- Download descompacta e usa o nome original.
- Exclusão remove o registro da coleção, sem lixeira ou recuperação observada.

## Compactação e limitações
A função compartilhada lê o arquivo como ArrayBuffer, comprime os bytes com `pako.deflate`, converte o resultado para Base64 e armazena no registro. Para download/visualização, usa `pako.inflate` e cria um Blob. Apesar do rótulo da interface mencionar Gzip, a implementação usa `deflate`/`inflate`; não se deve presumir que os bytes sejam um fluxo Gzip padrão. Fotos do estoque usam a mesma rotina compartilhada.

O modelo original não registra tipo MIME, tamanho original, data de envio, usuário responsável, checksum, versão, estado de validação, política de retenção ou trilha de auditoria. Também não há limite explícito de tamanho no formulário. Armazenar binários Base64 no payload monolítico pode aumentar bastante o volume sincronizado e o custo de leitura/escrita.

## API sombra criada
- `GET /api/v1/documentos` lista documentos.
- `GET /api/v1/documentos/{id}` consulta um documento.
- `POST /api/v1/documentos` cria.
- `PUT /api/v1/documentos/{id}` atualiza.
- `DELETE /api/v1/documentos/{id}` exclui.
- Campos da API preservam `id`, `pasta`, `titulo`, `nomeArquivo` e `arquivoCompactadoGzip`.
- IDs novos usam prefixo `doc_shadow_` e UUID.
- Serviço em memória; ainda não há armazenamento de objetos, persistência, integração com frontend ou produção.

## Cuidados antes de migrar
1. Confirmar compatibilidade byte a byte do formato `pako.deflate` atual; não converter documentos em lote sem validação e cópia de segurança.
2. Migrar binários para armazenamento de objetos e manter no banco apenas metadados e chave do objeto, após decidir provedor e política de acesso.
3. Registrar MIME, tamanho, checksum, data/hora e usuário responsável.
4. Definir limites de tamanho, tipos permitidos e validação de conteúdo no servidor.
5. Proteger downloads/visualizações por autorização e links temporários, sem expor buckets públicos.
6. Definir exclusão recuperável ou retenção, com trilha de auditoria.
7. Resolver pastas por identificador estável em uma migração futura, preservando o nome legado e mapeando documentos órfãos.
8. Fazer migração piloto com amostras de PDFs, imagens e outros formatos, comparando hashes após descompactação.

## Testes
Testes automatizados foram escritos para CRUD, recuperação, preservação do conteúdo Base64 e validação de arquivo obrigatório. Não foram executados nesta etapa.