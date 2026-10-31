# Cómo se usa el CRM

## Piezas

| Qué | Dónde |
|---|---|
| Programa del CRM (fuente de verdad) | `Programa del CRM/postulaciones.db` (SQLite). No va a git: tiene datos personales. Se crea una vez con `python "Programa del CRM/crear_base.py"` desde tu `mis_datos.json`. **Un solo equipo a la vez:** si la guardas en una carpeta sincronizada (Drive, Dropbox…), cierra el CRM (`abrir_pagina.py`) antes de cambiar de equipo y espera a que termine de sincronizar. Esas nubes no unen cambios hechos en dos equipos: guardan una copia en conflicto (`postulaciones (1).db`). Si aparece una, se le avisa al usuario y no se borra |
| Escribir en la base | `python "Programa del CRM/comandos.py" <comando> …` (nunca a mano) |
| Leer la base | `python "Programa del CRM/comandos.py" consulta "SELECT …"` (solo lectura) y `python "Programa del CRM/comandos.py" perfil` |
| Página del CRM | `Abrir CRM.bat` (doble clic) o `python "Programa del CRM/abrir_pagina.py"` → abre `http://localhost:8765` en el Chrome del usuario. Solo funciona en este computador |
| Página | `Programa del CRM/pagina.html`. `abrir_pagina.py` la sirve junto con `puntaje.js` y la HV |
| Código de la base | `Programa del CRM/leer_y_guardar.py` (esquema y lectura/escritura), usado por `comandos.py` y `abrir_pagina.py` |
| Puntaje | `Programa del CRM/puntaje.js` (página) y `Programa del CRM/puntaje.py` (lo usa `comandos.py`). Son gemelos: toda regla cambia en los dos |
| HV de 2 páginas | `Mi hoja de vida/HV.pdf` |
| Crear la base | `python "Programa del CRM/crear_base.py"` (con tu `mis_datos.json`) o `--demo` (con vacantes de ejemplo). Nunca pisa una base existente |
| Pruebas | `python "Programa del CRM/pruebas.py"`: unas 30 pruebas sobre una base de ejemplo temporal (nunca la tuya). Todas deben salir OK |

## Tablas

Las colecciones guardan cada registro como un documento JSON en la columna `data` (tabla `id, data`). Cada documento lleva
`_rev`, que `leer_y_guardar.py` sube en 1 en cada escritura: la página lo manda al guardar y `abrir_pagina.py` rechaza (409) la escritura si el
registro cambió desde que la página lo leyó, o si acorta el historial de una vacante. No se escribe a mano.

- **`vacantes`**: una por vacante (`v001`, `v002`…).
  - Campos principales: `empresa`, `cargo`, `perfil`, `nivel`, `modalidad`, `ciudad`, `salarioMin`/`salarioMax`, `link`, `portal`,
    `canal` (`portal`/`correo`), `etapa`, `resultado`, `alertas`, `historial`, `proximaAccion`, `seguimientos`, `puntaje`, `neto`.
  - Etapas: `descubierta` → `por_aprobar` → `aprobada` → `postulada` → `hv_vista` → `en_proceso` → `oferta` → `cerrada`.
- **`empresas`**: `nombre` y `contactos` (nombre, email, teléfono, rol, fuente).
- **`borradores`**: correos listos (`para`, `asunto`, `cuerpo`, `tipo`, `estado`, `vacanteId`). Los envía Claude con el "sí"
  del usuario (`prohibiciones.md` y `CLAUDE.md`, y `"borrador"` en `cambios.json`) o el usuario desde su Gmail, marcando "Ya lo envié" en la página.
- **`config`**: el registro `ajustes` (`ciudadBase`, `casos` de búsqueda con sus palabras clave y su salario mínimo,
  `umbralAprobar`, `limitePorCorrida` y la cadencia de seguimientos). Mientras el usuario no guarde Ajustes, los casos y las
  palabras son los de `AJUSTES_BASE` en `puntaje.js`/`puntaje.py`. `neto` de la vacante = su salario de referencia (ya no se restan costos de traslado). **Siempre se leen de aquí.** el usuario los cambia en la pestaña Ajustes.
- **`corridas`**: un registro por día con lo que se hizo. La página muestra el más reciente.

Vistas para consultar sin JSON: `vacantes_v` (empresa, cargo, etapa, resultado, puntaje, neto, portal, modalidad, ciudad, link,
fechaPostulacion, proximaFecha, proximaTexto), `empresas_v` y `borradores_v`.

Datos del usuario (tablas normales): `perfil` (secciones contacto, perfil, formularios y portafolio), `logros` (L1–L5),
`plantillas` (A, B, C, F y G; `bloqueada` = 1 las deja fuera de uso) y `servicios` (opcional, vacía al crear). Para verlos todos: `python "Programa del CRM/comandos.py" perfil`.

Las listas válidas de etapas, resultados, alertas y tipos de historial están en `Programa del CRM/pagina.html` (la página); `comandos.py` las lee de ahí.

## Consultas útiles

```
python "Programa del CRM/comandos.py" consulta "SELECT id, empresa, cargo, etapa FROM vacantes_v WHERE empresa LIKE '%acme%'"
python "Programa del CRM/comandos.py" consulta "SELECT id, empresa, cargo FROM vacantes_v WHERE link = 'https://...'"
python "Programa del CRM/comandos.py" consulta "SELECT etapa, count(*) FROM vacantes_v GROUP BY etapa"
python "Programa del CRM/comandos.py" consulta "SELECT data FROM vacantes WHERE id = 'v120'"
python "Programa del CRM/comandos.py" consulta "SELECT id, asunto, estado FROM borradores_v WHERE estado = 'pendiente'"
```

`consulta` abre la base en solo lectura: aunque se escriba un UPDATE o DELETE, no cambia nada.

## Escribir con `comandos.py`

`HOY` = fecha de hoy en `AAAA-MM-DD`. Los archivos de entrada se escriben en el scratchpad de la sesión.

```
python "Programa del CRM/comandos.py" vencidas        HOY
python "Programa del CRM/comandos.py" nuevas          nuevas.json HOY
python "Programa del CRM/comandos.py" cambios         cambios.json HOY
python "Programa del CRM/comandos.py" aprobar         HOY v120 v129 …
python "Programa del CRM/comandos.py" cerrar-vencidas HOY
python "Programa del CRM/comandos.py" registro        HOY registro.json
python "Programa del CRM/comandos.py" editar-perfil   cambios-mis_datos.json
```

- Cada comando guarda todo en una sola transacción: o queda todo, o nada. Mientras corre, bloquea la base: lo que lee y lo que
  escribe no se mezcla con lo que guarde la página.
- Si sale `ERROR:`, no se guardó nada. Corregir la entrada que nombra y repetir. No saltarse el script.
- `Programa del CRM/abrir_pagina.py` puede estar abierto al mismo tiempo: la página se actualiza sola en unos segundos.

### `vencidas`

Lista las vacantes con la próxima acción vencida, en dos grupos:
- `SIN_CONTACTO`: no hay a quién escribir. Se propone al usuario cerrarlas (`cerrar-vencidas`, solo con su sí).
- `ACCION`: se revisan una por una (seguimiento, postular, algo que debe hacer el usuario).

### `nuevas.json` — vacantes que no están en el CRM

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

### `cambios.json` — novedades de vacantes que ya están

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

### `registro.json` — lo que se hizo en el día (`corridas`)

`{"tipo": "<acciones hechas>", "resumen": "<una línea>", "detalle": ["...", "..."]}`.
Si ya hay registro de ese día, el detalle se suma al anterior.

### `cambios-mis_datos.json` — cambiar datos del usuario o logros (solo con su "sí")

No es el `mis_datos.json` de la carpeta principal: ese solo se usa una vez, con `crear_base.py`, para crear la base.

`{"perfil": [{"seccion": "formularios", "campo": "Aspiración salarial", "valor": "..."}], "logros": [{"id": "L5", "logro": "...", "cuando": "..."}]}`.
Solo cambia filas que ya existen (los nombres de `seccion` y `campo` son los que muestra `comandos.py perfil`); `cuando` es opcional.

## Mantener el código

Solo cuando el usuario lo pida. Se trabaja sobre `comandos.py`, `leer_y_guardar.py`, `abrir_pagina.py`, `puntaje.py` y `puntaje.js` (en `Programa del CRM/`)
y `pagina.html` (la página, también en `Programa del CRM/`).

1. **Orientarse antes de leer archivos:** buscar con Grep la función o el texto y leer solo esas líneas.
2. **Antes de editar:** copiar `Programa del CRM/postulaciones.db` al scratchpad y probar siempre con `--db <copia>`
   (`python "Programa del CRM/comandos.py" --db <copia> …`, `python "Programa del CRM/abrir_pagina.py" --db <copia>`). Nunca probar sobre la base real.
   Guardar la salida de `vencidas` y de `nuevas` con un `nuevas.json` de prueba.
3. **Qué buscar (reglas de ponytail):** primero errores que pierdan datos o den puntajes distintos entre `puntaje.js` y `puntaje.py`;
   después código muerto o duplicado. Borrar es mejor que agregar. Nada de opciones o "por si acaso".
4. **Reglas:**
   - `comandos.py` no cambia sus comandos, argumentos ni el formato de lo que imprime.
   - Toda regla de puntaje cambia igual en `puntaje.py` y `puntaje.js`. Si no se pueden cambiar los dos, no se cambia ninguno.
   - Nunca quitar validaciones, manejo de errores, las transacciones ni el historial.
   - `abrir_pagina.py` sigue escuchando solo en 127.0.0.1 y rechazando pedidos de otro origen.
   - No tocar los archivos de instrucciones (`CLAUDE.md`, `prohibiciones.md`, `como_elegir_vacantes_y_escribir_cartas.md`, este) ni la base real. `.claude/` solo si el usuario lo pide (regla 8 de `prohibiciones.md`).
   - No dejar archivos sueltos ni carpetas nuevas: la estructura es la de `CLAUDE.md`.
   - Máximo 5 cambios por vez. Lo demás se lista como pendiente.
5. **Verificar:** `python "Programa del CRM/pruebas.py"` (todas OK; incluye la paridad de `puntaje.py` y `puntaje.js` si hay node),
   `python -m py_compile "Programa del CRM"/*.py` y `node --check "Programa del CRM/puntaje.js"`. Repetir las salidas del paso 2
   sobre la copia: deben salir idénticas, salvo el cambio buscado. Un cambio de comportamiento lleva su prueba nueva en
   `pruebas.py`. Borrar `Programa del CRM/__pycache__/` al terminar.
