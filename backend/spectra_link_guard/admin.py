"""Administração pelo terminal do servidor.

Só quem tem acesso à máquina vira admin master; nenhuma senha especial fica
no código. Use o mesmo ``SPECTRA_BD`` do servidor::

    python -m spectra_link_guard.admin master seu@email.com
    python -m spectra_link_guard.admin remover-master seu@email.com
    python -m spectra_link_guard.admin listar

A conta precisa existir: cadastre-se no site antes. Virar master também
marca o e-mail como confirmado.
"""

from __future__ import annotations

import sys

from .auth import bd, papeis

USO = "Uso: python -m spectra_link_guard.admin master|remover-master <email> | listar"


def main(argv: list[str]) -> int:
    if argv[:1] == ["listar"]:
        with bd.conexao() as con:
            linhas = con.execute(
                "SELECT u.email, u.nome, p.papel FROM papeis p JOIN usuarios u ON u.id = p.usuario_id "
                "ORDER BY p.papel DESC, u.email"
            ).fetchall()
        for linha in linhas:
            print(f"{linha['papel']:7} {linha['email']} ({linha['nome']})")
        if not linhas:
            print("Nenhum admin cadastrado.")
        return 0
    if len(argv) != 2 or argv[0] not in ("master", "remover-master"):
        print(USO)
        return 2
    usuario = bd.buscar_por_email(argv[1])
    if not usuario:
        print(f"Conta não encontrada: {argv[1]}. Cadastre-se no site antes.")
        return 1
    if argv[0] == "master":
        papeis.definir(usuario["id"], "master", "terminal")
        with bd.conexao() as con:
            con.execute("UPDATE usuarios SET email_verificado = 1 WHERE id = ?", (usuario["id"],))
        papeis.registrar_acao("terminal", "tornar_master", usuario["id"])
        print(f"{usuario['email']} agora é admin master.")
    else:
        papeis.definir(usuario["id"], None, "terminal")
        papeis.registrar_acao("terminal", "remover_master", usuario["id"])
        print(f"{usuario['email']} voltou a ser membro comum.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))


def semear_do_ambiente() -> str | None:
    """Garante o admin master a partir de SPECTRA_ADMIN_EMAIL e SPECTRA_ADMIN_SENHA.

    Existe porque o plano gratuito do Render não dá acesso ao shell, então o
    comando ``python -m spectra_link_guard.admin master`` fica inalcançável.
    E porque, sem disco persistente, o banco é recriado a cada deploy: rodando
    na subida do servidor, esta função devolve o admin toda vez, sem intervenção.

    Idempotente: se a conta já existe, só confere o papel; se já é master, não
    faz nada. Sem as duas variáveis, não faz nada — é um recurso opcional.

    Devolve o e-mail promovido, ou None se não havia o que fazer.
    """
    import os
    import sqlite3

    from .auth import seguranca

    email = (os.getenv("SPECTRA_ADMIN_EMAIL") or "").strip()
    senha = os.getenv("SPECTRA_ADMIN_SENHA") or ""
    if not email or not senha:
        return None

    usuario = bd.buscar_por_email(email)
    if usuario is None:
        try:
            usuario = bd.criar_usuario(
                nome=(os.getenv("SPECTRA_ADMIN_NOME") or "Administração").strip(),
                email=email,
                senha_hash=seguranca.gerar_hash(senha),
                email_verificado=True,
            )
        except sqlite3.IntegrityError:
            # corrida entre dois processos subindo juntos: o outro criou primeiro
            usuario = bd.buscar_por_email(email)
            if usuario is None:
                return None

    if papeis.papel(usuario["id"]) != "master":
        papeis.definir(usuario["id"], "master", por="semeadura")
    return usuario["email"]
