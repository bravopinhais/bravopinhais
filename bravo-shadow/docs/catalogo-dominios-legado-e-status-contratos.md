# Catálogo de domínios do legado e estado dos contratos

**Status:** inventário estrutural; não é allowlist de importação e não autoriza leitura ou gravação em banco real.  
**Base de evidência:** objeto `DEFAULT_DATA` do `index.html` legado e contratos especializados já documentados no Shadow.  
**Regra:** nomes abaixo são chaves efetivamente observadas no objeto inicial do legado. A presença de uma chave não comprova que todos os registros reais tenham o mesmo formato.

## 1. Domínios observados

| Chave legada | Forma inicial observada | Situação do contrato |
|---|---|---|
| `condominio` | objeto singleton | Localizador da origem ainda manual; contrato de destino documentado, sem extração automática |
| `conselheiros` | lista | Campos de registro não catalogados; bloqueado para importação |
| `usuarios` | lista | Campos não catalogados integralmente; credenciais, hashes, senhas, tokens e dados de sessão são proibidos no pacote de migração |
| `plano_contas` | lista | Campos iniciais observados: `id`, `codigo`, `nome`, `tipo`; exige validação da coleção real e referências |
| `financeiro` | lista | Contrato especializado existente; permanece sujeito a reconciliação e revisão |
| `formas_monetarias` | lista | Campos não catalogados; bloqueado para importação |
| `contas_bancarias` | lista | Campos não catalogados; potencial dado financeiro/sensível; bloqueado para importação |
| `moradores` | lista | Campos não catalogados; contém potencial dado pessoal; exige minimização e revisão de privacidade |
| `fornecedores` | lista | Campos não catalogados; pode conter dados pessoais e bancários; bloqueado para importação |
| `empregados` | lista | Campos não catalogados; contém potencial dado pessoal e trabalhista; exige minimização e revisão de privacidade |
| `categorias` | lista | Campos não catalogados; bloqueado para importação |
| `estoque` | lista | Contrato especializado existente; fotos e quantidades exigem validação específica |
| `acertos_estoque` | lista | Contrato especializado existente; movimentos e referências exigem reconciliação |
| `motivos_acerto_estoque` | lista | Campos iniciais observados: `id`, `nome`; validar formato real e referências antes de qualquer uso |
| `documentos` | lista | Contrato especializado existente; conteúdo binário/compactado não pode ser tratado como texto comum |
| `logs` | lista | Campos não catalogados; potencial conteúdo pessoal e operacional; não importar por padrão |

A forma inicial acima descreve apenas o valor padrão do código. Ela não é prova da forma de dados persistidos na nuvem nem substitui uma amostra sintética validada.

**Achado adicional no `DEFAULT_DATA`:** as listas `conselheiros`, `formas_monetarias`, `contas_bancarias`, `moradores`, `fornecedores`, `empregados`, `categorias` e `logs` são inicializadas vazias (`[]`). Portanto, o código padrão não fornece nenhum campo ou tipo de registro para esses oito domínios. A classificação correta é `schema_unobserved_empty_default`; isso não significa que a coleção persistida esteja vazia. É proibido deduzir seu esquema apenas pela interface ou pelo nome da coleção.

## 2. Contratos especializados existentes

Há contratos conservadores específicos para:

- `financeiro`;
- `documentos`;
- `estoque`;
- `acertos_estoque`.

Esses contratos descrevem campos observados e bloqueadores, mas uma avaliação de formato compatível continua exigindo revisão semântica. Não representam autorização para importar.

O objeto `condominio` é tratado separadamente como singleton e precisa de localização explícita no snapshot. Não se deve fabricar uma lista ou identificador para encaixá-lo no scanner de coleções.

## 3. Regras transversais obrigatórias

1. Não copiar `senhaHash`, senha em texto, credenciais antigas, tokens, cookies, segredos, chaves de API ou dados de autenticação para o Shadow.
2. Não presumir que o login legado representa a autenticação atual. A identidade no Shadow continua baseada em Google e vínculo com uma conta interna ativa.
3. Não importar dados pessoais de moradores, empregados, fornecedores ou conselheiros sem contrato de campos, finalidade, minimização e revisão específica.
4. Não interpretar números financeiros ou quantidades como valores exatos sem regra decimal documentada.
5. Não descartar silenciosamente campos desconhecidos, mesmo quando pareçam metadados. Campo inesperado bloqueia o registro/lote até decisão documentada.
6. Distinguir chave ausente, `null`, string vazia, zero e `false`; não aplicar defaults durante a migração.
7. Preservar identificadores como texto, inclusive zeros à esquerda.
8. Referências entre coleções devem ser resolvidas por correspondência exata e única. Referências órfãs ou ambíguas ficam pendentes.
9. Documentos e fotos exigem validação de Base64, codec, tamanho e hash em ambiente descartável. Não exibir nem registrar conteúdo.
10. Relatórios de inventário devem conter somente nomes de campos, tipos agregados, contagens e códigos de problema; nunca valores, identificadores ou trechos de registros.

## 4. O que falta para habilitar cada domínio

Para cada domínio sem contrato especializado, a próxima etapa é obter evidência estrutural sintética ou anonimizada, confirmar os campos e tipos por ocorrência, documentar referências e classificar campos sensíveis. Só então poderá ser proposta uma allowlist versionada com testes positivos e negativos.

Não é permitido inferir uma allowlist completa a partir de `DEFAULT_DATA`, de nomes de campos isolados ou de exemplos de interface.

## 5. Estado de segurança

- Pacote de evidências: valida cadeia estrutural e hashes; não faz varredura semântica completa de valores arbitrários.
- Catálogo deste documento: inventário de domínios e bloqueadores; não é validador.
- CLI de exportação/importação: não autorizada por este documento.
- Banco real, dados reais e escrita de destino: fora do escopo.
- Próxima homologação: exclusivamente fixtures sintéticas em PostgreSQL descartável.

**Conclusão:** o catálogo reduz o risco de omitir domínios, mas ainda não há allowlist completa. O processo permanece bloqueado para dados reais até contratos e testes específicos cobrirem cada domínio.
