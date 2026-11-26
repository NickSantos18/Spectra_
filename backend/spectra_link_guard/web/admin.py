"""API da página /admin.

Para quem não é admin, todas as rotas respondem 404, como se não existissem.
Mexer em papéis é só do master e exige login recente; o master em si só
muda pelo terminal (``python -m spectra_link_guard.admin``).
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request

from ..auth import bd, papeis, protecao, usuario_atual
from . import acessos

router = APIRouter()

#: Minutos desde o último login para poder promover ou rebaixar.
LOGIN_RECENTE_MIN = 30


def _admin(request: Request) -> dict:
    u = usuario_atual(request.cookies.get("spectra_sessao"))
    if not papeis.eh_admin(u):
        raise HTTPException(404, "Página não encontrada.")
    if request.method != "GET" and not protecao.origem_permitida(request):
        raise HTTPException(403, "Origem inválida.")
    return u


def _master(request: Request) -> dict:
    u = _admin(request)
    if not papeis.eh_master(u):
        raise HTTPException(404, "Página não encontrada.")
    return u


def _login_recente(u: dict) -> None:
    ultimo = u.get("ultimo_acesso")
    if not ultimo or bd.agora() - datetime.fromisoformat(ultimo) > timedelta(minutes=LOGIN_RECENTE_MIN):
        raise HTTPException(403, "Por segurança, saia e entre de novo para alterar administradores.")


@router.get("/api/admin/estatisticas")
def estatisticas(request: Request):
    _admin(request)
    return acessos.estatisticas()


@router.get("/api/admin/publicacoes")
def publicacoes(request: Request):
    _admin(request)
    with bd.conexao() as con:
        linhas = con.execute(
            """SELECT p.id, p.tipo, p.titulo, p.texto, p.criado_em, p.autor, u.nome AS autor_nome,
                      (SELECT count(*) FROM curtidas c WHERE c.publicacao = p.id) AS curtidas,
                      (SELECT count(*) FROM respostas r WHERE r.publicacao = p.id) AS respostas,
                      EXISTS(SELECT 1 FROM fixadas f WHERE f.publicacao = p.id) AS fixado
               FROM publicacoes p JOIN usuarios u ON u.id = p.autor
               WHERE p.tipo IN ('blog','aviso') ORDER BY p.criado_em DESC, p.id DESC LIMIT 200"""
        ).fetchall()
    return [dict(l, fixado=bool(l["fixado"])) for l in linhas]


@router.get("/api/admin/registro")
def registro(request: Request):
    _admin(request)
    with bd.conexao() as con:
        linhas = con.execute(
            """SELECT r.id, r.acao, r.detalhe, r.criado_em,
                      CASE WHEN r.autor = 'terminal' THEN 'Terminal do servidor' ELSE COALESCE(a.nome, r.autor) END AS autor_nome,
                      COALESCE(alvo.nome, pub.titulo, r.alvo) AS alvo_nome
               FROM admin_registro r LEFT JOIN usuarios a ON a.id = r.autor
               LEFT JOIN usuarios alvo ON alvo.id = r.alvo LEFT JOIN publicacoes pub ON pub.id = r.alvo
               ORDER BY r.id DESC LIMIT 100"""
        ).fetchall()
    return [dict(l) for l in linhas]


def _contas(con, onde: str, args: tuple) -> list[dict]:
    linhas = con.execute(
        f"""SELECT u.id, u.nome, u.email, u.email_verificado, COALESCE(p.papel, 'membro') AS papel
            FROM usuarios u LEFT JOIN papeis p ON p.usuario_id = u.id WHERE {onde}
            ORDER BY p.papel DESC, u.nome LIMIT 20""",
        args,
    ).fetchall()
    return [dict(l, email_verificado=bool(l["email_verificado"])) for l in linhas]


@router.get("/api/admin/contas")
def contas(request: Request, busca: str = ""):
    _master(request)
    busca = busca.strip().lower()[:120]
    if len(busca) < 2:
        return []
    with bd.conexao() as con:
        return _contas(con, "instr(lower(u.nome), ?) > 0 OR instr(u.email, ?) > 0", (busca, busca))


@router.get("/api/admin/admins")
def admins(request: Request):
    _master(request)
    with bd.conexao() as con:
        return _contas(con, "p.papel IS NOT NULL", ())


def _alvo(usuario_id: str) -> str:
    if not bd.buscar_por_id(usuario_id):
        raise HTTPException(404, "Conta não encontrada.")
    atual = papeis.papel(usuario_id)
    if atual == "master":
        raise HTTPException(403, "O admin master só pode ser alterado pelo terminal do servidor.")
    return atual


@router.post("/api/admin/admins/{usuario_id}")
def promover(usuario_id: str, request: Request):
    u = _master(request)
    _login_recente(u)
    _alvo(usuario_id)
    papeis.definir(usuario_id, "admin", u["id"])
    papeis.registrar_acao(u["id"], "promover", usuario_id)
    return {"papel": "admin"}


@router.delete("/api/admin/admins/{usuario_id}")
def rebaixar(usuario_id: str, request: Request):
    u = _master(request)
    _login_recente(u)
    if _alvo(usuario_id) != "admin":
        raise HTTPException(404, "Esta conta não é admin.")
    papeis.definir(usuario_id, None, u["id"])
    papeis.registrar_acao(u["id"], "rebaixar", usuario_id)
    return {"papel": "membro"}
