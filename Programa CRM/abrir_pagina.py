"""Abre el CRM en este computador: python "Programa CRM/abrir_pagina.py" [--db ruta] [--sin-navegador]

Sirve la página (pagina.html, puntaje.js y la HV) y una API mínima sobre postulaciones.db:
  GET  /api/<coleccion>        -> [{"id", "data"}, ...]
  POST /api/<coleccion>/<id>   cuerpo {"op": "set"|"update", "data": {...}}
       Con "_rev" en data: 409 si el registro cambió desde esa versión. 409 también si acorta el historial de una vacante.
Solo escucha en 127.0.0.1 y solo acepta pedidos que vengan de la propia página.
"""
import http.server
import json
import os
import sys
import webbrowser

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)  # Finder_Work: ahí están las carpetas de contexto (la HV)
sys.path.insert(0, AQUI)
import leer_y_guardar  # noqa: E402
import puntaje  # noqa: E402

PUERTO = 8765
HOSTS = {"127.0.0.1:%d" % PUERTO, "localhost:%d" % PUERTO}
ARCHIVOS = {"/": (os.path.join(AQUI, "pagina.html"), "text/html; charset=utf-8"),
            "/puntaje.js": (os.path.join(AQUI, "puntaje.js"), "text/javascript; charset=utf-8"),
            "/hv/HV.pdf": (os.path.join(RAIZ, "Mi hoja de vida", "HV.pdf"), "application/pdf")}


def ajustes_invalidos(a):
    """Qué ajuste tiene un tipo que el puntaje no sabe usar (un texto donde va un número), o None si todo está bien."""
    numero = lambda x: puntaje.num(x) is not None  # noqa: E731
    for k, base_ in puntaje.AJUSTES_BASE.items():
        if k not in a:
            continue
        if numero(base_) and not numero(a[k]):
            return "%s debe ser un número" % k
        if isinstance(base_, str) and not isinstance(a[k], str):
            return "%s debe ser texto" % k
    casos = a.get("casos", [])
    if not isinstance(casos, list) or not all(isinstance(c, dict) for c in casos):
        return "casos debe ser una lista"
    for i, c in enumerate(casos, 1):
        if c.get("salarioMinimo") is not None and not numero(c["salarioMinimo"]):
            return "el salario mínimo del caso %d debe ser un número" % i
        if not isinstance(c.get("palabras") or "", str):
            return "las palabras del caso %d deben ser texto" % i
    return None


class Manejador(http.server.BaseHTTPRequestHandler):
    ruta_db = leer_y_guardar.RUTA

    def responder(self, codigo, cuerpo=b"", tipo="application/json; charset=utf-8"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def error_json(self, codigo, msg):
        self.responder(codigo, json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8"))

    def propio(self):
        # Evita que otra página abierta en el navegador lea o cambie la base (DNS rebinding / CSRF).
        origen = self.headers.get("Origin")
        return self.headers.get("Host") in HOSTS and (origen is None or origen.split("//")[-1] in HOSTS)

    def coleccion(self):
        partes = self.path.split("?")[0].strip("/").split("/")
        if len(partes) < 2 or partes[0] != "api" or partes[1] not in leer_y_guardar.COLECCIONES:
            return None, None
        return partes[1], (partes[2] if len(partes) == 3 and partes[2] else None)

    def do_GET(self):
        if not self.propio():
            return self.error_json(403, "pedido de otro origen")
        if self.path.split("?")[0] in ARCHIVOS:
            nombre, tipo = ARCHIVOS[self.path.split("?")[0]]
            try:
                with open(nombre, "rb") as f:
                    return self.responder(200, f.read(), tipo)
            except OSError:
                return self.error_json(404, "falta el archivo %s" % os.path.basename(nombre))
        col, _ = self.coleccion()
        if not col:
            return self.error_json(404, "no existe")
        con = leer_y_guardar.conectar(self.ruta_db)
        try:
            filas = [{"id": i, "data": d} for i, d in sorted(leer_y_guardar.leer(con, col).items())]
        finally:
            con.close()
        self.responder(200, json.dumps(filas, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        if not self.propio():
            return self.error_json(403, "pedido de otro origen")
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self.error_json(415, "se espera JSON")
        col, doc_id = self.coleccion()
        if not col or not doc_id:
            return self.error_json(404, "no existe")
        try:
            pedido = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)))
            op, data = pedido["op"], pedido["data"]
            if op not in ("set", "update") or not isinstance(data, dict):
                raise ValueError
        except (ValueError, KeyError, TypeError):
            return self.error_json(400, "pedido inválido")
        con = leer_y_guardar.conectar(self.ruta_db)
        try:
            con.execute("BEGIN IMMEDIATE")  # leer y escribir sin que comandos.py escriba en medio
            with con:
                actual = leer_y_guardar.leer_uno(con, col, doc_id)
                if op == "update" and actual is None:
                    return self.error_json(404, "no existe %s/%s" % (col, doc_id))
                # "_rev" = la versión que leyó la página. Si cambió desde entonces no se escribe y la página relee.
                esperado = data.pop("_rev", None)
                if esperado is not None and actual is not None and (actual.get("_rev") or 0) != esperado:
                    return self.error_json(409, "el registro cambió después de leerlo: vuelve a leerlo")
                nuevo = data if op == "set" else dict(actual, **data)
                if col == "config" and doc_id == "ajustes":
                    malo = ajustes_invalidos(nuevo)
                    if malo:
                        return self.error_json(400, "ajuste inválido: %s" % malo)
                if col == "vacantes" and actual and len(nuevo.get("historial") or []) < len(actual.get("historial") or []):
                    return self.error_json(409, "no se puede acortar el historial de %s" % doc_id)
                leer_y_guardar.guardar(con, col, doc_id, nuevo)
        finally:
            con.close()
        self.responder(204)

    def log_message(self, *args):
        pass  # sin ruido en la consola


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--db" in a:
        Manejador.ruta_db = a[a.index("--db") + 1]
    if not os.path.exists(Manejador.ruta_db):
        sys.exit("ERROR: no existe la base del CRM: %s" % Manejador.ruta_db)
    url = "http://localhost:%d/" % PUERTO
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador)
    print("CRM abierto en %s (base: %s). Ctrl+C para cerrar." % (url, Manejador.ruta_db))
    if "--sin-navegador" not in a:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
