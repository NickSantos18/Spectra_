/* Interruptor de movimento — carregado antes de tudo, sem `defer`.
 *
 * As animações começam ligadas na primeira visita. A pessoa pode desligar
 * pelas configurações, e a escolha fica guardada no navegador.
 *
 * Roda cedo de propósito: define o atributo antes da primeira pintura, senão
 * a página começa animando e trava um quadro depois.
 */

(function () {
  const CHAVE = "spectra:movimento";
  const raiz = document.documentElement;

  function lerEscolha() {
    try {
      return localStorage.getItem(CHAVE); // "on" | "off" | null
    } catch {
      return null; // navegação privada ou armazenamento bloqueado
    }
  }

  function aplicar(estado) {
    raiz.dataset.movimento = estado;
    for (const botao of document.querySelectorAll("[data-interruptor-movimento]")) {
      botao.setAttribute("aria-pressed", String(estado === "on"));
      const rotulo = botao.querySelector("[data-rotulo-movimento]");
      if (rotulo) rotulo.textContent = estado === "on" ? "Movimento ligado" : "Movimento parado";
    }
  }

  function resolver() {
    const escolha = lerEscolha();
    if (escolha === "on" || escolha === "off") return escolha;
    return "on";
  }

  aplicar(resolver());

  // A UI só existe depois do DOM; o atributo já foi definido acima.
  document.addEventListener("DOMContentLoaded", () => {
    aplicar(raiz.dataset.movimento);

    for (const botao of document.querySelectorAll("[data-interruptor-movimento]")) {
      botao.addEventListener("click", () => {
        const novo = raiz.dataset.movimento === "on" ? "off" : "on";
        try {
          localStorage.setItem(CHAVE, novo);
        } catch {
          /* sem armazenamento: vale só para esta página */
        }
        aplicar(novo);
        window.dispatchEvent(new CustomEvent("spectra:movimento", { detail: novo }));
      });
    }
  });

  // Consultado por cubos.js e por qualquer efeito em JS.
  window.spectraMovimentoLigado = () => raiz.dataset.movimento === "on";
})();
