# Mapa funcional dos módulos — Bravo Shadow

Fonte: inspeção estática de `index.html` na branch `upgrade/project-hardening`, blob `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`. Este mapa é inicial; campos e fluxos precisam ser confirmados em execução.

| Módulo original | Coleções/dados observados | Comportamentos identificados | Prioridade de descoberta |
|---|---|---|---|
| Dashboard | `financeiro`, `plano_contas`, `estoque`, `moradores`, `fornecedores`, `documentos` | Indicadores, panorama financeiro e gráficos | Alta |
| Condomínio & Conselho | `condominio`, `conselheiros` | Dados institucionais e concessionárias; corpo diretivo com nome/cargo obrigatórios e bloco/ap e telefone opcionais. CRUD inicial na sombra; auditoria em `auditoria-condominio-conselho.md` | Média |
| Plano de Contas | `plano_contas` | Código, nome, tipo; cadastro/edição/exclusão | Alta |
| Contas a Pagar / Receber | `financeiro`, `plano_contas` | Título com tipo, vínculo opcional, histórico e valor; cadastro/edição/exclusão. Auditoria detalhada em `auditoria-financeiro.md` | Alta |
| Formas Monetárias | `formas_monetarias` | Nome e percentual de multa (padrão 2%); CRUD. Auditoria em `auditoria-formas-monetarias-contas-bancarias.md` | Média |
| Contas Bancárias / Caixa | `contas_bancarias` | Banco e saldo manual; CRUD. Sem conciliação ou vínculo com títulos no original. Auditoria em `auditoria-formas-monetarias-contas-bancarias.md` | Alta |
| Moradores & Unidades | `moradores` | Bloco, apartamento e nome obrigatórios; contato, CPF/RG, pet e vaga opcionais; filtros por bloco/nome e importação em lote JSON (não upload XLSX/CSV). Auditoria em `auditoria-moradores-unidades.md` | Alta |
| Fornecedores | `fornecedores` | CNPJ e razão social obrigatórios; CRUD. Auditoria em `auditoria-fornecedores-empregados.md` | Média |
| Empregados | `empregados` | Nome e cargo obrigatórios; empresa, endereço, telefone e contato de emergência opcionais; CRUD. Auditoria em `auditoria-fornecedores-empregados.md` | Média |
| Pastas & Categorias | `categorias`, `motivos_acerto_estoque` | Pastas (`id`, `nome`) usadas textualmente em `documentos.pasta`; motivos (`id`, `nome`) sem vínculo por ID confirmado nos acertos. Auditoria em `auditoria-pastas-categorias-motivos.md` | Média |
| Estoque & Inventário | `estoque` | Cadastro, etiqueta, saldo, mínimo/máximo, foto Gzip, filtros e scanner; API sombra inclui marca, linha, fabricante e data de cadastro como extensão. Auditoria em `auditoria-estoque-inventario-acertos.md` | Alta |
| Acerto de Estoque | `acertos_estoque`, `estoque`, `motivos_acerto_estoque` | Entrada/saída atualiza saldo; histórico guarda produtoId, quantidade, tipo, data e motivo textual. Exclusão não estorna saldo no original. Auditoria em `auditoria-estoque-inventario-acertos.md` | Alta |
| Gestão de Documentos | `documentos`, `categorias` | Pasta textual, título, nome original e conteúdo deflate/Base64; visualizar, baixar, editar e excluir. Auditoria em `auditoria-gestao-documentos.md` | Média |
| Central de Relatórios & DRE | `financeiro`, `plano_contas` | DRE soma todos os títulos, sem filtro por data/status; totais gerais incluem títulos sem conta. Não equivale a caixa realizado | Alta |
| Gestão de Usuários | `usuarios` | Cadastro, perfis, edição, exclusão e administração de acesso | Crítica |

## Serviços transversais observados

- Persistência local via `localStorage` usando a chave `guardioes_bravo_db`.
- Sessão no navegador via `sessionStorage` usando a chave `guardioes_sessao`.
- Persistência em nuvem no registro `condominio_dados` (`id = principal`) com `payload`.
- Atualizações em tempo real via Supabase Realtime na mesma tabela.
- Backup e restauração geral em JSON.
- Exportação CSV e impressão/PDF.
- Compactação de anexos/fotos em gzip.
- Visualização e download de documentos.
- Gráficos Chart.js.
- Encerramento de sessão após 15 minutos de inatividade no frontend.

## Sequência recomendada de migração

1. **Contratos de dados e validações**: plano de contas, formas monetárias e contas bancárias (auditorias e CRUDs iniciais concluídos na sombra).
2. **Cadastros de referência**: fornecedores, empregados, condomínio e conselho auditados e com CRUD inicial na sombra.
3. **Moradores e unidades**: inclui importação, filtros e integridade de cadastro.
4. **Estoque e ajustes**: dependência entre produtos, categorias, motivos, fotos e documentos.
5. **Financeiro**: paridade inicial com os cinco campos encontrados; depois avaliar evolução funcional aprovada.
6. **Documentos**: arquivos, metadados, categorias e armazenamento.
7. **Dashboard e DRE**: reconstruir indicadores depois de validar as fontes de dados e explicitar limitações da soma atual.
8. **Gestão de usuários**: somente após definir e testar o contrato de identidade, autenticação e autorização atual.

A ordem poderá mudar conforme dependências reais e risco operacional.

## Lacunas para auditoria dinâmica

- Campos completos, obrigatoriedade, máscaras e validações de cada formulário.
- Regras de cálculo de saldos, multas, títulos e DRE.
- Relações por IDs e comportamento em exclusões.
- Regras de importação e tratamento de duplicidades.
- Tamanho e formato de imagens/documentos compactados.
- Concorrência: duas sessões podem atualizar o mesmo `payload`; investigar perda de atualização.
- Estratégia de conflito entre cache local e Supabase.
- Permissões por perfil e políticas RLS.
- Integração efetiva de login Google/e-mail.

## Segurança e autenticação — ponto de atenção

A varredura do HTML encontrou dados legados de usuários e lógica local de autenticação baseada em senha. Isso não será copiado para a versão sombra. O requisito vigente é preservar a identificação Google/e-mail. Antes de implementar o módulo de usuários, identificar no ambiente ativo o provedor real, os fluxos de sessão, os claims e as políticas de autorização. Não registrar nem transportar credenciais ou hashes legados.
