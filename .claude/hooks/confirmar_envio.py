"""Hook PreToolUse: pide confirmación antes de enviar o responder un correo y antes de adjuntar la HV en Chrome.

Aplica a cualquier conector de Gmail (el matcher usa mcp__*__send_message y __reply, sin depender de su id) y a
file_upload de Claude in Chrome, que es como se adjunta la HV en las postulaciones por correo (rules.md).
"""
import json
import sys

d = json.load(sys.stdin)
herramienta = d.get("tool_name", "")
if herramienta.endswith("file_upload"):
    razon = "Adjuntar un archivo en Chrome (la HV): ¿El usuario dijo sí a esta postulación en el chat?"
else:
    razon = "Enviar o responder un correo: ¿El usuario dijo sí a este correo (destinatario, asunto y texto) en el chat?"
print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                         "permissionDecisionReason": razon}}))
