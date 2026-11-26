"""Papéis master/admin, comando de terminal e página de administração."""
from datetime import timedelta

from fastapi.testclient import TestClient

from spectra_link_guard import admin
from spectra_link_guard.auth import bd, papeis
from spectra_link_guard.web.app import app


def conta(email, nome="Pessoa Teste"):
    c = TestClient(app)
    r = c.post("/api/auth/cadastrar", json={"nome": nome, "email": email, "senha": "Senha-forte123!"})
    assert r.status_code == 201, r.text
    return c, r.json()["usuario"]["id"]


# --------------------------------------------------------------------------- #
# Terminal
# --------------------------------------------------------------------------- #


def test_papel_padrao_e_membro():
    _, uid = conta("membro@example.com")
    assert papeis.papel(uid) == "membro"
    assert not papeis.eh_admin(bd.buscar_por_id(uid))


def test_comando_master_promove_e_confirma_email(capsys):
    _, uid = conta("dono@example.com")
    assert admin.main(["master", "DONO@example.com"]) == 0
    u = bd.buscar_por_id(uid)
    assert papeis.papel(uid) == "master"
    assert papeis.eh_master(u) and papeis.eh_admin(u)
    assert u["email_verificado"] == 1
    assert "dono@example.com" in capsys.readouterr().out


def test_comando_master_com_email_inexistente_sai_com_erro(capsys):
    assert admin.main(["master", "ninguem@example.com"]) == 1
    assert "não encontrada" in capsys.readouterr().out.lower()


def test_remover_master_pelo_terminal():
    _, uid = conta("dono@example.com")
    admin.main(["master", "dono@example.com"])
    assert admin.main(["remover-master", "dono@example.com"]) == 0
    assert papeis.papel(uid) == "membro"


def tornar(uid, papel):
    papeis.definir(uid, papel, "teste")


POST = {"titulo": "Dicas de segurança", "texto": "Como se proteger contra phishing."}


# --------------------------------------------------------------------------- #
# Comunidade
# --------------------------------------------------------------------------- #


def test_so_admin_publica_no_blog():
    membro, _ = conta("membro@example.com")
    adm, aid = conta("adm@example.com")
    tornar(aid, "admin")
    assert membro.post("/api/comunidade/blog", json=POST).status_code == 403
    assert adm.post("/api/comunidade/blog", json=POST).status_code == 201


def test_perfil_informa_papel():
    c, uid = conta("pessoa@example.com")
    p = c.get("/api/perfil").json()
    assert (p["papel"], p["admin"], p["master"], p["pode_publicar"]) == ("membro", False, False, False)
    tornar(uid, "master")
    p = c.get("/api/perfil").json()
    assert (p["papel"], p["admin"], p["master"], p["pode_publicar"]) == ("master", True, True, True)


def test_lista_traz_papel_do_autor():
    adm, aid = conta("adm@example.com")
    tornar(aid, "admin")
    membro, _ = conta("membro@example.com")
    assert adm.post("/api/comunidade/blog", json=POST).status_code == 201
    assert membro.post("/api/comunidade/forum", json=POST).status_code == 201
    feed = membro.get("/api/comunidade/explorar").json()
    assert {p["tipo"]: p["autor_papel"] for p in feed} == {"blog": "admin", "forum": "membro"}


def test_admin_exclui_publicacao_de_membro():
    autor, _ = conta("autor@example.com")
    outro, _ = conta("outro@example.com")
    adm, aid = conta("adm@example.com")
    tornar(aid, "admin")
    ident = autor.post("/api/comunidade/forum", json=POST).json()["id"]
    assert outro.delete(f"/api/publicacoes/{ident}").status_code == 404
    assert adm.delete(f"/api/publicacoes/{ident}").status_code == 200
    assert autor.get("/api/comunidade/forum").json() == []


def test_listar_mostra_papeis(capsys):
    conta("dono@example.com")
    admin.main(["master", "dono@example.com"])
    capsys.readouterr()
    assert admin.main(["listar"]) == 0
    saida = capsys.readouterr().out
    assert "master" in saida and "dono@example.com" in saida


# --------------------------------------------------------------------------- #
# Página e API de admin
# --------------------------------------------------------------------------- #


def test_pagina_admin_redireciona_quem_nao_e_admin():
    anonimo = TestClient(app)
    r = anonimo.get("/admin", follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/inicio?erro=entre_primeiro&proximo=%2Fadmin")
    membro, _ = conta("membro@example.com")
    r = membro.get("/admin", follow_redirects=False)
    assert (r.status_code, r.headers["location"]) == (303, "/painel")


def test_api_admin_esconde_de_membro():
    membro, mid = conta("membro@example.com")
    for metodo, rota in [("get", "/api/admin/estatisticas"), ("get", "/api/admin/publicacoes"),
                         ("get", "/api/admin/registro"), ("get", "/api/admin/contas?busca=pe"),
                         ("get", "/api/admin/admins"), ("post", f"/api/admin/admins/{mid}"),
                         ("delete", f"/api/admin/admins/{mid}")]:
        assert getattr(membro, metodo)(rota).status_code == 404, rota


def test_admin_comum_ve_numeros_mas_nao_mexe_em_papeis():
    adm, aid = conta("adm@example.com")
    tornar(aid, "admin")
    _, mid = conta("membro@example.com")
    dados = adm.get("/api/admin/estatisticas").json()
    assert dados["total_contas"] == 2 and len(dados["por_dia"]) == 30
    assert adm.get("/api/admin/contas?busca=membro").status_code == 404
    assert adm.post(f"/api/admin/admins/{mid}").status_code == 404
    assert papeis.papel(mid) == "membro"


def test_master_promove_e_rebaixa_com_registro():
    master, xid = conta("dono@example.com", "Dono do Site")
    tornar(xid, "master")
    _, mid = conta("membro@example.com", "Membro Promovido")
    [achado] = master.get("/api/admin/contas?busca=promovido").json()
    assert (achado["id"], achado["papel"], achado["email_verificado"]) == (mid, "membro", False)
    assert master.post(f"/api/admin/admins/{mid}").json() == {"papel": "admin"}
    assert {a["id"]: a["papel"] for a in master.get("/api/admin/admins").json()} == {xid: "master", mid: "admin"}
    assert master.delete(f"/api/admin/admins/{mid}").json() == {"papel": "membro"}
    registro = master.get("/api/admin/registro").json()
    assert [(r["acao"], r["autor_nome"], r["alvo_nome"]) for r in registro[:2]] == [
        ("rebaixar", "Dono do Site", "Membro Promovido"), ("promover", "Dono do Site", "Membro Promovido")]


def test_master_nao_e_rebaixado_pelo_site():
    master, xid = conta("dono@example.com")
    tornar(xid, "master")
    _, outro = conta("outro-master@example.com")
    tornar(outro, "master")
    assert master.delete(f"/api/admin/admins/{outro}").status_code == 403
    assert master.delete(f"/api/admin/admins/{xid}").status_code == 403
    assert master.post(f"/api/admin/admins/{outro}").status_code == 403
    assert papeis.papel(outro) == "master" and papeis.papel(xid) == "master"


def test_promover_exige_login_recente():
    master, xid = conta("dono@example.com")
    tornar(xid, "master")
    _, mid = conta("membro@example.com")
    antigo = (bd.agora() - timedelta(minutes=31)).isoformat(timespec="seconds")
    with bd.conexao() as con:
        con.execute("UPDATE usuarios SET ultimo_acesso=? WHERE id=?", (antigo, xid))
    r = master.post(f"/api/admin/admins/{mid}")
    assert r.status_code == 403 and "entre de novo" in r.json()["erro"]
    assert papeis.papel(mid) == "membro"


def test_publicacoes_do_admin_trazem_contagens():
    adm, aid = conta("adm@example.com", "Pessoa Admin")
    tornar(aid, "admin")
    membro, _ = conta("membro@example.com")
    blog = adm.post("/api/comunidade/blog", json=POST).json()["id"]
    adm.post("/api/comunidade/aviso", json=POST)
    membro.post("/api/comunidade/forum", json=POST)
    membro.post(f"/api/publicacoes/{blog}/curtida")
    membro.post(f"/api/publicacoes/{blog}/respostas", json={"texto": "Muito bom"})
    lista = adm.get("/api/admin/publicacoes").json()
    assert sorted(p["tipo"] for p in lista) == ["aviso", "blog"]
    [b] = [p for p in lista if p["tipo"] == "blog"]
    assert (b["curtidas"], b["respostas"], b["fixado"], b["autor_nome"]) == (1, 1, False, "Pessoa Admin")
