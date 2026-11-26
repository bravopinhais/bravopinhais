# Frontend — identidade visual Bravo Shadow

## Direção visual

A interface deve ser reconhecível como Bravo: modo noturno fixo, visual profissional e navegação integrada. A evolução será de refinamento, não uma ruptura de identidade.

## Tokens iniciais

| Token | Valor | Uso |
|---|---|---|
| Fundo principal | #111315 | Fundo geral |
| Superfície 1 | #191d20 | Sidebar e painéis |
| Superfície 2 | #202529 | Cards e áreas elevadas |
| Superfície 3 | #272e33 | Hover e controles |
| Texto principal | #edf1f3 | Títulos e dados |
| Texto secundário | #c2cbd0 | Conteúdo de apoio |
| Texto suave | #929da4 | Metadados |
| Borda | #343d43 | Separadores |
| Borda forte | #465159 | Contornos de destaque |
| Acento | #36b7a5 | Ações e estados ativos |

## Regras de experiência

- Modo noturno fixo, sem alternância para tema claro.
- Sidebar, dashboard, abas e área de trabalho devem compartilhar a mesma linguagem visual.
- Uma única navegação global e um único workspace; módulos são áreas internas da mesma aplicação.
- Cards, tabelas, filtros, formulários, modais e estados vazios devem reutilizar tokens e componentes.
- Hierarquia tipográfica clara, espaçamento consistente e animações discretas.
- Responsividade para desktop, tablet e celular.
- Foco visível, contraste adequado e navegação por teclado.
- Evitar fundos brancos, gradientes decorativos excessivos e duplicação de cabeçalhos/abas.

## Estado

Este documento define o contrato visual. A interface será construída após o inventário de fluxos e componentes do original, evitando criar telas fictícias ou controles sem funcionalidade.


## Primeiro módulo conectado à API

O módulo **Formas Monetárias** já utiliza a API relativa `/api/v1/formas-monetarias` para listar, cadastrar, editar e excluir registros. A interface apresenta estados de carregamento e erro, valida o nome e a multa (0–100%) e escapa os valores exibidos.

O backend deste módulo ainda utiliza armazenamento em memória. Os registros são exclusivos do processo do ambiente sombra e são perdidos quando ele reinicia. Isso não é persistência definitiva nem integração com o banco de produção.

Os demais módulos continuam identificados como estrutura visual até que seus contratos e fluxos sejam conectados individualmente.
