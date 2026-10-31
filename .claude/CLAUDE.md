# Finder Work — Instrucciones para Claude

CRM de postulaciones de empleo que se opera con Claude Code. Todo en español, simple y directo. "El usuario" es quien busca trabajo.

Este es el único archivo de instrucciones. Secciones, en orden:

1. **Prohibiciones:** lo que Claude no puede hacer. Se lee primero y no se rompe.
2. **Carpetas, Entorno y las Acciones 0 a 4:** qué hacer, paso a paso.
3. **Qué vacantes sirven y cómo escribir:** qué avisos se registran y cómo van las cartas y los mensajes.
4. **La base del CRM:** cómo se lee y se escribe, y los formatos de entrada de `Programa CRM/comandos.py`.
5. **Revisar o simplificar el código:** solo cuando el usuario lo pida.

Todo lo demás (vacantes, empresas, borradores, historial, registros, datos del usuario, logros y plantillas) vive en la base
SQLite `Programa CRM/postulaciones.db`, no en archivos de texto.

## Prohibiciones

Valen en toda acción y en toda sesión. "El usuario" es la persona dueña del CRM.

1. **No escribas la base por fuera de `Programa CRM/comandos.py`.** Nada de SQL a mano, ni editar, mover, copiar encima o borrar `postulaciones.db`.
   Para probar código, copiarla al scratchpad y usar `--db`. (La única excepción es `crear_base.py`, que la crea cuando no existe.)
2. **No apruebes, postules, cierres ni envíes nada sin un "sí" del usuario en el chat.** Un clic en la página no autoriza.
   El "sí" vale solo para lo que se le mostró.
3. **No sigas adelante ante la duda; detente y pregunta.** Iniciar sesión, CAPTCHA, crear cuenta, pagos, un dato que no está en la HV
   ni en `comandos.py perfil`, una prueba técnica o una acción bloqueada por permisos: se para y se le dice al usuario. No busques otra vía.
4. **No inventes ni estimes datos.** Lo que no dice el aviso o el correo no se pone (salario, fecha, modalidad, empresa).
   Si no sabes de qué vacante es algo, repórtalo.
5. **No uses Gmail para nada que no sea postular.** Solo: postulaciones por correo a vacantes del CRM, seguimientos de esas
   postulaciones y respuestas a reclutadores que piden algo. Ni compras, bancos, clientes, proveedores, impuestos ni correos personales.
   - No envíes sin mostrarle antes al usuario destinatario, asunto, texto y si lleva la HV.
   - No reenvíes, no borres, no marques spam y no crees etiquetas.
   - No cambies leído/no leído ni toques hilos que no encajen con seguridad en la tabla de la Acción 1.
6. **No uses el navegador interno de Claude.** Todo va en el Chrome del usuario, con sus sesiones ya abiertas.
7. **No postules vacantes con `posible_estafa`.**
8. **No cambies `.claude/` (hooks y permisos) sin que el usuario lo pida**, y nunca para quitar o debilitar una protección.
   Los permisos de envío de correo solo se tocan con su "sí" explícito.
9. **No trabajes con el CRM si hay una copia en conflicto** (`postulaciones (1).db` o parecida) en `Programa CRM/`: avisa y no la borres.
10. **No escribas contraseñas ni códigos de verificación, no aceptes condiciones y no subas documentos** en ningún sitio sin el
    "sí" del usuario.

## Carpetas

No se crean otras ni se dejan archivos sueltos.
- Raíz (lo del usuario): `Abrir CRM.bat`, `README.md`, `LICENSE` y su `mis_datos.json` (no se sube a git).
- `Mi hoja de vida/`: su HV de 2 páginas (`HV.pdf`) y, si quiere, la HV completa. No se sube a git.
- `Programa CRM/`: `postulaciones.db`, la página (`pagina.html`), el código (`comandos.py`, `leer_y_guardar.py`, `abrir_pagina.py`,
  `puntaje.py`, `puntaje.js`, `crear_base.py`) y sus pruebas (`pruebas.py`).
- `.claude/` (lo de Claude): este archivo, `settings.json` (activa los hooks) y `protecciones.py` (el hook: bloquea escribir
  `postulaciones.db` por fuera de `comandos.py` y pide confirmar cada envío de correo y cada adjunto en Chrome).

**Al empezar cualquier acción:** correr `python "Programa CRM/comandos.py" perfil` (datos del usuario, logros y plantillas).
`HOY` = fecha de hoy en `AAAA-MM-DD`. Los JSON de entrada se escriben en el scratchpad de la sesión.

## Entorno

Las acciones que usan portales y correo se ejecutan en el Chrome del usuario (Claude in Chrome, herramientas
`mcp__claude-in-chrome__*`), con sus sesiones ya abiertas en Gmail y en los portales de empleo que use. Nunca en el navegador interno de Claude.
Si una sesión no está abierta, se detiene y se avisa. Gmail se usa con su conector.

## Acción 0. Configurar (solo la primera vez)

Cuando no existe `Programa CRM/postulaciones.db`:

1. Leer el README, sección "Paso 2" (qué datos pide `mis_datos.json`).
2. Entrevistar al usuario por el chat, **una sección a la vez** (contacto, perfil, formularios, logros, búsqueda). No inventar nada:
   si falta un dato, preguntarlo. Los logros se escriben con cifras reales que el usuario confirme.
3. Escribir `mis_datos.json` (crearlo con `python "Programa CRM/crear_base.py" --plantilla` y cambiar los datos de ejemplo por los suyos) y mostrárselo antes de crear la base.
4. Con su "sí": `python "Programa CRM/crear_base.py"`. Después `python "Programa CRM/comandos.py" perfil` para comprobar.
5. Pedirle que ponga su HV de 2 páginas en `Mi hoja de vida/HV.pdf`.

## Enviar un correo (solo con el "sí" del usuario a ese correo; ver Prohibiciones)

- **Sin adjunto** (seguimientos, respuestas): con el conector de Gmail, `reply` al hilo o `send_message`.
- **Con la HV adjunta** (postulaciones): en Gmail del Chrome del usuario, redactar, adjuntar
  `Mi hoja de vida/HV.pdf` con `file_upload` y enviar.
- Después: entrada en `cambios.json` con `"tipo": "correo_enviado"` (o `"postulacion"`), `"si_del_usuario": "<lo que respondió
  el usuario en el chat>"` y, si salió de un borrador del CRM, `"borrador": "<id>"` para que quede como enviado (sin `si_del_usuario`
  el script no lo acepta). Así cada envío deja en el historial quién lo autorizó.

## Acción 1. Leer y revisar

Cómo van las postulaciones que ya están en el CRM. Se pide con "Leer y revisar", "revisa" o "corrida".

1. **Pendientes:** `python "Programa CRM/comandos.py" vencidas HOY`. Guardar la lista para el Resumen.
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
   Para saber a qué vacante corresponde cada novedad: `python "Programa CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`.
4. **Decidir cada novedad** con esta tabla y anotarla en `cambios.json` (formato en "La base del CRM"):

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
5. **Actualizar el CRM:** `python "Programa CRM/comandos.py" cambios cambios.json HOY`.
6. **Con el "sí" del usuario** a cerrar las vencidas sin contacto (grupo `SIN_CONTACTO`): `python "Programa CRM/comandos.py" cerrar-vencidas HOY`.

## Acción 2. Buscar

Vacantes nuevas, **solo las publicadas en la última semana** (fecha de publicación ≥ HOY − 7 días). Se pide con "Buscar" o "busca vacantes".

1. Buscar una vez por cada una de las "palabras de búsqueda" que muestra `comandos.py perfil` (las de los casos de búsqueda; el usuario las cambia en Ajustes del CRM),
   en cada portal que use, desde su Chrome. Quedarse con las de los últimos 7 días. También los correos que piden "enviar HV a…".
2. Descartar las que ya están en el CRM: `python "Programa CRM/comandos.py" consulta "SELECT id, empresa, cargo FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`
   (`comandos.py nuevas` también descarta las duplicadas).
3. Decidir cada vacante con la tabla "Qué hacer con cada aviso".
4. Anotar cada una en `nuevas.json` (formato en "La base del CRM"), con el texto completo del aviso en `"aviso"`:
   así queda el registro aunque la empresa borre la publicación.
5. **Revisar las cartas** antes de guardarlas, a mano: ningún dato que no esté en `comandos.py perfil`, un solo logro (el más afín
   según "usar en"), el idioma del aviso. Corregir las que fallen. Después, `python "Programa CRM/comandos.py" nuevas nuevas.json HOY`.
   Si alguna dice `FALTA CARTA`, **no se guardó nada**: escribir esas cartas con las "Reglas para cartas, formularios y mensajes", agregarlas como
   `"carta"` (y `"idioma": "en"` si el aviso está en inglés) y repetir el comando.
6. **Seguimientos:** para cada vacante de la lista `ACCION` de pendientes que diga "Enviar seguimiento" y tenga correo,
   escribirlo con la plantilla A, B o C de `comandos.py perfil` y mostrárselo al usuario. Con su "sí": `reply` al correo original
   de la postulación (ver "Enviar un correo"). Sin su "sí", dejarlo como borrador con `create_draft`.
7. Con el "sí" del usuario: "Aprobar y postular".

## Acción 3. Búsquedas externas

**Se ejecuta sola, sin que el usuario la nombre,** cuando pasa información de una postulación que no viene de una página web:
un WhatsApp, una llamada, un referido, un aviso compartido o un correo de otra cuenta.

1. Buscar la vacante: `python "Programa CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%<empresa>%'"`.
2. Si **no está**: registrarla como en la Acción 2, pasos 3 a 5, con lo que el usuario pasó. `"portal"` = la fuente
   (p. ej. `"WhatsApp"`, `"Referido"`). Si ya se postuló: `"postulada_por_usuario": "<lo que contó>"` y `"fechaPostulacion"`.
3. Si **ya está**: una entrada en `cambios.json` con la tabla de la Acción 1, `"texto"` = lo que contó el usuario y por qué medio,
   y `"contacto"` si dio uno. `python "Programa CRM/comandos.py" cambios cambios.json HOY`.
4. Si hace falta responder o postular por correo: escribirlo, mostrárselo al usuario y enviarlo con su "sí" (ver "Enviar un correo").
5. Con el "sí" del usuario: "Aprobar y postular".

## Aprobar y postular (Acciones 2 y 3, solo con el "sí" del usuario)

1. Aprobó vacantes: `python "Programa CRM/comandos.py" aprobar HOY v120 v129 …`.
2. **Por portal:** postular cada aprobada en su portal, en el Chrome del usuario, con la HV de 2 páginas
   (`Mi hoja de vida/HV.pdf`), la carta y las respuestas de `comandos.py perfil`, a ritmo humano. Detenerse ante login,
   CAPTCHA, una pregunta sin dato, una prueba técnica o cualquier cobro.
3. **Por correo:** leer el borrador (`python "Programa CRM/comandos.py" consulta "SELECT data FROM borradores WHERE id = 'b-v120-1'"`),
   mostrárselo al usuario y, con su "sí" a ese correo, enviarlo con la HV adjunta desde Gmail en Chrome (ver "Enviar un correo"). Luego en
   `cambios.json`: `{"id": "v120", "etapa": "postulada", "tipo": "postulacion", "borrador": "b-v120-1", "si_del_usuario": "<su sí>", "texto": "Postulación enviada por correo a <para>"}`.
4. Si el portal confirma ("Te aplicaste correctamente", "We received your application"), en `cambios.json`:
   `{"id": "v120", "etapa": "postulada", "tipo": "postulacion", "texto": "<confirmación del portal>"}`.
   Si se detuvo: `{"id": "v120", "texto": "<qué pasó>", "alertas_mas": ["preguntas_pendientes"], "notas_mas": "<qué falta>"}`.
5. `python "Programa CRM/comandos.py" cambios cambios.json HOY`.

## Acción 4. Resumen

Al terminar cualquier acción, o cuando el usuario lo pida.

1. Un solo mensaje, numerado:
   1. Nuevas por aprobar: empresa, cargo, puntaje, neto y lo que piden que no está en la HV.
   2. Aprobadas que faltan por postular.
   3. Vencidas sin contacto (grupo `SIN_CONTACTO`): proponer cerrarlas.
   4. Cambios de etapa, con su evidencia.
   5. Borradores que quedaron en Gmail.
   6. Sesiones que no estaban abiertas y bloqueos.
2. Guardar el registro del día: `python "Programa CRM/comandos.py" registro HOY registro.json` (formato en "La base del CRM").
3. Cerrar las pestañas de Chrome que se abrieron.
4. Esperar la respuesta del usuario (por ejemplo, "sí a 1, 3 y 5").

## Qué vacantes sirven y cómo escribir

**Esta sección es del usuario: la ajusta a su búsqueda.** La tabla "Qué hacer con cada aviso" trae ejemplos; se cambian por los descartes del usuario.

Los datos del usuario están en la base del CRM, no en este archivo: contacto, perfil, "Datos para formularios", logros y plantillas.
Para verlos: `python "Programa CRM/comandos.py" perfil`. Se cargan una sola vez desde `mis_datos.json` con `crear_base.py` (ver el README).
La fuente original es su HV (`Mi hoja de vida/HV.pdf`).

### Qué hacer con cada aviso

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
- El puntaje lo calcula `Programa CRM/comandos.py` con los Ajustes del CRM. Las de puntaje ≥ `umbralAprobar` (máximo `limitePorCorrida`)
  pasan a "por aprobar"; las demás quedan "descubiertas".

### Reglas para cartas, formularios y mensajes

- **Carta:** solo el cuerpo, sin saludo ni firma (los pone el script). Máximo 150 palabras. **Un solo logro** (el más
  afín al cargo, según su columna "usar en"). Solo datos de la HV. Si el aviso está en inglés, la carta va en inglés.
- **Formularios:** se responden solo con la HV y "Datos para formularios". Si falta un dato, se detiene y se pregunta al usuario
  (la vacante lleva la alerta `preguntas_pendientes`).
- **Mensajes con plantilla:** asunto corto y concreto · máximo 150 palabras · un solo logro · una sola petición al final.
- **Seguimientos:** máximo `maxSeguimientos` por vacante (Ajustes del CRM). Al llegar al tope se propone cerrar como `sin_respuesta`.
  Nunca dos mensajes a la misma empresa con menos de 10 días de diferencia.

## La base del CRM

### Piezas

| Qué | Dónde |
|---|---|
| La base (fuente de verdad) | `Programa CRM/postulaciones.db` (SQLite). No va a git: tiene datos personales. Se crea una vez con `python "Programa CRM/crear_base.py"` desde tu `mis_datos.json`. **Un solo equipo a la vez:** si la guardas en una carpeta sincronizada (Drive, Dropbox…), cierra el CRM (`abrir_pagina.py`) antes de cambiar de equipo y espera a que termine de sincronizar. Esas nubes no unen cambios hechos en dos equipos: guardan una copia en conflicto (`postulaciones (1).db`). Si aparece una, se le avisa al usuario y no se borra |
| Escribir en la base | `python "Programa CRM/comandos.py" <comando> …` (nunca a mano) |
| Leer la base | `python "Programa CRM/comandos.py" consulta "SELECT …"` (solo lectura) y `python "Programa CRM/comandos.py" perfil` |
| Página del CRM | `Abrir CRM.bat` (doble clic) o `python "Programa CRM/abrir_pagina.py"` → abre `http://localhost:8765` en el Chrome del usuario. Solo funciona en este computador |
| Página | `Programa CRM/pagina.html`. `abrir_pagina.py` la sirve junto con `puntaje.js` y la HV |
| Código de la base | `Programa CRM/leer_y_guardar.py` (esquema y lectura/escritura), usado por `comandos.py` y `abrir_pagina.py` |
| Puntaje | `Programa CRM/puntaje.js` (página) y `Programa CRM/puntaje.py` (lo usa `comandos.py`). Son gemelos: toda regla cambia en los dos |
| HV de 2 páginas | `Mi hoja de vida/HV.pdf` |
| Crear la base | `python "Programa CRM/crear_base.py"` (con tu `mis_datos.json`) o `--demo` (con vacantes de ejemplo). Nunca pisa una base existente |
| Pruebas | `python "Programa CRM/pruebas.py"`: unas 30 pruebas sobre una base de ejemplo temporal (nunca la tuya). Todas deben salir OK |

### Tablas

Las colecciones guardan cada registro como un documento JSON en la columna `data` (tabla `id, data`). Cada documento lleva
`_rev`, que `leer_y_guardar.py` sube en 1 en cada escritura: la página lo manda al guardar y `abrir_pagina.py` rechaza (409) la escritura si el
registro cambió desde que la página lo leyó, o si acorta el historial de una vacante. No se escribe a mano.

- **`vacantes`**: una por vacante (`v001`, `v002`…).
  - Campos principales: `empresa`, `cargo`, `perfil`, `nivel`, `modalidad`, `ciudad`, `salarioMin`/`salarioMax`, `link`, `portal`,
    `canal` (`portal`/`correo`), `etapa`, `resultado`, `alertas`, `historial`, `proximaAccion`, `seguimientos`, `puntaje`, `neto`.
  - Etapas: `descubierta` → `por_aprobar` → `aprobada` → `postulada` → `hv_vista` → `en_proceso` → `oferta` → `cerrada`.
- **`empresas`**: `nombre` y `contactos` (nombre, email, teléfono, rol, fuente).
- **`borradores`**: correos listos (`para`, `asunto`, `cuerpo`, `tipo`, `estado`, `vacanteId`). Los envía Claude con el "sí"
  del usuario (Prohibiciones y "Enviar un correo", y `"borrador"` en `cambios.json`) o el usuario desde su Gmail, marcando "Ya lo envié" en la página.
- **`config`**: el registro `ajustes` (`ciudadBase`, `casos` de búsqueda con sus palabras clave y su salario mínimo,
  `umbralAprobar`, `limitePorCorrida` y la cadencia de seguimientos). Mientras el usuario no guarde Ajustes, los casos y las
  palabras son los de `AJUSTES_BASE` en `puntaje.js`/`puntaje.py`. `neto` de la vacante = su salario de referencia (ya no se restan costos de traslado). **Siempre se leen de aquí.** el usuario los cambia en la pestaña Ajustes.
- **`corridas`**: un registro por día con lo que se hizo. La página muestra el más reciente.

Vistas para consultar sin JSON: `vacantes_v` (empresa, cargo, etapa, resultado, puntaje, neto, portal, modalidad, ciudad, link,
fechaPostulacion, proximaFecha, proximaTexto), `empresas_v` y `borradores_v`.

Datos del usuario (tablas normales): `perfil` (secciones contacto, perfil, formularios y portafolio), `logros` (L1–L5),
`plantillas` (A, B, C, F y G; `bloqueada` = 1 las deja fuera de uso) y `servicios` (opcional, vacía al crear). Para verlos todos: `python "Programa CRM/comandos.py" perfil`.

Las listas válidas de etapas, resultados, alertas y tipos de historial están en `Programa CRM/pagina.html` (la página); `comandos.py` las lee de ahí.

### Consultas útiles

```
python "Programa CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%acme%'"
python "Programa CRM/comandos.py" consulta "SELECT id, empresa, cargo FROM vacantes_v WHERE link = 'https://...'"
python "Programa CRM/comandos.py" consulta "SELECT etapa, count(*) FROM vacantes_v GROUP BY etapa"
python "Programa CRM/comandos.py" consulta "SELECT data FROM vacantes WHERE id = 'v120'"
python "Programa CRM/comandos.py" consulta "SELECT id, asunto, estado FROM borradores_v WHERE estado = 'pendiente'"
```

`consulta` abre la base en solo lectura: aunque se escriba un UPDATE o DELETE, no cambia nada.

### Escribir con `comandos.py`

`HOY` = fecha de hoy en `AAAA-MM-DD`. Los archivos de entrada se escriben en el scratchpad de la sesión.

```
python "Programa CRM/comandos.py" vencidas        HOY
python "Programa CRM/comandos.py" nuevas          nuevas.json HOY
python "Programa CRM/comandos.py" cambios         cambios.json HOY
python "Programa CRM/comandos.py" aprobar         HOY v120 v129 …
python "Programa CRM/comandos.py" cerrar-vencidas HOY
python "Programa CRM/comandos.py" registro        HOY registro.json
python "Programa CRM/comandos.py" editar-perfil   cambios-perfil.json
```

- Cada comando guarda todo en una sola transacción: o queda todo, o nada. Mientras corre, bloquea la base: lo que lee y lo que
  escribe no se mezcla con lo que guarde la página.
- Si sale `ERROR:`, no se guardó nada. Corregir la entrada que nombra y repetir. No saltarse el script.
- `Programa CRM/abrir_pagina.py` puede estar abierto al mismo tiempo: la página se actualiza sola en unos segundos.

#### `vencidas`

Lista las vacantes con la próxima acción vencida, en dos grupos:
- `SIN_CONTACTO`: no hay a quién escribir. Se propone al usuario cerrarlas (`cerrar-vencidas`, solo con su sí).
- `ACCION`: se revisan una por una (seguimiento, postular, algo que debe hacer el usuario).

#### `nuevas.json` — vacantes que no están en el CRM

Una lista. Obligatorios: `empresa`, `cargo`, `perfil`, `modalidad`, `portal` y `aviso`.

```json
[{"empresa": "Acme Contable SAS", "cargo": "Accountant", "perfil": "Contable/Financiero", "modalidad": "remoto",
  "portal": "Indeed", "aviso": "<texto completo del aviso>", "link": "https://...", "experienciaAnios": 3, "fechaPublicacion": "2026-10-02",
  "salarioMin": 5000000, "salarioMax": 6000000, "salarioTexto": "COP 5.000.000 a 6.000.000/mes",
  "notas": "Pide inglés avanzado."}]
```

- `aviso`: el texto completo del aviso, copiado tal cual (descripción, requisitos, salario, condiciones). Es el registro
  de la vacante aunque la empresa la borre del portal; la página lo muestra en "Aviso guardado". Si no hay aviso
  (WhatsApp, referido, confirmación por correo), va lo que dijo el usuario o el correo.
- `perfil`: `Auditoría/Revisoría`, `Contable/Financiero`, `QA` u `Otro`.
- `modalidad`: `remoto`, `hibrido`, `presencial` o `no_especificado`.
- Opcionales: `ciudad`, `link`, `salarioMin`, `salarioMax`, `salarioTexto`, `experienciaAnios`, `fechaPublicacion` (AAAA-MM-DD), `nivel`, `notas`, `alertas`.
- `contrato`: `tiempo_completo` o `parcial` (medio tiempo o por servicio), solo si el aviso lo dice; sin él se asume tiempo completo.
  Con el `cargo` (palabras clave), `contrato`, `modalidad` y `ciudad` (remoto, en la ciudad del usuario o con mudanza) el script
  elige el caso de búsqueda de la vacante (Ajustes) y su salario mínimo; si ningún caso la acepta, queda bloqueada con puntaje 0.
- Empresa sin nombre: `"empresa": "Importante empresa del sector", "empresaId": null`.
- Por correo: `"canal": "correo", "correoPostulacion": "...", "asunto": "<el que pide el aviso>"`. El script crea el borrador.
- Requisito que la HV no cumple: `"excluyente": "<qué pide>"` → queda cerrada como "no aplica".
- El usuario ya se postuló: `"postulada_por_usuario": "<evidencia>"` y `"fechaPostulacion"`.
- Carta: `"carta": "<solo el cuerpo>"` y, si va en inglés, `"idioma": "en"`. El script pone saludo y firma (los toma de `perfil`).
- **Si a una vacante que pasa a "por aprobar" le falta la carta, el script dice `FALTA CARTA` y no guarda nada.**
  Se agrega la carta a esas y se repite el mismo comando.
- El script descarta solo las duplicadas (mismo `link`, o misma `empresa + cargo + ciudad`).

#### `cambios.json` — novedades de vacantes que ya están

Una lista. Cada entrada:
- `id` (obligatorio) y `texto` (obligatorio: qué pasó y la fuente, p. ej. `"Correo de Computrabajo del 05-oct: Han descartado tu CV"`).
- `etapa` (opcional) y `resultado` (obligatorio si `etapa` es `cerrada`: `no_seleccionado`, `vacante_cerrada`, `sin_respuesta`…).
- `tipo` (por defecto `nota`; p. ej. `postulacion`, `correo_enviado`, `cambio_etapa`) y `fecha` del hecho (por defecto HOY).
- `alertas_mas`, `alertas_menos`, `notas_mas` (texto que se agrega a las notas), `proximaAccion` (`{"fecha": "AAAA-MM-DD", "texto": "..."}`
  exactamente con esas dos claves, o `null`; otra forma es `ERROR:`, porque una fecha mal escrita nunca vencería).
- Solo las claves de esta lista: una mal escrita (`"etapo"`) es `ERROR:`, no se ignora.
- `campos`: solo campos simples como `seguimientos`, `correoPostulacion`, `link`, salarios, `ciudad` o `aviso`
  (para guardar el aviso de una vacante vieja que no lo tiene).
- `contacto`: `{"nombre", "email", "telefono", "rol"}` (al menos email o teléfono). Se agrega a la empresa de la vacante,
  sin repetir un correo que ya esté.
- `borrador`: id del borrador que Claude envió desde Gmail (con el "sí" del usuario). Queda como enviado con la fecha;
  si ya figuraba enviado, el script se detiene para no mandarlo dos veces. **Exige `si_del_usuario`.**
- `si_del_usuario`: el texto con que el usuario autorizó el envío en el chat (p. ej. `"sí a 1 y 3"`). Va en **toda** entrada de un
  correo o una postulación que envió Claude, con o sin borrador; queda en el historial como "Autorizado por el usuario en el chat".
  No va en lo que envió el usuario mismo (seguimientos que se ven en Enviados).

El script agrega al historial sin borrar lo anterior y pone la próxima acción según los Ajustes.

#### `registro.json` — lo que se hizo en el día (`corridas`)

`{"tipo": "<acciones hechas>", "resumen": "<una línea>", "detalle": ["...", "..."]}`.
Si ya hay registro de ese día, el detalle se suma al anterior.

#### `cambios-perfil.json` — cambiar datos del usuario o logros (solo con su "sí")

No es el `mis_datos.json` de la carpeta principal: ese solo se usa una vez, con `crear_base.py`, para crear la base.

`{"perfil": [{"seccion": "formularios", "campo": "Aspiración salarial", "valor": "..."}], "logros": [{"id": "L5", "logro": "...", "cuando": "..."}]}`.
Solo cambia filas que ya existen (los nombres de `seccion` y `campo` son los que muestra `comandos.py perfil`); `cuando` es opcional.

## Revisar o simplificar el código

Solo cuando el usuario lo pida.

Se trabaja sobre `comandos.py`, `leer_y_guardar.py`, `abrir_pagina.py`, `puntaje.py` y `puntaje.js` (en `Programa CRM/`)
y `pagina.html` (la página, también en `Programa CRM/`).

1. **Orientarse antes de leer archivos:** buscar con Grep la función o el texto y leer solo esas líneas.
2. **Antes de editar:** copiar `Programa CRM/postulaciones.db` al scratchpad y probar siempre con `--db <copia>`
   (`python "Programa CRM/comandos.py" --db <copia> …`, `python "Programa CRM/abrir_pagina.py" --db <copia>`). Nunca probar sobre la base real.
   Guardar la salida de `vencidas` y de `nuevas` con un `nuevas.json` de prueba.
3. **Qué buscar (reglas de ponytail):** primero errores que pierdan datos o den puntajes distintos entre `puntaje.js` y `puntaje.py`;
   después código muerto o duplicado. Borrar es mejor que agregar. Nada de opciones o "por si acaso".
4. **Reglas:**
   - `comandos.py` no cambia sus comandos, argumentos ni el formato de lo que imprime.
   - Toda regla de puntaje cambia igual en `puntaje.py` y `puntaje.js`. Si no se pueden cambiar los dos, no se cambia ninguno.
   - Nunca quitar validaciones, manejo de errores, las transacciones ni el historial.
   - `abrir_pagina.py` sigue escuchando solo en 127.0.0.1 y rechazando pedidos de otro origen.
   - No tocar este archivo de instrucciones ni la base real. `.claude/` solo si el usuario lo pide (regla 8 de Prohibiciones).
   - No dejar archivos sueltos ni carpetas nuevas: la estructura es la de "Carpetas".
   - Máximo 5 cambios por vez. Lo demás se lista como pendiente.
5. **Verificar:** `python "Programa CRM/pruebas.py"` (todas OK; incluye la paridad de `puntaje.py` y `puntaje.js` si hay node),
   `python -m py_compile "Programa CRM"/*.py` y `node --check "Programa CRM/puntaje.js"`. Repetir las salidas del paso 2
   sobre la copia: deben salir idénticas, salvo el cambio buscado. Un cambio de comportamiento lleva su prueba nueva en
   `pruebas.py`. Borrar `Programa CRM/__pycache__/` al terminar.
