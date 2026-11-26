# Inventário inicial do Bravo original

Fonte analisada: `index.html` da branch `upgrade/project-hardening`.
SHA do blob consultado: `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`.

## Fotografia técnica

- Um arquivo HTML principal com aproximadamente 208.790 caracteres.
- Seis tags `script`; o maior bloco JavaScript inline tem aproximadamente 198.983 caracteres.
- Dois blocos `style`.
- 69 declarações de funções nomeadas identificadas na extração inicial.
- Quatro chamadas `addEventListener` identificadas no bloco principal.
- Referência direta a `localStorage` e `sessionStorage`.
- Bibliotecas externas identificadas: Tailwind CDN, Chart.js, pako e Supabase JS v2.
- Um acesso direto à tabela Supabase `condominio_dados` identificado nesta primeira varredura.
- Nenhum ID HTML duplicado encontrado na varredura inicial.

## Capacidades identificadas por nomes de funções

- Persistência e sincronização: cache local, carregamento e gravação na nuvem.
- Navegação: abertura/fechamento de módulos e abas, menu móvel.
- Renderização: aplicação, conteúdo de módulo, dashboard e workspace.
- Exportação e backup: Excel, PDF, JSON e restauração.
- Dashboard e gráficos.
- Condomínio e plano de contas.
- Financeiro, formas monetárias e contas bancárias.
- Moradores, fornecedores e empregados.
- Categorias.
- Estoque, scanner, fotos, acertos e gráficos.
- Documentos e processamento de arquivos.
- Usuários e relatórios.

## Integração de dados observada

A leitura identificada consulta `condominio_dados`, registro `id = principal`, selecionando `payload`. A gravação usa `upsert` no mesmo registro e existe assinatura Realtime para mudanças nessa tabela.

O modelo atual aparenta concentrar o estado da aplicação em um payload amplo. É necessário mapear seu formato, tamanho, chaves, concorrência e regras de atualização antes de decidir se e como normalizar dados.

## Pontos ainda não auditados

- Estrutura completa de `DEFAULT_DATA` e de cada coleção.
- Todas as propriedades e relacionamentos dos registros.
- Regras de negócio e validações de cada formulário.
- Chamadas indiretas, dependências globais e funções chamadas dinamicamente.
- Políticas RLS, permissões e configuração real do Supabase.
- Fluxo efetivo de autenticação Google/e-mail e gerenciamento de sessão.
- Estratégia de concorrência e prevenção de sobrescrita do payload.
- Comportamento offline e recuperação de falhas.
- Cobertura de testes atual e fluxos críticos.

## Cuidados

Este documento é uma primeira varredura estática, não uma certificação funcional ou de segurança. Não alterar autenticação, dados ou schema com base apenas neste inventário. A implementação de autenticação deve preservar Google/e-mail, conforme requisito do projeto.
