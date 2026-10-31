"""Crea la base del CRM (Base de datos/finder.db) a partir de tu perfil.json.

Uso:
  python "Base de datos/iniciar.py"                 crea la base con tus datos (perfil.json en la carpeta principal)
  python "Base de datos/iniciar.py" --demo          la crea con vacantes de ejemplo para probar el CRM
  python "Base de datos/iniciar.py" --perfil otro.json --db otra.db

Nunca pisa una base que ya existe: si ya hay una, se detiene. Si algo falla no deja nada a medias.
Los datos se llenan copiando perfil.ejemplo.json a perfil.json (ver el README). Solo usa la biblioteca estándar.
"""
import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import base  # noqa: E402
import motor  # noqa: E402
import servir  # noqa: E402

EJEMPLO = os.path.join(RAIZ, "perfil.ejemplo.json")
SECCIONES = ("contacto", "perfil", "formularios")
CONTRATOS = ("tiempo_completo", "parcial", "cualquiera")
MODALIDADES = ("remoto", "ciudad", "remoto_ciudad", "mudanza", "cualquiera")

# Vacantes inventadas para probar el CRM (--demo). Pasan por crm.py nuevas, igual que las reales.
DEMO = [
    {"empresa": "Acme Contable SAS", "cargo": "Analista Contable", "perfil": "Contable/Financiero", "modalidad": "remoto",
     "portal": "Computrabajo", "link": "https://ejemplo.invalid/acme-analista-contable", "salarioMin": 4200000,
     "salarioMax": 5000000, "aviso": "Aviso de ejemplo: analista contable remoto, 2 años de experiencia, Excel avanzado.",
     "carta": "Me interesa el cargo de Analista Contable en Acme. Cierro cada mes con conciliaciones al día y control de "
              "impuestos. Quedo atento a una entrevista."},
    {"empresa": "Muestra Software SAS", "cargo": "QA Tester Junior", "perfil": "QA", "modalidad": "remoto",
     "portal": "Indeed", "link": "https://ejemplo.invalid/muestra-qa", "salarioMin": 3800000, "salarioMax": 4500000,
     "canal": "correo", "correoPostulacion": "rrhh@ejemplo.invalid", "asunto": "Postulación QA Tester Junior",
     "aviso": "Aviso de ejemplo: QA Tester junior, pruebas manuales y de API. Enviar la HV por correo.",
     "carta": "Me postulo como QA Tester Junior. Tengo formación en pruebas manuales y de API y documento cada defecto "
              "con pasos claros para reproducirlo."},
    {"empresa": "Ejemplo Auditores", "cargo": "Revisor Fiscal", "perfil": "Auditoría/Revisoría", "modalidad": "remoto",
     "contrato": "parcial", "portal": "LinkedIn", "link": "https://ejemplo.invalid/ejemplo-revisor", "salarioMin": 1800000,
     "salarioMax": 2200000, "aviso": "Aviso de ejemplo: revisor fiscal por servicio, medio tiempo, remoto.",
     "carta": "Me interesa la revisoría fiscal por servicio. Tengo experiencia en control interno y cumplimiento "
              "tributario, y disponibilidad para medio tiempo."},
    {"empresa": "Demo Ltda", "cargo": "Contador Senior", "perfil": "Contable/Financiero", "modalidad": "remoto",
     "portal": "Magneto", "link": "https://ejemplo.invalid/demo-contador", "salarioMin": 5200000, "salarioMax": 6000000,
     "aviso": "Aviso de ejemplo: contador senior remoto.", "postulada_por_usuario": "Postulación de ejemplo hecha en el portal",
     "fechaPostulacion": None},
    # Sin salario y con aviso viejo: así las pruebas de paridad del puntaje cubren esos caminos.
    {"empresa": "Prueba Logística SAS", "cargo": "Auxiliar Contable", "perfil": "Contable/Financiero", "modalidad": "remoto",
     "portal": "Computrabajo", "link": "https://ejemplo.invalid/prueba-auxiliar", "fechaPublicacion": "2026-01-15",
     "aviso": "Aviso de ejemplo sin salario publicado.", "carta": "Me interesa el cargo de Auxiliar Contable."},
    {"empresa": "Ficticia Seguros", "cargo": "Auditor Interno", "perfil": "Auditoría/Revisoría", "modalidad": "remoto",
     "portal": "LinkedIn", "link": "https://ejemplo.invalid/ficticia-auditor", "salarioMin": 6000000,
     "aviso": "Aviso de ejemplo que pide 8 años en SAP.", "excluyente": "8 años en SAP"},
]

PLANTILLAS = [
    ("A", "Postulación sin respuesta (7 a 15 días)", 0,
     "Asunto: Seguimiento — postulación a [Cargo]\n\nCordial saludo,\n\nMe postulé a la vacante de [Cargo] el [fecha] a través de "
     "[portal]. Escribo para confirmar que mi hoja de vida fue recibida y conocer en qué etapa se encuentra el proceso.\n\n"
     "Soy {titulo} con {experiencia}. [Logro en una línea.]\n\nQuedo atento a cualquier información adicional que requieran "
     "para avanzar.\n\nCordialmente,\n{firma}"),
    ("B", "La empresa ya vio la HV pero no ha contactado", 0,
     "Asunto: [Cargo] — disponibilidad e información adicional\n\nCordial saludo,\n\nVi que revisaron mi perfil para la vacante "
     "de [Cargo], y quería ponerme a disposición por si necesitan ampliar algún punto de mi experiencia.\n\n[Logro en una o dos "
     "líneas, escogido por afinidad con el cargo.]\n\nEstoy disponible para una entrevista en el horario que les convenga y "
     "puedo enviar certificaciones o referencias si las requieren.\n\nCordialmente,\n{firma}"),
    ("C", "Después de entrevista o en lista de espera", 0,
     "Asunto: Seguimiento tras nuestra conversación — [Cargo]\n\nCordial saludo [Nombre],\n\nGracias nuevamente por el espacio del "
     "[fecha]. Quería retomar el contacto para saber si el proceso de [Cargo] ha tenido movimiento y confirmarles que mi interés "
     "y disponibilidad siguen vigentes.\n\n[Una línea que retome algo concreto de la entrevista, si aplica.]\n\nSi la posición "
     "ya fue cubierta, agradezco que me lo indiquen y quedo atento a futuras oportunidades en el equipo.\n\nCordialmente,\n{nombre}"),
    ("F", "LinkedIn (máx. 300 caracteres)", 0,
     "Buen día [Nombre], me postulé a la vacante de [Cargo] en [empresa]. Soy {titulo} con {experiencia}. Quedo atento si "
     "necesitan ampliar algo de mi perfil. Gracias."),
    ("G", "Guion telefónico", 0,
     "1. Presentación (10 s): \"Buen día, habla {nombre}, {titulo}. Me postulé a la vacante de [Cargo] el [fecha].\"\n"
     "2. Motivo (10 s): \"Llamo para confirmar que recibieron mi hoja de vida y saber en qué etapa va el proceso.\"\n"
     "3. Si piden perfil (20 s): {experiencia} + [logro] + disponibilidad y modalidad.\n"
     "4. Cierre: pedir nombre y correo de quien lleva el proceso, y confirmar si pueden avisar por ese medio.\n"
     "5. Lo que salga de la llamada se registra en el CRM con la acción \"Búsquedas externas\"."),
]


def falla(msg):
    sys.exit("ERROR: " + msg)


def cargar(ruta):
    if not os.path.exists(ruta):
        falla("no encuentro %s. Copia perfil.ejemplo.json a perfil.json y llénalo (ver el README)." % ruta)
    try:
        with open(ruta, encoding="utf-8-sig") as f:  # -sig: el Bloc de notas de Windows guarda con BOM
            return json.load(f)
    except ValueError as e:
        falla("%s no es un JSON válido: %s" % (ruta, e))


def texto(valor, donde):
    if not isinstance(valor, str) or not valor.strip():
        falla("%s debe ser un texto con contenido" % donde)
    if "<" in valor and ">" in valor:
        falla("%s todavía tiene un <marcador> sin llenar: %s" % (donde, valor))
    return valor.strip()


def validar(p):
    """Devuelve una copia del perfil ya limpia; ERROR: con el campo exacto si falta algo."""
    if not isinstance(p, dict):
        falla("el perfil debe ser un objeto JSON")
    p = copy.deepcopy(p)
    for s in SECCIONES:
        if not isinstance(p.get(s), dict) or not p[s]:
            falla("falta la sección '%s' (o está vacía)" % s)
        p[s] = {k: texto(v, "%s.%s" % (s, k)) for k, v in p[s].items()}
    for k in ("nombre", "telefono", "correo"):
        if k not in p["contacto"]:
            falla("contacto.%s es obligatorio: va en la firma de cada carta" % k)
    for k in ("titulo", "experiencia"):
        if k not in p["perfil"]:
            falla("perfil.%s es obligatorio: lo usan las plantillas" % k)
    logros = p.get("logros")
    if not isinstance(logros, list) or not logros:
        falla("'logros' necesita al menos un logro: {\"logro\": \"...\", \"usar_en\": \"...\"}")
    p["logros"] = [(texto(l.get("logro"), "logros[%d].logro" % i), texto(l.get("usar_en"), "logros[%d].usar_en" % i))
                   for i, l in enumerate(logros)]
    b = p.get("busqueda")
    if not isinstance(b, dict) or not isinstance(b.get("casos"), list) or not b["casos"]:
        falla("'busqueda' necesita 'casos' con al menos un caso de búsqueda")
    sobran = set(b) - set(motor.AJUSTES_BASE)
    if sobran:
        falla("busqueda tiene claves que no existen: %s (las válidas: %s)" % (", ".join(sorted(sobran)), ", ".join(motor.AJUSTES_BASE)))
    for i, c in enumerate(b["casos"], 1):
        if not isinstance(c, dict) or c.get("contrato") not in CONTRATOS or c.get("modalidad") not in MODALIDADES \
                or c.get("salarioMinimo") is None:
            falla("busqueda.casos[%d] necesita contrato %s, modalidad %s y salarioMinimo" % (i, CONTRATOS, MODALIDADES))
        if c.get("palabras"):  # sin palabras = cualquier cargo
            texto(c["palabras"], "busqueda.casos[%d].palabras" % i)
    error = servir.ajustes_invalidos(b)  # la misma validación que usa la página al guardar Ajustes
    if error:
        falla("busqueda: " + error)
    return p


def es_ejemplo(contacto):
    """True si algún dato de la firma sigue siendo el de perfil.ejemplo.json."""
    with open(EJEMPLO, encoding="utf-8-sig") as f:
        ej = json.load(f)["contacto"]
    return any(contacto.get(k) == ej.get(k) for k in ("nombre", "telefono", "correo")) \
        or contacto["correo"].endswith(".invalid")


def crear(ruta, perfil, demo=False, hoy=None):
    """Crea la base en `ruta` (que no debe existir). Con demo agrega vacantes de ejemplo."""
    if os.path.exists(ruta):
        falla("ya existe %s. No la piso: si quieres empezar de cero, bórrala tú (haz antes una copia)." % ruta)
    p = validar(perfil)
    if es_ejemplo(p["contacto"]) and not demo:
        falla("el nombre, el teléfono o el correo de contacto siguen siendo los del ejemplo. Pon tus datos en perfil.json "
              "(o usa --demo para probar).")
    hoy = hoy or date.today().isoformat()
    tmp = ruta + ".nuevo"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = base.conectar(tmp, crear=True)
    try:
        with con:
            orden = 0
            for seccion in SECCIONES:
                for campo, valor in p[seccion].items():
                    orden += 1
                    con.execute("INSERT INTO perfil (seccion, campo, valor, orden) VALUES (?, ?, ?, ?)",
                                (seccion, campo, valor, orden))
            for i, (logro, usar_en) in enumerate(p["logros"], 1):
                con.execute("INSERT INTO logros (id, logro, cuando) VALUES (?, ?, ?)", ("L%d" % i, logro, usar_en))
            c = p["contacto"]
            datos = {"nombre": c["nombre"], "firma": "%s\n%s · %s" % (c["nombre"], c["telefono"], c["correo"]),
                     "titulo": p["perfil"]["titulo"], "experiencia": p["perfil"]["experiencia"]}
            for pid, nombre, bloqueada, cuerpo in PLANTILLAS:
                con.execute("INSERT INTO plantillas (id, nombre, texto, bloqueada) VALUES (?, ?, ?, ?)",
                            (pid, nombre, cuerpo.format(**datos), bloqueada))
            base.guardar(con, "config", "ajustes", p["busqueda"])
        con.close()
        if demo:
            entradas = [dict(v, fechaPostulacion=hoy) if "fechaPostulacion" in v else v for v in DEMO]
            with tempfile.TemporaryDirectory() as d:
                ruta_json = os.path.join(d, "demo.json")
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(entradas, f, ensure_ascii=False)
                r = subprocess.run([sys.executable, os.path.join(AQUI, "crm.py"), "--db", tmp, "nuevas", ruta_json, hoy],
                                   capture_output=True, text=True, encoding="utf-8")
            if r.returncode:
                falla("no se pudieron cargar las vacantes de ejemplo: " + (r.stdout + r.stderr).strip())
        os.replace(tmp, ruta)
    except BaseException:
        try:
            con.close()
        except Exception:
            pass
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--perfil", default=os.path.join(RAIZ, "perfil.json"))
    ap.add_argument("--db", default=base.RUTA)
    ap.add_argument("--demo", action="store_true", help="agrega vacantes de ejemplo y usa perfil.ejemplo.json si no hay perfil.json")
    a = ap.parse_args()
    ruta_perfil = a.perfil
    if a.demo and not os.path.exists(ruta_perfil):
        ruta_perfil = EJEMPLO
    crear(a.db, cargar(ruta_perfil), demo=a.demo)
    print("Listo: %s" % a.db)
    print("Siguiente paso: abre el CRM con 'Abrir CRM.bat' (o python \"Base de datos/servir.py\").")
