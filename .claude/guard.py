"""Hook PreToolUse con las dos protecciones del CRM (Prohibiciones en .claude/CLAUDE.md).

1. crm.db solo se escribe con cli.py (regla 1). Bloquea (código 2) editar la base con Edit/Write y los
   comandos que la tocan por fuera de cli.py, server.py o scoring.py: sqlite3 de consola, mover o borrar,
   redirigir a ella, python -c con connect, o copiar algo ENCIMA de ella. Copiarla a otro lado (para probar) sí se permite.
2. Pide confirmación antes de enviar o responder un correo y antes de adjuntar la HV en Chrome. Aplica a cualquier
   conector de Gmail (mcp__*__send_message y __reply, sin depender de su id) y a file_upload de Claude in Chrome.
"""
import json
import re
import sys

sys.stderr.reconfigure(encoding="utf-8")
MSG = ("Bloqueado: crm.db solo se escribe con cli.py (regla 1 de Prohibiciones, .claude/CLAUDE.md). "
       "Para probar, copiarla al scratchpad y usar --db.")

d = json.load(sys.stdin)
herramienta, entrada = d.get("tool_name", ""), d.get("tool_input") or {}


def bloquear():
    print(MSG, file=sys.stderr)
    sys.exit(2)


def preguntar(razon):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                             "permissionDecisionReason": razon}}))
    sys.exit(0)


if herramienta in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
    if re.search(r"crm\.db(-journal|-wal|-shm)?$", str(entrada.get("file_path", "")), re.I):
        bloquear()
elif herramienta == "Bash":
    c = str(entrada.get("command", ""))
    if re.search(r"crm\.db", c, re.I):
        encima = re.search(r"\b(cp|copy|copy-item|mv|move)\b[^|;&\n]*crm\.db\"?'?\s*($|[|;&\n])", c, re.I)
        peligro = re.search(r"\bsqlite3\s|\b(rm|del|erase|remove-item|unlink)\b|>\s*\S*crm\.db|connect\(", c, re.I)
        if encima or peligro:
            bloquear()
elif herramienta.endswith("file_upload"):
    preguntar("Adjuntar un archivo en Chrome (la HV): ¿El usuario dijo sí a esta postulación en el chat?")
elif re.search(r"__send_message|__reply", herramienta):  # el mismo patrón del matcher en settings.json
    preguntar("Enviar o responder un correo: ¿El usuario dijo sí a este correo (destinatario, asunto y texto) en el chat?")
sys.exit(0)
