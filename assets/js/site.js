(function () {
  var raiz = document.documentElement;
  // Tema claro/escuro
  var botaoTema = document.getElementById('tema');
  if (botaoTema) botaoTema.addEventListener('click', function () {
    var escuro = raiz.dataset.theme ? raiz.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    raiz.dataset.theme = escuro ? 'light' : 'dark';
    try { localStorage.setItem('tema', raiz.dataset.theme); } catch (e) {}
  });

  // Filtro por categoria
  var filtros = document.querySelectorAll('[data-filtro]');
  filtros.forEach(function (b) {
    b.addEventListener('click', function () {
      filtros.forEach(function (x) { x.classList.remove('ativo'); });
      b.classList.add('ativo');
      var f = b.dataset.filtro, visiveis = 0;
      document.querySelectorAll('#grade .card').forEach(function (c) {
        var ok = f === 'todas' || c.dataset.cat === f;
        c.hidden = !ok; if (ok) visiveis++;
      });
      document.getElementById('vazio').hidden = visiveis > 0;
    });
  });

  // Copiar link
  document.querySelectorAll('[data-copiar]').forEach(function (b) {
    b.addEventListener('click', function () {
      navigator.clipboard && navigator.clipboard.writeText(location.href);
      b.querySelector('span').textContent = 'Link copiado!';
    });
  });

  // Barra de progresso de leitura
  var barra = document.getElementById('progresso');
  if (barra) addEventListener('scroll', function () {
    var h = document.body.scrollHeight - innerHeight;
    barra.style.transform = 'scaleX(' + (h > 0 ? scrollY / h : 0) + ')';
  }, { passive: true });

  // Topo muda ao rolar
  var topo = document.querySelector('.topo');
  addEventListener('scroll', function () { topo.classList.toggle('rolado', scrollY > 10); }, { passive: true });

  // Busca instantânea
  var caixa = document.getElementById('busca'), input = document.getElementById('busca-input'),
      lista = document.getElementById('busca-resultados'), dados = null;
  var base = document.querySelector('link[rel=stylesheet][href*="style.css"]').getAttribute('href').replace(/assets\/css\/style\.css$/, '');
  function norm(s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
  function abrir() {
    caixa.hidden = false; input.value = ''; input.focus(); render('');
    if (!dados) fetch(base + 'search.json').then(function (r) { return r.json(); }).then(function (d) { dados = d; render(input.value); });
  }
  function fechar() { caixa.hidden = true; }
  function render(q) {
    if (!dados) { lista.innerHTML = '<li class="busca__info">Carregando…</li>'; return; }
    var n = norm(q), res = dados.filter(function (p) { return !n || norm(p.t + ' ' + p.d + ' ' + p.c).indexOf(n) > -1; }).slice(0, 8);
    lista.innerHTML = res.length ? res.map(function (p) {
      var li = document.createElement('li'), a = document.createElement('a');
      a.href = p.u; a.innerHTML = '<img alt=""><div><small></small><strong></strong></div>';
      a.querySelector('img').src = p.i; a.querySelector('small').textContent = p.c || ''; a.querySelector('strong').textContent = p.t;
      li.appendChild(a); return li.outerHTML;
    }).join('') : '<li class="busca__info">Nenhuma notícia encontrada.</li>';
  }
  document.querySelectorAll('[data-abrir-busca]').forEach(function (b) { b.addEventListener('click', abrir); });
  document.querySelectorAll('[data-fechar-busca]').forEach(function (b) { b.addEventListener('click', fechar); });
  caixa.addEventListener('click', function (e) { if (e.target === caixa) fechar(); });
  input.addEventListener('input', function () { render(input.value); });
  addEventListener('keydown', function (e) {
    if (e.key === 'Escape') fechar();
    if (e.key === '/' && caixa.hidden && !/input|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); abrir(); }
  });
})();
