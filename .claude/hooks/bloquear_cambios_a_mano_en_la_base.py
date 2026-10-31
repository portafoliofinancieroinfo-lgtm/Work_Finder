"""Hook PreToolUse: postulaciones.db solo se escribe con comandos.py (regla 1 de prohibiciones.md).

Bloquea (código 2) editar la base con Edit/Write y los comandos que la tocan por fuera de comandos.py, abrir_pagina.py o
puntaje.py: sqlite3 de consola, mover o borrar, redirigir a ella, python -c con connect, o copiar algo ENCIMA de ella.
Copiarla a otro lado (paso 2 de "Mantener el código") sí se permite.
"""
import json
import re
import sys

sys.stderr.reconfigure(encoding="utf-8")
MSG = "Bloqueado: postulaciones.db solo se escribe con comandos.py (regla 1 de prohibiciones.md). Para probar, copiarla al scratchpad y usar --db."

d = json.load(sys.stdin)
herramienta, entrada = d.get("tool_name", ""), d.get("tool_input") or {}

if herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    if re.search(r"postulaciones\.db(-journal|-wal|-shm)?$", str(entrada.get("file_path", "")), re.I):
        print(MSG, file=sys.stderr)
        sys.exit(2)
elif herramienta == "Bash":
    c = str(entrada.get("command", ""))
    if re.search(r"postulaciones\.db", c, re.I):
        encima = re.search(r"\b(cp|copy|copy-item|mv|move)\b[^|;&\n]*postulaciones\.db\"?'?\s*($|[|;&\n])", c, re.I)
        peligro = re.search(r"\bsqlite3\s|\b(rm|del|erase|remove-item|unlink)\b|>\s*\S*postulaciones\.db|connect\(", c, re.I)
        if encima or peligro:
            print(MSG, file=sys.stderr)
            sys.exit(2)
sys.exit(0)
