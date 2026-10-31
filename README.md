# Finder Work

CRM de postulaciones de empleo que corre en tu computador y se opera con [Claude Code](https://claude.com/claude-code).
Guarda cada vacante, calcula un puntaje según lo que tú buscas, escribe las cartas y los seguimientos, y deja en el
historial **quién autorizó cada envío**. Claude propone; tú dices "sí".

- Programa del CRM local en SQLite (un archivo). Sin nube, sin cuentas, sin dependencias: solo Python.
- Página del CRM en `http://localhost:8765` (embudo, vacantes, borradores, ajustes).
- Claude no escribe la base a mano: todo pasa por `comandos.py`, con validaciones y transacciones (o se guarda todo, o nada).
- Hooks que bloquean escribir la base por fuera de `comandos.py` y piden tu confirmación antes de cada correo enviado.

## Requisitos

- Python 3.9 o superior (solo biblioteca estándar).
- Para usar las acciones con Claude: [Claude Code](https://claude.com/claude-code) y la extensión Claude in Chrome, con tus sesiones
  abiertas en Gmail y en tus portales de empleo. Para solo ver el CRM no hace falta nada de esto.
- Opcional: Node.js, para que las pruebas comparen el puntaje de `puntaje.js` con el de `puntaje.py`.
- **macOS / Linux:** los hooks de `.claude/settings.json` llaman a `python`. Si en tu equipo solo existe `python3`, cambia `python`
  por `python3` en ese archivo. Si no, los hooks fallan sin bloquear y las protecciones quedan apagadas.

## Probarlo en 1 minuto (sin tus datos)

```bash
python "Programa del CRM/crear_base.py" --demo
python "Programa del CRM/abrir_pagina.py"
```

Se crea una base con una persona y cuatro vacantes inventadas, y se abre `http://localhost:8765`.
Borra `Programa del CRM/postulaciones.db` antes de crear la tuya.

## Montarlo con tus datos

### Paso 1. Reúne tus documentos

1. Tu **hoja de vida de 2 páginas** en PDF. Guárdala como `Mi hoja de vida/HV.pdf`: es la que se adjunta en las postulaciones por correo.
2. Tu hoja de vida completa (opcional), para sacar logros y fechas exactas.
3. Una lista de **3 a 5 logros con cifras reales** (qué hiciste, cuánto, en qué empresa). Las cartas usan uno solo por vacante, el más afín al cargo.
4. Tus **datos de formularios**: ciudad, aspiración salarial, nivel de inglés, software que manejas, si estás autorizado para trabajar donde buscas.
5. Qué buscas: **palabras clave** del cargo, **modalidad** (remoto, en tu ciudad, con mudanza), **contrato** (tiempo completo o parcial) y el **salario mínimo** con el que sí te mueves.

### Paso 2. Llena `mis_datos.json`

```bash
cp mis_datos.ejemplo.json mis_datos.json
```

(En Windows: `copy mis_datos.ejemplo.json mis_datos.json`.) Edita `mis_datos.json` con tus datos. `mis_datos.json` está en `.gitignore`: no se sube.

| Sección | Qué lleva | Obligatorio |
|---|---|---|
| `contacto` | `nombre`, `telefono`, `correo` (van en la firma de cada carta) y, si quieres, `linkedin`, `github` u otros | `nombre`, `telefono`, `correo` |
| `perfil` | `titulo` (p. ej. "Ingeniera de Sistemas"), `experiencia` (p. ej. "4 años en desarrollo web") y, si quieres, `resumen`, `diferencial`, `trayectoria` | `titulo`, `experiencia` |
| `formularios` | Pares "pregunta": "respuesta" con lo que piden los portales. Si Claude encuentra una pregunta que no está aquí, se detiene y te la hace | al menos uno |
| `logros` | Lista de `{"logro": "...", "usar_en": "tipos de cargo donde sirve"}`. Se numeran L1, L2… | al menos uno |
| `busqueda` | `ciudadBase`, `umbralAprobar` (puntaje mínimo para proponerte una vacante), `limitePorCorrida`, `maxSeguimientos` y los `casos` de búsqueda | `casos` |

Cada **caso de búsqueda** dice qué vacantes aceptas:

```json
{"palabras": "desarrollador, developer, backend", "contrato": "tiempo_completo", "modalidad": "remoto", "salarioMinimo": 5000000}
```

- `palabras`: palabras que debe tener el cargo. También son las que se buscan en los portales.
- `contrato`: `tiempo_completo`, `parcial` o `cualquiera`.
- `modalidad`: `remoto`, `ciudad` (presencial o híbrido en tu ciudad), `remoto_ciudad`, `mudanza` o `cualquiera`.
- `salarioMinimo`: pesos al mes. Una vacante por debajo no puntúa en lo económico.

Con Claude Code puedes saltarte la edición a mano: abre la carpeta, escribe **"Configurar"** y Claude te entrevista y llena `mis_datos.json`
(Acción 0 de `CLAUDE.md`). Nunca inventa datos: te los pregunta.

### Paso 3. Crea tu base

```bash
python "Programa del CRM/crear_base.py"
```

Revisa que todo quedó bien:

```bash
python "Programa del CRM/comandos.py" perfil
```

`crear_base.py` nunca pisa una base que ya existe. Se detiene si tu nombre, teléfono o correo siguen siendo los del ejemplo, si dejaste
un `<marcador>` sin llenar o si un ajuste de búsqueda tiene un tipo o un nombre que no existe.

### Paso 4. Abre el CRM

Doble clic en `Abrir CRM.bat` (Windows) o:

```bash
python "Programa del CRM/abrir_pagina.py"
```

Se abre `http://localhost:8765`. Solo escucha en tu equipo (127.0.0.1). En la pestaña **Ajustes** puedes cambiar después los casos de búsqueda.

### Paso 5. Ajusta tus criterios de decisión

Edita `.claude/como_elegir_vacantes_y_escribir_cartas.md`: qué avisos no quieres ver, cuáles descartas por estafa y cómo deben ser tus cartas.
Es el archivo que Claude lee para decidir por ti qué vacantes registrar.

## Cómo se usa con Claude Code

Abre esta carpeta con Claude Code. Lee `.claude/CLAUDE.md`, `.claude/prohibiciones.md` y `.claude/como_usar_la_base_de_datos.md`. Después pídele una acción:

| Dile | Qué hace |
|---|---|
| **"Buscar"** | Busca vacantes publicadas en la última semana en tus portales, descarta las repetidas, las puntúa y escribe una carta por cada una |
| **"Leer y revisar"** | Ordena tu Gmail, lee las novedades de tus postulaciones y actualiza las etapas del CRM |
| **"Sí a 1 y 3"** (tras el resumen) | Aprueba y postula **solo** esas vacantes, con tu HV y la carta |
| Cuéntale un WhatsApp, una llamada o un referido | Lo registra como "búsqueda externa" |

Toda acción termina con un **resumen numerado** de lo que espera tu decisión. Claude no aprueba, postula ni envía nada sin tu "sí" en el chat
(ver `.claude/prohibiciones.md`), y cada envío queda en el historial de la vacante con lo que respondiste.

Necesitas crear en Gmail las etiquetas que usa la Acción 1 (Postulaciones, Activo, Requiere respuesta, Cerrado, Ruido).

## Estructura

**Lo tuyo** (lo que abres o llenas tú):

```
Abrir CRM.bat                  doble clic: abre el CRM en el navegador
mis_datos.ejemplo.json         plantilla de tus datos (cópiala como mis_datos.json y llénala)
mis_datos.json                 tus datos (no se sube a git)
Mi hoja de vida/               tu HV.pdf de 2 páginas (no se sube a git)
README.md                      esta guía
```

**El programa** (no hace falta abrirlo):

```
Programa del CRM/
  postulaciones.db             la base: vacantes, empresas, historial (no se sube a git)
  pagina.html                  la página del CRM
  abrir_pagina.py              la sirve en localhost (lo usa Abrir CRM.bat)
  comandos.py                  los comandos que usa Claude; único camino para escribir la base
  crear_base.py                crea postulaciones.db desde mis_datos.json
  puntaje.py   puntaje.js      calculan el puntaje de cada vacante (gemelos: toda regla cambia en los dos)
  leer_y_guardar.py            lee y guarda en la base (esquema SQLite)
  pruebas.py                   ~30 pruebas, sobre una base de ejemplo temporal
```

**Lo de Claude** (instrucciones y protecciones):

```
.claude/
  CLAUDE.md                                   las acciones, paso a paso
  prohibiciones.md                            lo que Claude no puede hacer
  como_elegir_vacantes_y_escribir_cartas.md   qué vacantes sirven y cómo escribir cartas
  como_usar_la_base_de_datos.md               formatos de entrada y mantenimiento del código
  settings.json                               activa los hooks
  hooks/bloquear_cambios_a_mano_en_la_base.py la base solo se escribe con comandos.py
  hooks/pedir_permiso_antes_de_enviar.py      pide tu sí antes de cada correo o adjunto
```

## Pruebas

```bash
python "Programa del CRM/pruebas.py"
```

Crean su propia base de ejemplo en una carpeta temporal; nunca tocan la tuya.

## Personalizar el puntaje

El puntaje (0 a 100) suma el tipo de perfil, la experiencia que piden, el salario frente a tu mínimo, la modalidad y qué tan reciente es el aviso;
una alerta de estafa o un requisito excluyente lo dejan en 0. Los tipos de perfil
que reconoce hoy son `Auditoría/Revisoría`, `Contable/Financiero`, `QA` y `Otro` (`PUNTOS_PERFIL` en `puntaje.py` y `puntaje.js`, y
las listas de `pagina.html`). Si buscas en otro rubro, cambia esos nombres **en los tres archivos a la vez** y corre las pruebas.

## Privacidad

- `postulaciones.db`, `mis_datos.json` y `Mi hoja de vida/` están en `.gitignore`: tu información no se sube.
- Si guardas la carpeta en Drive, Dropbox u otra nube, la base viaja con ella: usa **un solo equipo a la vez** (ver `.claude/como_usar_la_base_de_datos.md`).
- Antes de publicar un fork, revisa con `git status` que no haya subido nada tuyo.

## Licencia

MIT. Ver [LICENSE](LICENSE).
