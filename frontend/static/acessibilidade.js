/* Acessibilidade — tema claro/escuro, tamanho de fonte e alto contraste.
 *
 * Mesmo padrão de movimento.js: roda cedo, sem `defer`, para aplicar os
 * atributos em <html> antes da primeira pintura (evita flash de tema
 * errado). A escolha de cada pessoa fica em localStorage e vale para todas
 * as páginas do site.
 *
 * O controle de "reduzir movimento" não mora aqui: já existe em
 * movimento.js (`data-movimento`, tecla localStorage "spectra:movimento") e
 * esta barra só reaproveita aquele botão/estado, para não duplicar lógica.
 */

(function () {
  const CHAVE_TEMA = "spectra:tema";
  const CHAVE_FONTE = "spectra:fonte";
  const CHAVE_CONTRASTE = "spectra:contraste";
  const raiz = document.documentElement;

  const NIVEIS_FONTE = [87.5, 93.75, 100, 112.5, 125, 137.5, 150];
  const NIVEL_PADRAO = 2; // índice de 100%

  function lerNumero(chave, padrao) {
    try {
      const bruto = localStorage.getItem(chave);
      // Number(null) e Number("") dão 0, que é um nível válido (87,5%).
      if (bruto === null || bruto.trim() === "") return padrao;
      const v = Number(bruto);
      return Number.isInteger(v) && v >= 0 && v < NIVEIS_FONTE.length ? v : padrao;
    } catch {
      return padrao;
    }
  }

  function lerEscolha(chave) {
    try {
      return localStorage.getItem(chave);
    } catch {
      return null;
    }
  }

  function gravar(chave, valor) {
    try {
      localStorage.setItem(chave, valor);
    } catch {
      /* navegação privada ou armazenamento bloqueado: vale só nesta visita */
    }
  }

  function aplicarTema(tema) {
    raiz.dataset.tema = tema;
    // O ícone da aba acompanha a escolha do site, inclusive quando difere do sistema.
    document.querySelectorAll('link[rel="icon"]').forEach(icone => {
      icone.href = '/static/logo-spectra-' + (tema === 'claro' ? 'claro' : 'escuro') + '.svg';
    });
  }

  function aplicarFonte(nivel) {
    raiz.style.fontSize = NIVEIS_FONTE[nivel] + "%";
    raiz.dataset.nivelFonte = String(nivel);
  }

  function aplicarContraste(estado) {
    raiz.dataset.altoContraste = estado;
  }

  // O escuro é o tema original: só vira claro por escolha da própria pessoa.
  let tema = lerEscolha(CHAVE_TEMA) === "claro" ? "claro" : "escuro";
  let nivelFonte = lerNumero(CHAVE_FONTE, NIVEL_PADRAO);
  let contraste = lerEscolha(CHAVE_CONTRASTE) || "off";

  aplicarTema(tema);
  aplicarFonte(nivelFonte);
  aplicarContraste(contraste);

  function atualizarRotulos() {
    document.querySelectorAll("[data-a11y-tema]").forEach((el) => {
      const acao = `Mudar para o tema ${tema === "claro" ? "escuro" : "claro"}`;
      el.setAttribute("aria-label", acao);
      el.title = acao;
    });
    document.querySelectorAll("[data-a11y-contraste]").forEach((el) => {
      el.setAttribute("aria-pressed", String(contraste === "on"));
    });
    document.querySelectorAll("[data-a11y-fonte-valor]").forEach((el) => {
      el.textContent = `${NIVEIS_FONTE[nivelFonte]}%`;
    });
  }

  // O botão mora no canto superior (parcial conta.html), fora do painel.
  function montarTema() {
    document.querySelector("[data-a11y-tema]")?.addEventListener("click", () => {
      tema = tema === "claro" ? "escuro" : "claro";
      gravar(CHAVE_TEMA, tema);
      aplicarTema(tema);
      window.dispatchEvent(new CustomEvent("spectra:tema", { detail: tema }));
      atualizarRotulos();
    });
  }

  function montarPainel() {
    const host = document.getElementById("a11y-painel");
    if (!host) return;

    host.querySelector("[data-a11y-fonte-mais]")?.addEventListener("click", () => {
      nivelFonte = Math.min(NIVEIS_FONTE.length - 1, nivelFonte + 1);
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-fonte-menos]")?.addEventListener("click", () => {
      nivelFonte = Math.max(0, nivelFonte - 1);
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-fonte-reset]")?.addEventListener("click", () => {
      nivelFonte = NIVEL_PADRAO;
      gravar(CHAVE_FONTE, String(nivelFonte));
      aplicarFonte(nivelFonte);
      atualizarRotulos();
    });

    host.querySelector("[data-a11y-contraste]")?.addEventListener("click", () => {
      contraste = contraste === "on" ? "off" : "on";
      gravar(CHAVE_CONTRASTE, contraste);
      aplicarContraste(contraste);
      // O contraste também troca tokens: gráficos e canvas precisam relê-los.
      window.dispatchEvent(new CustomEvent("spectra:tema", { detail: tema }));
      atualizarRotulos();
    });

    // O painel abre pelo item "Configurações" (barra lateral, menu Mais do
    // celular e rodapé das páginas sem barra lateral). Não há mais botão
    // flutuante arrastável.
    const painel = document.getElementById("a11y-painel");
    const abridores = [...document.querySelectorAll("[data-abrir-configuracoes]")];
    if (!painel) return;
    let origem = null;

    function abrir(mostrar, gatilho) {
      if (mostrar) {
        origem = gatilho || origem;
        // Do menu Mais (um <dialog> modal), fecha a gaveta antes: o resto da página fica inerte enquanto ela está aberta.
        origem?.closest("dialog[open]")?.close();
      }
      painel.hidden = !mostrar;
      abridores.forEach((b) => b.setAttribute("aria-expanded", String(mostrar)));
      if (mostrar) painel.querySelector("button,a")?.focus();
      else if (origem && origem.offsetParent !== null) origem.focus();
    }
    abridores.forEach((b) => b.addEventListener("click", () => abrir(painel.hidden, b)));
    painel.querySelector("[data-a11y-fechar]")?.addEventListener("click", () => abrir(false));
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !painel.hidden) abrir(false);
    });
    document.addEventListener("click", (e) => {
      if (!painel.hidden && !painel.contains(e.target) && !abridores.some((b) => b.contains(e.target))) {
        abrir(false);
      }
    });
  }

  function preencherAno() {
    document.querySelectorAll("[data-ano-atual]").forEach((el) => {
      el.textContent = String(new Date().getFullYear());
    });
  }

  function iniciarIcones() {
    // Um único ponto de disparo para o lucide.createIcons(), já que este
    // script roda em toda página que tem rodapé — evita repetir a chamada
    // em cada arquivo *.js de página.
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons();
    }
  }

  function iniciar() {
    aplicarTema(tema);
    montarTema();
    montarPainel();
    atualizarRotulos();
    preencherAno();
    iniciarIcones();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
