/* Página de administração. Dados de pessoas e publicações entram só como texto. */
(() => {
  const $ = (id) => document.getElementById(id);
  const raiz = document.documentElement;
  const cor = (nome) => getComputedStyle(raiz).getPropertyValue(`--${nome}`).trim();
  const FONTE = { family: '"JetBrains Mono", ui-monospace, monospace', size: 10 };

  function no(tag, texto, classe) {
    const n = document.createElement(tag);
    if (texto !== undefined && texto !== null) n.textContent = String(texto);
    if (classe) n.className = classe;
    return n;
  }
  function botao(texto, atributo, valor) {
    const b = no("button", texto);
    b.type = "button";
    b.setAttribute(atributo, valor);
    return b;
  }
  async function api(url, method = "GET", dados) {
    const r = await fetch(url, {
      method,
      headers: dados ? { "Content-Type": "application/json" } : {},
      body: dados ? JSON.stringify(dados) : undefined,
    });
    let d;
    try { d = await r.json(); } catch { throw Error("O servidor não respondeu. Tente novamente."); }
    if (!r.ok) throw Error(typeof d.erro === "string" ? d.erro : "Não foi possível concluir a ação.");
    return d;
  }
  function avisar(texto, erro = false) {
    $("adm-aviso").textContent = texto;
    $("adm-aviso").dataset.erro = String(erro);
  }
  const executar = (fn) => async (evento) => {
    if (evento) evento.preventDefault();
    try { await fn(evento); } catch (e) { avisar(e.message, true); }
  };
  const quando = (iso) => new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  const diaCurto = (iso) => { const [, m, d] = iso.split("-"); return `${d}/${m}`; };

  /* ── abas */
  const carregadores = { visao: visaoGeral, blog: publicacoes, admins: administradores, registro };
  function abrirAba(nome) {
    document.querySelectorAll("[data-aba]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.aba === nome)));
    document.querySelectorAll("[data-painel]").forEach((p) => { p.hidden = p.dataset.painel !== nome; });
    avisar("");
    executar(carregadores[nome])();
  }
  document.querySelectorAll("[data-aba]").forEach((b) => b.addEventListener("click", () => abrirAba(b.dataset.aba)));

  /* ── visão geral */
  function cartao(rotulo, valor, detalhe, classeDetalhe) {
    const c = no("div", undefined, "adm-kpi");
    c.dataset.kpi = "";
    c.append(no("span", rotulo, "adm-kpi-rotulo"), no("strong", valor, "adm-kpi-valor"), no("span", detalhe, "adm-kpi-sub " + (classeDetalhe || "")));
    return c;
  }
  const graficos = {};
  let estatisticas = null;
  let periodo = 30;
  const semAnimacao = () => document.hidden || raiz.dataset.movimento === "off" || (!raiz.dataset.movimento && matchMedia("(prefers-reduced-motion: reduce)").matches);
  const guia = {
    id: "admGuia",
    afterDatasetsDraw(chart) {
      const ativo = chart.tooltip?.getActiveElements()[0];
      if (!ativo) return;
      const { ctx, chartArea } = chart;
      ctx.save(); ctx.beginPath(); ctx.setLineDash([4, 4]);
      ctx.strokeStyle = cor("texto-3"); ctx.lineWidth = 1;
      ctx.moveTo(ativo.element.x, chartArea.top); ctx.lineTo(ativo.element.x, chartArea.bottom);
      ctx.stroke(); ctx.restore();
    },
  };
  const pluginsGrafico = () => ({
    legend: { display: true, position: "bottom", align: "start", labels: { color: cor("texto-2"), font: FONTE, usePointStyle: true, pointStyle: "circle", boxWidth: 7, boxHeight: 7, padding: 22 }, onHover(event) { event.native.target.style.cursor = "pointer"; }, onLeave(event) { event.native.target.style.cursor = "default"; } },
    tooltip: { backgroundColor: cor("base-3"), titleColor: cor("texto"), bodyColor: cor("texto-2"), borderColor: cor("linha-forte"), borderWidth: 1, padding: 14, cornerRadius: 4, displayColors: true, usePointStyle: true, callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(ctx.parsed.y)}` } },
  });
  function degradê(contexto) {
    const { ctx, chartArea } = contexto.chart;
    if (!chartArea) return "transparent";
    const gradiente = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
    gradiente.addColorStop(0, `rgb(${cor("primaria-rgb")} / .3)`);
    gradiente.addColorStop(1, `rgb(${cor("primaria-rgb")} / .01)`);
    return gradiente;
  }
  function desenhar(id, config) {
    if (!window.Chart) return;
    const ocultos = graficos[id]?.data.datasets.map((_, i) => !graficos[id].isDatasetVisible(i));
    graficos[id]?.destroy();
    config.plugins = [guia];
    graficos[id] = new Chart($(id), config);
    ocultos?.forEach((oculto, i) => graficos[id].setDatasetVisibility(i, !oculto));
    if (ocultos) graficos[id].update("none");
  }
  const eixos = (empilhado) => ({
    x: { stacked: empilhado, grid: { display: false }, border: { display: false },
         ticks: { color: cor("texto-3"), font: FONTE, maxRotation: 0, autoSkip: true, maxTicksLimit: empilhado ? 12 : 8 } },
    y: { stacked: empilhado, beginAtZero: true, border: { display: false }, grid: { color: cor("linha"), drawTicks: false },
         ticks: { color: cor("texto-3"), font: FONTE, precision: 0, maxTicksLimit: 5, padding: 8 } },
  });
  async function visaoGeral() {
    const d = await api("/api/admin/estatisticas");
    estatisticas = d;
    const v = d.variacao_pct;
    const variacao = v === null ? "sem acessos ontem para comparar" : `${v > 0 ? "+" : ""}${v}% em relação a ontem`;
    $("adm-kpis").replaceChildren(
      cartao("Acessos hoje", d.hoje.acessos, variacao, v > 0 ? "sobe" : v < 0 ? "desce" : ""),
      cartao("Pessoas diferentes", d.hoje.pessoas, `${d.hoje.logadas} logadas · ${d.hoje.visitantes} visitantes`),
      cartao("Contas novas", d.contas_novas_hoje, `total: ${d.total_contas} contas`),
      cartao("Curtidas e comentários", d.interacoes_hoje, "hoje, em todas as publicações"),
    );
    renderizarGraficos();
  }
  function renderizarGraficos() {
    if (!estatisticas) return;
    const d = estatisticas;
    const dias = d.por_dia.slice(-periodo);
    const semMovimento = semAnimacao();
    $("adm-resumo-dias").textContent = `${dias.reduce((s, x) => s + x.acessos, 0).toLocaleString("pt-BR")} acessos nos últimos ${periodo} dias · ${d.total_contas.toLocaleString("pt-BR")} contas na comunidade`;
    desenhar("g-dias", {
      type: "line",
      data: {
        labels: dias.map((x) => diaCurto(x.dia)),
        datasets: [
          { label: "Acessos", data: dias.map((x) => x.acessos), borderColor: cor("primaria-clara"), backgroundColor: degradê, fill: true,
            borderWidth: 3, pointRadius: 0, pointHoverRadius: 6, pointHoverBackgroundColor: cor("primaria-clara"), pointHitRadius: 18, cubicInterpolationMode: "monotone", yAxisID: "y" },
          { label: "Total de contas", data: dias.map((x) => x.contas), borderColor: cor("terciaria"), backgroundColor: cor("terciaria"),
            borderWidth: 2, borderDash: [5, 4], pointRadius: 0, pointHitRadius: 10, stepped: true, yAxisID: "contas" },
        ],
      },
      options: {
        maintainAspectRatio: false, animation: semMovimento ? false : { duration: 850, easing: "easeOutQuart" },
        interaction: { mode: "index", intersect: false },
        scales: { ...eixos(false), contas: { position: "right", beginAtZero: true, border: { display: false }, grid: { display: false },
                  ticks: { color: cor("texto-3"), font: FONTE, precision: 0, maxTicksLimit: 5 } } },
        plugins: pluginsGrafico(),
      },
    });
    $("g-dias").setAttribute("aria-label", `Últimos ${periodo} dias: ${dias.reduce((s, x) => s + x.acessos, 0)} acessos; ${d.total_contas} contas no total.`);
    desenhar("g-horas", {
      type: "bar",
      data: {
        labels: d.por_hora.map((x) => `${x.hora}h`),
        datasets: [
          { label: "Logados", data: d.por_hora.map((x) => x.logados), backgroundColor: cor("primaria-clara"), borderRadius: 4, maxBarThickness: 24, hoverBackgroundColor: cor("terciaria") },
          { label: "Visitantes", data: d.por_hora.map((x) => x.visitantes), backgroundColor: `rgb(${cor("primaria-rgb")} / .3)`, borderRadius: 4, maxBarThickness: 24, hoverBackgroundColor: cor("primaria-clara") },
        ],
      },
      options: { maintainAspectRatio: false, animation: semMovimento ? false : { duration: 800, easing: "easeOutQuart" },
                 interaction: { mode: "index", intersect: false }, scales: eixos(true), plugins: pluginsGrafico() },
    });
    $("pico").textContent = d.pico_hora === null ? "ainda sem acessos nos últimos 7 dias" : `pico às ${d.pico_hora}h`;
  }
  document.querySelectorAll("[data-periodo]").forEach((b) => b.addEventListener("click", () => {
    periodo = Number(b.dataset.periodo);
    document.querySelectorAll("[data-periodo]").forEach((item) => item.setAttribute("aria-pressed", String(item === b)));
    renderizarGraficos();
  }));
  window.addEventListener("spectra:tema", renderizarGraficos);
  window.addEventListener("spectra:movimento", renderizarGraficos);
  document.addEventListener("visibilitychange", () => {
    raiz.toggleAttribute("data-admin-pausado", document.hidden);
    if (document.hidden) Object.values(graficos).forEach((g) => g.stop());
  });

  /* ── blog e avisos */
  let editando = null;
  function modoEdicao(p) {
    editando = p ? p.id : null;
    const enviar = $("form-publicar").querySelector("[type=submit]");
    enviar.textContent = p ? "Salvar edição" : "Publicar";
    document.querySelectorAll("#form-publicar [name=tipo]").forEach((r) => { r.disabled = !!p; if (p) r.checked = r.value === p.tipo; });
    $("pub-capa").disabled = !!p;
    $("pub-titulo").value = p ? p.titulo : "";
    $("pub-texto").value = p ? p.texto : "";
    if (p) $("pub-titulo").focus();
  }
  async function enviarCapa() {
    const arquivo = $("pub-capa").files[0];
    if (!arquivo) return [];
    if (!["image/png", "image/jpeg", "image/webp"].includes(arquivo.type)) throw Error("Use uma capa PNG, JPEG ou WebP.");
    if (arquivo.size > 10 * 1024 * 1024) throw Error("A capa pode ter no máximo 10 MB.");
    const r = await fetch("/api/midias", { method: "POST", headers: { "Content-Type": arquivo.type }, body: arquivo });
    const d = await r.json();
    if (!r.ok) throw Error(d.erro || "Não foi possível enviar a capa.");
    return [d.id];
  }
  $("form-publicar").addEventListener("submit", executar(async () => {
    const enviar = $("form-publicar").querySelector("[type=submit]");
    enviar.disabled = true;
    try {
      const corpo = { titulo: $("pub-titulo").value, texto: $("pub-texto").value };
      if (editando) {
        await api(`/api/publicacoes/${encodeURIComponent(editando)}`, "PUT", corpo);
        avisar("Publicação atualizada.");
      } else {
        const tipo = document.querySelector("#form-publicar [name=tipo]:checked").value;
        await api(`/api/comunidade/${tipo}`, "POST", { ...corpo, midias: await enviarCapa() });
        avisar(tipo === "aviso" ? "Aviso publicado e fixado no topo do site." : "Post publicado no blog.");
      }
      $("form-publicar").reset();
      modoEdicao(null);
      await publicacoes();
    } finally { enviar.disabled = false; }
  }));
  async function publicacoes() {
    const lista = await api("/api/admin/publicacoes");
    const alvo = $("adm-publicacoes");
    alvo.replaceChildren();
    if (!lista.length) alvo.append(no("li", "Nada publicado ainda.", "adm-vazio"));
    for (const p of lista) {
      const item = no("li", undefined, "adm-item");
      item.dataset.pub = p.id;
      item.dataset.fixado = String(p.fixado);
      const info = no("div");
      const selos = no("div", undefined, "adm-selos");
      selos.append(no("span", p.tipo === "aviso" ? "Aviso" : "Blog", "adm-tag adm-tag-" + p.tipo));
      if (p.fixado) selos.append(no("span", "Fixado", "adm-tag adm-tag-fixado"));
      info.append(selos, no("strong", p.titulo), no("small", `♥ ${p.curtidas} · ${p.respostas} comentário(s) · por ${p.autor_nome} · ${quando(p.criado_em)}`));
      const acoes = no("div", undefined, "adm-acoes");
      const editar = botao("Editar", "data-editar", p.id);
      editar.onclick = () => modoEdicao(p);
      const fixar = botao(p.fixado ? "Desafixar" : "Fixar", "data-fixar", p.id);
      fixar.onclick = executar(async () => {
        await api(`/api/publicacoes/${encodeURIComponent(p.id)}/fixar`, "POST", { fixado: !p.fixado });
        await publicacoes();
      });
      const excluir = botao("Excluir", "data-excluir", p.id);
      excluir.className = "adm-perigo";
      excluir.onclick = executar(async () => {
        if (!confirm(`Excluir "${p.titulo}" com curtidas e comentários?`)) return;
        await api(`/api/publicacoes/${encodeURIComponent(p.id)}`, "DELETE");
        await publicacoes();
      });
      acoes.append(editar, fixar, excluir);
      item.append(info, acoes);
      alvo.append(item);
    }
  }

  /* ── administradores (só master) */
  function linhaConta(c, acao) {
    const item = no("li", undefined, "adm-item");
    const info = no("div");
    info.append(no("strong", c.nome), no("small", `${c.email} · ${c.email_verificado ? "e-mail confirmado" : "e-mail não confirmado"}`));
    const papel = no("span", c.papel, "adm-tag adm-tag-" + c.papel);
    item.append(info, papel);
    if (acao) item.append(acao);
    return item;
  }
  async function administradores() {
    const lista = await api("/api/admin/admins");
    $("lista-admins").replaceChildren(...lista.map((c) => {
      if (c.papel !== "admin") return linhaConta(c);
      const tirar = botao("Tirar admin", "data-rebaixar", c.id);
      tirar.className = "adm-perigo";
      tirar.onclick = executar(async () => {
        if (!confirm(`Tirar ${c.nome} da administração?`)) return;
        await api(`/api/admin/admins/${encodeURIComponent(c.id)}`, "DELETE");
        avisar(`${c.nome} voltou a ser membro.`);
        await administradores();
      });
      return linhaConta(c, tirar);
    }));
  }
  $("form-busca").addEventListener("submit", executar(async () => {
    const lista = await api("/api/admin/contas?busca=" + encodeURIComponent($("busca-conta").value));
    const alvo = $("resultado-contas");
    alvo.replaceChildren();
    if (!lista.length) alvo.append(no("li", "Nenhuma conta encontrada.", "adm-vazio"));
    for (const c of lista) {
      let acao;
      if (c.papel === "membro") {
        acao = botao("Promover a admin", "data-promover", c.id);
        acao.onclick = executar(async () => {
          await api(`/api/admin/admins/${encodeURIComponent(c.id)}`, "POST");
          avisar(`${c.nome} agora é admin.`);
          alvo.replaceChildren();
          await administradores();
        });
      }
      alvo.append(linhaConta(c, acao));
    }
  }));

  /* ── registro de ações */
  const FRASES = {
    promover: (a, b) => `${a} promoveu ${b} a admin`,
    rebaixar: (a, b) => `${a} tirou ${b} da administração`,
    tornar_master: (a, b) => `${a} tornou ${b} admin master`,
    remover_master: (a, b) => `${a} removeu ${b} do papel de master`,
    publicar_blog: (a, b) => `${a} publicou no blog: ${b}`,
    publicar_aviso: (a, b) => `${a} publicou um aviso: ${b}`,
    editar: (a, b) => `${a} editou: ${b}`,
    fixar: (a, b) => `${a} fixou: ${b}`,
    desafixar: (a, b) => `${a} desafixou: ${b}`,
    excluir: (a) => `${a} excluiu uma publicação`,
  };
  async function registro() {
    const lista = await api("/api/admin/registro");
    const alvo = $("lista-registro");
    alvo.replaceChildren();
    if (!lista.length) alvo.append(no("li", "Nenhuma ação registrada ainda.", "adm-vazio"));
    for (const r of lista) {
      const frase = (FRASES[r.acao] || ((a) => `${a}: ${r.acao}`))(r.autor_nome, r.alvo_nome);
      const item = no("li", undefined, "adm-item");
      const tempo = no("time", quando(r.criado_em));
      tempo.dateTime = r.criado_em;
      item.append(no("span", frase), tempo);
      alvo.append(item);
    }
  }

  /* ── início */
  executar(async () => {
    const eu = await (window.spectraCarregarPerfil ? window.spectraCarregarPerfil() : api("/api/perfil"));
    $("adm-papel").textContent = eu.master ? "Admin master" : "Admin";
    document.querySelector("[data-aba=admins]").hidden = !eu.master;
    await visaoGeral();
  })();
})();
