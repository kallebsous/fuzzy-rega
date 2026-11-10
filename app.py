"""
Interface interativa do sistema fuzzy de irrigação.
Execute com:  streamlit run app.py
"""
import numpy as np
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import fazenda
import fuzzy_irrigacao as fz

st.set_page_config(page_title="Irrigação fuzzy", page_icon="💧", layout="wide")

# ------------------------------------------------------------------ tokens de design
NEVOA, MUSGO, AGUA, SOL, NOITE, ARGILA = "#EAF0F2", "#183A37", "#1F7A8C", "#E2A93B", "#2E3A6E", "#B4533C"
CINZA, LINHA, BRANCO = "#5E716D", "#C9D5D6", "#FFFFFF"
CORES_TERMOS = [AGUA, SOL, ARGILA, NOITE]
NOMES = {
    "extremamente_seco": "extremamente seco", "seco": "seco", "ideal": "ideal", "umido": "úmido",
    "frio": "frio", "agradavel": "agradável", "quente": "quente",
    "escuro": "escuro", "nublado": "nublado", "ensolarado": "ensolarado",
    "nulo": "nulo", "curto": "curto", "medio": "médio", "longo": "longo",
    "desligado": "desligado", "gotejamento": "gotejamento", "forte": "forte",
}
ROTULOS = {"umidade": "Umidade do solo", "temperatura": "Temperatura", "sol": "Luminosidade (LDR)",
           "tempo": "Tempo de rega", "vazao": "Vazão da água"}
UNIDADES = {"umidade": "%", "temperatura": "°C", "sol": "", "tempo": "min", "vazao": "%"}


def rgba(h, a):
    h = h.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


CURTO = {"extremamente_seco": "extr. seco"}
DTICK = {"umidade": 20, "temperatura": 10, "sol": 200, "tempo": 5, "vazao": 20}
FONTE_TITULO = "Bricolage Grotesque, Atkinson Hyperlegible, sans-serif"


def nomear_termos(fig, var, cores, y=1.1):
    """Escreve o nome de cada termo sobre o pico da curva, no lugar da legenda."""
    x = fz.UNIVERSOS[var]
    for i, t in enumerate(fz.TERMOS[var]):
        idx = np.where(fz.curva(var, t) >= 0.999)[0]
        xc = float(x[idx].mean()); frac = (xc - x[0]) / (x[-1] - x[0])
        anc = "left" if frac < 0.08 else ("right" if frac > 0.92 else "center")
        yy = y + 0.13 if (var in ("umidade", "vazao") and i == 1) else y
        fig.add_annotation(x=xc, y=yy, text=CURTO.get(t, NOMES[t]), showarrow=False, xanchor=anc,
                           font=dict(color=cores[i], size=12))


def br(x, casas=1):
    return f"{x:.{casas}f}".replace(".", ",")


st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Atkinson+Hyperlegible:wght@400;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, label, p, li, button, input {{
  font-family: 'Atkinson Hyperlegible', system-ui, sans-serif;
}}
.stApp {{ background: {NEVOA}; }}
.block-container {{ padding-top: 2.2rem; max-width: 1240px; }}
h1, h2, h3, .display {{ font-family: 'Bricolage Grotesque', 'Atkinson Hyperlegible', sans-serif; color: {MUSGO}; }}
[data-testid="stSidebar"] {{ background: #F6F9F9; border-right: 1px solid {LINHA}; }}
[data-testid="stSidebar"] h2 {{ font-size: 1.15rem; font-weight: 600; margin-bottom: .2rem; }}
.cabeca h1 {{ font-size: 2.6rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.05; margin: 0; }}
.cabeca p {{ color: {CINZA}; font-size: 1.05rem; margin: .45rem 0 0; max-width: 62ch; }}

/* faixa do céu: a assinatura visual */
.ceu {{ position: relative; margin: 1.8rem 0 .4rem; height: 86px; border-radius: 14px;
  background: linear-gradient(90deg, {NOITE} 0%, #4F5C8C 18%, #9FB3BE 42%, #D9DDD3 58%, #F1CF7C 78%, {SOL} 100%); }}
.ceu .marca {{ position: absolute; top: -9px; bottom: -9px; width: 4px; border-radius: 2px; background: {MUSGO};
  transform: translateX(-2px); box-shadow: 0 0 0 3px {NEVOA}; }}
.ceu .rotulo {{ position: absolute; top: 50%; background: {BRANCO}; color: {MUSGO};
  font-weight: 700; padding: .35rem .7rem; border-radius: 999px; white-space: nowrap; font-size: .95rem; }}
.escala {{ display: flex; justify-content: space-between; color: {CINZA}; font-size: .88rem; margin-bottom: 1.6rem; }}

/* decisão */
.decisao {{ display: grid; grid-template-columns: auto auto 1fr; gap: 2.6rem; align-items: end; margin-bottom: 1.4rem; }}
.numero {{ font-family: 'Bricolage Grotesque', sans-serif; font-size: 5.2rem; font-weight: 600; line-height: .9;
  color: {MUSGO}; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.numero small {{ font-size: 1.3rem; font-weight: 400; color: {CINZA}; letter-spacing: 0; margin-left: .35rem; }}
.legenda {{ color: {CINZA}; font-size: .95rem; margin-top: .5rem; }}
.explica {{ font-size: 1.12rem; line-height: 1.5; color: {MUSGO}; max-width: 46ch; padding-left: 1.4rem;
  border-left: 3px solid {AGUA}; }}
.explica.parado {{ border-left-color: {CINZA}; }}
@media (max-width: 900px) {{
  .decisao {{ grid-template-columns: 1fr 1fr; gap: 1.2rem; }}
  .explica {{ grid-column: 1 / -1; }}
  .numero {{ font-size: 3.6rem; }}
  .cabeca h1 {{ font-size: 2rem; }}
}}

/* regras */
.regra {{ display: grid; grid-template-columns: 3.2rem 1fr 9rem; gap: .9rem; align-items: center;
  padding: .55rem 0; border-bottom: 1px solid {LINHA}; }}
.regra .id {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 700; color: {AGUA}; }}
.regra.inativa {{ opacity: .42; }}
.regra.inativa .id {{ color: {CINZA}; }}
.regra .txt {{ color: {MUSGO}; line-height: 1.35; }}
.regra .txt span {{ color: {CINZA}; font-size: .9rem; }}
.barra {{ height: 8px; background: {LINHA}; border-radius: 4px; overflow: hidden; }}
.barra i {{ display: block; height: 100%; background: {AGUA}; border-radius: 4px; }}
.forca {{ font-variant-numeric: tabular-nums; font-size: .85rem; color: {CINZA}; margin-top: .2rem; text-align: right; }}
.nota {{ color: {CINZA}; font-size: .95rem; max-width: 70ch; }}
.stTabs [data-baseweb="tab"] {{ font-size: 1rem; }}
:focus-visible {{ outline: 3px solid {SOL} !important; outline-offset: 2px; }}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ estado e controles
CENARIOS = {
    "Escolha um cenário…": None,
    "11h, 30 °C, solo seco e sol forte": (20, 30, 900),
    "19h, 30 °C, solo seco e anoitecendo": (20, 30, 20),
    "Solo seco, dia nublado": (22, 25, 450),
    "Solo extremamente seco, à noite": (5, 30, 10),
    "Solo extremamente seco, sol forte": (5, 36, 900),
    "Solo ideal, dia quente e sol forte": (50, 36, 900),
    "Solo úmido": (85, 28, 500),
}
for k, v in {"umidade": 20, "temperatura": 30, "sol": 900}.items():
    st.session_state.setdefault(k, v)


def aplicar_cenario():
    c = CENARIOS[st.session_state["cenario"]]
    if c:
        st.session_state["umidade"], st.session_state["temperatura"], st.session_state["sol"] = c


with st.sidebar:
    st.markdown("## Leituras dos sensores")
    st.selectbox("Cenário pronto", list(CENARIOS), key="cenario", on_change=aplicar_cenario)
    st.slider("Umidade do solo (%)", 0, 100, key="umidade")
    st.slider("Temperatura (°C)", 0, 50, key="temperatura")
    st.slider("Luminosidade do LDR (0 = noite, 1000 = sol pleno)", 0, 1000, step=10, key="sol")
    st.caption("Compare os cenários das 11h e das 19h: a temperatura é a mesma, "
               "mas a decisão muda por causa da luz.")

res = fz.inferir(st.session_state["umidade"], st.session_state["temperatura"], st.session_state["sol"])
tempo, vazao = res["saida"]["tempo"], res["saida"]["vazao"]
dom = {v: max(res["mu"][v], key=res["mu"][v].get) for v in fz.ENTRADAS}
ativas = sorted([d for d in res["disparos"] if d["forca"] > 1e-9], key=lambda d: -d["forca"])


@st.cache_data(show_spinner="Simulando o dia…")
def dia_simulado(u0):
    return fazenda.simular_dia(u0)


def pagina_fazenda():
    st.markdown("""
    <div class="cabeca">
      <h1>Fazenda</h1>
      <p>A cena segue as leituras da barra lateral. Use "Simular um dia" para ver 24 horas passarem,
      começando com a umidade escolhida no controle.</p>
    </div>""", unsafe_allow_html=True)
    st.write("")
    agora = dict(u=res["entradas"]["umidade"], t=res["entradas"]["temperatura"], s=res["entradas"]["sol"],
                 tempo=round(tempo["valor"], 1), vazao=round(vazao["valor"], 1))
    components.html(fazenda.html_cena(agora, dia_simulado(st.session_state["umidade"])), height=900, scrolling=False)


def pagina_controlador():
    # ------------------------------------------------------------------ cabeçalho
    st.markdown("""
    <div class="cabeca">
      <h1>Irrigação fuzzy</h1>
      <p>Mova as leituras dos sensores e veja como o controlador decide quanto tempo regar e com que vazão.</p>
    </div>""", unsafe_allow_html=True)

    # ------------------------------------------------------------------ faixa do céu
    luz = res["entradas"]["sol"]
    pos = luz / 10  # 0..100 %
    txt_luz = {"escuro": "noite", "nublado": "nublado", "ensolarado": "sol forte"}[dom["sol"]]
    if pos > 70:
        estilo_rotulo = f"left:calc({pos}% - 12px); transform:translate(-100%,-50%)"
    else:
        estilo_rotulo = f"left:calc({pos}% + 12px); transform:translate(0,-50%)"
    st.markdown(f"""
    <div class="ceu" role="img" aria-label="Luminosidade atual: {int(luz)} de 1000, {txt_luz}">
      <div class="marca" style="left:{pos}%"></div>
      <div class="rotulo" style="{estilo_rotulo}">{txt_luz}, LDR {int(luz)}</div>
    </div>
    <div class="escala"><span>noite</span><span>nublado</span><span>sol pleno</span></div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------ decisão
    if tempo["valor"] == 0:
        frase = (f"Solo {NOMES[dom['umidade']]} e {txt_luz}: as regras indicam não irrigar agora.")
        classe = "explica parado"
    else:
        regra_txt = ativas[0]["texto"].split("  [")[0]
        frase = f"Solo {NOMES[dom['umidade']]}, clima {NOMES[dom['temperatura']]} e {txt_luz}. Regra mais forte, {ativas[0]['id']}: {regra_txt[0].lower() + regra_txt[1:]}"
        classe = "explica"
    st.markdown(f"""
    <div class="decisao">
      <div><div class="numero">{br(tempo['valor'])}<small>min</small></div><div class="legenda">tempo de rega</div></div>
      <div><div class="numero">{vazao['valor']:.0f}<small>%</small></div><div class="legenda">da vazão da bomba</div></div>
      <div class="{classe}">{frase}</div>
    </div>""", unsafe_allow_html=True)


    # ------------------------------------------------------------------ gráficos
    def base_fig(altura=260):
        fig = go.Figure()
        fig.update_layout(
            height=altura, margin=dict(l=10, r=10, t=36, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Atkinson Hyperlegible, sans-serif", color=MUSGO, size=13),
            showlegend=False, separators=",.",
        )
        fig.update_xaxes(showgrid=False, linecolor=LINHA, ticks="outside", tickcolor=LINHA, zeroline=False)
        fig.update_yaxes(range=[0, 1.32], gridcolor="#DCE4E5", zeroline=False, tickvals=[0, .5, 1])
        return fig


    CONFIG = {"displayModeBar": False}
    aba1, aba2, aba3, aba4 = st.tabs(["1. Leitura dos sensores", "2. Regras disparadas", "3. Decisão final",
                                      "Superfície de decisão"])

    with aba1:
        st.markdown('<p class="nota">Cada leitura vira um grau de pertinência entre 0 e 1 em cada termo. '
                    'A linha vertical é o valor atual; a área preenchida mostra o quanto ele pertence a cada termo.</p>',
                    unsafe_allow_html=True)
        cols = st.columns(3)
        for col, var in zip(cols, fz.ENTRADAS):
            x = fz.UNIVERSOS[var]; v = res["entradas"][var]
            fig = base_fig()
            for i, t in enumerate(fz.TERMOS[var]):
                cor = CORES_TERMOS[i]; y = fz.curva(var, t); g = res["mu"][var][t]
                if g > 0:
                    fig.add_trace(go.Scatter(x=x, y=np.minimum(y, g), fill="tozeroy", mode="none",
                                             fillcolor=rgba(cor, .22), hoverinfo="skip"))
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=cor, width=2.4), name=NOMES[t],
                                         hovertemplate=f"{NOMES[t]}: %{{y:.2f}}<extra></extra>"))
            fig.add_vline(x=v, line=dict(color=MUSGO, width=1.6, dash="dot"))
            nomear_termos(fig, var, CORES_TERMOS)
            fig.update_xaxes(tickvals=np.arange(x[0], x[-1] + 1e-9, DTICK[var]), range=[x[0], x[-1] * 1.01])
            fig.update_layout(title=dict(text=ROTULOS[var], font=dict(family=FONTE_TITULO, size=17), x=0, y=.97))
            col.plotly_chart(fig, width="stretch", config=CONFIG)
            graus = [f"<b>{br(g, 2)}</b> {NOMES[t]}" for t, g in res["mu"][var].items() if g > 0]
            col.markdown(f'<p class="nota">{br(v, 0)} {UNIDADES[var]}: ' + ", ".join(graus) + "</p>", unsafe_allow_html=True)

    with aba2:
        st.markdown('<p class="nota">A força de cada regra vem dos operadores E = mínimo, OU = máximo e NÃO = 1 − μ. '
                    'Regras com força zero não participam da decisão.</p>', unsafe_allow_html=True)
        linhas = []
        for d in sorted(res["disparos"], key=lambda d: -d["forca"]):
            on = d["forca"] > 1e-9
            texto = d["texto"].split("  [")[0]
            cons = f"tempo {NOMES[d['cons']['tempo']]}, vazão {NOMES[d['cons']['vazao']]}"
            linhas.append(f"""<div class="regra{'' if on else ' inativa'}">
              <div class="id">{d['id']}</div>
              <div class="txt">{texto}<br><span>{cons}</span></div>
              <div><div class="barra"><i style="width:{d['forca'] * 100:.0f}%"></i></div><div class="forca">{br(d['forca'], 2)}</div></div>
            </div>""")
        st.markdown("".join(linhas), unsafe_allow_html=True)

    with aba3:
        st.markdown('<p class="nota">Cada regra corta o termo de saída na altura da sua força. Os cortes são somados pelo máximo, '
                    'e o centroide dessa área é o valor enviado à bomba.</p>', unsafe_allow_html=True)
        cols = st.columns(2)
        for col, s in zip(cols, fz.SAIDAS):
            o = res["saida"][s]; x = fz.UNIVERSOS[s]
            fig = base_fig(300)
            for i, t in enumerate(fz.TERMOS[s]):
                fig.add_trace(go.Scatter(x=x, y=fz.curva(s, t), mode="lines", name=NOMES[t],
                                         line=dict(color=CORES_TERMOS[i], width=1.3, dash="dot"),
                                         hovertemplate=f"{NOMES[t]}<extra></extra>"))
            fig.add_trace(go.Scatter(x=x, y=o["agregado"], fill="tozeroy", mode="lines", name="área agregada",
                                     line=dict(color=AGUA, width=2), fillcolor=rgba(AGUA, .3),
                                     hovertemplate="%{y:.2f}<extra></extra>"))
            fig.add_vline(x=o["centroide"], line=dict(color=ARGILA, width=2.4),
                          annotation_text=f"centroide {br(o['centroide'])}", annotation_position="bottom right", annotation_y=0.55,
                          annotation_font=dict(color=ARGILA, size=13))
            nomear_termos(fig, s, CORES_TERMOS)
            fig.update_xaxes(tickvals=np.arange(x[0], x[-1] + 1e-9, DTICK[s]), range=[x[0], x[-1] * 1.01])
            fig.update_layout(title=dict(text=f"{ROTULOS[s]} ({UNIDADES[s]})", font=dict(family=FONTE_TITULO, size=17), x=0, y=.97))
            col.plotly_chart(fig, width="stretch", config=CONFIG)
            if o["valor"] == 0 and o["centroide"] > 0:
                col.markdown(f'<p class="nota">O centroide ({br(o["centroide"])}) fica abaixo da zona morta '
                             f'({br(fz.ZONA_MORTA[s])} {UNIDADES[s]}), então a bomba não liga.</p>', unsafe_allow_html=True)

    with aba4:
        saida = st.radio("Saída", ["tempo", "vazao"], format_func=lambda s: ROTULOS[s], horizontal=True)
        st.markdown(f'<p class="nota">Decisão para todas as combinações de umidade e luz, com a temperatura fixa em '
                    f'{st.session_state["temperatura"]} °C. O ponto marca a leitura atual.</p>', unsafe_allow_html=True)

        @st.cache_data(show_spinner="Calculando a superfície…")
        def malha(temp, s):
            us, ss = np.arange(0, 101, 4), np.arange(0, 1001, 40)
            Z = np.array([[fz.inferir(u, temp, l)["saida"][s]["valor"] for u in us] for l in ss])
            return us, ss, Z

        us, ss, Z = malha(st.session_state["temperatura"], saida)
        fig = go.Figure(go.Surface(x=us, y=ss, z=Z, colorscale=[[0, NOITE], [.45, AGUA], [1, SOL]], showscale=False,
                                   hovertemplate="umidade %{x}%<br>LDR %{y}<br>%{z:.1f}<extra></extra>"))
        fig.add_trace(go.Scatter3d(x=[res["entradas"]["umidade"]], y=[luz], z=[res["saida"][saida]["valor"]],
                                   mode="markers", marker=dict(size=7, color=ARGILA), hoverinfo="skip"))
        fig.update_layout(height=520, margin=dict(l=0, r=0, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)",
                          font=dict(family="Atkinson Hyperlegible, sans-serif", color=MUSGO),
                          scene=dict(xaxis_title="umidade (%)", yaxis_title="LDR", zaxis_title=f"{ROTULOS[saida]} ({UNIDADES[saida]})",
                                     camera=dict(eye=dict(x=1.6, y=-1.5, z=0.9))))
        st.plotly_chart(fig, width="stretch", config=CONFIG)


navegacao = st.navigation([
    st.Page(pagina_controlador, title="Controlador fuzzy", icon=":material/tune:", default=True),
    st.Page(pagina_fazenda, title="Fazenda", icon=":material/agriculture:"),
])
navegacao.run()
