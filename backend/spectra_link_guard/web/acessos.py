"""Contagem anônima de acessos às páginas, para os gráficos do admin.

Nada de IP nem cookie de rastreamento: cada visitante vira um código derivado
de um sal aleatório **do dia** + IP + navegador. O sal do dia anterior é
apagado, então ninguém consegue recalcular o código nem ligar a mesma pessoa
entre dias diferentes. Quem está logado é contado pela conta, para valer uma
vez só mesmo em vários aparelhos.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import date, datetime, timedelta, timezone

from ..auth import bd

#: Horário de Brasília (o Brasil não tem horário de verão desde 2019).
FUSO = timezone(timedelta(hours=-3))
DIAS_GUARDADOS = 90

bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS acessos (
 dia TEXT NOT NULL, hora INTEGER NOT NULL, visitante TEXT NOT NULL, logado INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS idx_acessos_dia ON acessos(dia);
CREATE TABLE IF NOT EXISTS acessos_sal (dia TEXT PRIMARY KEY, sal TEXT NOT NULL);
""")


def _local(quando: datetime | None = None) -> datetime:
    return (quando or bd.agora()).astimezone(FUSO)


def _sal(con, dia: str) -> str:
    con.execute("DELETE FROM acessos_sal WHERE dia <> ?", (dia,))
    linha = con.execute("SELECT sal FROM acessos_sal WHERE dia = ?", (dia,)).fetchone()
    if linha:
        return linha["sal"]
    sal = secrets.token_hex(16)
    con.execute("INSERT OR IGNORE INTO acessos_sal VALUES (?,?)", (dia, sal))
    return con.execute("SELECT sal FROM acessos_sal WHERE dia = ?", (dia,)).fetchone()["sal"]


def registrar(request, usuario_id: str | None, quando: datetime | None = None) -> None:
    local = _local(quando)
    dia = local.date().isoformat()
    if usuario_id:
        quem = "conta:" + usuario_id
    else:
        ip = request.client.host if request.client else ""
        quem = ip + "|" + request.headers.get("user-agent", "")[:300]
    with bd.conexao() as con:
        visitante = hashlib.sha256(f"{_sal(con, dia)}|{quem}".encode()).hexdigest()[:16]
        con.execute("INSERT INTO acessos VALUES (?,?,?,?)", (dia, local.hour, visitante, int(bool(usuario_id))))
        con.execute("DELETE FROM acessos WHERE dia < ?", ((local.date() - timedelta(days=DIAS_GUARDADOS)).isoformat(),))


def _inicio_utc(dia: date) -> str:
    """Começo do dia local, no formato UTC em que o banco guarda ``criado_em``."""
    return datetime(dia.year, dia.month, dia.day, tzinfo=FUSO).astimezone(timezone.utc).isoformat(timespec="seconds")


def estatisticas(hoje: date | None = None) -> dict:
    hoje = hoje or _local().date()
    ontem = hoje - timedelta(days=1)
    dias = [hoje - timedelta(days=n) for n in range(29, -1, -1)]
    inicio, fim = _inicio_utc(hoje), _inicio_utc(hoje + timedelta(days=1))
    with bd.conexao() as con:
        def contar(sql, *args):
            return con.execute(sql, args).fetchone()[0]

        d = hoje.isoformat()
        hoje_dados = {
            "acessos": contar("SELECT count(*) FROM acessos WHERE dia=?", d),
            "pessoas": contar("SELECT count(DISTINCT visitante) FROM acessos WHERE dia=?", d),
            "logadas": contar("SELECT count(DISTINCT visitante) FROM acessos WHERE dia=? AND logado=1", d),
            "visitantes": contar("SELECT count(DISTINCT visitante) FROM acessos WHERE dia=? AND logado=0", d),
        }
        ontem_acessos = contar("SELECT count(*) FROM acessos WHERE dia=?", ontem.isoformat())
        por_dia_bruto = dict(con.execute(
            "SELECT dia, count(*) FROM acessos WHERE dia >= ? AND dia <= ? GROUP BY dia",
            (dias[0].isoformat(), d)).fetchall())
        por_dia = [{"dia": x.isoformat(), "acessos": por_dia_bruto.get(x.isoformat(), 0),
                    "contas": contar("SELECT count(*) FROM usuarios WHERE criado_em < ?", _inicio_utc(x + timedelta(days=1)))}
                   for x in dias]
        horas = {(h, l): n for h, l, n in con.execute(
            "SELECT hora, logado, count(*) FROM acessos WHERE dia > ? AND dia <= ? GROUP BY hora, logado",
            ((hoje - timedelta(days=7)).isoformat(), d)).fetchall()}
        contas_novas = contar("SELECT count(*) FROM usuarios WHERE criado_em >= ? AND criado_em < ?", inicio, fim)
        total_contas = contar("SELECT count(*) FROM usuarios")
        interacoes = (contar("SELECT count(*) FROM curtidas WHERE criado_em >= ? AND criado_em < ?", inicio, fim)
                      + contar("SELECT count(*) FROM respostas WHERE criado_em >= ? AND criado_em < ?", inicio, fim))
    por_hora = [{"hora": h, "logados": round(horas.get((h, 1), 0) / 7, 1), "visitantes": round(horas.get((h, 0), 0) / 7, 1)}
                for h in range(24)]
    pico = max(por_hora, key=lambda x: x["logados"] + x["visitantes"])
    return {
        "hoje": hoje_dados,
        "ontem_acessos": ontem_acessos,
        "variacao_pct": round(100 * (hoje_dados["acessos"] - ontem_acessos) / ontem_acessos) if ontem_acessos else None,
        "contas_novas_hoje": contas_novas,
        "total_contas": total_contas,
        "interacoes_hoje": interacoes,
        "por_dia": por_dia,
        "por_hora": por_hora,
        "pico_hora": pico["hora"] if pico["logados"] + pico["visitantes"] else None,
    }
