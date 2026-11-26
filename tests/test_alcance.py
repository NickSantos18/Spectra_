"""Alcance de cada membro: seguidores e curtidas recebidas, com gráfico de 30 dias."""
from datetime import timedelta

from fastapi.testclient import TestClient

from spectra_link_guard.auth import bd
from spectra_link_guard.web.app import app

POST = {"titulo": "Golpe do Pix falso", "texto": "Como reconhecer a cobrança falsa."}


def conta(email, nome="Pessoa"):
    c = TestClient(app)
    r = c.post("/api/auth/cadastrar", json={"nome": nome, "email": email, "senha": "Senha-forte123!"})
    assert r.status_code == 201, r.text
    return c, r.json()["usuario"]["id"]


def test_alcance_conta_seguidores_e_curtidas_recebidas():
    a, aid = conta("a@example.com")
    b, bid = conta("b@example.com")
    c, _ = conta("c@example.com")
    p1 = a.post("/api/comunidade/forum", json=POST).json()["id"]
    p2 = a.post("/api/comunidade/forum", json=POST).json()["id"]
    b.post(f"/api/usuarios/{aid}/seguir")
    c.post(f"/api/usuarios/{aid}/seguir")
    for cliente, pid in ((b, p1), (b, p2), (c, p1), (a, p1)):  # a última é curtida em si mesmo: não conta
        cliente.post(f"/api/publicacoes/{pid}/curtida")
    dados = a.get("/api/alcance").json()
    assert (dados["seguidores"], dados["seguindo"], dados["curtidas"]) == (2, 0, 3)
    assert len(dados["por_dia"]) == 30
    assert {k: dados["por_dia"][-1][k] for k in ("seguidores", "curtidas")} == {"seguidores": 2, "curtidas": 3}
    outro = b.get("/api/alcance").json()
    assert (outro["seguidores"], outro["seguindo"], outro["curtidas"]) == (0, 1, 0)


def test_alcance_acumula_seguidores_e_separa_curtidas_por_dia():
    a, aid = conta("a@example.com")
    b, bid = conta("b@example.com")
    pid = a.post("/api/comunidade/forum", json=POST).json()["id"]
    b.post(f"/api/usuarios/{aid}/seguir")
    b.post(f"/api/publicacoes/{pid}/curtida")
    dez_dias = (bd.agora() - timedelta(days=10)).isoformat(timespec="seconds")
    with bd.conexao() as con:
        con.execute("UPDATE seguidores SET criado_em=? WHERE seguido=?", (dez_dias, aid))
        con.execute("UPDATE curtidas SET criado_em=? WHERE publicacao=?", (dez_dias, pid))
    por_dia = a.get("/api/alcance").json()["por_dia"]
    assert [d["seguidores"] for d in por_dia[:19]] == [0] * 19
    assert all(d["seguidores"] == 1 for d in por_dia[19:])  # quem segue continua contando nos dias seguintes
    assert [d["curtidas"] for d in por_dia] == [0] * 19 + [1] + [0] * 10


def test_alcance_exige_login():
    assert TestClient(app).get("/api/alcance").status_code == 401
