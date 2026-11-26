"""Papéis de administração e registro das ações administrativas.

Em tabela própria, e não numa coluna de ``usuarios``: bancos já existentes
ganham a tabela na primeira conexão, sem migração. Quem não aparece aqui é
membro comum.

* ``master``: só o terminal do servidor concede ou retira (``spectra_link_guard.admin``).
* ``admin``: concedido e retirado pelo master na página /admin.
"""

from __future__ import annotations

from typing import Any

from . import bd

bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS papeis (
 usuario_id TEXT PRIMARY KEY REFERENCES usuarios(id) ON DELETE CASCADE,
 papel TEXT NOT NULL CHECK (papel IN ('admin','master')),
 concedido_por TEXT NOT NULL, concedido_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_registro (
 id INTEGER PRIMARY KEY AUTOINCREMENT, autor TEXT NOT NULL, acao TEXT NOT NULL,
 alvo TEXT NOT NULL DEFAULT '', detalhe TEXT NOT NULL DEFAULT '', criado_em TEXT NOT NULL);
""")


def papel(usuario_id: str) -> str:
    with bd.conexao() as con:
        linha = con.execute("SELECT papel FROM papeis WHERE usuario_id = ?", (usuario_id,)).fetchone()
    return linha["papel"] if linha else "membro"


def eh_admin(usuario: dict[str, Any] | None) -> bool:
    return bool(usuario) and papel(usuario["id"]) in ("admin", "master")


def eh_master(usuario: dict[str, Any] | None) -> bool:
    return bool(usuario) and papel(usuario["id"]) == "master"


def definir(usuario_id: str, novo: str | None, por: str) -> None:
    """Grava o papel (``None`` volta a membro comum)."""
    with bd.conexao() as con:
        if novo is None:
            con.execute("DELETE FROM papeis WHERE usuario_id = ?", (usuario_id,))
        else:
            con.execute(
                "INSERT INTO papeis VALUES (?,?,?,?) ON CONFLICT(usuario_id) DO UPDATE SET "
                "papel=excluded.papel, concedido_por=excluded.concedido_por, concedido_em=excluded.concedido_em",
                (usuario_id, novo, por, bd.agora().isoformat(timespec="seconds")),
            )


def registrar_acao(autor: str, acao: str, alvo: str = "", detalhe: str = "") -> None:
    with bd.conexao() as con:
        con.execute(
            "INSERT INTO admin_registro(autor,acao,alvo,detalhe,criado_em) VALUES (?,?,?,?,?)",
            (autor, acao, alvo, detalhe[:200], bd.agora().isoformat(timespec="seconds")),
        )
