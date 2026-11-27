/* Conta global e transição entre documentos, com fallback e redução de movimento. */
(() => {
  const root=document.documentElement, chave='spectra:perfil-transicao',avisoChave='spectra:perfil-movimento-parado';
  const tempos={arredondar:360,deslocar:1250,formulario:450,encaixar:140};
  // movimento.js já resolve a preferência do sistema e a escolha explícita do usuário.
  const movimento=()=>window.spectraMovimentoLigado?window.spectraMovimentoLigado():root.dataset.movimento!=='off';
  const perfilCompacto=()=>window.matchMedia('(max-width: 599px)').matches;
  let pendente=null,navegando=false,iniciou=false,transicaoNativa=null;
  let perfilPromise=null;
  window.spectraCarregarPerfil=(atualizar=false)=>{
    if(atualizar)perfilPromise=null;
    if(!perfilPromise)perfilPromise=fetch('/api/perfil').then(async r=>{
      const dados=await r.json();if(!r.ok)throw Error(dados.erro||'Não foi possível carregar o perfil.');return dados;
    }).catch(erro=>{perfilPromise=null;throw erro;});
    return perfilPromise;
  };
  try{pendente=JSON.parse(sessionStorage.getItem(chave)||'null');sessionStorage.removeItem(chave);}catch{}
  if(location.pathname!=='/painel/perfil'||!pendente||Date.now()-pendente.instante>10000||
    ![pendente.x,pendente.y,pendente.raio,pendente.instante].every(Number.isFinite)||!movimento())pendente=null;
  if(pendente?.perfil)perfilPromise=Promise.resolve(pendente.perfil);

  function limparEntrada(){
    root.classList.remove('perfil-avatar-entrada','perfil-avatar-voando','perfil-transicao-nativa');
    document.querySelectorAll('.perfil-morph').forEach(n=>n.remove());
    delete root.dataset.perfilTransicao;
    window.dispatchEvent(new Event('spectra:perfil-transicao'));
  }
  function origemSalva(){
    try{const valor=JSON.parse(sessionStorage.getItem('spectra:perfil-ultima-origem')||'null');if(valor&&[valor.x,valor.y,valor.raio].every(Number.isFinite))return valor;}catch{}
    return {x:innerWidth-174,y:30,raio:18};
  }
  function face(elemento){
    const img=elemento.tagName==='IMG'?elemento:elemento.querySelector('img');
    const copia=document.createElement(img?'img':'span');
    if(img){copia.src=img.src;copia.alt='';}else{
      const letra=document.createElement('span');letra.className='perfil-glifo';letra.textContent=elemento.textContent;copia.append(letra);
    }
    return copia;
  }
  // Os dados vieram da API autenticada na origem. Preencher antes da primeira
  // pintura permite capturar o perfil pronto, em vez de uma página vazia.
  function prepararPerfil(perfil=pendente?.perfil){
    if(!perfil||!document.getElementById('form-perfil'))return;
    document.getElementById('perfil').hidden=false;
    document.getElementById('titulo').textContent='Perfil';
    document.body.classList.add('com-conta');
    const conta=document.querySelector('[data-conta]');if(conta)conta.hidden=false;
    for(const campo of ['nome','bio'])document.getElementById(campo).value=perfil[campo]||'';
    for(const campo of ['email','ip'])document.getElementById(campo).textContent=perfil[campo]||'';
    document.getElementById('identificador').textContent=perfil.id||'';
    document.getElementById('criado').textContent=perfil.criado_em?new Date(perfil.criado_em).toLocaleString('pt-BR'):'';
    const foto=document.getElementById('foto-preview'),inicial=document.getElementById('foto-inicial');
    foto.hidden=!perfil.foto;inicial.hidden=!!perfil.foto;
    if(perfil.foto)foto.src=perfil.foto;
    inicial.textContent=(perfil.nome||'').trim().slice(0,1).toUpperCase();
    document.getElementById('ajustar-foto').hidden=!perfil.foto;
    document.getElementById('remover-foto').hidden=!perfil.foto;
    document.getElementById('confirmar-email').hidden=perfil.email_verificado||!perfil.email_disponivel;
    document.getElementById('email-estado').textContent=perfil.email_verificado
      ?'E-mail confirmado.':'Seu e-mail ainda não foi confirmado.';
  }
  window.spectraPrepararPerfilInicial=()=>{
    const perfil=JSON.parse(document.getElementById('perfil-inicial').textContent);
    if(!perfil)return;
    perfilPromise=Promise.resolve(perfil);
    if(pendente)pendente.perfil=perfil;
    prepararPerfil(perfil);
    if(perfilCompacto()&&pendente)requestAnimationFrame(()=>revelar().catch(limparEntrada));
  };
  async function revelar(){
    if(!pendente||iniciou)return;
    if(pendente.nativa&&!transicaoNativa&&root.classList.contains('perfil-transicao-nativa'))return;
    const foto=document.getElementById('foto-preview'),inicial=document.getElementById('foto-inicial');
    const alvo=foto&&!foto.hidden?foto:inicial;
    if(!alvo||alvo.hidden||!alvo.getBoundingClientRect().width)return;
    iniciou=true;window.scrollTo(0,0);
    const destino=alvo.getBoundingClientRect();
    const x=Math.max(pendente.raio,Math.min(innerWidth-pendente.raio,pendente.x));
    const y=Math.max(pendente.raio,Math.min(innerHeight-pendente.raio,pendente.y));
    const tamanho=pendente.raio*2;
    const clone=document.createElement('div');clone.className='perfil-morph';clone.setAttribute('aria-hidden','true');clone.append(face(alvo));
    const estiloAlvo=getComputedStyle(alvo);
    const dx=x-pendente.raio-destino.left,dy=y-pendente.raio-destino.top;
    const origemTransform=`translate3d(${dx}px,${dy}px,0) scale(${tamanho/destino.width},${tamanho/destino.height})`;
    // Geometria final é medida uma vez. Durante o voo, só transform muda.
    Object.assign(clone.style,{left:destino.left+'px',top:destino.top+'px',width:destino.width+'px',height:destino.height+'px',borderRadius:'50%',fontSize:estiloAlvo.fontSize,background:estiloAlvo.backgroundColor,color:estiloAlvo.color,transformOrigin:'0 0',transform:transicaoNativa?'none':origemTransform,willChange:'transform'});
    document.body.append(clone);
    root.style.setProperty('--perfil-origem-x',x+'px');root.style.setProperty('--perfil-origem-y',y+'px');
    root.style.setProperty('--perfil-inicio-x',(x-pendente.raio)+'px');
    root.style.setProperty('--perfil-inicio-y',(y-pendente.raio)+'px');
    root.style.setProperty('--perfil-fim-x',destino.left+'px');root.style.setProperty('--perfil-fim-y',destino.top+'px');
    root.style.setProperty('--perfil-largura',destino.width+'px');root.style.setProperty('--perfil-altura',destino.height+'px');
    root.style.setProperty('--perfil-escala-x',tamanho/destino.width);root.style.setProperty('--perfil-escala-y',tamanho/destino.height);
    const glifo=clone.querySelector('.perfil-glifo');
    if(transicaoNativa&&glifo&&pendente.letra){
      const fim=glifo.getBoundingClientRect(),inicio=pendente.letra;
      for(const [nome,valor] of Object.entries({
        'inicio-x':inicio.left+'px','inicio-y':inicio.top+'px','fim-x':fim.left+'px','fim-y':fim.top+'px',
        largura:fim.width+'px',altura:fim.height+'px','escala-x':inicio.width/fim.width,'escala-y':inicio.height/fim.height
      }))root.style.setProperty('--perfil-letra-'+nome,valor);
    }
    root.classList.add('perfil-avatar-voando');root.classList.remove('perfil-avatar-entrada');root.dataset.perfilTransicao='deslocando';
    window.dispatchEvent(new Event('spectra:perfil-transicao'));
    let repetir=false;
    try{
      if(transicaoNativa){
        // O navegador conserva a captura da tela anterior. A mesma superfície
        // do avatar viaja acima das duas telas; o perfil só entra na chegada.
        await transicaoNativa.ready;
        await transicaoNativa.finished;
        return;
      }
      const compacto=perfilCompacto();
      const duracaoVoo=compacto?480:tempos.deslocar;
      if(!compacto){
        const formulario=document.getElementById('form-perfil');
        formulario?.animate([{opacity:0},{opacity:1}],{
          duration:tempos.formulario,delay:800,easing:'ease-in-out',fill:'backwards'
        });
      }
      await clone.animate([
        {transform:origemTransform},
        {transform:'translate3d(0,0,0) scale(1,1)'}
      ],{duration:duracaoVoo,easing:compacto?'cubic-bezier(.25,.1,.25,1)':'cubic-bezier(.45,0,.2,1)',fill:'forwards'}).finished;
      // O avatar real aparece sob a cópia já encaixada, evitando uma troca seca.
      root.dataset.perfilTransicao='encaixando';root.classList.remove('perfil-avatar-voando');
      await clone.animate([{opacity:1},{opacity:0}],{duration:tempos.encaixar,easing:'ease-out',fill:'forwards'}).finished;
    }catch(erro){
      if(transicaoNativa){
        transicaoNativa=null;root.classList.remove('perfil-transicao-nativa');
        repetir=true;
      }else throw erro;
    }finally{limparEntrada();}
    if(repetir){iniciou=false;return revelar();}
  }
  if(pendente){
    root.classList.add('perfil-avatar-entrada');
    if(pendente.nativa)root.classList.add('perfil-transicao-nativa');
    window.addEventListener('pagereveal',e=>{
      if(e.viewTransition&&pendente.nativa){
        transicaoNativa=e.viewTransition;
        prepararPerfil();
        revelar().catch(limparEntrada);
      }else{
        root.classList.remove('perfil-transicao-nativa');
        if(e.viewTransition){e.viewTransition.ready.catch(()=>{});e.viewTransition.skipTransition();}
        prepararPerfil();revelar().catch(limparEntrada);
      }
    },{once:true});
    window.addEventListener('spectra:perfil-pronto',()=>revelar().catch(limparEntrada),{once:true});
    document.addEventListener('DOMContentLoaded',()=>{
      prepararPerfil();
      setTimeout(()=>{if(!iniciou){iniciou=true;limparEntrada();}},2500);
    },{once:true});
  }

  async function abrirPerfil(evento){
    if(evento.button!==0||evento.ctrlKey||evento.metaKey||evento.shiftKey||evento.altKey)return;
    const link=evento.currentTarget,avatar=link.querySelector('[data-conta-inicial]'),rect=avatar.getBoundingClientRect();
    const origem=rect.width?{x:rect.left+rect.width/2,y:rect.top+rect.height/2,raio:rect.width/2,instante:Date.now()}:{...origemSalva(),instante:Date.now()};
    try{sessionStorage.setItem('spectra:perfil-ultima-origem',JSON.stringify(origem));}catch{}
    if(!movimento()){
      try{sessionStorage.setItem(avisoChave,'1');}catch{}
      return;
    }
    if(!Element.prototype.animate)return;
    if(perfilCompacto()){
      // O perfil já busca seus dados ao abrir. No celular o voo acontece
      // inteiro no destino, sem animar antes e ficar parado durante a navegação.
      try{sessionStorage.setItem(chave,JSON.stringify(origem));}catch{}
      return;
    }
    evento.preventDefault();if(navegando)return;navegando=true;
    const clone=document.createElement('div');clone.className='perfil-morph';clone.setAttribute('aria-hidden','true');
    const estilo=getComputedStyle(avatar);
    Object.assign(clone.style,{left:(origem.x-origem.raio)+'px',top:(origem.y-origem.raio)+'px',width:origem.raio*2+'px',height:origem.raio*2+'px'});
    Object.assign(clone.style,{fontSize:estilo.fontSize,background:estilo.backgroundColor,color:estilo.color});
    clone.append(face(avatar));document.body.append(clone);root.dataset.perfilTransicao='arredondando';
    window.dispatchEvent(new Event('spectra:perfil-transicao'));
    try{
      const dados=Promise.race([window.spectraCarregarPerfil(true).catch(()=>null),new Promise(resolve=>setTimeout(()=>resolve(null),1800))]);
      link.animate([{opacity:1},{opacity:0}],{duration:220,delay:120,easing:'ease-in-out',fill:'forwards'});
      await clone.animate([{borderRadius:'0'},{borderRadius:'50%'}],{duration:tempos.arredondar,easing:'cubic-bezier(.4,0,.2,1)',fill:'forwards'}).finished;
      origem.perfil=await dados;origem.instante=Date.now();
      const glifo=clone.querySelector('.perfil-glifo');
      if(glifo){const r=glifo.getBoundingClientRect();origem.letra={left:r.left,top:r.top,width:r.width,height:r.height};}
      origem.nativa=!!origem.perfil&&'onpagereveal' in window;
      if(origem.nativa)root.classList.add('perfil-transicao-nativa');
      try{sessionStorage.setItem(chave,JSON.stringify(origem));}catch{}
      location.assign(link.href);
    }catch{clone.remove();navegando=false;delete root.dataset.perfilTransicao;location.assign(link.href);}
  }

  /* Sininho: avisos de curtidas e comentários. Tudo entra como texto. */
  const FRASES_SINO={
    curtida:n=>`${n.ator_nome} curtiu “${n.publicacao_titulo}”`,
    comentario:n=>`${n.ator_nome} comentou em “${n.publicacao_titulo}”: ${n.trecho}`,
    resposta:n=>`${n.ator_nome} também comentou em “${n.publicacao_titulo}”`,
  };
  function elemento(tag,texto,classe){const n=document.createElement(tag);if(texto!==undefined)n.textContent=texto;if(classe)n.className=classe;return n;}
  async function sino(){
    const botao=document.querySelector('[data-sino]'),lista=document.querySelector('[data-sino-lista]'),contador=document.querySelector('[data-sino-contador]');
    if(!botao||!lista)return;
    const resposta=await fetch('/api/notificacoes');if(!resposta.ok)return;
    const dados=await resposta.json();
    contador.textContent=dados.nao_lidas>99?'99+':String(dados.nao_lidas);contador.hidden=!dados.nao_lidas;
    botao.setAttribute('aria-label',dados.nao_lidas?`Notificações: ${dados.nao_lidas} novas`:'Notificações');
    const ul=lista.querySelector('ul');ul.replaceChildren();
    if(!dados.itens.length)ul.append(elemento('li','Nenhuma notificação ainda.','sino-vazio'));
    for(const n of dados.itens){
      const li=elemento('li');if(!n.lida)li.dataset.nova='';
      const link=elemento('a',(FRASES_SINO[n.tipo]||(()=>n.ator_nome))(n));link.href='/painel/explorar';
      const tempo=elemento('time',new Date(n.criado_em).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}));tempo.dateTime=n.criado_em;
      li.append(link,tempo);ul.append(li);
    }
    const fechar=()=>{lista.hidden=true;botao.setAttribute('aria-expanded','false');};
    botao.onclick=async()=>{
      const abrir=lista.hidden;lista.hidden=!abrir;botao.setAttribute('aria-expanded',String(abrir));
      if(abrir&&!contador.hidden){contador.hidden=true;botao.setAttribute('aria-label','Notificações');try{await fetch('/api/notificacoes/lidas',{method:'POST'});}catch{}}
    };
    document.addEventListener('click',e=>{if(!lista.hidden&&!lista.contains(e.target)&&!botao.contains(e.target))fechar();});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!lista.hidden){fechar();botao.focus();}});
  }
  /* Avisos importantes fixados pelos admins, no topo do conteúdo. */
  async function avisoFixado(){
    const principal=document.querySelector('main');if(!principal)return;
    const resposta=await fetch('/api/avisos');if(!resposta.ok)return;
    const avisos=await resposta.json();if(!avisos.length)return;
    const faixa=elemento('aside',undefined,'aviso-fixado');faixa.dataset.avisoFixado='';faixa.setAttribute('aria-label','Avisos importantes');
    for(const a of avisos){const p=elemento('p');p.append(elemento('strong','Aviso: '+a.titulo),document.createTextNode(' — '+(a.texto.length>240?a.texto.slice(0,240)+'…':a.texto)));faixa.append(p);}
    principal.prepend(faixa);
  }

  async function iniciar(){
    const acesso=document.querySelector('[data-perfil-acesso]');
    if(!acesso)return;
    acesso.addEventListener('click',abrirPerfil);
    document.querySelectorAll('[data-sair]').forEach(b=>b.addEventListener('click',async()=>{
      b.disabled=true;try{const r=await fetch('/api/auth/sair',{method:'POST'});if(!r.ok)throw Error('Falha ao sair');location.assign('/inicio');}
      catch{b.disabled=false;if(window.avisarToast)window.avisarToast('Não foi possível sair. Tente novamente.','erro');}
    }));
    try{
      const resposta=await fetch('/api/auth/eu');if(!resposta.ok)return;
      const {usuario}=await resposta.json();if(!usuario)return;
      document.querySelectorAll('[data-conta-nome]').forEach(n=>n.textContent=usuario.nome);
      document.querySelectorAll('[data-conta-inicial]').forEach(n=>n.textContent=usuario.nome.trim().charAt(0).toUpperCase());
      acesso.setAttribute('aria-label','Abrir perfil de '+usuario.nome);
      document.querySelector('[data-conta]').hidden=false;document.body.classList.add('com-conta');
      let avisar=false;
      try{avisar=sessionStorage.getItem(avisoChave)==='1';sessionStorage.removeItem(avisoChave);}catch{}
      if(avisar&&location.pathname==='/painel/perfil'&&!movimento()){
        const aviso=document.createElement('div');aviso.className='conta-aviso-movimento';aviso.setAttribute('role','status');
        const texto=document.createElement('p');texto.textContent='A animação está desativada nas preferências de movimento.';
        const ativar=document.createElement('button');ativar.type='button';ativar.textContent='Ativar e visualizar';ativar.dataset.ativarTransicao='';
        ativar.onclick=()=>{const controle=document.querySelector('[data-interruptor-movimento]');if(controle){controle.click();aviso.remove();acesso.click();}};
        const fechar=document.createElement('button');fechar.type='button';fechar.textContent='Agora não';fechar.onclick=()=>aviso.remove();
        aviso.append(texto,ativar,fechar);document.querySelector('main')?.prepend(aviso);
      }
      const perfil=await window.spectraCarregarPerfil();
      const admin=document.querySelector('[data-admin-link]');
      if(admin){admin.hidden=!perfil.admin;if(location.pathname==='/admin')admin.setAttribute('aria-current','page');}
      sino().catch(()=>{});avisoFixado().catch(()=>{});
      if(perfil.foto)document.querySelectorAll('[data-conta-inicial]').forEach(n=>{const img=document.createElement('img');img.src=perfil.foto;img.alt='';img.className='conta-foto';n.replaceChildren(img);});
    }catch{ /* O link e a navegação da página permanecem disponíveis. */ }
  }
  window.addEventListener('pageshow',evento=>{
    if(!evento.persisted)return;
    navegando=false;
    document.querySelector('[data-perfil-acesso]')?.getAnimations().forEach(a=>a.cancel());
    limparEntrada();
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',iniciar,{once:true});else iniciar();
})();
