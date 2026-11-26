# Admin, blog, curtidas e avisos — plano de implementação

> **Para quem executa:** use superpowers:executing-plans (execução nativa, decidida pelo usuário ao pedir "já implemente"). Passos com `- [ ]`. Sem commit até o usuário pedir.

**Objetivo:** página `/admin` com papéis master/admin, gráficos de acesso, publicação de blog e avisos; curtidas, comentários e sininho de notificações para todos os membros.

**Arquitetura:** papéis em tabela própria (sem migrar `usuarios`); contagem de acessos anônima feita por middleware nas páginas HTML; APIs novas em `web/admin.py` e `web/interacoes.py`; front-end sem framework, texto sempre por `textContent`, gráficos com o Chart.js já usado na Visão geral.

**Tecnologia:** FastAPI, SQLite (`auth/bd.py`), JavaScript puro, Chart.js 4.4.4 (jsdelivr com SRI), testes pytest + `scripts/verificar_explorar.cjs` (Edge headless).

**Especificação (decidida na conversa de 29/10/2026, esboços em `.superpowers/brainstorm/153-1793281368/content/`):**
- Admin master: vira master só pelo terminal (`python -m spectra_link_guard.admin master <email>`). Pelo site promove e rebaixa admins; ninguém tira o master pelo site.
- Admin: publica blog e avisos, vê gráficos e o registro; não mexe em papéis.
- Quem não é admin e abre `/admin`: vai para a página normal (painel se logado, `/inicio` se não).
- Visão geral: acessos de hoje (+% vs. ontem), pessoas diferentes (logadas/visitantes), contas novas e total, curtidas+comentários de hoje; gráfico diário de 30 dias (acessos e total de contas); gráfico por hora 0–23h (média de 7 dias) separando logados e visitantes, com pico.
- Acessos contados sem guardar IP nem cookie de rastreamento.
- Blog e avisos: tipo "Post do blog" ou "Aviso importante", título, texto, capa opcional; lista com curtidas/comentários e Editar, Fixar/Desafixar, Excluir.
- Aviso importante fica fixado no topo para todo mundo até desafixar.
- Curtir e comentar em todas as publicações (blog, fórum, Explorar); selo ADMIN no autor.
- Sininho avisa o autor quando curtem ou comentam, e avisa quem já comentou quando chega comentário novo na mesma publicação.
- Só admins publicam no blog; o convite de especialistas sai.

**Decisões minhas (não discutidas):** "login recente" = `ultimo_acesso` há no máximo 30 min, exigido para promover/rebaixar; comentários seguem planos (sem respostas aninhadas), então "respondeu" vira "também comentou"; fuso de horários UTC−3 fixo (Brasil sem horário de verão); acessos guardados por 90 dias; página `/admin` não é contada como acesso; aviso novo nasce fixado; APIs de admin respondem 404 para não admins.

## Restrições globais

- Toda SQL com parâmetros `?`; nada de HTML montado com dados de usuário (só `textContent`).
- Mutação em `/api/` passa pela proteção existente (origem, JSON, limites).
- Nenhuma senha de admin fixa em código, `.env` ou chat.
- Esquemas novos via `bd.registrar_esquema`, tabelas novas apenas (bancos existentes não migram colunas).

## Foco de revisão

1. Membro comum chamando APIs de admin direto (sem a tela): 404 em todas.
2. Admin comum tentando promover/rebaixar ou mexer no master: 403/404.
3. Curtir duas vezes / curtir a própria publicação: contagem não duplica; sem notificação para si mesmo.
4. Excluir publicação com curtidas, comentários e notificações: tudo some junto (cascade).
5. Dia sem nenhum acesso no gráfico de 30 dias: aparece com zero, não some do eixo.

---

### Task 1: Papéis e comando de terminal

**Arquivos:** criar `src/spectra_link_guard/auth/papeis.py`, `src/spectra_link_guard/admin.py`; teste `tests/test_admin.py`.

**Interfaces produzidas:**
- tabela `papeis(usuario_id TEXT PK → usuarios ON DELETE CASCADE, papel TEXT CHECK IN ('admin','master'), concedido_por TEXT, concedido_em TEXT)`
- `papeis.papel(usuario_id: str) -> str` ('membro'|'admin'|'master'); `eh_admin(u: dict) -> bool` (admin ou master); `eh_master(u: dict) -> bool`
- `papeis.definir(usuario_id: str, papel: str | None, por: str) -> None` (None = membro)
- `papeis.registrar_acao(autor: str, acao: str, alvo: str = '', detalhe: str = '') -> None` e tabela `admin_registro(id, autor, acao, alvo, detalhe, criado_em)`
- CLI `python -m spectra_link_guard.admin master <email>` (vira master e `email_verificado=1`), `remover-master <email>` (vira membro), `listar`; código de saída 1 se e-mail não existe.

- [ ] Testes: `test_comando_master_promove_e_confirma_email`, `test_comando_master_com_email_inexistente_sai_com_erro`, `test_remover_master_pelo_terminal`, `test_papel_padrao_e_membro` (via `admin.main([...])`, sem subprocesso).
- [ ] Rodar e ver falhar (módulo inexistente). Implementar. Rodar e ver passar.

### Task 2: Blog só para admins, sem convites, papel no perfil e selo do autor

**Arquivos:** `web/comunidade.py`, `tests/test_comunidade.py`, `tests/test_protecoes.py`, `tests/test_admin.py`.

**Interfaces:** `/api/perfil` ganha `papel`, `admin`, `master`; `pode_publicar = admin`; listas de publicações ganham `autor_papel`. Rotas `/api/blog/convites` e `/api/blog/aceitar` removidas; `editor()` e `especialistas` deixam de ser usados.

- [ ] Testes: `test_so_admin_publica_no_blog` (membro 403, admin 201), `test_lista_traz_papel_do_autor`, `test_perfil_informa_papel`, `test_admin_exclui_publicacao_de_membro`; reescrever o teste de convite e o de editor não verificado para o novo papel.
- [ ] Falhar → implementar → passar.

### Task 3: Curtidas e notificações

**Arquivos:** criar `web/interacoes.py` (router incluído no app); modificar `web/comunidade.py` (comentário gera notificação; lista traz `curtidas`, `curtiu`); teste `tests/test_interacoes.py`.

**Interfaces:**
- tabelas `curtidas(publicacao, usuario, criado_em, PK(publicacao,usuario))`, `notificacoes(id, usuario, ator, tipo, publicacao, trecho, lida, criado_em)` com cascade em publicação e usuários
- `POST|DELETE /api/publicacoes/{id}/curtida` → `{"curtido": bool, "curtidas": int}`
- `GET /api/notificacoes` → `{"nao_lidas": int, "itens": [{id, tipo, ator_nome, publicacao, publicacao_titulo, trecho, lida, criado_em}]}` (30 mais recentes); `POST /api/notificacoes/lidas` → `{"ok": true}`
- `interacoes.notificar(con, usuario, ator, tipo, publicacao, trecho='')` (ignora quando usuario == ator)

- [ ] Testes: `test_curtir_conta_uma_vez_e_descurtir`, `test_curtida_notifica_autor_mas_nao_a_si_mesmo`, `test_comentario_notifica_autor_e_quem_ja_comentou`, `test_marcar_notificacoes_como_lidas`, `test_excluir_publicacao_apaga_curtidas_e_notificacoes`, `test_curtir_publicacao_inexistente_404`.
- [ ] Falhar → implementar → passar.

### Task 4: Avisos fixados, edição e registro de ações

**Arquivos:** `web/comunidade.py`, `web/interacoes.py`; teste `tests/test_interacoes.py`.

**Interfaces:**
- tipo `aviso` em `POST /api/comunidade/aviso` (só admin); aviso novo é fixado
- tabela `fixadas(publicacao PK → publicacoes ON DELETE CASCADE, fixado_em)`; `POST /api/publicacoes/{id}/fixar` `{"fixado": bool}` (só admin, só blog/aviso)
- `GET /api/avisos` → até 3 avisos fixados `[{id,titulo,texto,criado_em}]`
- `PUT /api/publicacoes/{id}` `{titulo, texto}` → autor edita a própria; admin edita blog/aviso de qualquer um
- listas trazem `fixado: bool`; ações de admin (publicar blog/aviso, editar, fixar, desafixar, excluir alheio) vão para `admin_registro`

- [ ] Testes: `test_aviso_so_admin_e_nasce_fixado`, `test_desafixar_tira_aviso_do_topo`, `test_editar_propria_publicacao_e_bloquear_alheia`, `test_acoes_de_admin_ficam_registradas`.
- [ ] Falhar → implementar → passar.

### Task 5: Contagem anônima de acessos e estatísticas

**Arquivos:** criar `web/acessos.py`; middleware em `web/app.py`; teste `tests/test_acessos.py`.

**Interfaces:**
- tabelas `acessos(dia TEXT, hora INTEGER, visitante TEXT, logado INTEGER)` e `acessos_sal(dia PK, sal)`; `FUSO = timezone(timedelta(hours=-3))`
- `acessos.registrar(request, usuario_id: str | None, quando: datetime | None = None)`: visitante = sha256(sal do dia + IP + User-Agent)[:16]; sal aleatório por dia, sais e acessos com mais de 90 dias apagados
- middleware conta GET com resposta 200 `text/html`, fora de `/api/`, `/static/`, `/admin`, `/docs`
- `acessos.estatisticas(hoje: date | None = None) -> dict` com `hoje{acessos,pessoas,logadas,visitantes}`, `ontem_acessos`, `variacao_pct` (None se ontem=0), `contas_novas_hoje`, `total_contas`, `interacoes_hoje`, `por_dia` (30 itens, inclusive dias zerados, `{dia, acessos, contas}`), `por_hora` (24 itens `{hora, logados, visitantes}` com média de 7 dias, 1 casa), `pico_hora`

- [ ] Testes: `test_pagina_conta_acesso_e_api_nao_conta`, `test_mesma_pessoa_no_dia_conta_uma_vez_sem_guardar_ip`, `test_estatisticas_por_dia_inclui_dias_zerados`, `test_estatisticas_por_hora_separa_logados`, `test_variacao_sem_acessos_ontem`.
- [ ] Falhar → implementar → passar.

### Task 6: API de admin e rota `/admin`

**Arquivos:** criar `web/admin.py` (router); `web/app.py` (rota da página); teste `tests/test_admin.py`.

**Interfaces:**
- `GET /api/admin/estatisticas` (admin) → `acessos.estatisticas()`
- `GET /api/admin/publicacoes` (admin) → blog e avisos com `curtidas`, `respostas`, `fixado`, `autor_nome`
- `GET /api/admin/registro` (admin) → 100 últimas ações com `autor_nome`
- `GET /api/admin/contas?busca=` (master) → até 20 `{id,nome,email,papel}`
- `POST|DELETE /api/admin/admins/{usuario_id}` (master + login recente) → promove/rebaixa; mexer em master = 403
- não admin em qualquer `/api/admin/*` → 404; `/admin` → 303 para `/painel` (logado) ou `/inicio?erro=entre_primeiro&proximo=%2Fadmin`

- [ ] Testes: `test_pagina_admin_redireciona_quem_nao_e_admin`, `test_api_admin_esconde_de_membro`, `test_admin_comum_nao_promove`, `test_master_promove_e_rebaixa_com_registro`, `test_master_nao_e_rebaixado_pelo_site`, `test_promover_exige_login_recente`.
- [ ] Falhar → implementar → passar.

### Task 7: Página `/admin`

**Arquivos:** criar `web/static/admin.html`, `admin.js`, `admin.css`; teste `scripts/verificar_explorar.cjs --admin`.

Abas Visão geral, Blog e avisos, Admins (só master), Registro de ações, no layout dos esboços. Gráficos com Chart.js; capa enviada por `/api/midias`.

- [ ] Modo `--admin` no verificador: promove a conta de teste via `admin.main`, abre `/admin`, confere 4 indicadores, 2 canvases com gráfico, publica aviso e post, fixa/desafixa, promove outra conta, registro mostra as ações, celular sem rolagem lateral, sem erro de JavaScript.
- [ ] Falhar → implementar → passar.

### Task 8: Curtir, sininho, avisos e selo nas páginas

**Arquivos:** `web/static/comunidade.js`, `comunidade.html`, `comunidade.css`, `parciais/conta.html`, `static/conta.js`, `static/conta.css`; teste `verificar_explorar.cjs` (modo padrão).

- [ ] Verificador padrão: curtir alterna contagem; selo ADMIN; sininho mostra notificação de curtida e zera ao abrir; aviso fixado aparece no topo; link Admin só para admin.
- [ ] Falhar → implementar → passar.

### Task 9: Documentação e verificação final

- [ ] `docs/comunidade.md`, `.env.example`, `README.md`: papéis, comando de terminal, sem `SPECTRA_EDITOR_*`.
- [ ] `pytest -q`, `node --test tests/*.test.cjs`, os 8 modos do verificador.
