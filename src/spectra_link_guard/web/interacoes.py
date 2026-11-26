"""Curtidas, notificações (o sininho), avisos fixados e edição de publicações."""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from datetime import datetime, timedelta

from ..auth import bd, papeis
from .acessos import FUSO, _local
from .comunidade import exigir, data

router = APIRouter()
bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS curtidas (
 publicacao TEXT NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
 usuario TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 criado_em TEXT NOT NULL, PRIMARY KEY(publicacao, usuario));
CREATE TABLE IF NOT EXISTS notificacoes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 usuario TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 ator TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 tipo TEXT NOT NULL CHECK (tipo IN ('curtida','comentario','resposta')),
 publicacao TEXT NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
 trecho TEXT NOT NULL DEFAULT '', lida INTEGER NOT NULL DEFAULT 0, criado_em TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_notificacoes_usuario ON notificacoes(usuario, id);
CREATE TABLE IF NOT EXISTS fixadas (
 publicacao TEXT PRIMARY KEY REFERENCES publicacoes(id) ON DELETE CASCADE, fixado_em TEXT NOT NULL);
""")


def notificar(con, usuario, ator, tipo, publicacao, trecho=""):
    """Avisa ``usuario`` sobre a ação de ``ator``; ninguém é avisado das próprias ações.

    Curtir de novo depois de descurtir não repete o aviso.
    """
    if usuario == ator:
        return
    if tipo == "curtida" and con.execute(
        "SELECT 1 FROM notificacoes WHERE usuario=? AND ator=? AND tipo='curtida' AND publicacao=?",
        (usuario, ator, publicacao),
    ).fetchone():
        return
    con.execute(
        "INSERT INTO notificacoes(usuario,ator,tipo,publicacao,trecho,criado_em) VALUES (?,?,?,?,?,?)",
        (usuario, ator, tipo, publicacao, trecho[:120], data()),
    )


def _publicacao(con, identificador):
    p = con.execute("SELECT id, autor FROM publicacoes WHERE id=?", (identificador,)).fetchone()
    if not p:
        raise HTTPException(404, "Publicação não encontrada.")
    return p


def _total(con, identificador):
    return con.execute("SELECT count(*) FROM curtidas WHERE publicacao=?", (identificador,)).fetchone()[0]


@router.post("/api/publicacoes/{identificador}/curtida")
def curtir(identificador: str, request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        p = _publicacao(con, identificador)
        if con.execute("INSERT OR IGNORE INTO curtidas VALUES (?,?,?)", (identificador, u["id"], data())).rowcount:
            notificar(con, p["autor"], u["id"], "curtida", identificador)
        return {"curtido": True, "curtidas": _total(con, identificador)}


@router.delete("/api/publicacoes/{identificador}/curtida")
def descurtir(identificador: str, request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        _publicacao(con, identificador)
        con.execute("DELETE FROM curtidas WHERE publicacao=? AND usuario=?", (identificador, u["id"]))
        return {"curtido": False, "curtidas": _total(con, identificador)}


@router.get("/api/notificacoes")
def notificacoes(request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        itens = con.execute(
            """SELECT n.id, n.tipo, n.publicacao, n.trecho, n.lida, n.criado_em,
                      a.nome AS ator_nome, p.titulo AS publicacao_titulo
               FROM notificacoes n JOIN usuarios a ON a.id = n.ator JOIN publicacoes p ON p.id = n.publicacao
               WHERE n.usuario = ? ORDER BY n.id DESC LIMIT 30""",
            (u["id"],),
        ).fetchall()
        nao_lidas = con.execute("SELECT count(*) FROM notificacoes WHERE usuario=? AND lida=0", (u["id"],)).fetchone()[0]
    return {"nao_lidas": nao_lidas, "itens": [dict(i, lida=bool(i["lida"])) for i in itens]}


@router.post("/api/notificacoes/lidas")
def marcar_lidas(request: Request):
    u = exigir(request)
    with bd.conexao() as con:
        con.execute("UPDATE notificacoes SET lida=1 WHERE usuario=? AND lida=0", (u["id"],))
    return {"ok": True}


class Edicao(BaseModel):
    titulo: str = Field(min_length=5, max_length=180)
    texto: str = Field(min_length=10, max_length=20000)


@router.put("/api/publicacoes/{identificador}")
def editar(identificador: str, p: Edicao, request: Request):
    """Cada pessoa edita o que publicou; admins também editam blog e avisos de outros admins."""
    u = exigir(request)
    if len(p.titulo.strip()) < 5 or len(p.texto.strip()) < 10:
        raise HTTPException(422, "Preencha o título e o conteúdo.")
    with bd.conexao() as con:
        pub = con.execute("SELECT autor, tipo FROM publicacoes WHERE id=?", (identificador,)).fetchone()
        gestao = pub is not None and pub["tipo"] in ("blog", "aviso") and papeis.eh_admin(u)
        if not pub or (pub["autor"] != u["id"] and not gestao):
            raise HTTPException(404, "Publicação não encontrada.")
        con.execute("UPDATE publicacoes SET titulo=?, texto=? WHERE id=?", (p.titulo.strip(), p.texto.strip(), identificador))
    if gestao:
        papeis.registrar_acao(u["id"], "editar", identificador, p.titulo.strip())
    return {"ok": True}


class Fixacao(BaseModel):
    fixado: bool


@router.post("/api/publicacoes/{identificador}/fixar")
def fixar(identificador: str, p: Fixacao, request: Request):
    u = exigir(request)
    if not papeis.eh_admin(u):
        raise HTTPException(404, "Publicação não encontrada.")
    with bd.conexao() as con:
        pub = con.execute("SELECT tipo FROM publicacoes WHERE id=?", (identificador,)).fetchone()
        if not pub:
            raise HTTPException(404, "Publicação não encontrada.")
        if pub["tipo"] not in ("blog", "aviso"):
            raise HTTPException(422, "Só posts do blog e avisos podem ser fixados.")
        if p.fixado:
            con.execute("INSERT OR IGNORE INTO fixadas VALUES (?,?)", (identificador, data()))
        else:
            con.execute("DELETE FROM fixadas WHERE publicacao=?", (identificador,))
    papeis.registrar_acao(u["id"], "fixar" if p.fixado else "desafixar", identificador)
    return {"fixado": p.fixado}


@router.get("/api/avisos")
def avisos(request: Request):
    """Avisos importantes fixados, mostrados no topo das páginas para quem está logado."""
    exigir(request)
    with bd.conexao() as con:
        linhas = con.execute(
            """SELECT p.id, p.titulo, p.texto, p.criado_em FROM fixadas f JOIN publicacoes p ON p.id = f.publicacao
               WHERE p.tipo = 'aviso' ORDER BY f.fixado_em DESC, p.id LIMIT 3"""
        ).fetchall()
    return [dict(l) for l in linhas]


@router.get("/api/alcance")
def alcance(request: Request):
    """Seguidores e curtidas recebidas da própria conta, para o gráfico de Conexões.

    Curtir a própria publicação não conta. Seguidores são acumulados (quem
    deixou de seguir sai da conta); curtidas são as recebidas em cada dia.
    """
    u = exigir(request)
    dia_local = lambda iso: datetime.fromisoformat(iso).astimezone(FUSO).date()
    with bd.conexao() as con:
        seguidores = [dia_local(r[0]) for r in con.execute("SELECT criado_em FROM seguidores WHERE seguido=?", (u["id"],))]
        seguindo = con.execute("SELECT count(*) FROM seguidores WHERE seguidor=?", (u["id"],)).fetchone()[0]
        curtidas = [dia_local(r[0]) for r in con.execute(
            "SELECT c.criado_em FROM curtidas c JOIN publicacoes p ON p.id = c.publicacao WHERE p.autor=? AND c.usuario<>?",
            (u["id"], u["id"]))]
    hoje = _local().date()
    dias = [hoje - timedelta(days=n) for n in range(29, -1, -1)]
    return {
        "seguidores": len(seguidores),
        "seguindo": seguindo,
        "curtidas": len(curtidas),
        "por_dia": [{"dia": d.isoformat(), "seguidores": sum(x <= d for x in seguidores),
                     "curtidas": sum(x == d for x in curtidas)} for d in dias],
    }
