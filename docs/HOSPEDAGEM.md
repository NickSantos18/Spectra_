# Como publicar o Spectra

Guia curto para tirar o site do localhost. A documentação do projeto está no
[README.md](../README.md); o guia de ambiente, em [COMO-CONTINUAR.md](../COMO-CONTINUAR.md).

## GitHub Pages não serve

O Pages entrega **apenas arquivos estáticos** — HTML, CSS e JS. O Spectra é uma
aplicação de servidor: analisa links, consulta RDAP e DNS, autentica pessoas e
grava mensagens. Publicado no Pages, as páginas até carregariam, mas toda
chamada a `/api/...` daria 404 e nada funcionaria.

O GitHub hospeda o **código**. Para o site rodar, é preciso um serviço que
execute Python.

## O que o serviço precisa oferecer

| Requisito | Por quê |
|---|---|
| Executar Python 3.11+ | A aplicação é FastAPI sobre Uvicorn |
| Porta via variável `PORT` | Quase todo serviço define a porta assim |
| **Disco persistente ou banco externo** | Sem isso, os dados somem a cada deploy |
| HTTPS | O cookie de sessão exige, e o login do Google também |

Render, Railway e Fly.io atendem e fazem deploy direto do repositório GitHub.

## O ponto que mais importa: persistência

Hoje a aplicação grava num arquivo SQLite (`dados/spectra.db`), e a pasta
`dados/` está no `.gitignore`. Em hospedagem com disco efêmero — Render,
Railway ou Vercel sem volume montado — esse arquivo é **recriado a cada
deploy**. Na prática:

- As contas criadas somem.
- **As mensagens trocadas entre perfis somem.**
- Com mais de uma instância do servidor, cada uma teria o seu próprio arquivo
  e os perfis não se enxergariam.

Duas saídas:

1. **Volume persistente** no serviço escolhido, apontando `SPECTRA_BD` para
   dentro dele. Resolve o deploy, mas não o caso de múltiplas instâncias.
2. **Postgres gerenciado** (Supabase, por exemplo). Resolve os dois casos.
   É uma refatoração ampla: há 120 chamadas SQL em 12 arquivos, além de
   sintaxe exclusiva do SQLite a reescrever (marcadores `?`,
   `INSERT OR IGNORE`, `AUTOINCREMENT`).

## Variáveis de ambiente em produção

Obrigatórias:

```
SPECTRA_SEGREDO=<string longa e aleatória>
SPECTRA_ORIGEM_PUBLICA=https://seudominio
SPECTRA_COOKIE_SEGURO=1
SPECTRA_BD=<caminho no volume persistente>
```

`SPECTRA_SEGREDO` assina o cookie de sessão. Se mudar, todas as sessões caem —
gere uma vez e guarde.

Opcionais, cada uma liga um recurso hoje desligado:

```
SPECTRA_GSB_API_KEY=          # Google Safe Browsing
SPECTRA_VT_API_KEY=           # VirusTotal
SPECTRA_PHISHTANK_APP_KEY=    # PhishTank
GEMINI_API_KEY=               # assistente de IA (ou GROQ_API_KEY / ANTHROPIC_API_KEY)
SPECTRA_GOOGLE_CLIENT_ID=     # login com Google
SPECTRA_GOOGLE_CLIENT_SECRET=
SPECTRA_GOOGLE_REDIRECT=https://seudominio/auth/google/callback
```

## Login com Google em produção

O código valida a URL de retorno com rigor e **não ativa o botão** se ela não
terminar em `/auth/google/callback`, tiver query string, não for da mesma
origem de `SPECTRA_ORIGEM_PUBLICA`, ou não for HTTPS fora do localhost.

Cadastre no Google Cloud Console, em *OAuth client ID → Web application*, a URL
exatamente igual à que estiver em `SPECTRA_GOOGLE_REDIRECT`.

## Comando de inicialização

```bash
python -m uvicorn spectra_link_guard.web.app:app --host 0.0.0.0 --port $PORT
```

Instalação: `pip install -e ".[extras,web]"`.

**Atenção ao layout:** desde a separação em `backend/` e `frontend/`, o
servidor localiza o front pela árvore do repositório, não pelo pacote
instalado. Se for containerizar, o `Dockerfile` precisa copiar **`frontend/`
junto com `backend/`** — copiar só o pacote Python deixa o site sem HTML, CSS
nem JS.
