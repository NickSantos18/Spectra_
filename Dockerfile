# Imagem de produção do Spectra Link Guard.
#
# Dois cuidados que não são óbvios e quebram o site se esquecidos:
#
# 1. frontend/ precisa vir junto. Desde a separação backend/frontend, o HTML,
#    o CSS e o JS moram fora do pacote Python; copiar só backend/ sobe um site
#    sem interface nenhuma.
#
# 2. A instalação precisa ser editável (pip install -e). O app.py localiza o
#    front subindo três níveis a partir de si mesmo (RAIZ_REPO em app.py).
#    Numa instalação comum o pacote iria para site-packages e esse caminho
#    apontaria para fora do projeto, onde frontend/ não existe.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    SPECTRA_BD=/dados/spectra.db

WORKDIR /app

# As dependências mudam menos que o código: instalar antes aproveita o cache
# de camadas a cada novo deploy.
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt

COPY pyproject.toml ./
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# --no-deps porque o lock acima já fixou tudo; -e mantém o pacote em
# /app/backend, que é o que faz RAIZ_REPO encontrar /app/frontend.
RUN pip install --no-cache-dir --no-deps -e .

# O banco fica fora de /app para poder ser um volume montado. Sem volume, os
# dados somem a cada deploy — contas e mensagens entre perfis inclusive.
RUN mkdir -p /dados \
    && useradd --create-home --uid 10001 spectra \
    && chown -R spectra:spectra /dados /app
USER spectra

VOLUME ["/dados"]
EXPOSE 8000

# sh -c para o $PORT do serviço de hospedagem ser expandido em tempo de execução.
CMD ["sh", "-c", "python -m uvicorn spectra_link_guard.web.app:app --host 0.0.0.0 --port ${PORT}"]
