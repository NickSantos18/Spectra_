"""Contagem anônima de acessos e números da Visão geral do admin."""
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from starlette.requests import Request

from spectra_link_guard.auth import bd
from spectra_link_guard.web import acessos
from spectra_link_guard.web.app import app

DIA = date(2026, 10, 20)  # data fixa: o teste não depende do relógio


def pedido(ip="203.0.113.7", agente="Navegador de teste"):
    return Request({"type": "http", "method": "GET", "path": "/", "client": (ip, 1234),
                    "headers": [(b"user-agent", agente.encode())]})


def em(dia, hora=12):
    return datetime(dia.year, dia.month, dia.day, hora, 30, tzinfo=acessos.FUSO)


def linhas():
    with bd.conexao() as con:
        return [dict(r) for r in con.execute("SELECT * FROM acessos")]


def test_pagina_conta_acesso_e_api_nao_conta():
    c = TestClient(app)
    assert c.get("/inicio").status_code == 200
    for rota in ("/api/saude", "/static/tokens.css", "/admin", "/nao-existe"):
        c.get(rota, follow_redirects=False)
    assert len(linhas()) == 1


def test_mesma_pessoa_no_dia_conta_uma_vez_sem_guardar_ip():
    for _ in range(3):
        acessos.registrar(pedido(), None, em(DIA))
    acessos.registrar(pedido(agente="Outro navegador"), None, em(DIA))
    hoje = acessos.estatisticas(DIA)["hoje"]
    assert (hoje["acessos"], hoje["pessoas"], hoje["visitantes"], hoje["logadas"]) == (4, 2, 2, 0)
    for linha in linhas():
        assert "203.0.113.7" not in str(linha.values()) and len(linha["visitante"]) == 16


def test_estatisticas_por_dia_inclui_dias_zerados():
    acessos.registrar(pedido(), None, em(DIA))
    acessos.registrar(pedido(), None, em(DIA - timedelta(days=3)))
    por_dia = acessos.estatisticas(DIA)["por_dia"]
    assert len(por_dia) == 30
    assert por_dia[-1] == {"dia": "2026-10-20", "acessos": 1, "contas": 0}
    assert por_dia[-4]["dia"] == "2026-10-17" and por_dia[-4]["acessos"] == 1
    assert sum(d["acessos"] for d in por_dia) == 2


def test_contas_novas_e_total_no_dia_de_hoje():
    TestClient(app).post("/api/auth/cadastrar", json={"nome": "Pessoa", "email": "nova@example.com", "senha": "Senha-forte123!"})
    hoje = acessos._local().date()
    dados = acessos.estatisticas(hoje)
    assert dados["contas_novas_hoje"] == 1 and dados["total_contas"] == 1
    assert dados["por_dia"][-1]["contas"] == 1 and dados["por_dia"][0]["contas"] == 0


def test_estatisticas_por_hora_separa_logados():
    for n in range(7):
        acessos.registrar(pedido(), "conta-1", em(DIA - timedelta(days=n), 19))
        acessos.registrar(pedido(agente="a"), None, em(DIA - timedelta(days=n), 19))
        acessos.registrar(pedido(agente="b"), None, em(DIA - timedelta(days=n), 19))
    acessos.registrar(pedido(), None, em(DIA - timedelta(days=8), 19))  # fora da janela de 7 dias
    dados = acessos.estatisticas(DIA)
    assert len(dados["por_hora"]) == 24
    assert dados["por_hora"][19] == {"hora": 19, "logados": 1.0, "visitantes": 2.0}
    assert dados["por_hora"][3] == {"hora": 3, "logados": 0.0, "visitantes": 0.0}
    assert dados["pico_hora"] == 19


def test_variacao_em_relacao_a_ontem():
    acessos.registrar(pedido(), None, em(DIA))
    assert acessos.estatisticas(DIA)["variacao_pct"] is None  # ontem sem acessos
    for _ in range(2):
        acessos.registrar(pedido(), None, em(DIA - timedelta(days=1)))
    acessos.registrar(pedido(), None, em(DIA))
    acessos.registrar(pedido(), None, em(DIA))
    dados = acessos.estatisticas(DIA)
    assert (dados["hoje"]["acessos"], dados["ontem_acessos"], dados["variacao_pct"]) == (3, 2, 50)
