"""
Cena animada da fazenda para a interface.

- Modo "agora": a cena segue as leituras dos controles (luz, temperatura, umidade) e a decisão fuzzy.
- Modo "dia": 24 horas simuladas em passos de 15 min. O controlador fuzzy é consultado a cada hora;
  a umidade do solo cai com a evaporação (luz e calor) e sobe com a rega decidida.

O balanço de água é um modelo ilustrativo, só para a demonstração: não foi calibrado com dados reais.
"""
import json

import numpy as np

import fuzzy_irrigacao as fz

# parâmetros do balanço de água (ilustrativos), em pontos de umidade por passo de 15 min
GANHO_POR_MIN = 0.6     # ganho por minuto de bomba a 100% de vazão
EVAP_BASE = 0.08        # perda mínima (noite)
EVAP_LUZ = 0.5          # perda extra com sol pleno
EVAP_CALOR = 0.015      # perda extra por °C acima de 20 °C
CONSULTA_A_CADA = 4     # passos entre consultas ao controlador (4 x 15 min = 1 h)


def simular_dia(u0: float):
    u, resto, vaz, tempo_dec = float(u0), 0.0, 0.0, 0.0
    serie = []
    for i in range(96):
        h = i * 0.25
        sol, temp = fz.hora_para_cenario(h)
        if resto <= 0 and i % CONSULTA_A_CADA == 0:
            r = fz.inferir(u, temp, sol)
            tempo_dec, vaz = r["saida"]["tempo"]["valor"], r["saida"]["vazao"]["valor"]
            resto = tempo_dec
        minutos = min(15.0, resto) if resto > 0 else 0.0
        resto -= minutos
        serie.append(dict(h=h, u=round(u, 2), t=round(temp, 1), s=round(sol), min=round(minutos, 2),
                          vazao=round(vaz if minutos > 0 else 0, 1), tempo=round(tempo_dec, 1), vdec=round(vaz, 1)))
        perda = EVAP_BASE + EVAP_LUZ * sol / 1000 + EVAP_CALOR * max(temp - 20, 0)
        u = float(np.clip(u + GANHO_POR_MIN * vaz / 100 * minutos - perda, 0, 100))
    return serie


def html_cena(agora: dict, serie: list) -> str:
    dados = json.dumps({"agora": agora, "dia": serie})
    return HTML.replace("__DADOS__", dados)


HTML = r"""
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600&family=Atkinson+Hyperlegible:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root { --musgo:#183A37; --agua:#1F7A8C; --sol:#E2A93B; --noite:#2E3A6E; --argila:#B4533C; --cinza:#5E716D; --linha:#C9D5D6; --nevoa:#EAF0F2; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:'Atkinson Hyperlegible',system-ui,sans-serif; color:var(--musgo); background:transparent; }
  .cena { width:100%; border-radius:14px; overflow:hidden; display:block; background:#0d1430; }
  svg { display:block; width:100%; height:auto; }
  .painel { display:grid; grid-template-columns: repeat(5, minmax(0,1fr)); gap:1px; background:var(--linha);
            border:1px solid var(--linha); border-radius:12px; overflow:hidden; margin-top:12px; }
  .painel div { background:#fff; padding:10px 14px; }
  .painel b { display:block; font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:1.22rem;
              font-variant-numeric:tabular-nums; line-height:1.1; }
  .painel span { color:var(--cinza); font-size:.85rem; }
  .painel .bomba b { color:var(--cinza); }
  .painel .bomba.on b { color:var(--agua); }
  .controles { display:flex; flex-wrap:wrap; gap:10px; align-items:center; margin-top:12px; }
  button { font:inherit; font-weight:700; border:0; border-radius:10px; padding:.6rem 1rem; cursor:pointer;
           background:var(--musgo); color:#fff; }
  button.sec { background:#fff; color:var(--musgo); border:1px solid var(--linha); }
  button:focus-visible, input:focus-visible, select:focus-visible { outline:3px solid var(--sol); outline-offset:2px; }
  input[type=range] { flex:1; min-width:180px; accent-color:var(--agua); }
  select { font:inherit; padding:.5rem; border-radius:10px; border:1px solid var(--linha); background:#fff; color:var(--musgo); }
  .hora { font-family:'Bricolage Grotesque',sans-serif; font-weight:600; font-size:1.25rem; min-width:4.2rem;
          font-variant-numeric:tabular-nums; }
  .grafico { margin-top:10px; }
  .nota { color:var(--cinza); font-size:.85rem; margin:.4rem 0 0; }
  @media (max-width:640px) { .painel { grid-template-columns: repeat(2, minmax(0,1fr)); } .painel b { font-size:1.2rem; } .painel .bomba { grid-column: 1 / -1; } }
</style></head><body>

<div class="cena">
<svg id="svg" viewBox="0 0 1000 440" role="img" aria-label="Cena da fazenda com o sistema de irrigação">
  <defs>
    <linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1">
      <stop id="ceuTopo" offset="0"/><stop id="ceuBase" offset="1"/>
    </linearGradient>
    <radialGradient id="brilho"><stop offset="0" stop-color="#FFE7A6" stop-opacity=".9"/><stop offset="1" stop-color="#FFE7A6" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="1000" height="440" fill="url(#ceu)"/>
  <g id="estrelas"></g>
  <circle id="brilhoSol" r="90" fill="url(#brilho)"/>
  <circle id="sol" r="30" fill="#F6C453"/>
  <g id="lua"><circle r="22" fill="#E8ECF4"/><circle r="20" cx="9" cy="-6" fill="#0d1430" id="luaSombra"/></g>
  <!-- morros -->
  <path d="M0 250 C 160 200 300 215 420 240 C 560 268 700 205 1000 230 L1000 440 L0 440Z" fill="#3E6B4E" id="morro1"/>
  <path d="M0 275 C 220 245 420 262 620 270 C 780 276 900 255 1000 262 L1000 440 L0 440Z" fill="#2F5A40" id="morro2"/>
  <!-- casa da bomba e caixa d'água -->
  <g transform="translate(70 230)">
    <rect x="0" y="20" width="70" height="52" fill="#E9E2D3"/><path d="M-6 22 L35 -4 L76 22Z" fill="#8A4B39"/>
    <rect x="26" y="44" width="18" height="28" fill="#5B4030"/>
    <circle id="luzBomba" cx="58" cy="34" r="6" fill="#7F8C8A"/>
    <rect x="86" y="-28" width="40" height="46" rx="4" fill="#9FB3BE"/><rect x="92" y="18" width="4" height="54" fill="#6B7B80"/><rect x="116" y="18" width="4" height="54" fill="#6B7B80"/>
  </g>
  <!-- campo -->
  <path id="solo" d="M150 440 L330 300 L1000 300 L1000 440Z"/>
  <path id="cano" d="M140 302 L330 302" stroke="#24403C" stroke-width="5" fill="none"/>
  <g id="linhas"></g>
  <g id="gotas"></g>
  <g id="plantas"></g>
  <text id="rotuloHora" x="970" y="40" text-anchor="end" font-family="Bricolage Grotesque, sans-serif" font-size="30" font-weight="600" fill="#fff"></text>
</svg>
</div>

<div class="painel" aria-live="polite">
  <div><b id="vHora">agora</b><span id="lHora">leituras dos controles</span></div>
  <div><b id="vUmid">–</b><span>umidade do solo</span></div>
  <div><b id="vTemp">–</b><span>temperatura e luz</span></div>
  <div><b id="vDec">–</b><span id="lDec">decisão do fuzzy</span></div>
  <div class="bomba" id="cBomba"><b id="vBomba">–</b><span id="lBomba">bomba</span></div>
</div>

<div class="controles">
  <button id="play">Simular um dia</button>
  <button class="sec" id="voltar" hidden>Voltar às leituras atuais</button>
  <span class="hora" id="hTxt">00:00</span>
  <input id="scrub" type="range" min="0" max="95" step="1" value="0" aria-label="Hora do dia simulado">
  <select id="vel" aria-label="Velocidade">
    <option value="60">1 dia em 60 s</option><option value="30" selected>1 dia em 30 s</option><option value="15">1 dia em 15 s</option>
  </select>
</div>
<svg class="grafico" id="graf" viewBox="0 0 1000 120" role="img" aria-label="Umidade do solo e regas ao longo do dia simulado"></svg>
<p class="nota">No dia simulado, o fuzzy é consultado a cada hora. A umidade do solo segue um modelo simples de evaporação e rega, só para ilustrar.</p>

<script>
const D = __DADOS__;
const reduz = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const el = (tag, attrs, pai) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (pai) pai.appendChild(e); return e; };
const mix = (a, b, t) => { t = Math.max(0, Math.min(1, t)); const p = x => [1,3,5].map(i => parseInt(x.slice(i, i+2), 16));
  const A = p(a), B = p(b); return '#' + A.map((v, i) => Math.round(v + (B[i]-v)*t).toString(16).padStart(2,'0')).join(''); };
const br = (x, c=1) => x.toFixed(c).replace('.', ',');

// estrelas fixas
for (let i = 0; i < 70; i++) el('circle', {cx: (i*137.5) % 1000, cy: 10 + ((i*71) % 190), r: (i % 3 === 0) ? 1.6 : 1, fill:'#fff'}, $('estrelas'));

// fileiras: linhas de gotejamento e plantas, em perspectiva
const FILEIRAS = [ {y:318, x0:315, s:.55}, {y:348, x0:276, s:.7}, {y:384, x0:230, s:.85}, {y:424, x0:178, s:1} ];
const emissores = [], fluxos = [], manchas = [];
fluxos.push(el('line', {x1:140, y1:302, x2:330, y2:302, stroke:'#8FD3E6', 'stroke-width':2.4, 'stroke-dasharray':'8 12', opacity:0}, $('linhas')));
FILEIRAS.forEach((f, k) => {
  el('line', {x1:f.x0, y1:f.y-14*f.s, x2:1000, y2:f.y-14*f.s, stroke:'#24403C', 'stroke-width':2.6*f.s}, $('linhas'));
  el('line', {x1:f.x0-10, y1:302, x2:f.x0, y2:f.y-14*f.s, stroke:'#24403C', 'stroke-width':2.6*f.s}, $('linhas'));
  fluxos.push(el('line', {x1:f.x0, y1:f.y-14*f.s, x2:1000, y2:f.y-14*f.s, stroke:'#8FD3E6', 'stroke-width':1.6*f.s,
                          'stroke-dasharray':`${6*f.s} ${12*f.s}`, opacity:0}, $('linhas')));
  const passo = 70 * f.s + 18;
  for (let x = f.x0 + 30; x < 990; x += passo) {
    const g = el('g', {transform:`translate(${x} ${f.y}) scale(${f.s})`}, $('plantas'));
    el('ellipse', {cx:0, cy:2, rx:16, ry:4, fill:'#000', opacity:.12}, g);
    manchas.push(el('ellipse', {cx:0, cy:3, rx:22, ry:6, fill:'#2A1C14', opacity:0}, g));
    const folhas = el('g', {}, g);
    [[-1, -28], [1, -24], [0, -36]].forEach(([lado, alt]) =>
      el('path', {d:`M0 0 Q ${lado*16} ${alt*0.6} ${lado*10} ${alt}`, stroke:'#4E9A5B', 'stroke-width':5, fill:'none', 'stroke-linecap':'round', class:'folha', 'data-lado':lado}, folhas));
    emissores.push({x: x, y0: f.y - 14*f.s, y1: f.y - 2, s: f.s});
  }
});

// gotas: um conjunto reaproveitado
const GOTAS = [];
for (let i = 0; i < 220; i++) GOTAS.push({ e: el('circle', {r:3, fill:'#BFE9F5', stroke:'#2F8FA6', 'stroke-width':.8, opacity:0}, $('gotas')), vivo:false });
let intensidade = 0;   // 0..1, vem da vazão
let deslocamento = 0;
function pingar(dt) {
  deslocamento -= dt * (20 + 80 * intensidade);
  fluxos.forEach(l => { l.setAttribute('opacity', intensidade > 0 ? .95 : 0); if (!reduz) l.setAttribute('stroke-dashoffset', deslocamento); });
  manchas.forEach(m => m.setAttribute('opacity', (intensidade > 0 ? .25 + .35 * intensidade : 0).toFixed(2)));
  if (reduz) { GOTAS.forEach((g, i) => { const em = emissores[i % emissores.length];
      g.e.setAttribute('opacity', (intensidade > 0 && i < emissores.length) ? .9 : 0);
      g.e.setAttribute('cx', em.x); g.e.setAttribute('cy', (em.y0+em.y1)/2); }); return; }
  const taxa = intensidade * 260;          // gotas por segundo
  let novas = taxa * dt;
  while (novas > 0) {
    if (Math.random() < Math.min(1, novas)) {
      const g = GOTAS.find(q => !q.vivo); if (!g) break;
      const em = emissores[Math.floor(Math.random()*emissores.length)];
      Object.assign(g, {vivo:true, x:em.x + (Math.random()-.5)*4, y:em.y0, y1:em.y1, v:25 + 15*em.s, s:em.s});
    }
    novas -= 1;
  }
  GOTAS.forEach(g => { if (!g.vivo) return;
    g.y += g.v * dt; g.v += 160 * dt;
    if (g.y >= g.y1) { g.vivo = false; g.e.setAttribute('opacity', 0); return; }
    g.e.setAttribute('cx', g.x); g.e.setAttribute('cy', g.y); g.e.setAttribute('r', 3.4*g.s); g.e.setAttribute('opacity', .95); });
}

function desenhar(st) {
  const luz = st.s / 1000;
  // céu
  const crep = Math.max(0, 1 - Math.abs(luz - .18) / .18);   // tom de entardecer perto do horizonte
  $('ceuTopo').setAttribute('stop-color', mix('#0D1430', '#6FA9CF', Math.pow(luz, .7)));
  $('ceuBase').setAttribute('stop-color', mix(mix('#2E3A6E', '#D6ECF2', Math.pow(luz, .6)), '#F0B27A', crep * .7));
  $('estrelas').setAttribute('opacity', Math.max(0, 1 - luz * 5));
  // sol e lua
  let sx, sy;
  if (st.h !== null && st.h !== undefined) {
    const f = (st.h - 6) / 12; sx = 80 + 840 * f; sy = 290 - 240 * Math.sin(Math.PI * Math.max(0, Math.min(1, f)));
  } else { sx = 780; sy = 290 - 240 * luz; }
  const solVis = luz > 0.005;
  ['sol', 'brilhoSol'].forEach(id => { $(id).setAttribute('cx', sx); $(id).setAttribute('cy', sy); $(id).setAttribute('opacity', solVis ? 1 : 0); });
  let mx = 220, my = 90;
  if (st.h !== null && st.h !== undefined) {
    const fn = ((st.h - 18 + 24) % 24) / 12;          // 0 às 18h, 1 às 6h
    mx = 80 + 840 * Math.min(1, fn); my = 270 - 190 * Math.sin(Math.PI * Math.min(1, fn));
  }
  $('lua').setAttribute('transform', `translate(${mx} ${my})`);
  $('lua').setAttribute('opacity', Math.max(0, 1 - luz * 6));
  $('luaSombra').setAttribute('fill', mix('#0D1430', '#6FA9CF', Math.pow(luz, .7)));
  $('morro1').setAttribute('fill', mix('#1C3328', '#4F8A5F', Math.pow(luz, .6)));
  $('morro2').setAttribute('fill', mix('#15281F', '#3B7049', Math.pow(luz, .6)));
  // solo: seco (claro) a molhado (escuro), escurecido à noite
  const molhado = Math.min(1, st.u / 60);
  $('solo').setAttribute('fill', mix(mix('#C9A27A', '#5B4030', molhado), '#1E1712', (1 - Math.pow(luz, .5)) * .55));
  // plantas murcham com solo seco
  const murcha = Math.max(0, (22 - st.u) / 22);
  document.querySelectorAll('.folha').forEach(p => { const l = +p.dataset.lado;
    p.setAttribute('transform', `rotate(${l * murcha * 35})`);
    p.setAttribute('stroke', mix(mix('#4E9A5B', '#A3A04A', murcha), '#1F3B24', (1 - Math.pow(luz, .5)) * .5)); });
  // bomba
  const on = st.vazao > 0;
  intensidade = on ? st.vazao / 100 : 0;
  $('luzBomba').setAttribute('fill', on ? '#5FD38A' : '#7F8C8A');
  // painel
  $('vUmid').textContent = br(st.u, 0) + '%';
  $('vTemp').textContent = br(st.t, 0) + ' °C, LDR ' + Math.round(st.s);
  $('vDec').textContent = st.tempo > 0 ? `${br(st.tempo)} min a ${Math.round(st.vazaoDec)}%` : 'não irrigar';
  $('lDec').textContent = st.h == null ? 'decisão do fuzzy' : 'última decisão do fuzzy';
  $('vBomba').textContent = on ? `ligada a ${Math.round(st.vazao)}%` : 'desligada';
  $('cBomba').classList.toggle('on', on);
}

// gráfico do dia
function grafico(cursor) {
  const g = $('graf'); g.innerHTML = '';
  const X = i => 40 + i * (950 / 95), Y = u => 100 - u * 1.6;
  [0, 25, 50].forEach(v => { el('line', {x1:40, x2:990, y1:Y(v), y2:Y(v), stroke:'#C9D5D6', 'stroke-width':1}, g);
    el('text', {x:32, y:Y(v)+4, 'text-anchor':'end', 'font-size':11, fill:'#5E716D'}, g).textContent = v + '%'; });
  D.dia.forEach((p, i) => { if (p.min > 0) el('rect', {x:X(i)-3, y:Y(0) - p.vazao * .4, width:6, height:p.vazao * .4, fill:'#1F7A8C', opacity:.35}, g); });
  el('polyline', {points: D.dia.map((p, i) => `${X(i)},${Y(p.u)}`).join(' '), fill:'none', stroke:'#183A37', 'stroke-width':2.2}, g);
  [0, 6, 12, 18, 24].forEach(h => el('text', {x:40 + h * (950/24), y:116, 'text-anchor':'middle', 'font-size':11, fill:'#5E716D'}, g).textContent = h + 'h');
  if (cursor !== null) el('line', {x1:X(cursor), x2:X(cursor), y1:8, y2:100, stroke:'#B4533C', 'stroke-width':2}, g);
}

// estados
let modo = 'agora', tocando = false, pos = 0, ultimo = null;
const hhmm = h => String(Math.floor(h)).padStart(2,'0') + ':' + String(Math.round((h % 1) * 60)).padStart(2,'0');
function mostrarAgora() {
  modo = 'agora'; tocando = false; $('play').textContent = 'Simular um dia'; $('voltar').hidden = true;
  $('vHora').textContent = 'agora'; $('lHora').textContent = 'leituras dos controles'; $('rotuloHora').textContent = '';
  const a = D.agora; desenhar({h:null, u:a.u, t:a.t, s:a.s, tempo:a.tempo, vazao:a.vazao, vazaoDec:a.vazao}); grafico(null);
}
function mostrarDia(i) {
  const p = D.dia[i]; $('scrub').value = i; $('hTxt').textContent = hhmm(p.h);
  $('vHora').textContent = hhmm(p.h); $('lHora').textContent = 'dia simulado'; $('rotuloHora').textContent = hhmm(p.h);
  desenhar({h:p.h, u:p.u, t:p.t, s:p.s, tempo:p.tempo, vazao:p.vazao, vazaoDec: p.vdec}); grafico(i);
}
$('play').onclick = () => {
  if (modo === 'agora') { modo = 'dia'; pos = +$('scrub').value; $('voltar').hidden = false; }
  tocando = !tocando; $('play').textContent = tocando ? 'Pausar' : 'Continuar'; mostrarDia(Math.floor(pos));
};
$('voltar').onclick = mostrarAgora;
$('scrub').oninput = e => { modo = 'dia'; $('voltar').hidden = false; pos = +e.target.value; mostrarDia(Math.floor(pos));
  if (!tocando) $('play').textContent = 'Continuar'; };

function quadro(t) {
  const dt = ultimo === null ? 0 : Math.min(.05, (t - ultimo) / 1000); ultimo = t;
  if (modo === 'dia' && tocando) {
    pos += dt * 96 / (+$('vel').value);
    if (pos >= 96) pos = 0;
    mostrarDia(Math.floor(pos));
  }
  pingar(dt);
  requestAnimationFrame(quadro);
}
mostrarAgora();
requestAnimationFrame(quadro);
</script></body></html>
"""
