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
