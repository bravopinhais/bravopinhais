# Ficha técnica — coleções da Fase 0 (lote 04)

**Escopo:** Pastas Gerais (categorias) e Motivos de Acerto de Estoque.  
**Fonte legada:** `index.html`, branch `bravo-shadow`, inspecionado sem alteração.  
**Status:** levantamento estático; nenhuma extração ou carga executada.

## 1. Pastas Gerais / Categorias

**Coleção legada:** `db.categorias[]`

| Campo | Uso legado observado | Shadow |
|---|---|---|
| `id` | texto, gerado como `cat_<timestamp>` | `id: str` |
| `nome` | texto obrigatório no formulário | `nome: str` |

**Operações legadas observadas:** listagem, criação e exclusão. Não foi localizado fluxo de edição no módulo. O módulo aparece na tela junto dos Motivos de Acerto, sob o título “Pastas Gerais”.

**Shadow:** schema contém `id` e `nome`; router oferece GET, POST e DELETE. O serviço gera `cat_shadow_<uuid>`. O serviço também possui verificação de referências a documentos e retorna conflito 409 quando a categoria está vinculada.

**Diferenças/gates:**
- O fluxo de criação Shadow gera ID novo; o mecanismo de carga deverá aceitar e preservar o ID legado.
- Não há PUT de edição no router Shadow, compatível com as operações localizadas no legado.
- A exclusão Shadow protege referências documentais, mas é necessário confirmar que a referência e o vínculo são equivalentes ao modelo real do legado antes de considerar a regra suficiente.
- A coleção é chamada de “categorias” no banco e “Pastas Gerais” na interface. Preservar o nome técnico e registrar o rótulo funcional.

## 2. Motivos de Acerto de Estoque

**Coleção legada:** `db.motivos_acerto_estoque[]`

| Campo | Uso legado observado | Shadow |
|---|---|---|
| `id` | texto, gerado como `mot_<timestamp>` | `id: str` |
| `nome` | texto obrigatório; exemplos no rótulo: “Perca, Quebra” | `nome: str` |

**Operações legadas observadas:** listagem, criação e exclusão com confirmação. Não foi localizado fluxo de edição. O cadastro usa apenas o campo `nome`.

**Shadow:** schema contém `id` e `nome`; router oferece GET, POST e DELETE. O serviço gera `mot_shadow_<uuid>` e possui verificação de referências a acertos de estoque, retornando conflito 409 se o motivo estiver em uso.

**Diferenças/gates:**
- A carga deve preservar IDs originais; o POST comum gera novos IDs.
- A proteção de exclusão no Shadow depende de um verificador de referências. Confirmar sua ligação com os registros reais de `acertos_estoque` e validar no banco local antes de liberar exclusões.
- A busca estática não encontrou nomes de propriedades evidentes como `categoriaId`, `motivoId` ou `pastaId` no `index.html`. Isso não prova ausência de vínculos: a estrutura completa de documentos e acertos deve ser examinada nos respectivos módulos e no payload JSON.

## 3. Observação sobre dados padrão

Na inicialização do legado, quando o cache local existe mas não contém `motivos_acerto_estoque`, o código preenche a coleção com `DEFAULT_DATA.motivos_acerto_estoque`. Esse comportamento é fallback de interface/cache e **não é evidência de que esses registros sejam dados reais de produção**. A extração deverá ler o payload persistido de origem e distinguir ausência de coleção, coleção vazia e valores padrão. Nunca importar `DEFAULT_DATA` como se fosse dado produtivo.

## 4. Regras de migração

1. Extrair `categorias[]` e `motivos_acerto_estoque[]` diretamente do JSON persistido, preservando IDs e nomes sem gerar identificadores substitutos.
2. Preservar texto original; normalização de espaços deve ser aplicada somente após registrar divergências e sem alterar silenciosamente o valor histórico.
3. Antes de permitir exclusão no destino, reconciliar vínculos com documentos e acertos de estoque.
4. Registrar contagens, IDs repetidos, registros sem nome, coleções ausentes e divergências entre origem e destino.
5. Implementar idempotência e rollback antes da primeira carga; não usar dados de demonstração e não acessar produção.

## 5. Evidências e limites

- Inspeção estática do `index.html`, SHA `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.
- Schemas, routers e services Shadow consultados na branch `bravo-shadow`.
- Não foram executados testes automatizados, validação em navegador ou ensaio de banco de dados.
