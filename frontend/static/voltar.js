/* Botão de voltar das páginas de documento (Privacidade, Termos).
 *
 * O destino depende de onde a página foi aberta: veio de outra página do
 * próprio site, volta para ela; veio de fora ou foi aberta direto pela URL,
 * cai em /inicio. Aberta em aba nova o histórico não tem entrada anterior e o
 * history.back() não faz nada — por isso o temporizador cobre esse caso, senão
 * o botão ficaria morto justamente quando o rodapé abre em aba nova.
 */

(function () {
  const botao = document.querySelector("[data-voltar]");
  if (!botao) return;

  const veioDoSite = (function () {
    try {
      return !!document.referrer && new URL(document.referrer).origin === location.origin;
    } catch {
      return false;
    }
  })();

  botao.addEventListener("click", function () {
    if (!veioDoSite) {
      location.assign("/inicio");
      return;
    }

    const partiuDe = location.href;
    history.back();

    setTimeout(function () {
      if (location.href === partiuDe) location.assign("/inicio");
    }, 400);
  });
})();
