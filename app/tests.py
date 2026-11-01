"""Pruebas del CRM: python "app/tests.py"   (o con -v para ver cada una)

Nunca tocan tu base: crean una base de ejemplo (init_db.py --demo, con sus datos de ejemplo) en una carpeta temporal y
cada prueba trabaja sobre su propia copia. Cubren el puntaje (y la paridad con scoring.js si hay node), los comandos de cli.py, que un ERROR no
cambie nada, y la API de server.py. Es el paso 5 de "Revisar o simplificar el código" en .claude/CLAUDE.md: todo debe salir OK.
Solo usa la biblioteca estándar de Python.
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import storage  # noqa: E402
import cli  # noqa: E402
import init_db  # noqa: E402
import scoring  # noqa: E402

CRM = os.path.join(AQUI, "cli.py")
HOY = "2026-10-27"
TMP = None
MOLDE = None  # base de ejemplo creada al empezar; cada prueba copia este molde


def setUpModule():
    global TMP, MOLDE
    TMP = tempfile.mkdtemp(prefix="finder-pruebas-")
    MOLDE = os.path.join(TMP, "molde.db")
    init_db.crear(MOLDE, init_db.EJEMPLO, demo=True, hoy=HOY)


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


class Base(unittest.TestCase):
    """Cada prueba tiene su copia (self.db) y ayudas para correr cli.py y leer la base."""

    def setUp(self):
        self.db = os.path.join(TMP, "%s.db" % self.id().split(".")[-1])
        shutil.copy(MOLDE, self.db)
        self.assertNotEqual(os.path.abspath(self.db), os.path.abspath(storage.RUTA))

    def cli(self, *args):
        r = subprocess.run([sys.executable, CRM, "--db", self.db] + list(args), capture_output=True, text=True,
                           encoding="utf-8")
        return r.returncode, r.stdout + r.stderr

    def json_tmp(self, datos):
        ruta = os.path.join(TMP, "entrada-%s.json" % self.id().split(".")[-1])
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        return ruta

    def foto(self):
        """Todo el contenido de la base, para comprobar que un ERROR no cambió nada."""
        con = sqlite3.connect(self.db)
        try:
            tablas = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
            return {t: sorted(map(repr, con.execute("SELECT * FROM %s" % t))) for t in tablas}
        finally:
            con.close()

    def vac(self, vid):
        con = sqlite3.connect(self.db)
        try:
            return storage.leer_uno(con, "vacantes", vid)
        finally:
            con.close()

    def consulta(self, sql):
        con = sqlite3.connect(self.db)
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()

    def abierta(self, con_empresa=False):
        filtro = " AND json_extract(data, '$.empresaId') IS NOT NULL" if con_empresa else ""
        return self.consulta("SELECT id FROM vacantes WHERE json_extract(data, '$.etapa') <> 'cerrada'%s ORDER BY id LIMIT 1"
                             % filtro)[0][0]

    def falla_sin_cambios(self, *args):
        antes = self.foto()
        codigo, salida = self.cli(*args)
        self.assertNotEqual(codigo, 0, salida)
        self.assertIn("ERROR:", salida)
        self.assertEqual(antes, self.foto(), "un ERROR cambió la base")
        return salida


def nueva(**extra):
    v = {"empresa": "Empresa De Prueba SAS", "cargo": "Contador Público", "perfil": "Contable/Financiero",
         "modalidad": "remoto", "portal": "Indeed", "aviso": "Aviso de prueba", "link": "https://ejemplo.invalid/1",
         "fechaPublicacion": HOY, "salarioMin": 5000000, "salarioMax": 6000000, "carta": "Cuerpo de prueba."}
    v.update(extra)
    return v


# ---------------------------------------------------------------- puntaje
class Motor(unittest.TestCase):
    def test_redondeo_como_js(self):
        self.assertEqual(scoring.salario_referencia({"salarioMin": 1, "salarioMax": 2}), 2)  # 1,5 sube, no va al par
        self.assertEqual(scoring.salario_referencia({"salarioMin": 3}), 3)

    def test_fechas_estrictas(self):
        for mala in ("2026-02-30", "20261022", "2026-10", None, ""):
            self.assertIsNone(scoring.fecha(mala), mala)
        self.assertEqual(scoring.dias_entre("2026-10-20", "2026-10-27"), 7)

    def test_palabras_por_prefijo(self):
        casos = scoring.AJUSTES_BASE["casos"]
        for cargo in ("Analista de Cuentas por Pagar", "IT Audit and Fraud", "Controller Colombia", "Revisora fiscal",
                      "Analista Financiero", "Contadora", "QA Tester"):
            self.assertGreaterEqual(scoring.caso_de({"cargo": cargo}, "remoto", casos), 0, cargo)
        self.assertEqual(scoring.caso_de({"cargo": "Gerente de Proyectos"}, "remoto", casos), -1)

    def test_bloqueos(self):
        v = {"cargo": "Contador", "perfil": "Contable/Financiero", "modalidad": "remoto"}
        self.assertGreater(scoring.puntaje(v, None, HOY)["total"], 0)
        for alerta, motivo in (("posible_estafa", "Posible estafa"), ("no_aplica", "No cumples un requisito excluyente")):
            r = scoring.puntaje(dict(v, alertas=[alerta]), None, HOY)
            self.assertEqual((r["total"], r["bloqueo"]), (0, motivo))
        r = scoring.puntaje(dict(v, cargo="Gerente de Proyectos"), None, HOY)
        self.assertEqual((r["total"], r["bloqueo"]), (0, "Ningún caso de búsqueda la acepta"))

    def test_salario_bajo_el_minimo(self):
        v = {"cargo": "Contador", "perfil": "Contable/Financiero", "modalidad": "remoto", "salarioMin": 1000000}
        self.assertEqual(scoring.puntaje(v, None, HOY)["partes"]["economico"], 0)

    @unittest.skipUnless(shutil.which("node"), "sin node: no se puede comparar con scoring.js")
    def test_paridad_con_motor_js(self):
        for hoy in (HOY, date.today().isoformat(), "2027-03-01"):
            self.assertEqual(scoring.paridad(MOLDE, hoy), [], hoy)


# ---------------------------------------------------------------- cli.py nuevas
class Nuevas(Base):
    def test_registra_y_pasa_a_por_aprobar(self):
        codigo, salida = self.cli("nuevas", self.json_tmp([nueva()]), HOY)
        self.assertEqual(codigo, 0, salida)
        vid = salida.split(" · ")[0]
        v = self.vac(vid)
        self.assertEqual(v["etapa"], "por_aprobar")
        self.assertTrue(v["carta"].startswith("Cordial saludo,") and "Cuerpo de prueba." in v["carta"])
        self.assertEqual(len(v["historial"]), 1)
        self.assertEqual(v["_rev"], 1)

    def test_falta_carta_no_guarda_nada(self):
        self.assertIn("falta la carta", self.falla_sin_cambios("nuevas", self.json_tmp([nueva(carta=None)]), HOY))

    def test_carta_larga(self):
        self.falla_sin_cambios("nuevas", self.json_tmp([nueva(carta=" ".join(["palabra"] * 151))]), HOY)

    def test_campo_sobrante(self):
        self.falla_sin_cambios("nuevas", self.json_tmp([nueva(sueldo=1)]), HOY)

    def test_falta_obligatorio(self):
        self.falla_sin_cambios("nuevas", self.json_tmp([nueva(aviso="")]), HOY)

    def test_duplicada_por_link(self):
        link = self.consulta("SELECT link FROM vacantes_v WHERE link IS NOT NULL LIMIT 1")[0][0]
        antes = self.foto()
        codigo, salida = self.cli("nuevas", self.json_tmp([nueva(link=link)]), HOY)
        self.assertEqual(codigo, 0, salida)
        self.assertIn("DUPLICADA (link)", salida)
        self.assertEqual(antes, self.foto())

    def test_excluyente_queda_cerrada(self):
        codigo, salida = self.cli("nuevas", self.json_tmp([nueva(excluyente="5 años en SAP")]), HOY)
        self.assertEqual(codigo, 0, salida)
        v = self.vac(salida.split(" · ")[0])
        self.assertEqual((v["etapa"], v["resultado"], v["puntaje"]), ("cerrada", "descartada", 0))

    def test_canal_correo_crea_borrador(self):
        codigo, salida = self.cli("nuevas", self.json_tmp([nueva(canal="correo", correoPostulacion="rrhh@ejemplo.invalid")]), HOY)
        self.assertEqual(codigo, 0, salida)
        vid = salida.split(" · ")[0]
        self.assertEqual(self.consulta("SELECT estado FROM borradores_v WHERE id = 'b-%s-1'" % vid), [("pendiente",)])


# ---------------------------------------------------------------- cli.py cambios
class Cambios(Base):
    def test_historial_solo_crece_y_sube_rev(self):
        vid = self.abierta()
        antes = self.vac(vid)
        codigo, salida = self.cli("cambios", self.json_tmp([{"id": vid, "texto": "Nota de prueba"}]), HOY)
        self.assertEqual(codigo, 0, salida)
        despues = self.vac(vid)
        self.assertEqual(despues["historial"][:-1], antes["historial"])
        self.assertEqual(despues["historial"][-1]["texto"], "Nota de prueba")
        self.assertEqual(despues["_rev"], (antes.get("_rev") or 0) + 1)

    def test_clave_mal_escrita(self):
        vid = self.abierta()
        self.assertIn("claves que no van", self.falla_sin_cambios(
            "cambios", self.json_tmp([{"id": vid, "texto": "x", "etapo": "oferta"}]), HOY))

    def test_proxima_accion_mal_formada(self):
        vid = self.abierta()
        for mala in ({"fecha": "mañana", "texto": "x"}, {"fecha": HOY}, {"fecha": HOY, "texto": " "}, "2026-11-01"):
            self.falla_sin_cambios("cambios", self.json_tmp([{"id": vid, "texto": "x", "proximaAccion": mala}]), HOY)

    def test_proxima_accion_valida_o_null(self):
        vid = self.abierta()
        pa = {"fecha": "2026-11-05", "texto": "Llamar"}
        self.assertEqual(self.cli("cambios", self.json_tmp([{"id": vid, "texto": "x", "proximaAccion": pa}]), HOY)[0], 0)
        self.assertEqual(self.vac(vid)["proximaAccion"], pa)
        self.assertEqual(self.cli("cambios", self.json_tmp([{"id": vid, "texto": "y", "proximaAccion": None}]), HOY)[0], 0)
        self.assertIsNone(self.vac(vid)["proximaAccion"])

    def test_cerrar_exige_resultado(self):
        self.falla_sin_cambios("cambios", self.json_tmp([{"id": self.abierta(), "texto": "x", "etapa": "cerrada"}]), HOY)

    def test_un_id_malo_rechaza_toda_la_lista(self):
        self.falla_sin_cambios("cambios", self.json_tmp([{"id": self.abierta(), "texto": "ok"}, {"id": "v999", "texto": "x"}]), HOY)

    def test_campo_no_permitido_y_fecha_mala(self):
        vid = self.abierta()
        self.falla_sin_cambios("cambios", self.json_tmp([{"id": vid, "texto": "x", "campos": {"puntaje": 100}}]), HOY)
        self.falla_sin_cambios("cambios", self.json_tmp([{"id": vid, "texto": "x", "fecha": "2026-13-40"}]), HOY)

    def test_borrador_exige_si_y_no_se_envia_dos_veces(self):
        bid, vid = self.consulta("SELECT id, vacanteId FROM borradores_v WHERE estado <> 'enviado' LIMIT 1")[0]
        entrada = {"id": vid, "tipo": "correo_enviado", "borrador": bid, "texto": "Enviado"}
        self.assertIn("si_del_usuario", self.falla_sin_cambios("cambios", self.json_tmp([entrada]), HOY))
        entrada["si_del_usuario"] = "sí a 2"
        self.assertEqual(self.cli("cambios", self.json_tmp([entrada]), HOY)[0], 0)
        self.assertIn("«sí a 2»", self.vac(vid)["historial"][-1]["texto"])
        self.assertIn("ya figura como enviado", self.falla_sin_cambios("cambios", self.json_tmp([entrada]), HOY))

    def test_contacto_sin_repetir_correo(self):
        vid = self.abierta(con_empresa=True)
        eid = self.vac(vid)["empresaId"]
        entrada = {"id": vid, "texto": "Correo del reclutador", "contacto": {"nombre": "Ana", "email": "ana@ejemplo.invalid"}}
        for _ in range(2):
            self.assertEqual(self.cli("cambios", self.json_tmp([entrada]), HOY)[0], 0)
        contactos = json.loads(self.consulta("SELECT data FROM empresas WHERE id = '%s'" % eid)[0][0])["contactos"]
        self.assertEqual(sum(c.get("email") == "ana@ejemplo.invalid" for c in contactos), 1)

    def test_aprobar(self):
        vid = self.cli("nuevas", self.json_tmp([nueva()]), HOY)[1].split(" · ")[0]  # una por aprobar, sin depender de la base
        self.assertEqual(self.cli("aprobar", HOY, vid)[0], 0)
        self.assertEqual(self.vac(vid)["etapa"], "aprobada")
        self.assertNotEqual(self.cli("aprobar", HOY, vid)[0], 0)  # ya aprobada: no se vuelve a aprobar


# ---------------------------------------------------------------- vencidas, registro, perfil, consulta
class Otros(Base):
    def test_cerrar_vencidas_solo_sin_contacto(self):
        ids = [i for (i,) in self.consulta("SELECT id FROM vacantes WHERE json_extract(data, '$.etapa') <> 'cerrada' ORDER BY id LIMIT 2")]
        sin, con = ids
        entradas = [{"id": sin, "texto": "x", "proximaAccion": {"fecha": "2026-01-01", "texto": cli.TEXTO_SIN_NOVEDAD}},
                    {"id": con, "texto": "x", "proximaAccion": {"fecha": "2026-01-01", "texto": "Enviar seguimiento"}}]
        self.assertEqual(self.cli("cambios", self.json_tmp(entradas), HOY)[0], 0)
        salida = self.cli("vencidas", HOY)[1]
        self.assertIn("SIN_CONTACTO\t%s" % sin, salida)
        self.assertIn("ACCION\t%s" % con, salida)
        self.assertEqual(self.cli("cerrar-vencidas", HOY)[0], 0)
        self.assertEqual((self.vac(sin)["etapa"], self.vac(sin)["resultado"]), ("cerrada", "sin_respuesta"))
        self.assertNotEqual(self.vac(con)["etapa"], "cerrada")

    def test_registro_suma_el_detalle(self):
        self.assertEqual(self.cli("registro", "2030-01-01", self.json_tmp({"tipo": "a", "resumen": "uno", "detalle": ["d1"]}))[0], 0)
        self.assertEqual(self.cli("registro", "2030-01-01", self.json_tmp({"tipo": "b", "resumen": "dos", "detalle": ["d2"]}))[0], 0)
        doc = json.loads(self.consulta("SELECT data FROM corridas WHERE id = '2030-01-01'")[0][0])
        self.assertEqual((doc["detalle"], doc["tipo"], doc["resumen"]), (["d1", "d2"], "a, b", "dos"))

    def test_editar_perfil_campo_inexistente(self):
        self.falla_sin_cambios("editar-perfil", self.json_tmp({"perfil": [{"seccion": "contacto", "campo": "no existe", "valor": "x"}]}))

    def test_perfil_imprime_secciones(self):
        codigo, salida = self.cli("perfil")
        self.assertEqual(codigo, 0, salida)
        for s in ("## contacto", "## logros", "## plantillas", "palabras de búsqueda"):
            self.assertIn(s, salida)

    def test_consulta_es_solo_lectura(self):
        self.falla_sin_cambios("consulta", "UPDATE vacantes SET data = '{}'")


# ---------------------------------------------------------------- server.py
class Servidor(Base):
    def setUp(self):
        super().setUp()
        import server
        self.servidor = server.http.server.ThreadingHTTPServer(("127.0.0.1", 0), server.Manejador)
        self.puerto = self.servidor.server_address[1]
        self._hosts, self._db = server.HOSTS, server.Manejador.ruta_db
        server.HOSTS = {"127.0.0.1:%d" % self.puerto, "localhost:%d" % self.puerto}
        server.Manejador.ruta_db = self.db
        self.server = server
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def tearDown(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.server.HOSTS, self.server.Manejador.ruta_db = self._hosts, self._db

    def pedir(self, ruta, cuerpo=None, cabeceras=None, tipo="application/json"):
        datos = None if cuerpo is None else (cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode())
        h = dict({"Content-Type": tipo} if datos is not None else {}, **(cabeceras or {}))
        r = urllib.request.Request("http://127.0.0.1:%d%s" % (self.puerto, ruta), datos, h, method="POST" if datos else "GET")
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_origen_y_formato(self):
        self.assertEqual(self.pedir("/api/vacantes", cabeceras={"Origin": "http://otro.invalid"})[0], 403)
        self.assertEqual(self.pedir("/api/vacantes", cabeceras={"Host": "otro.invalid"})[0], 403)
        self.assertEqual(self.pedir("/api/perfil")[0], 404)
        self.assertEqual(self.pedir("/api/vacantes/v001", b"x", tipo="text/plain")[0], 415)
        self.assertEqual(self.pedir("/api/vacantes/v999", {"op": "update", "data": {"a": 1}})[0], 404)

    def test_version_e_historial(self):
        vid = self.abierta()
        v = self.vac(vid)
        rev = v.get("_rev") or 0
        self.assertEqual(self.pedir("/api/vacantes/" + vid, {"op": "update", "data": {"notas": "a", "_rev": rev}})[0], 204)
        self.assertEqual(self.vac(vid)["_rev"], rev + 1)
        antes = self.foto()
        self.assertEqual(self.pedir("/api/vacantes/" + vid, {"op": "update", "data": {"notas": "b", "_rev": rev}})[0], 409)
        self.assertEqual(self.pedir("/api/vacantes/" + vid, {"op": "update", "data": {"historial": []}})[0], 409)
        self.assertEqual(antes, self.foto())

    def test_ajustes_con_tipos_malos(self):
        antes = self.foto()
        for malo in ({"umbralAprobar": "mucho"}, {"casos": "x"}, {"casos": [{"salarioMinimo": "alto"}]}, {"ciudadBase": 3}):
            self.assertEqual(self.pedir("/api/config/ajustes", {"op": "update", "data": malo})[0], 400, malo)
        self.assertEqual(antes, self.foto())
        self.assertEqual(self.pedir("/api/config/ajustes", {"op": "update", "data": {"umbralAprobar": 65}})[0], 204)

    def test_lee_colecciones_y_pagina(self):
        codigo, cuerpo = self.pedir("/api/vacantes")
        self.assertEqual(codigo, 200)
        self.assertEqual(len(json.loads(cuerpo)), self.consulta("SELECT count(*) FROM vacantes")[0][0])
        self.assertEqual(self.pedir("/")[0], 200)
        self.assertEqual(self.pedir("/scoring.js")[0], 200)


if __name__ == "__main__":
    unittest.main()
