# Perfil y decisión de vacantes

Este archivo dice qué vacantes sirven y cómo se escriben las cartas y los mensajes.
**Es tuyo: ajústalo a tu búsqueda.** La tabla de la sección 1 trae ejemplos; cámbialos por tus propios descartes.

Los datos del usuario están en la base del CRM, no aquí: contacto, perfil, "Datos para formularios", logros y plantillas.
Para verlos: `python "Base de datos/crm.py" perfil`. Se cargan una sola vez desde `perfil.json` con `iniciar.py` (ver el README).
La fuente original es tu HV (`Contexto postulante/HV.pdf`).

---

## 1. Qué hacer con cada aviso

Leer la tabla **de arriba abajo; se aplica la primera fila que encaje**:

| Si el aviso… | Qué hacer |
|---|---|
| es de un tipo que nunca quieres (ejemplos: digitación pura, contrato por prácticas, cargos que piden años de experiencia que no tienes en un área que no es la tuya) | no registrar |
| pide pagar, usa un formulario externo raro, o es de una empresa sin sitio verificable | registrar con `"alertas": ["posible_estafa"]`. **Nunca se postula** |
| pide como obligatorio algo que no está en la HV ni en "Datos para formularios" (más años, otro software, un idioma mayor al tuyo) | registrar con `"excluyente": "<qué pide>"` (queda cerrada como "no aplica") |
| lo demás | registrar normal |

Reglas de registro:
- Solo lo que dice el aviso. Si falta el salario, la fecha o la modalidad, queda vacío: **nunca se estima.**
- Si el aviso no dice la empresa: `"Importante empresa del sector"` con `"empresaId": null`.
- El puntaje lo calcula `Base de datos/crm.py` con los Ajustes del CRM. Las de puntaje ≥ `umbralAprobar` (máximo `limitePorCorrida`)
  pasan a "por aprobar"; las demás quedan "descubiertas".

## 2. Reglas para cartas, formularios y mensajes

- **Carta:** solo el cuerpo, sin saludo ni firma (los pone el script). Máximo 150 palabras. **Un solo logro** (el más
  afín al cargo, según su columna "usar en"). Solo datos de la HV. Si el aviso está en inglés, la carta va en inglés.
- **Formularios:** se responden solo con la HV y "Datos para formularios". Si falta un dato, se detiene y se pregunta al usuario
  (la vacante lleva la alerta `preguntas_pendientes`).
- **Mensajes con plantilla:** asunto corto y concreto · máximo 150 palabras · un solo logro · una sola petición al final.
- **Seguimientos:** máximo `maxSeguimientos` por vacante (Ajustes del CRM). Al llegar al tope se propone cerrar como `sin_respuesta`.
  Nunca dos mensajes a la misma empresa con menos de 10 días de diferencia.
