"""
Sistema Fuzzy de Irrigação Inteligente (Mamdani, MISO)
======================================================

Entradas : umidade do solo (%), temperatura (°C), intensidade luminosa (LDR, 0-1000)
Saídas   : tempo de rega (min) e vazão da água (% da capacidade da bomba/válvula)

O motor de inferência está implementado "à mão" (NumPy) para que cada etapa
(fuzzificação -> disparo das regras -> implicação -> agregação -> defuzzificação)
possa ser exibida na interface. A função `validar_com_skfuzzy` reconstrói o mesmo
sistema com a biblioteca scikit-fuzzy e serve para conferir que os resultados batem.

Operadores (padrão Mamdani): E = mínimo, OU = máximo, NÃO = 1 - x,
implicação = mínimo (corte), agregação = máximo, defuzzificação = centroide.
"""
from __future__ import annotations

import numpy as np
import skfuzzy as fuzz

# ------------------------------------------------------------------------------
# 1. UNIVERSOS DE DISCURSO
# ------------------------------------------------------------------------------
UNIVERSOS = {
    "umidade": np.arange(0, 101, 1.0),        # % de umidade volumétrica do solo
    "temperatura": np.arange(0, 51, 1.0),     # °C
    "sol": np.arange(0, 1001, 1.0),           # leitura normalizada do LDR (0 = escuro, 1000 = sol pleno)
    "tempo": np.arange(0, 30.01, 0.1),        # minutos de bomba ligada
    "vazao": np.arange(0, 100.01, 0.5),       # % da vazão máxima
}

ROTULOS = {
    "umidade": "Umidade do solo (%)",
    "temperatura": "Temperatura (°C)",
    "sol": "Intensidade luminosa (LDR, 0–1000)",
    "tempo": "Tempo de rega (min)",
    "vazao": "Vazão da água (%)",
}

# ------------------------------------------------------------------------------
# 2. FUNÇÕES DE PERTINÊNCIA   (tipo, parâmetros)
# ------------------------------------------------------------------------------
TERMOS = {
    "umidade": {
        "extremamente_seco": ("trap", [0, 0, 8, 18]),
        "seco":              ("tri",  [10, 25, 40]),
        "ideal":             ("trap", [30, 45, 60, 75]),
        "umido":             ("trap", [65, 80, 100, 100]),
    },
    "temperatura": {
        "frio":      ("trap", [0, 0, 15, 22]),
        "agradavel": ("tri",  [18, 25, 32]),
        "quente":    ("trap", [28, 35, 50, 50]),
    },
    "sol": {
        "escuro":     ("trap", [0, 0, 100, 300]),
        "nublado":    ("tri",  [200, 450, 700]),
        "ensolarado": ("trap", [600, 800, 1000, 1000]),
    },
    "tempo": {
        "nulo":  ("tri",  [0, 0, 2]),
        "curto": ("tri",  [2, 6, 12]),
        "medio": ("tri",  [8, 15, 22]),
        "longo": ("trap", [18, 25, 30, 30]),
    },
    "vazao": {
        "desligado":   ("tri",  [0, 0, 10]),
        "gotejamento": ("tri",  [5, 25, 45]),
        "medio":       ("tri",  [35, 55, 75]),
        "forte":       ("trap", [65, 85, 100, 100]),
    },
}

ENTRADAS = ["umidade", "temperatura", "sol"]
SAIDAS = ["tempo", "vazao"]

# Zona morta do atuador: o centroide de um conjunto "nulo/desligado" nunca é exatamente 0
# (ele fica no centro de massa do triângulo). Abaixo destes limiares a bomba não aciona.
ZONA_MORTA = {"tempo": 1.0, "vazao": 5.0}


def pertinencia(var: str, termo: str, x):
    """Grau de pertinência de x (escalar ou array) ao termo da variável."""
    tipo, p = TERMOS[var][termo]
    universo = np.atleast_1d(np.asarray(x, dtype=float))
    f = fuzz.trimf if tipo == "tri" else fuzz.trapmf
    return f(universo, p)


def curva(var: str, termo: str):
    """Curva completa do termo sobre o universo da variável."""
    return pertinencia(var, termo, UNIVERSOS[var])


# ------------------------------------------------------------------------------
# 3. BASE DE REGRAS
#    Antecedente em árvore: ("is", var, termo) | ("and", a, b) | ("or", a, b) | ("not", a)
# ------------------------------------------------------------------------------
def IS(v, t): return ("is", v, t)
def AND(a, b): return ("and", a, b)
def OR(a, b): return ("or", a, b)
def NOT(a): return ("not", a)


REGRAS = [
    # --- solo úmido ou ideal: não há o que irrigar, exceto reposição em dia quente ---------------
    dict(id="R1", ant=IS("umidade", "umido"),
         cons={"tempo": "nulo", "vazao": "desligado"},
         texto="Solo úmido → não irrigar"),
    dict(id="R2", ant=AND(IS("umidade", "ideal"), OR(IS("temperatura", "frio"), IS("temperatura", "agradavel"))),
         cons={"tempo": "nulo", "vazao": "desligado"},
         texto="Solo ideal E (frio OU agradável) → não irrigar"),
    dict(id="R3", ant=AND(IS("umidade", "ideal"), AND(IS("temperatura", "quente"), NOT(IS("sol", "ensolarado")))),
         cons={"tempo": "curto", "vazao": "gotejamento"},
         texto="Solo ideal E quente E NÃO ensolarado → rega curta em gotejamento (reposição)"),
    dict(id="R4", ant=AND(IS("umidade", "ideal"), AND(IS("temperatura", "quente"), IS("sol", "ensolarado"))),
         cons={"tempo": "nulo", "vazao": "desligado"},
         texto="Solo ideal E quente E ensolarado → adiar (evita queima e evaporação)"),
    # --- solo seco ---------------------------------------------------------------------------------
    dict(id="R5", ant=AND(IS("umidade", "seco"), IS("sol", "ensolarado")),
         cons={"tempo": "curto", "vazao": "gotejamento"},
         texto="Solo seco E ensolarado → irrigação adiada/curta (apenas resfriamento)  [Regra de Ouro 1]"),
    dict(id="R6", ant=AND(IS("umidade", "seco"), AND(IS("sol", "escuro"), IS("temperatura", "quente"))),
         cons={"tempo": "longo", "vazao": "forte"},
         texto="Solo seco E escuro (noite) E quente → rega longa e forte"),
    dict(id="R7", ant=AND(IS("umidade", "seco"), AND(IS("sol", "escuro"), NOT(IS("temperatura", "quente")))),
         cons={"tempo": "medio", "vazao": "medio"},
         texto="Solo seco E escuro E NÃO quente → rega média, fluxo médio"),
    dict(id="R8", ant=AND(IS("umidade", "seco"), AND(IS("sol", "nublado"), IS("temperatura", "quente"))),
         cons={"tempo": "longo", "vazao": "medio"},
         texto="Solo seco E nublado E quente → rega longa, fluxo médio"),
    dict(id="R9", ant=AND(IS("umidade", "seco"), AND(IS("sol", "nublado"), NOT(IS("temperatura", "quente")))),
         cons={"tempo": "medio", "vazao": "medio"},
         texto="Solo seco E nublado E NÃO quente → rega média, fluxo médio"),
    # --- solo extremamente seco: gotejamento por muito tempo (não compactar a terra) ----------------
    dict(id="R10", ant=AND(IS("umidade", "extremamente_seco"), NOT(IS("sol", "ensolarado"))),
         cons={"tempo": "longo", "vazao": "gotejamento"},
         texto="Solo extremamente seco E NÃO ensolarado → gotejamento por tempo longo  [Regra de Ouro 2]"),
    dict(id="R11", ant=AND(IS("umidade", "extremamente_seco"), IS("sol", "ensolarado")),
         cons={"tempo": "medio", "vazao": "gotejamento"},
         texto="Solo extremamente seco E ensolarado → gotejamento por tempo médio (compromisso: umidade crítica)"),
]


def _ant_texto(n):
    k = n[0]
    if k == "is":
        return f"{n[1]} é {n[2]}"
    if k == "not":
        return f"NÃO ({_ant_texto(n[1])})"
    return f"({_ant_texto(n[1])} {'E' if k == 'and' else 'OU'} {_ant_texto(n[2])})"


def _avalia(n, mu):
    k = n[0]
    if k == "is":
        return mu[n[1]][n[2]]
    if k == "not":
        return 1.0 - _avalia(n[1], mu)
    a, b = _avalia(n[1], mu), _avalia(n[2], mu)
    return min(a, b) if k == "and" else max(a, b)


# ------------------------------------------------------------------------------
# 4. INFERÊNCIA MAMDANI (passo a passo, retornando tudo que a interface precisa)
# ------------------------------------------------------------------------------
def inferir(umidade: float, temperatura: float, sol: float, regras=None, saidas=None):
    """Executa a inferência e devolve um dicionário com cada etapa do processo."""
    regras = REGRAS if regras is None else regras
    saidas = SAIDAS if saidas is None else saidas
    entradas = {
        "umidade": float(np.clip(umidade, 0, 100)),
        "temperatura": float(np.clip(temperatura, 0, 50)),
        "sol": float(np.clip(sol, 0, 1000)),
    }

    # (1) Fuzzificação
    mu = {v: {t: float(pertinencia(v, t, x)[0]) for t in TERMOS[v]} for v, x in entradas.items()}

    # (2) Disparo das regras
    disparos = []
    for r in regras:
        disparos.append(dict(id=r["id"], texto=r["texto"], forca=float(_avalia(r["ant"], mu)), cons=r["cons"]))

    # (3) Implicação (corte) + (4) Agregação (máximo) + (5) Defuzzificação (centroide)
    saida = {}
    for s in saidas:
        x = UNIVERSOS[s]
        cortes = []
        agregado = np.zeros_like(x)
        for d in disparos:
            if s not in d["cons"]:
                continue
            termo = d["cons"][s]
            corte = np.minimum(d["forca"], curva(s, termo))
            cortes.append((d["id"], termo, d["forca"], corte))
            agregado = np.maximum(agregado, corte)
        area = np.trapezoid(agregado, x)
        if area <= 1e-12:
            raise ValueError(f"Nenhuma regra disparou para a saída '{s}' (base de regras esparsa).")
        centroide = float(np.trapezoid(agregado * x, x) / area)
        bruto = centroide
        aplicado = 0.0 if centroide < ZONA_MORTA[s] else centroide
        saida[s] = dict(universo=x, cortes=cortes, agregado=agregado, centroide=bruto, valor=aplicado)

    # Consistência do atuador: se uma das saídas cai na zona morta, a bomba não é acionada.
    if any(v["valor"] == 0.0 for v in saida.values()):
        for v in saida.values():
            v["valor"] = 0.0

    return dict(entradas=entradas, mu=mu, disparos=disparos, saida=saida)


def hora_para_cenario(hora: float):
    """Perfil sintético de um dia ensolarado de verão (apenas para demonstração/artigo)."""
    luz = np.sin(np.pi * (hora - 6.0) / 12.0) if 6 <= hora <= 18 else 0.0
    sol = 1000.0 * max(0.0, luz)
    temp = 24.0 + 12.0 * np.sin(np.pi * (hora - 8.0) / 14.0) if 8 <= hora <= 22 else 24.0
    return float(sol), float(temp)


# ------------------------------------------------------------------------------
# 5. VALIDAÇÃO CRUZADA COM scikit-fuzzy
# ------------------------------------------------------------------------------
def construir_skfuzzy():
    from skfuzzy import control as ctrl

    ants = {v: ctrl.Antecedent(UNIVERSOS[v], v) for v in ENTRADAS}
    cons = {s: ctrl.Consequent(UNIVERSOS[s], s) for s in SAIDAS}
    for grupo in (ants, cons):
        for v, obj in grupo.items():
            for nome, (tipo, p) in TERMOS[v].items():
                obj[nome] = (fuzz.trimf if tipo == "tri" else fuzz.trapmf)(UNIVERSOS[v], p)

    def conv(n):
        k = n[0]
        if k == "is":
            return ants[n[1]][n[2]]
        if k == "not":
            return ~conv(n[1])
        a, b = conv(n[1]), conv(n[2])
        return (a & b) if k == "and" else (a | b)

    regras = []
    for r in REGRAS:
        regras.append(ctrl.Rule(conv(r["ant"]), tuple(cons[s][t] for s, t in r["cons"].items())))
    return ctrl.ControlSystem(regras)


def validar_com_skfuzzy(pontos):
    """Compara o motor próprio com o scikit-fuzzy. Retorna o maior erro absoluto observado."""
    from skfuzzy import control as ctrl

    sistema = construir_skfuzzy()
    maior = 0.0
    for (u, t, s) in pontos:
        sim = ctrl.ControlSystemSimulation(sistema)
        sim.input["umidade"], sim.input["temperatura"], sim.input["sol"] = u, t, s
        sim.compute()
        meu = inferir(u, t, s)
        for k in SAIDAS:
            maior = max(maior, abs(sim.output[k] - meu["saida"][k]["centroide"]))
    return maior


if __name__ == "__main__":
    r = inferir(20, 38, 850)
    print({k: round(v["valor"], 2) for k, v in r["saida"].items()})
