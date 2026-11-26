# Auditoria de paridade — Plano de Contas

## Fonte auditada
- Arquivo: `index.html`
- Branch: `upgrade/project-hardening`
- Blob SHA consultado: `873dbf37bbcf2082faa0444ac28cb9ca9f8ff21c`
- Escopo: renderização, formulário, salvamento, exclusão genérica e vínculo com Financeiro.

## Contrato observado no original

### Campos
| Campo | Comportamento observado |
|---|---|
| `id` | Gerado no navegador como `pc_` + timestamp para novo registro; preservado na edição |
| `codigo` | Campo texto obrigatório no formulário; exemplo visual `1.3`; sem máscara ou regra de formato no salvamento |
| `nome` | Campo texto obrigatório no formulário |
| `tipo` | Select com opções `Receita` e `Despesa`; padrão inicial `Despesa` |

O original não define limites de tamanho, normalização, formato hierárquico do código nem regra de unicidade no manipulador de salvamento. Portanto, os limites de 30/160 caracteres e a unicidade case-insensitive da API sombra são decisões adicionais, ainda não homologadas como regras de negócio do Bravo.

### Operações
- Listagem exibe Código, Nome da Conta, Tipo e ações.
- Ordenação explícita não foi identificada na função de renderização; a tela usa a ordem do array.
- Cadastro e edição fazem upsert local no array por `id`, depois chamam `salvarDados(db)` e redesenham o módulo.
- Exclusão usa o helper genérico `excluirRegistro('plano_contas', id)`, que remove pelo `id` após confirmação e salva o objeto completo.
- O helper genérico não verifica vínculo financeiro antes de remover a conta.

## Dependência com Financeiro e DRE
- Os títulos financeiros podem armazenar `planoContaId`.
- A tela Financeiro procura a conta pelo `id` e exibe “Não vinculada” se não encontrar.
- O formulário de título permite selecionar uma conta do Plano de Contas, mas a seleção não está marcada como obrigatória no HTML.
- A DRE soma valores por `planoContaId` quando a conta existe no conjunto atual; uma conta removida deixa de receber essa agregação por conta.
- O campo `tipo` da conta classifica a apresentação da DRE em Receita/Despesa; o tipo do título financeiro é Receber/Pagar e o cálculo geral da DRE usa o tipo do título.

## Riscos e decisões para a sombra
1. **Não tratar regras novas como paridade:** unicidade de código, limites de comprimento e ordenação por código foram introduzidos na API sombra, mas não aparecem como regras explícitas no salvamento original.
2. **Integridade referencial:** o original permite excluir uma conta sem verificar títulos que a referenciam. A sombra deve oferecer proteção contra exclusão de contas referenciadas, mas isso é uma melhoria deliberada e deve ser validada antes de qualquer promoção.
3. **Tipo da conta:** manter Receita/Despesa; não confundir com Receber/Pagar do título financeiro.
4. **Persistência:** o original grava o objeto agregado `db` na linha `condominio_dados`; a sombra ainda não deve conectar nem escrever nessa tabela.
5. **Autenticação:** não implementar senha local. A identidade Google/e-mail e autorização ficam fora deste piloto até auditoria própria, sem reintroduzir fluxo legado.

## Critérios de paridade antes de integrar a interface
- Confirmar se códigos duplicados existem nos dados atuais (somente em cópia de homologação autorizada).
- Confirmar se há títulos financeiros com `planoContaId` ausente ou órfão.
- Definir a política de exclusão: bloquear quando houver referência ou oferecer desativação lógica.
- Confirmar se a ordenação visual deve permanecer pela ordem de cadastro ou passar a ser por código.
- Testar Receita/Despesa contra Receber/Pagar e os resultados exibidos na DRE.

## Estado
Auditoria estática do código-fonte concluída para o fluxo descrito. Não houve acesso ao banco, execução do sistema em navegador ou validação com dados reais.
