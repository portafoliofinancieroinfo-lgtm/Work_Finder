"""Escribe en el CRM (Programa del CRM/postulaciones.db) sin pisar datos.

El modelo no edita la base a mano: llena un JSON de entrada simple (o usa un comando corto) y corre este
script, que guarda todo en una sola transacción (o nada, si algo falla). El script se encarga de:
  - ids nuevos, valores por defecto, puntaje (puntaje.py), etapa según Ajustes, carta y borrador de correo;
  - agregar al historial sin borrar lo anterior;
  - la próxima acción según la cadencia de Ajustes.
Las listas de etapas, resultados, alertas, tipos y modalidades se leen de pagina.html (la página, una sola fuente).

Uso:
  python "Programa del CRM/comandos.py" nuevas          <entrada.json> <AAAA-MM-DD>
  python "Programa del CRM/comandos.py" cambios         <entrada.json> <AAAA-MM-DD>
  python "Programa del CRM/comandos.py" vencidas        <AAAA-MM-DD>
  python "Programa del CRM/comandos.py" aprobar         <AAAA-MM-DD> <id> [<id> ...]
  python "Programa del CRM/comandos.py" cerrar-vencidas <AAAA-MM-DD>
  python "Programa del CRM/comandos.py" registro        <AAAA-MM-DD> <entrada.json>
  python "Programa del CRM/comandos.py" perfil
  python "Programa del CRM/comandos.py" editar-perfil   <entrada.json>
  python "Programa del CRM/comandos.py" consulta        "<SELECT ...>"
Con --db <ruta> al inicio se usa otra base (para pruebas).

Ver .claude/como_usar_la_base_de_datos.md para el formato de cada entrada.
"""
import copy
import json
import os
import re
import sqlite3
import sys
from datetime import timedelta

sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no imprime "→"
sys.stderr.reconfigure(encoding="utf-8")  # ni las tildes de los mensajes de error
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import leer_y_guardar  # noqa: E402
import puntaje  # noqa: E402


def falla(msg):
    sys.exit("ERROR: " + msg)


def _listas_de_la_pagina():
    """Lee las listas de pagina.html (la página) para no tener copias que se desfasen."""
    with open(os.path.join(AQUI, "pagina.html"), encoding="utf-8") as f:
        html = f.read()

    def bloque(nombre, abre, cierra):
        m = re.search(r"const %s = \%s(.*?)\%s;" % (nombre, abre, cierra), html, re.S)
        if not m:
            falla("no encuentro 'const %s' en pagina.html" % nombre)
        return m.group(1)

    pares = lambda txt: re.findall(r'\["(\w+)",', txt)  # noqa: E731
    llaves = lambda txt: re.findall(r"(\w+):\s*[\[\"]", txt)  # noqa: E731
    sin_nov = re.search(r'const SIN_NOVEDAD = "([^"]+)"', html)
    if not sin_nov:
        falla("no encuentro 'const SIN_NOVEDAD' en pagina.html")
    return (pares(bloque("ETAPAS", "[", "]")), llaves(bloque("RESULTADOS", "{", "}")),
            llaves(bloque("ALERTAS", "{", "}")), llaves(bloque("TIPOS_HIST", "{", "}")),
            pares("[" + bloque("MODALIDADES", "[", "]")), pares("[" + bloque("CONTRATOS", "[", "]")), sin_nov.group(1))


ETAPAS, RESULTADOS, ALERTAS, TIPOS_HIST, MODALIDADES, CONTRATOS, SIN_NOVEDAD = _listas_de_la_pagina()
PERFILES = list(puntaje.PUNTOS_PERFIL)
TEXTO_SIN_NOVEDAD = SIN_NOVEDAD + ": si no hay novedad, cerrar como sin respuesta"
MAX_PALABRAS = 150

SALUDO = {"es": "Cordial saludo,", "en": "Dear hiring team,"}
DESPEDIDA = {"es": "Cordialmente,", "en": "Best regards,"}

DEFAULTS_VACANTE = dict(
    alertas=[], aviso="", canal="portal", ciudad=None, contrato=None, correoPostulacion=None, empresaId=None, estadoPortal="Nueva",
    etapa="descubierta", etapaMax="descubierta", experienciaAnios=None, fechaPostulacion=None, fechaPublicacion=None,
    historial=[], link=None, neto=None, notas="", proximaAccion=None, puntaje=None, resultado=None, salarioMax=None,
    salarioMin=None, salarioTexto="", seguimientos=0, ubicacion="")
# Campos que se aceptan en una entrada de "nuevas" (además de los de DEFAULTS_VACANTE).
CAMPOS_NUEVAS = set(DEFAULTS_VACANTE) | {"empresa", "cargo", "perfil", "modalidad", "portal", "nivel", "carta",
                                         "idioma", "asunto", "excluyente", "postulada_por_usuario"}
# Campos simples que se pueden cambiar con "campos" en "cambios". Etapa, resultado, alertas, notas,
# historial y proximaAccion tienen su propio campo con validación.
CAMPOS_LIBRES = {"aviso", "seguimientos", "correoPostulacion", "link", "salarioMin", "salarioMax", "salarioTexto", "ciudad",
                 "ubicacion", "experienciaAnios", "estadoPortal", "empresaId", "nivel",
                 "fechaPublicacion", "modalidad", "perfil", "contrato"}
CAMPOS_CONTACTO = {"nombre", "email", "telefono", "rol"}
# Claves que se aceptan en una entrada de "cambios": una mal escrita ("etapo") es error, no se ignora.
CLAVES_CAMBIO = {"id", "texto", "tipo", "fecha", "etapa", "resultado", "alertas_mas", "alertas_menos", "notas_mas",
                 "proximaAccion", "campos", "contacto", "borrador", "si_del_usuario"}
EMPRESA_GENERICA = re.compile(r"(importante|reconocida|prestigiosa|reconocido|lider) (empresa|compania|firma|grupo)"
                              r"|confidencial|reservad|no especificad|empresa (del|de|con) |^empresa$")


def valida(valor, permitidos, que):
    if valor not in permitidos:
        falla("%s inválido '%s': usar %s" % (que, valor, permitidos))


def leer_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def cargar(con):
    """(vacantes, empresas, ajustes) del CRM."""
    ajustes = puntaje._ajustes(leer_y_guardar.leer_uno(con, "config", "ajustes") or {})
    return leer_y_guardar.leer(con, "vacantes"), leer_y_guardar.leer(con, "empresas"), ajustes


def guardar_todo(con, writes, resumen):
    """Aplica las escrituras en una sola transacción: o se guardan todas o ninguna."""
    with con:
        for op, coleccion_, doc_id, data in writes:
            (leer_y_guardar.guardar if op == "set" else leer_y_guardar.actualizar)(con, coleccion_, doc_id, data)
    print("\n".join(resumen))
    print("\n%d escrituras guardadas en el CRM." % len(writes) if writes else "\nNada que escribir.")


def mas_dias(fecha, n):
    try:
        d = puntaje.fecha(fecha)
        if d:
            return (d + timedelta(days=int(n))).isoformat()
    except (TypeError, ValueError):
        pass
    falla("fecha inválida '%s': usar AAAA-MM-DD" % fecha)


def clave(s):
    return re.sub(r"\s+", " ", puntaje.sin_tildes(s))


def slug(nombre_clave):
    return re.sub(r"[^a-z0-9]+", "-", nombre_clave).strip("-")[:60].strip("-") or None


def firma(con):
    c = dict(con.execute("SELECT campo, valor FROM perfil WHERE seccion = 'contacto'"))
    if not all(c.get(k) for k in ("nombre", "telefono", "correo")):
        falla("faltan nombre, teléfono o correo en la tabla perfil (sección contacto)")
    return "%s\n%s · %s" % (c["nombre"], c["telefono"], c["correo"])


def armar_carta(cuerpo, idioma, cargo, firma_):
    """La carta llega solo con el cuerpo; el saludo y la firma los pone el script."""
    valida(idioma, SALUDO, "idioma")
    n = len(cuerpo.split())
    if n > MAX_PALABRAS:
        falla("la carta de '%s' tiene %d palabras (máximo %d, sin contar saludo ni firma)." % (cargo, n, MAX_PALABRAS))
    return "%s\n\n%s\n\n%s\n%s" % (SALUDO[idioma], cuerpo.strip(), DESPEDIDA[idioma], firma_)


def tiene_contacto(v, empresas):
    if v.get("correoPostulacion"):
        return True
    e = empresas.get(v.get("empresaId") or "")
    return bool(e and any(c.get("email") for c in e.get("contactos") or []))


def pasar_a_postulada(v, fecha, ajustes, empresas):
    """Campos que cambian cuando una vacante queda postulada (la usan `nuevas` y `cambios`)."""
    if tiene_contacto(v, empresas):
        proxima = {"fecha": mas_dias(fecha, ajustes["diasPrimerSeguimiento"]), "texto": "Enviar seguimiento"}
    else:
        proxima = {"fecha": mas_dias(fecha, ajustes["diasCierreSinNovedad"]), "texto": TEXTO_SIN_NOVEDAD}
    d = {"etapa": "postulada", "estadoPortal": "Postulado", "fechaPostulacion": fecha, "resultado": None,
         "proximaAccion": proxima}
    subir_etapa_max(v, "postulada", d)
    return d


def subir_etapa_max(v, etapa, d):
    """etapaMax solo sube: guarda la etapa más lejana a la que llegó la vacante (la usa el embudo)."""
    if ETAPAS.index(etapa) > ETAPAS.index(v.get("etapaMax") or "descubierta"):
        d["etapaMax"] = etapa


def valida_campo(k, val):
    """perfil, modalidad y contrato solo aceptan los valores de su lista (contrato puede ser null)."""
    if k in ("perfil", "modalidad") or (k == "contrato" and val is not None):
        valida(val, {"perfil": PERFILES, "modalidad": MODALIDADES, "contrato": CONTRATOS}[k], k)


def proxima_tras_seguimiento(seg, fecha, ajustes):
    """Próxima acción después de enviar un seguimiento; misma regla que "Ya lo envié" en pagina.html."""
    if seg >= ajustes["maxSeguimientos"]:
        return {"fecha": mas_dias(fecha, ajustes["diasEntreSeguimientos"]),
                "texto": "Tope de seguimientos: si no responden, cerrar como sin respuesta"}
    dias = ajustes["diasEntreSeguimientos"] if seg else ajustes["diasPrimerSeguimiento"]
    return {"fecha": mas_dias(fecha, dias), "texto": "Enviar seguimiento"}


# ---------------------------------------------------------------- nuevas
def cmd_nuevas(con, entrada, hoy):
    """entrada: lista de vacantes descubiertas. Obligatorios: empresa, cargo, perfil, modalidad, portal y
    aviso (el texto completo del aviso, copiado tal cual: queda guardado aunque la empresa borre la publicación;
    si no hay aviso, lo que dijo el correo o el usuario). Opcionales: ciudad, link, canal ('portal'|'correo'), correoPostulacion, asunto (para canal correo),
    salarioMin, salarioMax, salarioTexto, experienciaAnios, fechaPublicacion, nivel, notas, alertas,
    empresaId (null si el aviso no dice el nombre de la empresa),
    carta (SOLO el cuerpo; el script pone saludo y firma), idioma ('es'|'en', por defecto 'es'),
    excluyente (texto: requisito que la HV no cumple -> se registra cerrada/descartada),
    postulada_por_usuario (true o el texto de la evidencia: El usuario ya se postuló; usar fechaPostulacion).
    Si a alguna le falta la carta, no se guarda nada: se agregan las cartas y se repite."""
    mas_dias(hoy, 0)
    vac, empresas, ajustes = cargar(con)
    firma_ = firma(con)
    items = leer_json(entrada)
    links = {clave(v.get("link")) for v in vac.values() if v.get("link")}
    ecc = {(clave(v.get("empresa")), clave(v.get("cargo")), clave(v.get("ciudad"))) for v in vac.values()}
    n = max([int(k[1:]) for k in vac if re.fullmatch(r"v\d+", k)] + [0])
    writes, resumen, por_aprobar, faltan = [], [], 0, []
    for it in items:
        sobran = set(it) - CAMPOS_NUEVAS
        if sobran:
            falla("'%s' trae campos que no van en 'nuevas': %s" % (it.get("cargo"), sorted(sobran)))
        for c in ["empresa", "cargo", "perfil", "modalidad", "portal", "aviso"]:
            if not it.get(c):
                falla("a '%s' le falta el campo %s" % (it.get("cargo"), c))
        for k in ("perfil", "modalidad", "contrato"):
            valida_campo(k, it.get(k))
        if it.get("fechaPublicacion"):
            mas_dias(it["fechaPublicacion"], 0)  # valida el formato: si no, el puntaje difiere del de puntaje.js
        for a in it.get("alertas") or []:
            valida(a, ALERTAS, "alerta")
        lk = clave(it.get("link"))
        if it.get("link") and lk in links:
            resumen.append("DUPLICADA (link): %s · %s" % (it["empresa"], it["cargo"]))
            continue
        k = (clave(it["empresa"]), clave(it["cargo"]), clave(it.get("ciudad")))
        if k in ecc:
            resumen.append("DUPLICADA (empresa+cargo+ciudad): %s · %s" % (it["empresa"], it["cargo"]))
            continue
        links.add(lk)
        ecc.add(k)
        n += 1
        vid = "v%03d" % n
        cuerpo = it.pop("carta", None)
        idioma = it.pop("idioma", "es")
        asunto = it.pop("asunto", None)
        excluyente = it.pop("excluyente", None)
        por_usuario = it.pop("postulada_por_usuario", None)
        x = copy.deepcopy(DEFAULTS_VACANTE)
        x.update(fechaRegistro=hoy, ultimaActividad=hoy)
        x.update(it)
        x["nivel"] = x.get("nivel") or puntaje.inferir_nivel(x["cargo"])
        if "empresaId" not in it and not EMPRESA_GENERICA.search(k[0]):
            x["empresaId"] = slug(k[0])
        if excluyente:
            x["alertas"] = sorted(set(x["alertas"]) | {"no_aplica"})
            x["notas"] = (x["notas"] + " Requisito excluyente: " + excluyente).strip()
        r = puntaje.puntaje(x, ajustes, hoy)
        x["puntaje"], x["neto"] = r["total"], r["presupuesto"]["neto"]
        fecha_h = hoy
        if por_usuario:
            fecha_h = x["fechaPostulacion"] or hoy
            x.update(pasar_a_postulada(x, fecha_h, ajustes, empresas), ultimaActividad=fecha_h)
            evidencia = por_usuario if isinstance(por_usuario, str) else ""
            estado, tipo = "postulada (la hizo el usuario)", "postulacion"
            texto = ("Postulación por %s hecha por el usuario. %s" % (x["portal"], evidencia)).strip()
        elif "no_aplica" in x["alertas"]:
            x.update(etapa="cerrada", resultado="descartada")
            estado, tipo = "cerrada (no aplica)", "cambio_etapa"
            texto = "Registrada y descartada: " + (excluyente or "requisito excluyente")
        elif "posible_estafa" in x["alertas"]:
            estado, tipo, texto = "descubierta", "nota", "Registrada con alerta de posible estafa. No se postula."
        elif r["total"] >= ajustes["umbralAprobar"] and por_aprobar < ajustes["limitePorCorrida"]:
            if not cuerpo:
                faltan.append(x["empresa"] + " · " + x["cargo"])
                estado, tipo = "descubierta (FALTA CARTA)", "nota"
                texto = "Puntaje %s: falta la carta para pasar a Por aprobar." % r["total"]
            else:
                x.update(etapa="por_aprobar", etapaMax="por_aprobar", estadoPortal="Por aprobar",
                         carta=armar_carta(cuerpo, idioma, x["cargo"], firma_),
                         proximaAccion={"fecha": hoy, "texto": "Aprobar o descartar (carta lista)"})
                por_aprobar += 1
                estado, tipo = "por_aprobar", "nota"
                texto = "Descubierta (%s). Puntaje %s. Pasa a Por aprobar con carta lista." % (x["portal"], r["total"])
        else:
            estado, tipo = "descubierta", "nota"
            texto = "Descubierta (%s). Puntaje %s, bajo el umbral o sobre el límite." % (x["portal"], r["total"])
        x["historial"] = [{"fecha": fecha_h, "tipo": tipo, "texto": texto}]
        writes.append(("set", "vacantes", vid, x))
        if x["etapa"] == "por_aprobar" and x["canal"] == "correo":
            if not x.get("correoPostulacion"):
                falla("'%s' es canal correo pero no tiene correoPostulacion" % x["cargo"])
            bor = {"adjuntarHV": True, "asunto": asunto or "Postulación – " + x["cargo"], "cc": [], "creado": hoy,
                   "cuerpo": x["carta"], "estado": "pendiente", "nota": "Postulación por correo con la HV adjunta.",
                   "para": [x["correoPostulacion"]], "tipo": "postulacion", "vacanteId": vid}
            writes.append(("set", "borradores", "b-%s-1" % vid, bor))
            estado += " + borrador"
        eid = x["empresaId"]
        if eid and eid not in empresas:
            contactos = [{"email": x["correoPostulacion"], "nombre": None, "rol": None, "telefono": None,
                          "fuente": "Aviso de %s (%s)" % (x["portal"], hoy)}] if x.get("correoPostulacion") else []
            empresas[eid] = {"nombre": x["empresa"], "contactos": contactos, "notas": "", "sitio": None}
            writes.append(("set", "empresas", eid, empresas[eid]))
        resumen.append("%s · %s · %s · puntaje %s · neto %s · %s" % (vid, x["empresa"], x["cargo"], r["total"], x["neto"], estado))
    if faltan:
        print("\n".join(resumen))
        falla("no se guardó nada: falta la carta de %s. Agrega \"carta\" a esas y repite." % "; ".join(faltan))
    guardar_todo(con, writes, resumen)


# ---------------------------------------------------------------- cambios
def preparar_cambio(c, v, hoy, ajustes, empresas):
    """Arma el update de una vacante a partir de una entrada de cambio. Devuelve (datos, etiqueta)."""
    vid = c["id"]
    sobran = set(c) - CLAVES_CAMBIO
    if sobran:
        falla("el cambio de %s trae claves que no van: %s (usar %s)" % (vid, sorted(sobran), sorted(CLAVES_CAMBIO)))
    if not c.get("texto"):
        falla("el cambio de %s no tiene 'texto' (qué pasó y la fuente)" % vid)
    tipo = c.get("tipo", "nota")
    valida(tipo, TIPOS_HIST, "tipo")
    fecha = c.get("fecha", hoy)
    mas_dias(fecha, 0)  # valida el formato
    si = c.get("si_del_usuario")
    if si is not None and not (isinstance(si, str) and si.strip()):
        falla("'si_del_usuario' de %s debe ser el texto con que el usuario autorizó en el chat" % vid)
    if "borrador" in c and not si:
        falla("%s: para marcar el borrador %s como enviado falta 'si_del_usuario' (lo que respondió el usuario en el chat)"
              % (vid, c["borrador"]))
    texto = c["texto"] + (" · Autorizado por el usuario en el chat: «%s»" % si.strip() if si else "")
    d = {"historial": (v.get("historial") or []) + [{"fecha": fecha, "tipo": tipo, "texto": texto}],
         "ultimaActividad": hoy}
    etapa = c.get("etapa")
    if etapa:
        valida(etapa, ETAPAS, "etapa")
        if etapa == "postulada":
            if v.get("etapa") != "postulada":  # si ya estaba postulada, no se mueve la fecha ni el plazo
                d.update(pasar_a_postulada(v, fecha, ajustes, empresas))
        elif etapa == "cerrada":
            valida(c.get("resultado"), RESULTADOS, "resultado (obligatorio al cerrar %s)" % vid)
            d.update(etapa="cerrada", resultado=c["resultado"], proximaAccion=None)
        else:
            d.update(etapa=etapa, resultado=None)
            subir_etapa_max(v, etapa, d)
    orig = set(v.get("alertas") or [])
    for a in c.get("alertas_mas") or []:
        valida(a, ALERTAS, "alerta")
    al = (orig | set(c.get("alertas_mas") or [])) - set(c.get("alertas_menos") or [])
    if al != orig:
        d["alertas"] = sorted(al)
    if c.get("notas_mas"):
        d["notas"] = ((v.get("notas") or "") + " " + c["notas_mas"]).strip()
    if "proximaAccion" in c:
        pa = c["proximaAccion"]
        if pa is not None:  # una fecha que no es AAAA-MM-DD nunca vencería: la vacante se perdería de vista
            if not isinstance(pa, dict) or set(pa) != {"fecha", "texto"} or not isinstance(pa["texto"], str) or not pa["texto"].strip():
                falla("proximaAccion de %s debe ser null o {\"fecha\": \"AAAA-MM-DD\", \"texto\": \"...\"}" % vid)
            mas_dias(pa["fecha"], 0)
        d["proximaAccion"] = pa
    for k, val in (c.get("campos") or {}).items():
        valida(k, CAMPOS_LIBRES, "campo en 'campos'")
        valida_campo(k, val)
        d[k] = val
    if tipo == "correo_enviado" and "proximaAccion" not in c and d.get("etapa", v.get("etapa")) != "cerrada":
        d["proximaAccion"] = proxima_tras_seguimiento(d.get("seguimientos", v.get("seguimientos") or 0), fecha, ajustes)
    return d, (v.get("etapa") + " → " + etapa) if etapa else "nota"


def agregar_contacto(c, v, empresas, writes):
    """`contacto` en una entrada de cambios: se agrega a la empresa de la vacante (sin repetir el correo)."""
    nuevo = c["contacto"]
    if not isinstance(nuevo, dict) or not nuevo.get("email") and not nuevo.get("telefono"):
        falla("el contacto de %s necesita al menos email o telefono" % c["id"])
    sobran = set(nuevo) - CAMPOS_CONTACTO
    if sobran:
        falla("el contacto de %s trae campos que no van: %s (usar %s)" % (c["id"], sorted(sobran), sorted(CAMPOS_CONTACTO)))
    eid = v.get("empresaId")
    if not eid:
        falla("la vacante %s no tiene empresa (empresaId): no hay dónde guardar el contacto" % c["id"])
    e = empresas.setdefault(eid, {"nombre": v.get("empresa"), "contactos": [], "notas": "", "sitio": None})
    if nuevo.get("email") and any(x.get("email") == nuevo["email"] for x in e.get("contactos") or []):
        return
    fila = {k: nuevo.get(k) for k in sorted(CAMPOS_CONTACTO)}
    fila["fuente"] = c["texto"]
    e["contactos"] = (e.get("contactos") or []) + [fila]
    writes[:] = [w for w in writes if w[1:3] != ("empresas", eid)] + [("set", "empresas", eid, e)]


def borrador_enviado(con, c, hoy):
    """`borrador` en una entrada de cambios: Claude envió ese correo desde Gmail con el "sí" del usuario."""
    b = leer_y_guardar.leer_uno(con, "borradores", c["borrador"])
    if b is None or b.get("vacanteId") != c["id"]:
        falla("el borrador %s no existe o no es de la vacante %s" % (c["borrador"], c["id"]))
    if b.get("estado") == "enviado":
        falla("el borrador %s ya figura como enviado: revisar Enviados de Gmail antes de repetir" % c["borrador"])
    return ("update", "borradores", c["borrador"], {"estado": "enviado", "enviadoEn": c.get("fecha", hoy)})


def escribir_cambios(con, items, hoy):
    mas_dias(hoy, 0)
    vac, empresas, ajustes = cargar(con)
    for c in items:
        if c.get("id") not in vac:
            falla("no existe la vacante %s en el CRM" % c.get("id"))
    ids = [c["id"] for c in items]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        falla("%s aparece dos veces: junta los cambios en uno solo" % ", ".join(dup))
    writes, resumen = [], []
    for c in items:
        v = vac[c["id"]]
        if "contacto" in c:  # antes del cambio: si la vacante pasa a postulada, el plazo depende del contacto
            agregar_contacto(c, v, empresas, writes)
        d, etiqueta = preparar_cambio(c, v, hoy, ajustes, empresas)
        writes.append(("update", "vacantes", c["id"], d))
        if "borrador" in c:
            writes.append(borrador_enviado(con, c, hoy))
        resumen.append("%s · %s · %s · %s" % (c["id"], v.get("empresa"), v.get("cargo"), etiqueta))
    guardar_todo(con, writes, resumen)


def cmd_cambios(con, entrada, hoy):
    """entrada: lista de cambios a vacantes existentes. Campos:
    id (obligatorio), texto (obligatorio: qué pasó y la fuente, p. ej. 'Correo de Computrabajo del 05-oct'),
    tipo (de TIPOS_HIST, por defecto 'nota'), fecha (del hecho, AAAA-MM-DD, por defecto hoy),
    etapa, resultado (obligatorio si etapa=cerrada), alertas_mas, alertas_menos, notas_mas (texto que se
    agrega a notas), proximaAccion ({fecha, texto} o null), campos (dict; solo los de CAMPOS_LIBRES),
    contacto ({nombre, email, telefono, rol}: se agrega a la empresa de la vacante),
    borrador (id del borrador que Claude envió desde Gmail: queda como enviado; exige si_del_usuario),
    si_del_usuario (texto con que el usuario autorizó el envío en el chat: queda en el historial)."""
    escribir_cambios(con, leer_json(entrada), hoy)


def cmd_aprobar(con, hoy, *ids):
    """El usuario dijo "sí" en el chat a estas vacantes: pasan a Aprobada."""
    if not ids:
        falla("faltan los ids a aprobar")
    for i in ids:  # aprobar una cerrada o ya postulada la devolvería a "aprobada" y borraría su resultado
        v = leer_y_guardar.leer_uno(con, "vacantes", i)
        if v and v.get("etapa") not in ("descubierta", "por_aprobar"):
            falla("%s está en etapa '%s': solo se aprueban las descubiertas o por aprobar" % (i, v.get("etapa")))
    items = [{"id": i, "etapa": "aprobada", "tipo": "cambio_etapa",
              "texto": "Aprobada por el usuario en el chat el %s." % hoy,
              "proximaAccion": {"fecha": hoy, "texto": "Postular (aprobada en el chat)"}} for i in ids]
    escribir_cambios(con, items, hoy)


def vencidas(con, hoy):
    """[(grupo, id, vacante)] con próxima acción vencida. Grupo SIN_CONTACTO o ACCION."""
    mas_dias(hoy, 0)
    filas = []
    for vid, v in sorted(leer_y_guardar.leer(con, "vacantes").items()):
        pa = v.get("proximaAccion") or {}
        if v.get("etapa") != "cerrada" and pa.get("fecha") and pa["fecha"] <= hoy:
            grupo = "SIN_CONTACTO" if (pa.get("texto") or "").startswith(SIN_NOVEDAD) else "ACCION"
            filas.append((grupo, vid, v))
    return filas


def cmd_vencidas(con, hoy):
    filas = vencidas(con, hoy)
    for grupo, vid, v in filas:
        pa = v["proximaAccion"]
        print("%s\t%s\t%s\t%s · %s\t%s" % (grupo, vid, pa["fecha"], v.get("empresa"), v.get("cargo"), pa.get("texto")))
    print("Nada vencido." if not filas else
          "\nSIN_CONTACTO = proponer al usuario cerrarlas (comando cerrar-vencidas). ACCION = revisar una por una.")


def cmd_cerrar_vencidas(con, hoy):
    """El usuario dijo "sí" en el chat a cerrar las vencidas sin contacto: se cierran como sin_respuesta."""
    items = [{"id": vid, "etapa": "cerrada", "resultado": "sin_respuesta", "tipo": "cambio_etapa",
              "texto": "Cerrada como sin respuesta: pasó el plazo sin novedad ni contacto directo. Aprobado por el usuario en el chat el %s." % hoy}
             for grupo, vid, _ in vencidas(con, hoy) if grupo == "SIN_CONTACTO"]
    if not items:
        print("No hay vencidas sin contacto.")
        return
    escribir_cambios(con, items, hoy)


# ---------------------------------------------------------------- registro, perfil, consulta
def cmd_registro(con, hoy, entrada):
    """entrada: {"tipo": "<acciones hechas>", "resumen": "<una línea>", "detalle": ["...", ...]}.
    Si ya hay registro de ese día, se suma al detalle."""
    mas_dias(hoy, 0)
    e = leer_json(entrada)
    if not e.get("resumen") or not isinstance(e.get("detalle", []), list):
        falla("el registro necesita 'resumen' (texto) y 'detalle' (lista)")
    previo = leer_y_guardar.leer_uno(con, "corridas", hoy) or {}
    tipos = [t for t in (previo.get("tipo"), e.get("tipo")) if t]
    doc = dict(previo, fecha=hoy, tipo=", ".join(dict.fromkeys(tipos)) or "corrida", resumen=e["resumen"],
               detalle=(previo.get("detalle") or []) + e.get("detalle", []))
    guardar_todo(con, [("set", "corridas", hoy, doc)], ["Registro del %s: %s" % (hoy, e["resumen"])])


def cmd_perfil(con):
    """Datos del usuario, logros, plantillas y servicios, para escribir cartas y llenar formularios."""
    for seccion in ("contacto", "perfil", "formularios", "portafolio"):
        print("## " + seccion)
        for campo, valor in con.execute("SELECT campo, valor FROM perfil WHERE seccion = ? ORDER BY orden", (seccion,)):
            print("- %s: %s" % (campo, valor))
    aj = puntaje._ajustes(leer_y_guardar.leer_uno(con, "config", "ajustes"))
    print("\n## búsqueda (Ajustes del CRM)")
    print("- ciudad base: %s" % (aj["ciudadBase"] or "(falta)"))
    palabras = dict.fromkeys(p.strip() for c in aj["casos"] for p in str(c.get("palabras") or "").split(",") if p.strip())
    print("- palabras de búsqueda (las de todos los casos): %s" % ", ".join(palabras))
    for i, c in enumerate(aj["casos"], 1):
        print("- Caso %d · palabras: %s · contrato: %s · modalidad: %s · salario mínimo: %s"
              % (i, c.get("palabras") or "(cualquier cargo)", c.get("contrato"), c.get("modalidad"), c.get("salarioMinimo")))
    print("\n## logros")
    for fila in con.execute("SELECT id, logro, cuando FROM logros ORDER BY id"):
        print("- %s: %s (usar en: %s)" % fila)
    print("\n## plantillas")
    for pid, nombre, texto, bloq in con.execute("SELECT id, nombre, texto, bloqueada FROM plantillas ORDER BY id"):
        print("\n### %s — %s%s\n%s" % (pid, nombre, " (BLOQUEADA)" if bloq else "", texto))
    print("\n## servicios (solo para las plantillas D y E)")
    for fila in con.execute("SELECT area, incluye, tarifa FROM servicios ORDER BY orden"):
        print("- %s: %s · %s" % fila)


def cmd_editar_perfil(con, entrada):
    """entrada: {"perfil": [{"seccion", "campo", "valor"}], "logros": [{"id", "logro", "cuando"?}]}.
    Solo cambia filas que ya existen (un campo mal escrito es error, no una fila nueva)."""
    e = leer_json(entrada)
    if not isinstance(e, dict) or set(e) - {"perfil", "logros"} or not (e.get("perfil") or e.get("logros")):
        falla("editar-perfil necesita {\"perfil\": [...]} y/o {\"logros\": [...]}")
    cambios, resumen = [], []
    for p in e.get("perfil", []):
        if not all(isinstance(p.get(k), str) and p[k].strip() for k in ("seccion", "campo", "valor")):
            falla("cada entrada de 'perfil' necesita seccion, campo y valor (texto)")
        fila = con.execute("SELECT valor FROM perfil WHERE seccion = ? AND campo = ?", (p["seccion"], p["campo"])).fetchone()
        if not fila:
            falla("no existe el campo '%s' en la sección '%s' del perfil" % (p["campo"], p["seccion"]))
        cambios.append(("UPDATE perfil SET valor = ? WHERE seccion = ? AND campo = ?", (p["valor"], p["seccion"], p["campo"])))
        resumen.append("perfil/%s · %s: %s → %s" % (p["seccion"], p["campo"], fila[0], p["valor"]))
    for l in e.get("logros", []):
        if not isinstance(l.get("id"), str) or not isinstance(l.get("logro"), str) or not l["logro"].strip():
            falla("cada entrada de 'logros' necesita id y logro (texto)")
        fila = con.execute("SELECT logro, cuando FROM logros WHERE id = ?", (l["id"],)).fetchone()
        if not fila:
            falla("no existe el logro '%s'" % l["id"])
        cuando = l.get("cuando") or fila[1]
        cambios.append(("UPDATE logros SET logro = ?, cuando = ? WHERE id = ?", (l["logro"], cuando, l["id"])))
        resumen.append("logro %s: %s → %s (usar en: %s)" % (l["id"], fila[0], l["logro"], cuando))
    with con:
        for sql, params in cambios:
            con.execute(sql, params)
    print("\n".join(resumen))
    print("\n%d cambios guardados en el perfil." % len(cambios))


def cmd_consulta(ruta, sql):
    """Solo lectura: la base se abre en modo ro, así una consulta nunca cambia datos."""
    con = sqlite3.connect("file:%s?mode=ro" % ruta.replace("\\", "/"), uri=True)
    try:
        cur = con.execute(sql)
    except sqlite3.Error as e:
        falla("consulta inválida: %s" % e)
    print("\t".join(c[0] for c in cur.description or []))
    for fila in cur:
        print("\t".join("" if x is None else str(x) for x in fila))


COMANDOS = {"nuevas": (cmd_nuevas, 2), "cambios": (cmd_cambios, 2), "vencidas": (cmd_vencidas, 1),
            "aprobar": (cmd_aprobar, None), "cerrar-vencidas": (cmd_cerrar_vencidas, 1),
            "registro": (cmd_registro, 2), "perfil": (cmd_perfil, 0), "editar-perfil": (cmd_editar_perfil, 1)}

if __name__ == "__main__":
    a = sys.argv[1:]
    ruta = leer_y_guardar.RUTA
    if a[:1] == ["--db"] and len(a) > 1:
        ruta, a = a[1], a[2:]
    if a[:1] == ["consulta"] and len(a) == 2:
        if not os.path.exists(ruta):
            falla("no existe la base del CRM: %s" % ruta)
        cmd_consulta(ruta, a[1])
        sys.exit()
    cmd = COMANDOS.get(a[0]) if a else None
    if not cmd or (cmd[1] is not None and len(a) - 1 != cmd[1]) or (cmd[1] is None and len(a) < 3):
        sys.exit(__doc__)
    try:
        conexion = leer_y_guardar.conectar(ruta)
    except FileNotFoundError as e:
        falla(str(e))
    # Bloquea la base mientras corre el comando: lo que lee y lo que escribe es una sola transacción, y la página
    # (abrir_pagina.py) espera unos segundos en lugar de escribir en medio.
    conexion.execute("BEGIN IMMEDIATE")
    cmd[0](conexion, *a[1:])
