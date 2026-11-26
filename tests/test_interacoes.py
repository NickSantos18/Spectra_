"""Curtidas, notificações, avisos fixados e edição de publicações."""
from fastapi.testclient import TestClient

from spectra_link_guard.auth import bd, papeis
from spectra_link_guard.web.app import app

POST = {"titulo": "Golpe do Pix falso", "texto": "Como reconhecer a cobrança falsa."}


def conta(email, nome):
    c = TestClient(app)
    r = c.post("/api/auth/cadastrar", json={"nome": nome, "email": email, "senha": "Senha-forte123!"})
    assert r.status_code == 201, r.text
    return c, r.json()["usuario"]["id"]


def publicar(cliente, tipo="forum"):
    r = cliente.post(f"/api/comunidade/{tipo}", json=POST)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def notificacoes(cliente):
    return cliente.get("/api/notificacoes").json()


def test_curtir_conta_uma_vez_e_descurtir():
    a, _ = conta("a@example.com", "Pessoa A")
    b, _ = conta("b@example.com", "Pessoa B")
    pid = publicar(a)
    assert b.post(f"/api/publicacoes/{pid}/curtida").json() == {"curtido": True, "curtidas": 1}
    assert b.post(f"/api/publicacoes/{pid}/curtida").json() == {"curtido": True, "curtidas": 1}
    [visto_b] = b.get("/api/comunidade/forum").json()
    [visto_a] = a.get("/api/comunidade/forum").json()
    assert (visto_b["curtidas"], visto_b["curtiu"]) == (1, True)
    assert (visto_a["curtidas"], visto_a["curtiu"]) == (1, False)
    assert b.delete(f"/api/publicacoes/{pid}/curtida").json() == {"curtido": False, "curtidas": 0}


def test_curtida_notifica_autor_mas_nao_a_si_mesmo():
    a, _ = conta("a@example.com", "Pessoa A")
    b, _ = conta("b@example.com", "Pessoa B")
    pid = publicar(a)
    b.post(f"/api/publicacoes/{pid}/curtida")
    a.post(f"/api/publicacoes/{pid}/curtida")
    n = notificacoes(a)
    assert n["nao_lidas"] == 1
    [item] = n["itens"]
    assert (item["tipo"], item["ator_nome"], item["publicacao"], item["publicacao_titulo"]) == (
        "curtida", "Pessoa B", pid, "Golpe do Pix falso")
    assert notificacoes(b)["nao_lidas"] == 0


def test_comentario_notifica_autor_e_quem_ja_comentou():
    a, _ = conta("a@example.com", "Pessoa A")
    b, _ = conta("b@example.com", "Pessoa B")
    c, _ = conta("c@example.com", "Pessoa C")
    pid = publicar(a)
    b.post(f"/api/publicacoes/{pid}/respostas", json={"texto": "Caí nesse golpe semana passada"})
    c.post(f"/api/publicacoes/{pid}/respostas", json={"texto": "Obrigado pelo alerta"})
    a.post(f"/api/publicacoes/{pid}/respostas", json={"texto": "Fico feliz em ajudar"})
    tipos = lambda cli: sorted((i["tipo"], i["ator_nome"]) for i in notificacoes(cli)["itens"])
    assert tipos(a) == [("comentario", "Pessoa B"), ("comentario", "Pessoa C")]
    assert tipos(b) == [("resposta", "Pessoa A"), ("resposta", "Pessoa C")]
    assert tipos(c) == [("resposta", "Pessoa A")]
    assert notificacoes(a)["itens"][-1]["trecho"] == "Caí nesse golpe semana passada"


def test_marcar_notificacoes_como_lidas():
    a, _ = conta("a@example.com", "Pessoa A")
    b, _ = conta("b@example.com", "Pessoa B")
    b.post(f"/api/publicacoes/{publicar(a)}/curtida")
    assert a.post("/api/notificacoes/lidas").json() == {"ok": True}
    n = notificacoes(a)
    assert n["nao_lidas"] == 0 and all(i["lida"] for i in n["itens"])


def test_excluir_publicacao_apaga_curtidas_e_notificacoes():
    a, _ = conta("a@example.com", "Pessoa A")
    b, _ = conta("b@example.com", "Pessoa B")
    pid = publicar(a)
    b.post(f"/api/publicacoes/{pid}/curtida")
    b.post(f"/api/publicacoes/{pid}/respostas", json={"texto": "Comentário"})
    assert a.delete(f"/api/publicacoes/{pid}").status_code == 200
    assert notificacoes(a) == {"nao_lidas": 0, "itens": []}
    with bd.conexao() as con:
        assert con.execute("SELECT count(*) FROM curtidas").fetchone()[0] == 0


def test_curtir_publicacao_inexistente_404():
    a, _ = conta("a@example.com", "Pessoa A")
    assert a.post("/api/publicacoes/nao-existe/curtida").status_code == 404
    assert TestClient(app).get("/api/notificacoes").status_code == 401


# --------------------------------------------------------------------------- #
# Avisos, edição e registro de ações
# --------------------------------------------------------------------------- #


def admin(email="adm@example.com", nome="Pessoa Admin"):
    c, uid = conta(email, nome)
    papeis.definir(uid, "admin", "teste")
    return c, uid


def test_aviso_so_admin_e_nasce_fixado():
    membro, _ = conta("m@example.com", "Membro")
    adm, _ = admin()
    assert membro.post("/api/comunidade/aviso", json=POST).status_code == 403
    pid = publicar(adm, "aviso")
    [aviso] = membro.get("/api/avisos").json()
    assert (aviso["id"], aviso["titulo"], aviso["texto"]) == (pid, POST["titulo"], POST["texto"])
    [no_feed] = membro.get("/api/comunidade/explorar").json()
    assert no_feed["tipo"] == "aviso" and no_feed["fixado"]


def test_desafixar_tira_aviso_do_topo():
    membro, _ = conta("m@example.com", "Membro")
    adm, _ = admin()
    pid = publicar(adm, "aviso")
    forum = publicar(membro)
    assert membro.post(f"/api/publicacoes/{pid}/fixar", json={"fixado": False}).status_code == 404
    assert adm.post(f"/api/publicacoes/{forum}/fixar", json={"fixado": True}).status_code == 422
    assert adm.post(f"/api/publicacoes/{pid}/fixar", json={"fixado": False}).json() == {"fixado": False}
    assert membro.get("/api/avisos").json() == []
    assert adm.post(f"/api/publicacoes/{pid}/fixar", json={"fixado": True}).json() == {"fixado": True}
    assert len(membro.get("/api/avisos").json()) == 1


def test_editar_propria_publicacao_e_bloquear_alheia():
    autor, _ = conta("a@example.com", "Autor")
    outro, _ = conta("b@example.com", "Outro")
    adm, _ = admin()
    adm2, _ = admin("adm2@example.com", "Outra Admin")
    novo = {"titulo": "Título corrigido", "texto": "Texto revisado da publicação."}
    forum = publicar(autor)
    assert autor.put(f"/api/publicacoes/{forum}", json=novo).status_code == 200
    assert [p["titulo"] for p in outro.get("/api/comunidade/forum").json()] == ["Título corrigido"]
    assert outro.put(f"/api/publicacoes/{forum}", json=POST).status_code == 404
    assert adm.put(f"/api/publicacoes/{forum}", json=POST).status_code == 404
    blog = publicar(adm2, "blog")
    assert adm.put(f"/api/publicacoes/{blog}", json=novo).status_code == 200
    assert adm.put("/api/publicacoes/nao-existe", json=novo).status_code == 404


def test_acoes_de_admin_ficam_registradas():
    membro, _ = conta("m@example.com", "Membro")
    adm, aid = admin()
    adm2, _ = admin("adm2@example.com", "Outra Admin")
    blog = publicar(adm, "blog")
    aviso = publicar(adm, "aviso")
    outro_blog = publicar(adm2, "blog")
    adm.put(f"/api/publicacoes/{outro_blog}", json={"titulo": "Revisado", "texto": "Texto revisado pelo admin."})
    adm.post(f"/api/publicacoes/{aviso}/fixar", json={"fixado": False})
    adm.delete(f"/api/publicacoes/{publicar(membro)}")
    with bd.conexao() as con:
        acoes = [tuple(r) for r in con.execute("SELECT acao, alvo FROM admin_registro WHERE autor=? ORDER BY id", (aid,))]
    assert [a for a, _ in acoes] == ["publicar_blog", "publicar_aviso", "editar", "desafixar", "excluir"]
    assert acoes[0][1] == blog and acoes[2][1] == outro_blog and acoes[3][1] == aviso
