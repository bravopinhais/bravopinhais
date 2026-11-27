# Baseline atual de paridade — Bravo produção x Shadow

Data da inspeção: 2026-11-27.

Este documento complementa `matriz-equivalencia-modulos.md`. A matriz anterior usa uma fotografia histórica do legado; esta atualização registra a versão atualmente presente na branch `main`, sem alterar essa branch.

## Fontes e limites

| Artefato | Branch | Blob SHA | Observação |
|---|---|---|---|
| `index.html` | `main` | `2f55d89b14ce45e1df643fe4af5a1218704fdb71` | HTML principal atual, aproximadamente 2.045.415 caracteres |
| `bravo-shadow/frontend/index.html` | `bravo-shadow` | `d06eb5cfc4d9f9d83b666fb73e7e8163ee98a526` | Interface sombra, aproximadamente 33.447 caracteres |
| `bravo-shadow/backend/app/modules/` | `bravo-shadow` | Inspeção do diretório | Routers de domínio listados abaixo |

Inspeção estática de código versionado. Não houve login, navegação em navegador, leitura de dados de produção, consulta ao banco, execução de SQL, migração, deploy ou alteração da branch `main`.

## Módulos presentes na navegação atual de produção

A navegação principal identificada no `index.html` atual contém estes 17 módulos:

1. Dashboard Executivo (`dashboard`)
2. Dados do Condomínio (`condominio`)
3. Plano de Contas (`plano_contas`)
4. Pagar / Receber (`financeiro`)
5. Formas Monetárias (`formas_monetarias`)
6. Contas Bancárias (`contas_bancarias`)
7. DRE & Relatórios (`relatorios`)
8. Moradores & Unidades (`moradores`)
9. Fornecedores (`fornecedores`)
10. Empregados (`empregados`)
11. Estoque & Fotos (`estoque`)
12. Acerto de Estoque (`acerto_estoque`)
13. Compras x Consumo (`compras_consumo`)
14. Pastas (`categorias`)
15. Documentos Gzip (`documentos`)
16. Configurações (`configuracoes`)
17. Utilizadores (`usuarios`)

O HTML também contém atalhos contextuais para Dashboard, Financeiro, Moradores e Estoque; esses atalhos não são módulos adicionais. Conselho e motivos de acerto aparecem como cadastros/áreas auxiliares dos módulos correspondentes.

## Recursos transversais existentes na versão atual

A paridade não se limita às telas CRUD. A inspeção identificou recursos que também precisam ser inventariados, preservados e homologados:

### Identidade, sessão e acesso
- Fluxo de identidade Google/e-mail adotado pelo sistema atual e recuperação segura da sessão.
- Primeiro acesso, encerramento de sessão e controle de inatividade.
- Recuperação de conexão e revalidação da sessão.
- Controles de acesso e ativação/desativação de módulos.

**Regra do Shadow:** manter Google como provedor de identidade, validar a identidade no servidor e obter perfil/permissões exclusivamente do cadastro interno Bravo. Não reintroduzir login local por senha.

### Persistência, sincronização e operação offline
- Cache local/offline.
- Carregamento e gravação na nuvem.
- Sincronização em tempo real.
- Fila de gravações pendentes, detecção de divergência e recuperação de conexão.
- Histórico de sincronização e painel de falhas.

Esses recursos precisam de desenho equivalente no Shadow, com persistência transacional e resolução explícita de conflitos. Não conectar o Shadow ao banco de produção nem fazer dual write.

### Backup e recuperação
- Backup geral JSON e restauração.
- Backup criptografado e restauração criptografada.
- Backups automáticos locais e recuperação de cópia.
- Integridade/hash e histórico das operações de backup.

A implementação Shadow deve manter backup/restore compatíveis e testáveis, mas nunca transportar credenciais ou segredos para o navegador.

### Segurança, auditoria e administração
- Histórico de atividades.
- Diagnóstico/saúde do sistema.
- Configuração e ativação de funcionalidades/módulos.
- Proteções de sessão e recuperação.
- Auditoria de alterações e estado de sincronização.

A trilha de auditoria do Shadow deve registrar ator, ação, alvo, horário e resultado sem armazenar tokens, senhas ou payloads sensíveis desnecessários.

### IA e assistente
- Assistente Gemini e configuração da integração.
- Interpretação assistida de informações do Dashboard.
- Geração de relatórios/resumos assistidos.
- Diagnóstico e teste da integração.

A paridade desse recurso exige integração server-side, controle de segredo, permissões e limites de uso. Não expor chave de IA no frontend; manter o recurso desabilitado até existir configuração segura e aprovada.

### Arquivos, fotos e documentos
- Anexos e fotos com compactação.
- Upload/armazenamento externo, URLs assinadas e recuperação.
- Visualização e download de documentos.
- Tratamento de anexos órfãos e otimização de imagens.

O Shadow precisa preservar conteúdo, nome original, MIME, tamanho, associação ao registro e permissões. Não basta manter apenas o texto/base64 se o legado utiliza armazenamento externo.

### Exportação, importação e apresentação
- Exportação para Excel e PDF/impressão.
- Importação de planilha de moradores.
- Gráficos e indicadores do Dashboard/Estoque.
- Filtros rápidos e por coluna, ordenação, organização persistente de colunas e paginação.
- Abas de módulos, fechamento de abas e navegação móvel.
- PWA e layout responsivo.
- Animações e preferências visuais.

Esses comportamentos são parte do produto, não detalhes descartáveis. Devem ser avaliados por fluxo e por módulo.

### Recursos específicos de Estoque
- Fotos dos produtos e cache/otimização.
- Etiquetas e códigos de barras.
- Scanner por câmera e alternativa de digitação manual.
- Setores/localização, níveis mínimo/máximo e status.
- Checklist de vistoria/entrega/devolução.
- Relatórios por setor.
- Acertos de entrada/saída e histórico.
- Compras x Consumo.
- Campos adicionais solicitados para rastreabilidade: marca, linha, fabricante e data de cadastro.

Os quatro campos de rastreabilidade são extensões solicitadas para o Shadow, mesmo que não façam parte do formulário original observado na auditoria histórica.

## Situação observada no Shadow nesta baseline

### Interface

A navegação do Shadow contém 15 chaves: `dashboard`, `condominio`, `plano_contas`, `financeiro`, `formas_monetarias`, `contas_bancarias`, `moradores`, `fornecedores`, `empregados`, `categorias`, `estoque`, `acerto_estoque`, `documentos`, `relatorios` e `usuarios`.

Diferenças imediatas de navegação: ainda faltam `compras_consumo` e `configuracoes`.

- **Formas Monetárias:** único módulo com chamadas de API identificadas na interface; CRUD conectado ao endpoint, mas o armazenamento desse módulo permanece em memória. Não é persistência definitiva.
- **Dashboard:** estrutura visual inicial; não equivale aos indicadores, gráficos e ações do Dashboard de produção.
- **Usuários:** painel de pré-requisitos; operações ficam bloqueadas até concluir identidade Google, API HTTPS e matriz de capacidades.
- **Demais módulos:** cartões/estrutura visual inicial; os fluxos operacionais completos do sistema atual ainda não foram migrados para a interface Shadow.

### Backend

Routers encontrados em `bravo-shadow/backend/app/modules/`:

`acertos_estoque`, `auth`, `categorias`, `condominio`, `conselheiros`, `contas_bancarias`, `dashboard`, `documentos`, `empregados`, `estoque`, `financeiro`, `formas_monetarias`, `fornecedores`, `moradores`, `motivos_acerto`, `plano_contas` e `usuarios`.

Lacunas de domínio identificadas em relação à navegação atual: não há router dedicado para `compras_consumo`, `relatorios` ou `configuracoes`. Algumas dessas áreas poderão ser serviços de leitura ou configuração, não necessariamente CRUDs próprios; a decisão deve respeitar as regras atuais e as dependências reais.

A presença de um router ou serviço não comprova paridade de interface, persistência pronta, homologação funcional ou implantação. A API ainda precisa de ambiente independente, persistência configurada, autenticação conectada e homologação.

## Matriz de prioridade para completar paridade

| Prioridade | Entrega | Critério para considerar concluída |
|---|---|---|
| P0 | Inventário detalhado dos 17 módulos | Campos, formulários, ações, filtros, regras, relatórios e permissões comparados com o atual |
| P0 | Login Google e sessão | Fluxo completo no navegador com API HTTPS independente e usuário interno ativo |
| P0 | Persistência e auditoria | Operações transacionais, trilha auditável, backup e recuperação sem tocar produção |
| P1 | Cadastros e módulos operacionais | CRUDs e regras equivalentes, com erros, estados vazios, filtros e paginação |
| P1 | Estoque, acertos e compras x consumo | Saldos, scanner, fotos, setores, checklist, histórico e relatórios preservados |
| P1 | Financeiro, Plano de Contas, DRE e relatórios | Fórmulas, vínculos, períodos e limitações reproduzidos sem inventar dados |
| P1 | Documentos e anexos | Upload, armazenamento, visualização, download, metadados e autorização |
| P2 | Sincronização, offline e recuperação | Fila, conflitos, reprocessamento seguro, estado de conexão e reconciliação |
| P2 | Backup criptografado e exportações | JSON, backup criptografado, Excel, PDF e restauração homologados |
| P2 | IA, saúde, notificações e preferências | Recursos equivalentes com segredos protegidos e controles administrativos |
| P2 | PWA, responsividade e detalhes de interface | Experiência móvel, abas, filtros, rolagem e acessibilidade preservados |

## Regra de aceite

Um módulo só poderá receber status **paridade concluída** quando:
1. Todos os campos e ações relevantes do original estiverem mapeados.
2. As regras de negócio e validações estiverem documentadas.
3. A interface Shadow executar os fluxos completos, não apenas exibir um cartão.
4. API, autorização, persistência e auditoria estiverem integradas.
5. Filtros, pesquisa, paginação, ordenação, exportações e estados de erro aplicáveis estiverem presentes.
6. Houver evidência de homologação isolada e comparação de resultados com dados sintéticos/anonimizados.

Não remover nem simplificar recursos para acelerar a migração. Melhorias podem ser acrescentadas, mas diferenças comportamentais precisam ser registradas e aprovadas antes do aceite.

## Próxima ação técnica

Usar esta baseline para atualizar a matriz de equivalência, concluir o inventário campo a campo e priorizar os fluxos de maior dependência: identidade/sessão, persistência, cadastros de referência, estoque/acertos, financeiro e documentos. O sistema original permanece intacto; nenhum deploy ou corte é autorizado por este documento.
