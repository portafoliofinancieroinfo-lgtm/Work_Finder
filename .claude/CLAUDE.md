# Finder Work — Acciones

CRM de postulaciones de empleo que se opera con Claude Code. Todo en español, simple y directo. "El usuario" es quien busca trabajo.

Hay solo 4 archivos de instrucciones:

1. **Este (`.claude/CLAUDE.md`):** las acciones, paso a paso.
2. **`.claude/como_elegir_vacantes_y_escribir_cartas.md`:** cómo decidir qué vacantes sirven y cómo escribir cartas y mensajes.
3. **`.claude/como_usar_la_base_de_datos.md`:** cómo se lee y se escribe la base del CRM, los formatos de entrada de `Programa del CRM/comandos.py` y cómo mantener el código.
4. **`.claude/prohibiciones.md`:** lo que Claude no puede hacer. Se lee primero y no se rompe.

Todo lo demás (vacantes, empresas, borradores, historial, registros, datos del usuario, logros y plantillas) vive en la base
SQLite `Programa del CRM/postulaciones.db`, no en archivos de texto.

Carpetas (no se crean otras ni se dejan archivos sueltos):
- Raíz (lo del usuario): `Abrir CRM.bat`, `README.md`, `LICENSE`, `mis_datos.ejemplo.json` y su `mis_datos.json` (este último no se sube a git).
- `Mi hoja de vida/`: su HV de 2 páginas (`HV.pdf`) y, si quiere, la HV completa. No se sube a git.
- `Programa del CRM/`: `postulaciones.db`, la página (`pagina.html`), el código (`comandos.py`, `leer_y_guardar.py`, `abrir_pagina.py`,
  `puntaje.py`, `puntaje.js`, `crear_base.py`) y sus pruebas (`pruebas.py`).
- `.claude/` (lo de Claude): los 4 archivos de instrucciones, `settings.json` (hooks) y `hooks/`
  (`bloquear_cambios_a_mano_en_la_base.py` bloquea escribir `postulaciones.db` por fuera de `comandos.py`;
  `pedir_permiso_antes_de_enviar.py` pide confirmar cada envío de correo y cada adjunto en Chrome).

**Al empezar cualquier acción:** leer los archivos 2, 3 y 4 y correr `python "Programa del CRM/comandos.py" perfil` (datos del usuario, logros y plantillas).
`HOY` = fecha de hoy en `AAAA-MM-DD`. Los JSON de entrada se escriben en el scratchpad de la sesión.

## Entorno

Las acciones que usan portales y correo se ejecutan en el Chrome del usuario (Claude in Chrome, herramientas
`mcp__claude-in-chrome__*`), con sus sesiones ya abiertas en Gmail y en los portales de empleo que use. Nunca en el navegador interno de Claude.
Si una sesión no está abierta, se detiene y se avisa. Gmail se usa con su conector.

## Acción 0. Configurar (solo la primera vez)

Cuando no existe `Programa del CRM/postulaciones.db`:

1. Leer el README, sección "Paso 2" (qué datos pide `mis_datos.json`).
2. Entrevistar al usuario por el chat, **una sección a la vez** (contacto, perfil, formularios, logros, búsqueda). No inventar nada:
   si falta un dato, preguntarlo. Los logros se escriben con cifras reales que el usuario confirme.
3. Escribir `mis_datos.json` (copia de `mis_datos.ejemplo.json` con sus datos) y mostrárselo antes de crear la base.
4. Con su "sí": `python "Programa del CRM/crear_base.py"`. Después `python "Programa del CRM/comandos.py" perfil` para comprobar.
5. Pedirle que ponga su HV de 2 páginas en `Mi hoja de vida/HV.pdf`.

## Enviar un correo (solo con el "sí" del usuario a ese correo; ver `prohibiciones.md`)

- **Sin adjunto** (seguimientos, respuestas): con el conector de Gmail, `reply` al hilo o `send_message`.
- **Con la HV adjunta** (postulaciones): en Gmail del Chrome del usuario, redactar, adjuntar
  `Mi hoja de vida/HV.pdf` con `file_upload` y enviar.
- Después: entrada en `cambios.json` con `"tipo": "correo_enviado"` (o `"postulacion"`), `"si_del_usuario": "<lo que respondió
  el usuario en el chat>"` y, si salió de un borrador del CRM, `"borrador": "<id>"` para que quede como enviado (sin `si_del_usuario`
  el script no lo acepta). Así cada envío deja en el historial quién lo autorizó.

## Acción 1. Leer y revisar

Cómo van las postulaciones que ya están en el CRM. Se pide con "Leer y revisar", "revisa" o "corrida".

1. **Pendientes:** `python "Programa del CRM/comandos.py" vencidas HOY`. Guardar la lista para el Resumen.
2. **Ordenar el correo** con el conector de Gmail. Solo con `search_threads`, `get_thread`, `label_thread` y `unlabel_thread`.
   - Buscar (pageSize 50): `in:inbox newer_than:30d` y los correos de tus portales (`from:(computrabajo.com OR indeed.com OR linkedin.com …)`).
   - Clasificar cada hilo por remitente y asunto con esta tabla. Las etiquetas (`Postulaciones`, `Activo`, `Requiere respuesta`,
     `Cerrado`, `Ruido`) las creas tú en Gmail una vez; Claude no crea etiquetas. Pídele que las busque con `list_labels`.

| # | Si el correo es… | Etiquetas | ¿Sacar de Recibidos? |
|---|---|---|---|
| 1 | Una persona real que **pide algo**: entrevista, documentos, prueba, llamada, datos | Postulaciones + Requiere respuesta | **No** |
| 2 | Una persona real que dice que **la vacante se cerró**, que **no fue seleccionado** o que el proceso terminó | Postulaciones + Cerrado | Sí |
| 3 | Confirmación automática: "Te postulaste con éxito", "Thank you for applying" | Postulaciones + Activo | Sí |
| 4 | Portal: "tienes novedades en tu postulación" / "Nuevo estado" | Postulaciones + Activo | Sí |
| 5 | Alertas u ofertas recomendadas de los portales | Postulaciones + Ruido | Sí |
| 6 | Cualquier otra cosa: compras, publicidad, bancos, clientes | ninguna | **No tocar** |

   Si ninguna fila encaja con seguridad, no tocar el hilo y anotarlo. No cambiar leído/no leído.
3. **Revisar cómo van las postulaciones:** leer con `get_thread` (`PLAIN_TEXT`) cada hilo de las filas 1, 2 y 4, buscar
   `in:sent newer_than:15d` (seguimientos que mandó el usuario) y mirar la página de "mis postulaciones" de cada portal, en su Chrome.
   Para saber a qué vacante corresponde cada novedad: `python "Programa del CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`.
4. **Decidir cada novedad** con esta tabla y anotarla en `cambios.json` (formato en el archivo 3):

| El correo o portal dice… | Entrada en `cambios.json` |
|---|---|
| "Te postulaste con éxito" de una vacante que **no está** en el CRM | no va aquí: va a `nuevas.json` con `"postulada_por_usuario": "<fuente>"` y `"fechaPostulacion"` |
| Tu HV fue vista | `"etapa": "hv_vista"` |
| Entrevista, prueba técnica o "En proceso" | `"etapa": "en_proceso"` |
| "No te seleccionaron", "Proceso finalizado", "Han descartado tu CV" | `"etapa": "cerrada", "resultado": "no_seleccionado"` |
| La empresa dice que la vacante ya se cerró | `"etapa": "cerrada", "resultado": "vacante_cerrada"` |
| El usuario envió un seguimiento (está en Enviados) | `"tipo": "correo_enviado", "campos": {"seguimientos": <anterior + 1>}` |
| No se sabe de qué vacante es | **nada**: se le cuenta al usuario |

   Cada entrada lleva `"id"` (la vacante) y `"texto"` (qué pasó + fuente). Si aparece un contacto real (nombre, correo, teléfono),
   va en la misma entrada como `"contacto"`.
5. **Actualizar el CRM:** `python "Programa del CRM/comandos.py" cambios cambios.json HOY`.
6. **Con el "sí" del usuario** a cerrar las vencidas sin contacto (grupo `SIN_CONTACTO`): `python "Programa del CRM/comandos.py" cerrar-vencidas HOY`.

## Acción 2. Buscar

Vacantes nuevas, **solo las publicadas en la última semana** (fecha de publicación ≥ HOY − 7 días). Se pide con "Buscar" o "busca vacantes".

1. Buscar una vez por cada una de las "palabras de búsqueda" que muestra `comandos.py perfil` (las de los casos de búsqueda; el usuario las cambia en Ajustes del CRM),
   en cada portal que use, desde su Chrome. Quedarse con las de los últimos 7 días. También los correos que piden "enviar HV a…".
2. Descartar las que ya están en el CRM: `python "Programa del CRM/comandos.py" consulta "SELECT id, empresa, cargo FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`
   (`comandos.py nuevas` también descarta las duplicadas).
3. Decidir cada vacante con la tabla "Qué hacer con cada aviso" del archivo 2.
4. Anotar cada una en `nuevas.json` (formato en el archivo 3), con el texto completo del aviso en `"aviso"`:
   así queda el registro aunque la empresa borre la publicación.
5. **Revisar las cartas** antes de guardarlas, a mano: ningún dato que no esté en `comandos.py perfil`, un solo logro (el más afín
   según "usar en"), el idioma del aviso. Corregir las que fallen. Después, `python "Programa del CRM/comandos.py" nuevas nuevas.json HOY`.
   Si alguna dice `FALTA CARTA`, **no se guardó nada**: escribir esas cartas con las reglas del archivo 2, agregarlas como
   `"carta"` (y `"idioma": "en"` si el aviso está en inglés) y repetir el comando.
6. **Seguimientos:** para cada vacante de la lista `ACCION` de pendientes que diga "Enviar seguimiento" y tenga correo,
   escribirlo con la plantilla A, B o C de `comandos.py perfil` y mostrárselo al usuario. Con su "sí": `reply` al correo original
   de la postulación (ver "Enviar un correo"). Sin su "sí", dejarlo como borrador con `create_draft`.
7. Con el "sí" del usuario: "Aprobar y postular".

## Acción 3. Búsquedas externas

**Se ejecuta sola, sin que el usuario la nombre,** cuando pasa información de una postulación que no viene de una página web:
un WhatsApp, una llamada, un referido, un aviso compartido o un correo de otra cuenta.

1. Buscar la vacante: `python "Programa del CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`.
2. Si **no está**: registrarla como en la Acción 2, pasos 3 a 5, con lo que el usuario pasó. `"portal"` = la fuente
   (p. ej. `"WhatsApp"`, `"Referido"`). Si ya se postuló: `"postulada_por_usuario": "<lo que contó>"` y `"fechaPostulacion"`.
3. Si **ya está**: una entrada en `cambios.json` con la tabla de la Acción 1, `"texto"` = lo que contó el usuario y por qué medio,
   y `"contacto"` si dio uno. `python "Programa del CRM/comandos.py" cambios cambios.json HOY`.
4. Si hace falta responder o postular por correo: escribirlo, mostrárselo al usuario y enviarlo con su "sí" (ver "Enviar un correo").
5. Con el "sí" del usuario: "Aprobar y postular".

## Aprobar y postular (Acciones 2 y 3, solo con el "sí" del usuario)

1. Aprobó vacantes: `python "Programa del CRM/comandos.py" aprobar HOY v120 v129 …`.
2. **Por portal:** postular cada aprobada en su portal, en el Chrome del usuario, con la HV de 2 páginas
   (`Mi hoja de vida/HV.pdf`), la carta y las respuestas de `comandos.py perfil`, a ritmo humano. Detenerse ante login,
   CAPTCHA, una pregunta sin dato, una prueba técnica o cualquier cobro.
3. **Por correo:** leer el borrador (`python "Programa del CRM/comandos.py" consulta "SELECT data FROM borradores WHERE id = 'b-v120-1'"`),
   mostrárselo al usuario y, con su "sí" a ese correo, enviarlo con la HV adjunta desde Gmail en Chrome (ver "Enviar un correo"). Luego en
   `cambios.json`: `{"id": "v120", "etapa": "postulada", "tipo": "postulacion", "borrador": "b-v120-1", "si_del_usuario": "<su sí>", "texto": "Postulación enviada por correo a <para>"}`.
4. Si el portal confirma ("Te aplicaste correctamente", "We received your application"), en `cambios.json`:
   `{"id": "v120", "etapa": "postulada", "tipo": "postulacion", "texto": "<confirmación del portal>"}`.
   Si se detuvo: `{"id": "v120", "texto": "<qué pasó>", "alertas_mas": ["preguntas_pendientes"], "notas_mas": "<qué falta>"}`.
5. `python "Programa del CRM/comandos.py" cambios cambios.json HOY`.

## Acción 4. Resumen

Al terminar cualquier acción, o cuando el usuario lo pida.

1. Un solo mensaje, numerado:
   1. Nuevas por aprobar: empresa, cargo, puntaje, neto y lo que piden que no está en la HV.
   2. Aprobadas que faltan por postular.
   3. Vencidas sin contacto (grupo `SIN_CONTACTO`): proponer cerrarlas.
   4. Cambios de etapa, con su evidencia.
   5. Borradores que quedaron en Gmail.
   6. Sesiones que no estaban abiertas y bloqueos.
2. Guardar el registro del día: `python "Programa del CRM/comandos.py" registro HOY registro.json` (formato en el archivo 3).
3. Cerrar las pestañas de Chrome que se abrieron.
4. Esperar la respuesta del usuario (por ejemplo, "sí a 1, 3 y 5").

## Revisar o simplificar el código

Solo cuando el usuario lo pida: seguir "Mantener el código" del archivo 3.
