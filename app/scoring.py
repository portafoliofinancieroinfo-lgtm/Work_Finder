"""Gemelo en Python de scoring.js, para calificar vacantes en las corridas.

Las reglas deben coincidir con scoring.js. Uso desde la línea de comandos:
    python "app/scoring.py" vacante.json [ajustes.json] [AAAA-MM-DD]
    python "app/scoring.py" --paridad <ruta de crm.db> <AAAA-MM-DD>
--paridad califica todas las vacantes de esa base con este archivo y con scoring.js (necesita node) y dice si coinciden.
"""
import json
import re
import sys
import unicodedata
from datetime import date

PALABRAS = ("contador, contable, contabilidad, accountant, accounting, impuestos, nómina, auditor, audit, revisor fiscal, "
            "financiero, financiera, cuentas por pagar, cuentas por cobrar, controller, controlador, tesorería, QA, "
            "tester, testing, quality assurance, pruebas, automatización de pruebas")

AJUSTES_BASE = {
    "ciudadBase": "",
    # Casos de búsqueda: la vacante usa el primero (de arriba abajo) con una de sus palabras clave en el cargo (sin palabras:
    # cualquier cargo) que acepte su contrato y su modalidad. Las palabras son también las que se buscan en los portales.
    # modalidad: remoto | ciudad (presencial o híbrido en tu ciudad) | remoto_ciudad | mudanza (otra ciudad) | cualquiera.
    "casos": [
        {"palabras": PALABRAS, "contrato": "tiempo_completo", "modalidad": "remoto_ciudad", "salarioMinimo": 4500000},
        {"palabras": PALABRAS, "contrato": "tiempo_completo", "modalidad": "mudanza", "salarioMinimo": 6000000},
        {"palabras": "revisor fiscal, revisoría fiscal", "contrato": "parcial", "modalidad": "remoto", "salarioMinimo": 1750905},
        {"palabras": PALABRAS, "contrato": "parcial", "modalidad": "remoto_ciudad", "salarioMinimo": 1750000},
    ],
    "umbralAprobar": 60,
    "limitePorCorrida": 12,
    "diasPrimerSeguimiento": 10,
    "diasEntreSeguimientos": 10,
    "maxSeguimientos": 2,
    "diasCierreSinNovedad": 45,
}

PUNTOS_PERFIL = {"Auditoría/Revisoría": 30, "Contable/Financiero": 30, "QA": 22, "Otro": 10}


def sin_tildes(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def misma_ciudad(a, b):
    return bool(a) and bool(b) and sin_tildes(a) == sin_tildes(b)


def inferir_nivel(cargo):
    c = sin_tildes(cargo)
    if re.search(r"docente|profesor|catedra", c):
        return "docencia"
    if re.search(r"auxiliar|asistente|practicante|\baux\b|aprendiz", c):
        return "auxiliar"
    if re.search(r"gerente|director|jefe|controller|manager|head of", c):
        return "gerencia"
    if re.search(r"senior|\bsr\b|lider|coordinador|especialista|experto", c):
        return "senior"
    return "profesional"


def num(x):
    """x si es un número, si no None (como typeof x === "number" en scoring.js: True no cuenta)."""
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else None


def fecha(s):
    """La fecha de un texto AAAA-MM-DD exacto, si no None (fromisoformat acepta también "20261022"; scoring.js no)."""
    try:
        d = date.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    return d if d.isoformat() == s else None


def dias_entre(desde, hasta):
    a, b = fecha(desde), fecha(hasta)
    return None if a is None or b is None else (b - a).days


def salario_referencia(v):
    lo, hi = num(v.get("salarioMin")), num(v.get("salarioMax"))
    if lo is not None and hi is not None:
        return int((lo + hi) / 2 + 0.5)  # igual que Math.round de scoring.js (round() de Python va al par)
    return lo if lo is not None else hi


def _ajustes(ajustes):
    a = dict(AJUSTES_BASE)
    a.update(ajustes or {})
    return a


MODALIDAD_CASO = {"remoto": ["remoto"], "ciudad": ["ciudad"], "remoto_ciudad": ["remoto", "ciudad"],
                  "mudanza": ["mudanza"], "cualquiera": ["remoto", "ciudad", "mudanza"]}


def plano(s):
    """Texto en minúsculas, sin tildes ni signos: "Analista Contable (Sr.)" -> "analista contable sr"."""
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes(s)).strip()


def palabras_de(c):
    """Palabras clave de un caso, ya planas."""
    return [p for p in (plano(x) for x in str(c.get("palabras") or "").split(",")) if p]


def caso_de(v, modo, casos):
    """Índice del caso de búsqueda de la vacante (-1 si ninguno). Sin contrato publicado se asume tiempo completo.
    Una palabra clave coincide si cada una de sus palabras es el inicio de una palabra del cargo
    ("revisor fiscal" sirve para "Revisor(a) Fiscal" y "Revisora fiscal"; "contable" para "contables")."""
    contrato = v.get("contrato") or "tiempo_completo"
    cargo = plano(v.get("cargo")).split(" ")

    def coincide(p):
        return all(any(x.startswith(w) for x in cargo) for w in p.split(" "))

    for i, c in enumerate(casos):
        pal = palabras_de(c)
        if (c.get("contrato") in ("cualquiera", contrato) and modo in MODALIDAD_CASO.get(c.get("modalidad"), [])
                and (not pal or any(coincide(p) for p in pal))):
            return i
    return -1


def presupuesto(v, ajustes=None):
    """Salario de la vacante frente al mínimo del caso que le aplica. La ciudad decide si es en tu ciudad o con mudanza."""
    a = _ajustes(ajustes)
    ref = salario_referencia(v)
    nivel = v.get("nivel") or inferir_nivel(v.get("cargo"))
    if v.get("modalidad") == "remoto":
        modo = "remoto"
    elif misma_ciudad(v.get("ciudad"), a["ciudadBase"]):
        modo = "ciudad"
    else:
        modo = "mudanza"
    supuesto = modo == "mudanza" and (v.get("modalidad") == "no_especificado" or not v.get("ciudad"))
    casos = a.get("casos") or []
    i_caso = caso_de(v, modo, casos)
    minimo = num(casos[i_caso].get("salarioMinimo")) if i_caso >= 0 else None
    return {
        "salarioRef": ref, "neto": ref, "minimo": minimo, "nivel": nivel, "caso": i_caso + 1 if i_caso >= 0 else None,
        "modo": modo, "supuesto": supuesto,
        "cumple": None if ref is None or minimo is None else ref >= minimo,
    }


def puntaje(v, ajustes=None, hoy=None):
    hoy = hoy or date.today().isoformat()
    p = presupuesto(v, ajustes)
    alertas = v.get("alertas") or []
    partes = {"perfil": PUNTOS_PERFIL.get(v.get("perfil"), 10)}

    exp = num(v.get("experienciaAnios"))
    if p["nivel"] == "auxiliar":
        partes["experiencia"] = 6
    elif exp is None:
        partes["experiencia"] = 14
    elif exp <= 3:
        partes["experiencia"] = 20
    elif exp <= 4:
        partes["experiencia"] = 12
    else:
        partes["experiencia"] = 4

    if p["salarioRef"] is None or p["minimo"] is None:
        partes["economico"] = 15
    elif p["salarioRef"] < p["minimo"]:
        partes["economico"] = 0
    elif not p["minimo"]:
        partes["economico"] = 25
    else:
        # Math.round de JS redondea .5 hacia arriba; int(x + 0.5) replica eso para positivos.
        partes["economico"] = int(20 + min(10, 10 * (p["salarioRef"] / p["minimo"] - 1) / 0.4) + 0.5)

    partes["modalidad"] = 5 if p["supuesto"] else {"remoto": 10, "ciudad": 9, "mudanza": 3}[p["modo"]]

    dias = dias_entre(v.get("fechaPublicacion"), hoy)
    if dias is None:
        partes["frescura"] = 5
    elif dias <= 7:
        partes["frescura"] = 10
    elif dias <= 14:
        partes["frescura"] = 8
    elif dias <= 30:
        partes["frescura"] = 5
    else:
        partes["frescura"] = 2

    total = sum(partes.values())
    bloqueo = None
    if "posible_estafa" in alertas:
        bloqueo = "Posible estafa"
    elif "no_aplica" in alertas:
        bloqueo = "No cumples un requisito excluyente"
    elif not p["caso"]:
        bloqueo = "Ningún caso de búsqueda la acepta"
    if bloqueo:
        total = 0
    return {"total": max(0, min(100, total)), "partes": partes, "bloqueo": bloqueo, "presupuesto": p}


def paridad(ruta_db, hoy):
    """Compara scoring.py con scoring.js sobre todas las vacantes de una base. Devuelve [(id, total_py, total_js)] distintas."""
    import os
    import sqlite3
    import subprocess
    import storage
    con = sqlite3.connect("file:%s?mode=ro" % ruta_db.replace("\\", "/"), uri=True)
    aj = storage.leer_uno(con, "config", "ajustes")
    vs = storage.leer(con, "vacantes")
    con.close()
    js = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scoring.js")
    prog = ("const M = require(process.argv[1]); const e = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "const o = {}; for (const i in e.vs) o[i] = M.puntaje(e.vs[i], e.aj, e.hoy); process.stdout.write(JSON.stringify(o));")
    salida = subprocess.run(["node", "-e", prog, js], input=json.dumps({"vs": vs, "aj": aj, "hoy": hoy}, ensure_ascii=False),
                            capture_output=True, text=True, encoding="utf-8", check=True).stdout
    de_js = json.loads(salida)
    py = {i: puntaje(v, aj, hoy) for i, v in vs.items()}
    return [(i, py[i]["total"], de_js[i]["total"]) for i in sorted(vs) if py[i] != de_js[i]]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--paridad":
        if len(sys.argv) != 4:
            sys.exit(__doc__)
        malas = paridad(sys.argv[2], sys.argv[3])
        print("Paridad OK: scoring.py y scoring.js dan lo mismo." if not malas else
              "DIFERENCIAS (id, scoring.py, scoring.js): %s" % malas)
        sys.exit(1 if malas else 0)
    with open(sys.argv[1], encoding="utf-8") as f:
        vac = json.load(f)
    aj = None
    if len(sys.argv) > 2:
        with open(sys.argv[2], encoding="utf-8") as f:
            aj = json.load(f)
    hoy_arg = sys.argv[3] if len(sys.argv) > 3 else None
    items = vac if isinstance(vac, list) else [vac]
    out = [dict(v, _puntaje=puntaje(v, aj, hoy_arg)) for v in items]
    print(json.dumps(out if isinstance(vac, list) else out[0], ensure_ascii=False, indent=2))
