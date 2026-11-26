# Integridade entre Plano de Contas, Financeiro e DRE

## Evidência no original
A rotina genérica `excluirRegistro(col, id)` apenas filtra o registro do array indicado, salva o objeto agregado e redesenha a tela. Não verifica se há lançamentos em `financeiro` com `planoContaId` igual ao ID da conta removida.

O formulário financeiro permite escolher uma conta e grava o vínculo em `planoContaId`. O vínculo é opcional. As telas consultam esse vínculo para mostrar código/nome; quando a conta não existe, o Financeiro exibe “Não vinculada”. Portanto, excluir uma conta referenciada pode romper a identificação histórica, mesmo que o lançamento permaneça.

## Contrato financeiro identificado
O formulário original grava `id`, `tipo` (`Receber` ou `Pagar`), `planoContaId` (opcional), `historico` e `valor`. A auditoria completa está em `auditoria-financeiro.md`.

## Proteção aplicada na API sombra
A exclusão agora segue o princípio *fail closed*:
- Conta inexistente: HTTP 404.
- Verificador financeiro ainda não configurado: HTTP 503 e o registro permanece.
- Verificador confirma vínculos: HTTP 409 e o registro permanece.
- Verificador confirma ausência de vínculos: exclusão permitida.

O serviço recebe um verificador `has_financial_references(account_id)`. No estado atual, o serviço global da API não possui repositório financeiro conectado; por isso a rota de exclusão fica deliberadamente indisponível (503), em vez de presumir que a conta está sem vínculos.

## Efeitos no Dashboard e na DRE
No original, Dashboard e DRE somam todos os títulos sem filtro por data ou status. A classificação geral usa o tipo do título; a DRE agrupa por conta vinculada. Títulos sem conta entram nos totais gerais, mas não em linhas por conta. A soma por conta não confere se o tipo do título coincide com o tipo cadastrado na conta. O indicador “Saldo em Caixa” é apenas Receber menos Pagar, não um saldo bancário conciliado. Essas regras e limitações devem ser mantidas como referência de paridade até aprovação de uma mudança funcional.

## Limite atual
Ainda não existe módulo/repositório financeiro na sombra. A proteção é uma barreira de segurança e um contrato testável, não uma consulta real a lançamentos. A próxima etapa é modelar o domínio Financeiro e ligar o verificador ao repositório de homologação, com integridade referencial no banco (chave estrangeira ou política equivalente).

## Testes adicionados
- Exclusão bloqueada quando o verificador não está configurado.
- Exclusão bloqueada quando existem referências.
- Exclusão permitida quando a verificação confirma ausência de referências.

Os testes foram escritos, mas não executados neste ambiente.
