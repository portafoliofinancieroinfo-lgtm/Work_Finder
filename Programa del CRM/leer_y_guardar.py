"""Programa del CRM del CRM: un archivo SQLite, Programa del CRM/postulaciones.db.

Cada colección (vacantes, empresas, borradores, config, corridas) es una tabla (id, data) con el documento
en JSON, igual que lo usan comandos.py, puntaje.py y la página. Las vistas *_v sacan columnas para consultar.
Los datos del usuario van en tablas normales: perfil, logros, servicios y plantillas.
"""
import json
import os
import sqlite3

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "postulaciones.db")
COLECCIONES = ("vacantes", "empresas", "borradores", "config", "corridas")

ESQUEMA = "".join(
    "CREATE TABLE IF NOT EXISTS %s (id TEXT PRIMARY KEY, data TEXT NOT NULL CHECK (json_valid(data)));\n" % c
    for c in COLECCIONES) + """
CREATE TABLE IF NOT EXISTS perfil (seccion TEXT NOT NULL, campo TEXT NOT NULL, valor TEXT NOT NULL,
                                   orden INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (seccion, campo));
CREATE TABLE IF NOT EXISTS logros (id TEXT PRIMARY KEY, logro TEXT NOT NULL, cuando TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS servicios (area TEXT PRIMARY KEY, incluye TEXT NOT NULL, tarifa TEXT NOT NULL,
                                      orden INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS plantillas (id TEXT PRIMARY KEY, nombre TEXT NOT NULL, texto TEXT NOT NULL,
                                       bloqueada INTEGER NOT NULL DEFAULT 0);
CREATE VIEW IF NOT EXISTS vacantes_v AS SELECT id,
  json_extract(data, '$.empresa') AS empresa, json_extract(data, '$.cargo') AS cargo,
  json_extract(data, '$.etapa') AS etapa, json_extract(data, '$.resultado') AS resultado,
  json_extract(data, '$.puntaje') AS puntaje, json_extract(data, '$.neto') AS neto,
  json_extract(data, '$.portal') AS portal, json_extract(data, '$.modalidad') AS modalidad,
  json_extract(data, '$.ciudad') AS ciudad, json_extract(data, '$.link') AS link,
  json_extract(data, '$.fechaPostulacion') AS fechaPostulacion,
  json_extract(data, '$.proximaAccion.fecha') AS proximaFecha,
  json_extract(data, '$.proximaAccion.texto') AS proximaTexto FROM vacantes;
CREATE VIEW IF NOT EXISTS empresas_v AS SELECT id, json_extract(data, '$.nombre') AS nombre,
  json_array_length(data, '$.contactos') AS contactos FROM empresas;
CREATE VIEW IF NOT EXISTS borradores_v AS SELECT id, json_extract(data, '$.vacanteId') AS vacanteId,
  json_extract(data, '$.tipo') AS tipo, json_extract(data, '$.estado') AS estado,
  json_extract(data, '$.asunto') AS asunto FROM borradores;
"""


def conectar(ruta=RUTA, crear=False):
    """Abre la base. Sin `crear`, falla si el archivo no existe: así nunca se trabaja sobre una base vacía por error."""
    if not crear and not os.path.exists(ruta):
        raise FileNotFoundError("no existe la base del CRM: %s" % ruta)
    con = sqlite3.connect(ruta)
    con.executescript(ESQUEMA)
    return con


def leer(con, coleccion):
    """{id: documento} de una colección."""
    return {i: json.loads(d) for i, d in con.execute("SELECT id, data FROM %s" % _col(coleccion))}


def leer_uno(con, coleccion, doc_id):
    fila = con.execute("SELECT data FROM %s WHERE id = ?" % _col(coleccion), (doc_id,)).fetchone()
    return json.loads(fila[0]) if fila else None


def guardar(con, coleccion, doc_id, data):
    """Escribe el documento completo (lo crea si no existe). Cada escritura sube `_rev` en 1: con eso la página sabe
    si el registro cambió después de leerlo (abrir_pagina.py rechaza la escritura) y no pisa lo que escribió comandos.py."""
    fila = con.execute("SELECT json_extract(data, '$._rev') FROM %s WHERE id = ?" % _col(coleccion), (doc_id,)).fetchone()
    data = dict(data, _rev=((fila[0] or 0) if fila else 0) + 1)
    con.execute("INSERT OR REPLACE INTO %s (id, data) VALUES (?, ?)" % _col(coleccion),
                (doc_id, json.dumps(data, ensure_ascii=False)))


def actualizar(con, coleccion, doc_id, cambios):
    """Reemplaza solo los campos de `cambios` en un documento que ya existe."""
    actual = leer_uno(con, coleccion, doc_id)
    if actual is None:
        raise KeyError("no existe %s/%s" % (coleccion, doc_id))
    actual.update(cambios)
    guardar(con, coleccion, doc_id, actual)


def _col(nombre):
    if nombre not in COLECCIONES:  # el nombre va dentro del SQL: solo se aceptan los conocidos
        raise ValueError("colección desconocida: %s" % nombre)
    return nombre
