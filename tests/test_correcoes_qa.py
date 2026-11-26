"""Regressões dos erros achados no teste exploratório de 29/10/2026."""
import pytest
from fastapi.testclient import TestClient

from spectra_link_guard.web.app import app


@pytest.mark.parametrize(
    "rota, corpo, palavra",
    [
        # Passa na checagem do navegador, mas o servidor recusa domínios especiais.
        ("/api/auth/entrar", {"email": "aluno@escola.local", "senha": "qualquer"}, "e-mail"),
        ("/api/auth/cadastrar", {"nome": "Pessoa", "email": "aluno@escola.local", "senha": "Senha-forte123!"}, "e-mail"),
        ("/api/auth/cadastrar", {"nome": "Pessoa", "email": "pessoa@example.com", "senha": "x" * 201}, "senha"),
        ("/api/analisar", {"url": "https://a.com/" + "b" * 2040}, "link"),
    ],
)
def test_validacao_responde_com_frase_em_portugues(rota, corpo, palavra):
    r = TestClient(app).post(rota, json=corpo)
    assert r.status_code == 422
    erro = r.json()["erro"]
    assert isinstance(erro, str) and palavra in erro.lower()
    assert "detail" not in r.json()


def _pessoa(email):
    c = TestClient(app)
    r = c.post("/api/auth/cadastrar", json={"nome": "Pessoa Teste", "email": email, "senha": "Senha-forte123!"})
    assert r.status_code == 201
    return c, r.json()["usuario"]["id"]


@pytest.mark.parametrize("depois", ["99999999999999999999999", "-1"])
def test_chat_recusa_posicao_fora_do_intervalo_sem_erro_500(depois):
    a, _ = _pessoa("a@example.com")
    _, id_b = _pessoa("b@example.com")
    assert a.post(f"/api/usuarios/{id_b}/seguir").status_code == 200
    r = a.get(f"/api/chat/{id_b}?depois={depois}")
    assert r.status_code == 422
    assert a.get(f"/api/chat/{id_b}?depois=0").status_code == 200


def _fase_incidente(cliente):
    fase = cliente.get("/api/desafios/incidente/fases/1").json()
    assert fase["modo"] == "ordem" and len(fase["itens"]) == 4
    return fase["itens"]


def test_ordenar_pelo_id_nao_resolve_o_desafio():
    # Antes, os ids eram "0..3" na ordem certa e todo mundo acertava ordenando.
    # Com ids opacos, cinco pessoas acertarem por acaso tem chance de (1/24)^5.
    acertos = 0
    for n in range(5):
        c, _ = _pessoa(f"jogador{n}@example.com")
        ids = sorted(i["id"] for i in _fase_incidente(c))
        acertos += c.post("/api/desafios/incidente/fases/1/responder", json={"itens": ids}).json()["acertou"]
    assert acertos < 5


def test_ordem_certa_pelos_textos_continua_aceita():
    c, _ = _pessoa("jogador@example.com")
    itens = _fase_incidente(c)
    # A linha do tempo do caso fictício: 08:10, 08:14, 08:16 e 08:20.
    ordem = [next(i["id"] for i in itens if i["texto"].startswith(h)) for h in ("08:10", "08:14", "08:16", "08:20")]
    r = c.post("/api/desafios/incidente/fases/1/responder", json={"itens": ordem}).json()
    assert r["acertou"] is True and r["progresso"]["concluidas"] == 1
    errada = c.post("/api/desafios/incidente/fases/1/responder", json={"itens": ordem[::-1]}).json()
    assert errada["acertou"] is False


def test_retorno_do_google_apaga_state_e_grava_sessao(monkeypatch):
    # A proteção HTTP convertia os cabeçalhos em dicionário e só o último Set-Cookie sobrevivia.
    from spectra_link_guard.auth import fluxos, google, seguranca
    c = TestClient(app)
    state, _, _ = fluxos.iniciar_google()
    c.cookies.set("spectra_oauth_state", seguranca.assinar(state))

    async def perfil(*args):
        return {"sub": "google-qa", "email": "qa@example.com", "nome": "Pessoa QA", "email_verificado": True}

    monkeypatch.setattr(google, "trocar_codigo", perfil)
    r = c.get("/auth/google/callback", params={"code": "codigo", "state": state}, follow_redirects=False)
    cookies = r.headers.get_list("set-cookie")
    assert any(v.startswith("spectra_sessao=") for v in cookies)
    assert any(v.startswith("spectra_oauth_state=") and "Max-Age=0" in v for v in cookies)


def test_pagina_inexistente_mostra_pagina_html_sem_ecoar_o_endereco():
    r = TestClient(app).get("/painel/<b>zzqx-endereco-digitado</b>")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("text/html")
    assert 'href="/inicio"' in r.text
    assert "<b>zzqx" not in r.text and "zzqx-endereco-digitado" not in r.text
    nonce = r.headers["content-security-policy"].split("'nonce-")[1].split("'")[0]
    assert f'<script nonce="{nonce}"' in r.text  # scripts da página liberados pela CSP


@pytest.mark.parametrize("rota", ["/api/nao-existe", "/static/nao-existe.js"])
def test_recurso_inexistente_responde_json_com_erro(rota):
    r = TestClient(app).get(rota)
    assert r.status_code == 404
    assert isinstance(r.json()["erro"], str)


# Limites de login e cadastro: numa escola, a turma toda sai pelo mesmo IP.

def _entrar(cliente, email, senha):
    return cliente.post("/api/auth/entrar", json={"email": email, "senha": senha})


def test_logins_certos_seguidos_nao_bloqueiam_o_ip():
    c, _ = _pessoa("turma@example.com")
    for _ in range(12):
        assert _entrar(c, "turma@example.com", "Senha-forte123!").status_code == 200


def test_erros_de_uma_conta_nao_bloqueiam_outra_no_mesmo_ip():
    c, _ = _pessoa("errou@example.com")
    _pessoa("acertou@example.com")
    for _ in range(8):
        assert _entrar(c, "errou@example.com", "senha-errada").status_code == 401
    assert _entrar(c, "errou@example.com", "Senha-forte123!").status_code == 429
    assert _entrar(c, "acertou@example.com", "Senha-forte123!").status_code == 200


def test_muitas_falhas_no_mesmo_ip_bloqueiam_o_ip():
    c, _ = _pessoa("vitima@example.com")
    for n in range(30):  # 5 erros em cada uma de 6 contas: abaixo do limite por conta
        assert _entrar(c, f"tentativa{n % 6}@example.com", "senha-errada").status_code == 401
    assert _entrar(c, "vitima@example.com", "Senha-forte123!").status_code == 429


def test_cadastro_com_erro_de_digitacao_nao_consome_a_cota():
    c = TestClient(app)
    for _ in range(10):
        assert c.post("/api/auth/cadastrar", json={"nome": "Pessoa", "email": "sem-arroba", "senha": "Senha-forte123!"}).status_code == 422
    assert c.post("/api/auth/cadastrar", json={"nome": "Pessoa", "email": "nova@example.com", "senha": "Senha-forte123!"}).status_code == 201


def test_cadastro_limita_contas_criadas_por_ip(monkeypatch):
    from spectra_link_guard.auth import rotas
    monkeypatch.setattr(rotas, "CADASTROS_POR_HORA", 3)
    c = TestClient(app)
    for n in range(3):
        assert c.post("/api/auth/cadastrar", json={"nome": "Pessoa", "email": f"conta{n}@example.com", "senha": "Senha-forte123!"}).status_code == 201
    assert c.post("/api/auth/cadastrar", json={"nome": "Pessoa", "email": "conta9@example.com", "senha": "Senha-forte123!"}).status_code == 429


def test_json_malformado_tambem_vira_frase():
    r = TestClient(app).post("/api/auth/entrar", content=b"{nao json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert isinstance(r.json()["erro"], str)
