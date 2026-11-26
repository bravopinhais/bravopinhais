# Implantação portátil — Bravo Shadow

## Objetivo

Executar a interface web e a API Python no mesmo serviço, sem dependência da Vercel ou de outro fornecedor específico. O container usa Python 3.11, FastAPI/Uvicorn e serve os arquivos estáticos de `frontend/` na raiz HTTP; as rotas da API permanecem sob `/api/v1/`.

## Requisitos

- Docker Engine com suporte a Docker Compose opcional.
- Acesso ao código da branch `bravo-shadow`.
- Porta TCP 8000 disponível para o primeiro teste.

## Construir a imagem

Na raiz do repositório:

```bash
docker build -f bravo-shadow/Dockerfile -t bravo-shadow:local ./bravo-shadow
```

## Executar localmente

```bash
docker run --rm --name bravo-shadow -p 8000:8000 bravo-shadow:local
```

Acessos locais:

- Interface: http://localhost:8000/
- Saúde da API: http://localhost:8000/api/v1/health
- Documentação OpenAPI: http://localhost:8000/docs

Para encerrar, pressione Ctrl+C. O comando acima remove o container ao encerrar.

## Estado e limites de segurança

- O container seleciona explicitamente `BRAVO_STORAGE_BACKEND=memory`.
- Os dados são temporários e se perdem quando o processo/container é reiniciado.
- Não existe conexão com Supabase, banco de produção, autenticação Google validada ou autorização efetiva nesta etapa.
- Não inserir dados pessoais ou reais. Esta imagem é somente para demonstração e homologação visual.
- Não publicar a porta diretamente na internet. Uma implantação pública exigirá HTTPS, proxy reverso, política de CORS, identidade/autorização server-side, persistência validada, gestão de segredos, backups e revisão de segurança.
- O healthcheck confirma apenas que o endpoint HTTP de saúde responde; não valida banco de dados nem os fluxos dos módulos.

## Portabilidade

A imagem pode ser executada em qualquer host compatível com Docker. A Vercel deixa de ser requisito para executar este pacote. A escolha de VPS, domínio, proxy HTTPS e operação do servidor fica para uma etapa separada, após validação local.

## Próximas etapas antes de uso real

1. Construir a imagem e abrir a interface em ambiente local.
2. Fazer revisão visual e funcional em navegador.
3. Executar a suíte de testes Python e registrar o resultado.
4. Completar integração do frontend com a API.
5. Validar persistência em PostgreSQL local isolado, incluindo migrations e testes reais.
6. Implementar e auditar autenticação Google/e-mail e autorização por perfil.
7. Só então preparar implantação em servidor com HTTPS, backups, observabilidade e plano de reversão.
