"""Gera inventário técnico em PDF pesquisável, usando somente a biblioteca padrão."""
from pathlib import Path
import ast
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'Spectra-tecnologias-utilizadas.pdf'
PAGES = []


def esc(s):
    return ''.join(chr(b) if 32 <= b < 127 and chr(b) not in '()\\' else f'\\{b:03o}'
                   for b in s.encode('cp1252', errors='replace'))


def page(title, blocks):
    ops = []
    def txt(x, y, s, size=10, bold=False, color='0.10 0.18 0.25'):
        ops.append(f'BT /F{2 if bold else 1} {size} Tf {color} rg 1 0 0 1 {x} {842-y} Tm ({esc(s)}) Tj ET')
    txt(44, 40, 'SPECTRA  /  INVENTÁRIO DE TECNOLOGIAS', 10, True, '0.02 0.44 0.48')
    txt(44, 78, title, 22, True)
    ops.append('0.7 0.8 0.83 RG 44 748 m 551 748 l S')
    y = 119
    for heading, body in blocks:
        if y > 720:
            raise ValueError(f'Página cheia: {title}')
        txt(44, y, heading, 12, True)
        y += 19
        for paragraph in body.split('\n'):
            for line in textwrap.wrap(paragraph, width=94, break_long_words=True):
                txt(44, y, line)
                y += 14
            y += 3
        y += 12
    txt(44, 812, 'Código local analisado em 29/10/2026 | Versões conforme arquivos do projeto', 8)
    txt(518, 812, str(len(PAGES) + 1), 9)
    PAGES.append('\n'.join(ops).encode('ascii'))


page('Visão geral do projeto', [
    ('O que este documento apresenta', 'Inventário das linguagens, bibliotecas, protocolos, integrações e ferramentas identificadas no código do Spectra Link Guard. Cada tecnologia é relacionada ao seu uso e aos arquivos que comprovam sua presença.'),
    ('Arquitetura', 'Navegador (HTML, CSS e JavaScript) > requisições HTTP/JSON > aplicação FastAPI em Python > banco SQLite e serviços externos. Uvicorn executa a aplicação ASGI. O analisador de links também pode ser utilizado por linha de comando.'),
    ('Como interpretar as versões', 'pyproject.toml define versões mínimas e grupos opcionais. requirements-lock.txt fixa versões de um ambiente validado em 24/10/2026. package.json fixa ferramentas de estilos. Essas declarações não comprovam a versão instalada nem que um serviço externo esteja habilitado.'),
    ('Fontes utilizadas', 'pyproject.toml; package.json; requirements-lock.txt; tailwind.config.cjs; código em src/spectra_link_guard; testes em tests; automações em scripts. O levantamento usa o repositório local, sem consultar dados de usuários ou credenciais.'),
    ('Mapa de leitura', 'Páginas seguintes: backend e dados; interface; segurança e identidade; integrações; ferramentas e testes; dependências fixadas e módulos nativos. Componentes opcionais e arquivos legados são identificados separadamente.'),
])
page('Backend e armazenamento', [
    ('Python 3.11 ou superior', 'Linguagem principal do servidor, do analisador de links, dos scripts e dos testes. Usa tipagem, dataclasses e enums para representar análises e sinais de risco. Fontes: pyproject.toml; models.py; analisador.py.'),
    ('FastAPI, Starlette e Uvicorn', 'FastAPI cria rotas de API e páginas; Starlette fornece a base ASGI, respostas e recursos HTTP. Uvicorn serve a aplicação. Versões fixadas: FastAPI 0.162.0, Starlette 1.10.0 e Uvicorn 0.54.0. Fontes: web/app.py; auth/rotas.py; requirements-lock.txt.'),
    ('Pydantic e validação de e-mail', 'Pydantic valida corpos de requisição, tipos e limites por BaseModel e Field. EmailStr usa email-validator. Versões fixadas: Pydantic 2.14.1 e email-validator 2.3.0. Fontes: auth/rotas.py; web/app.py.'),
    ('SQLite e SQL', 'Banco embarcado acessado diretamente por sqlite3. Guarda contas, sessões, análises, publicações, respostas, conexões, mídias e outros registros. O código define tabelas, índices, chaves e consultas SQL; imagens também são armazenadas como BLOB. Fontes: auth/bd.py; web/analises.py; web/comunidade.py; web/explorar.py.'),
    ('HTTPX e asyncio', 'HTTPX 0.28.1 realiza chamadas HTTP para serviços externos. asyncio organiza operações assíncronas e trabalho de rede; locks e semáforos limitam concorrência em pontos do servidor. Fontes: rede.py; reputacao.py; auth/google.py; web/app.py.'),
    ('Pillow', 'Pillow 13.0.0 lê, valida e processa imagens enviadas à comunidade. Também é utilizado no gerador de documentação de modelagem. Fontes: web/midias.py; scripts/gerar_modelagem_pdf.py.'),
])
page('Interface e recursos do navegador', [
    ('HTML, CSS e JavaScript', 'Páginas HTML com JavaScript nativo e estilos CSS. O servidor monta parciais e injeta ativos; a interface usa DOM, eventos, Fetch e JSON. CSS inclui variáveis de tema, layouts responsivos e animações. Fontes: web/static; web/parciais; web/app.py.'),
    ('Tailwind CSS e plugin de formulários', 'Tailwind CSS 3.4.19 gera utilitarios.css a partir de styles/tailwind.css. @tailwindcss/forms 0.5.11 ajusta controles de formulários. A configuração liga cores às variáveis CSS do projeto. Fontes: package.json; tailwind.config.cjs.'),
    ('Chart.js e Lucide', 'Chart.js 4.4.4 apresenta gráficos no laudo e na visão geral. Lucide 0.462.0 fornece ícones SVG. As páginas carregam essas bibliotecas por CDN (jsDelivr e unpkg). Fontes: static/laudo.html; static/visao-geral.html; static/comunidade.html.'),
    ('Fontes e desenho', 'Google Fonts carrega Hanken Grotesk, Inter e JetBrains Mono. Canvas 2D desenha efeitos e apoia a edição de foto; SVG é utilizado em ícones e elementos gráficos. Fontes: static/comunidade.html; static/fundo.js; static/foto-editor.js.'),
    ('APIs nativas e acessibilidade', 'localStorage e sessionStorage guardam preferências e estados de interface. requestAnimationFrame, IntersectionObserver e ResizeObserver controlam desenho e visibilidade. matchMedia adapta o movimento; atributos ARIA e foco apoiam navegação acessível. Fontes: acessibilidade.js; movimento.js; menu.js; fundo.js.'),
    ('Three.js e anime.js: arquivo legado', 'static/cubos.js contém imports de Three.js, anime.js e recursos associados. Não foi encontrada referência a cubos.js nos HTML ou no montador atual de páginas. Sua presença representa código disponível no repositório, sem evidência de carregamento nas telas atuais.'),
])
page('Segurança e autenticação', [
    ('Argon2id e compatibilidade scrypt', 'argon2-cffi 25.1.0 gera e verifica hashes de senha Argon2id. hashlib.scrypt permanece para validar hashes antigos e permitir atualização. Fontes: auth/seguranca.py; auth/rotas.py.'),
    ('HMAC, SHA-256, tokens e cookies', 'hashlib, hmac e secrets sustentam assinaturas, hashes e tokens aleatórios. As sessões usam cookies e registros no SQLite. A assinatura protege a integridade do valor do cookie. Fontes: auth/seguranca.py; auth/fluxos.py; auth/bd.py.'),
    ('Google OAuth 2.0 e OpenID Connect', 'Login Google com fluxo de autorização e validação de ID token pelo google-auth 2.62.0, incluindo o transporte Requests. É uma integração configurável. Fontes: auth/google.py; docs/CONFIGURAR-GOOGLE.md.'),
    ('TLS, SSL e certificados X.509', 'ssl e socket fazem conexões e inspeção de certificados. cryptography 50.0.2 é opcional para leitura X.509, inclusive em situações em que a cadeia não valida. Fontes: tls.py; saida.py; pyproject.toml.'),
    ('Proteções da aplicação', 'Código próprio implementa verificações de origem, políticas HTTP/CSP com nonce, controle de acesso por papel e limites de requisições e concorrência. Não são produtos externos separados. Fontes: web/protecao.py; auth/protecao.py; auth/papeis.py; web/app.py.'),
    ('URLs, domínios e saída de rede', 'urllib.parse, ipaddress, socket, re e unicodedata apoiam normalização, resolução e validação. tldextract 5.4.0 é opcional e utiliza a Public Suffix List; há alternativa embutida. O módulo saida.py valida destinos públicos. Fontes: sintaxe.py; saida.py.'),
])
page('Integrações e comunicação', [
    ('Google Safe Browsing, VirusTotal e PhishTank', 'Consultas de reputação de URLs implementadas em reputacao.py. O código contém os endpoints Safe Browsing v4, VirusTotal v3 e PhishTank. O uso depende da configuração e das credenciais aplicáveis; sua existência no código não comprova ativação.'),
    ('RDAP e DNS sobre HTTPS', 'rede.py consulta rdap.org para dados de domínio e IP e cloudflare-dns.com/dns-query para resolução DNS via HTTPS. A análise também utiliza resolução de rede por socket. Protocolos: RDAP, DNS, HTTPS e TLS.'),
    ('Anthropic / Claude: opcional', 'O grupo ia declara anthropic>=1.12. web/assistente.py integra respostas em streaming para os assistentes do site. O identificador padrão configurado no código é claude-opus-5-5, substituível por variável de ambiente; não foi verificada disponibilidade externa. A biblioteca não consta no requirements-lock.txt atual.'),
    ('Streaming HTTP e consultas periódicas', 'StreamingResponse entrega a resposta do assistente progressivamente. As conversas da comunidade atualizam mensagens por consultas periódicas do navegador. A dependência websockets do ambiente não significa que o chat utilize WebSocket. Fontes: web/app.py; static/comunidade.js.'),
    ('SMTP e e-mail', 'smtplib, email.message e ssl permitem enviar mensagens relacionadas à conta, conforme configuração SMTP. Fontes: auth/correio.py; auth/fluxos.py.'),
    ('Formatos usados', 'JSON nas APIs; HTML/CSS/JS na interface; SQL e BLOB no banco; formatos de imagem tratados pelo Pillow; TOML na configuração Python; JSON no package.json; YAML nos arquivos pnpm; PDF na documentação. Variáveis de ambiente configuram serviços e segredos.'),
])
page('Desenvolvimento, testes e automação', [
    ('pytest e TestClient', 'pytest 9.1.1 executa testes Python. FastAPI/Starlette TestClient exercita rotas e sessões, e testes usam monkeypatch e ambientes isolados. Fontes: tests/test_auth.py; tests/test_comunidade.py; tests/test_explorar.py; tests/conftest.py.'),
    ('Node.js e testes JavaScript', 'Node.js executa ferramentas de estilos e scripts .cjs. node:test e node:assert verificam JavaScript; node:vm ajuda a simular o ambiente de execução. Fontes: tests/fundo.test.cjs; tests/foto_editor.test.cjs.'),
    ('Microsoft Edge headless e CDP', 'scripts/verificar_explorar.cjs abre Edge sem interface e controla o navegador pelo Chrome DevTools Protocol usando WebSocket. Verifica páginas, interações e adaptação ao celular com banco e perfil isolados. WebSocket aqui pertence à automação de testes.'),
    ('setuptools, pip, npm e pnpm', 'setuptools>=68 é o backend de build Python. pyproject.toml define pacote, extras e comando spectra-link-guard. requirements-lock.txt registra dependências fixadas. package.json define build:css; pnpm-lock.yaml e pnpm-workspace.yaml registram configuração do ecossistema Node.'),
    ('Git, GitHub e PowerShell', 'O script scripts/sincronizar.ps1 usa Git para criar commits e enviar alterações ao GitHub; seus comentários descrevem execução por tarefa agendada do Windows. A existência do script não confirma que a tarefa esteja ativa.'),
    ('CLI e documentação', 'argparse organiza o comando de análise por terminal; json serializa resultados. scripts/gerar_modelagem_pdf.py usa AST, SQLite em memória e Pillow para documentar o banco. Este inventário é gerado por scripts/gerar_tecnologias_pdf.py em PDF vetorial com texto selecionável.'),
])

locked = [line for line in (ROOT / 'requirements-lock.txt').read_text(encoding='utf-8').splitlines()
          if line and not line.startswith('#')]
for i in range(0, len(locked), 24):
    page('Apêndice: versões fixadas', [
        ('Inventário do requirements-lock.txt', 'Lista literal de dependências diretas e transitivas do ambiente registrado. Bibliotecas de suporte não representam funcionalidades independentes implementadas pelo projeto.'),
        ('Pacotes e versões', '\n'.join(locked[i:i+24])),
        ('Interpretação', 'O inventário acima descreve o arquivo de versões do repositório. O grupo opcional de IA e as dependências de frontend foram descritos nas páginas anteriores.'),
    ])

imports = set()
for path in (ROOT / 'src').rglob('*.py'):
    for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
        if isinstance(node, ast.Import):
            imports.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module.split('.')[0])
import sys
native = sorted(imports & sys.stdlib_module_names - {'__future__'})
page('Apêndice: módulos nativos Python', [
    ('Levantamento automático dos imports', ', '.join(native) + '.'),
    ('Organização por finalidade', 'Rede e protocolos: asyncio, socket, ssl e urllib. Segurança e representação: hashlib, hmac, secrets, base64 e binascii. Persistência: sqlite3. Conta e e-mail: smtplib e email. Estruturas, execução e utilitários: os demais módulos listados acima.'),
    ('Limites do levantamento', 'Foram considerados código-fonte, dependências declaradas, ativos de interface e automações presentes no workspace. Dependências transitivas estão reproduzidas no apêndice de versões. Não foi verificado o estado de produção, de contas externas nem a instalação de cada pacote.'),
])

objects = [b'<< /Type /Catalog /Pages 2 0 R >>', b'',
           b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
           b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>']
kids = []
for stream in PAGES:
    n = len(objects) + 1
    kids.append(f'{n} 0 R')
    objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {n+1} 0 R >>'.encode())
    objects.append(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream')
objects[1] = f'<< /Type /Pages /Kids [{" ".join(kids)}] /Count {len(kids)} >>'.encode()
pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
offsets = [0]
for i, obj in enumerate(objects, 1):
    offsets.append(len(pdf))
    pdf.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
xref = len(pdf)
pdf.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
for offset in offsets[1:]:
    pdf.extend(f'{offset:010d} 00000 n \n'.encode())
pdf.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
OUT.write_bytes(pdf)
print(f'{OUT} | {len(PAGES)} páginas | {len(pdf)} bytes')
