/*
 * Motor de calificación del CRM de postulaciones.
 * Fuente única de las reglas de puntaje y presupuesto. scoring.py es su
 * gemelo en Python para las corridas; si cambias una regla aquí, cámbiala allá.
 */
(function (root) {
  "use strict";

  const PALABRAS = "contador, contable, contabilidad, accountant, accounting, impuestos, nómina, auditor, audit, revisor fiscal, " +
    "financiero, financiera, cuentas por pagar, cuentas por cobrar, controller, controlador, tesorería, QA, " +
    "tester, testing, quality assurance, pruebas, automatización de pruebas";

  const AJUSTES_BASE = {
    ciudadBase: "",
    /* Casos de búsqueda: la vacante usa el primero (de arriba abajo) con una de sus palabras clave en el cargo (sin palabras:
       cualquier cargo) que acepte su contrato y su modalidad. Las palabras son también las que se buscan en los portales.
       modalidad: remoto | ciudad (presencial o híbrido en tu ciudad) | remoto_ciudad | mudanza (otra ciudad) | cualquiera. */
    casos: [
      { palabras: PALABRAS, contrato: "tiempo_completo", modalidad: "remoto_ciudad", salarioMinimo: 4500000 },
      { palabras: PALABRAS, contrato: "tiempo_completo", modalidad: "mudanza", salarioMinimo: 6000000 },
      { palabras: "revisor fiscal, revisoría fiscal", contrato: "parcial", modalidad: "remoto", salarioMinimo: 1750905 },
      { palabras: PALABRAS, contrato: "parcial", modalidad: "remoto_ciudad", salarioMinimo: 1750000 }
    ],
    umbralAprobar: 60,
    limitePorCorrida: 12,
    diasPrimerSeguimiento: 10,
    diasEntreSeguimientos: 10,
    maxSeguimientos: 2,
    diasCierreSinNovedad: 45
  };

  const PUNTOS_PERFIL = {
    "Auditoría/Revisoría": 30, "Contable/Financiero": 30, "QA": 22, "Otro": 10
  };

  function sinTildes(s) {
    return String(s || "").normalize("NFD").replace(/\p{Mn}/gu, "").toLowerCase().trim();
  }

  function mismaCiudad(a, b) {
    return !!a && !!b && sinTildes(a) === sinTildes(b);
  }

  function inferirNivel(cargo) {
    const c = sinTildes(cargo);
    if (/docente|profesor|catedra/.test(c)) return "docencia";
    if (/auxiliar|asistente|practicante|\baux\b|aprendiz/.test(c)) return "auxiliar";
    if (/gerente|director|jefe|controller|manager|head of/.test(c)) return "gerencia";
    if (/senior|\bsr\b|lider|coordinador|especialista|experto/.test(c)) return "senior";
    return "profesional";
  }

  function num(x) { return typeof x === "number" ? x : null; }

  /* La fecha (ms) de un texto AAAA-MM-DD exacto, si no null: Date.parse acepta también "2026-10" y "2026-02-30". */
  function fecha(s) {
    const t = Date.parse(s + "T00:00:00Z");
    return !isNaN(t) && new Date(t).toISOString().slice(0, 10) === s ? t : null;
  }

  function diasEntre(desde, hasta) {
    const a = fecha(desde), b = fecha(hasta);
    return a == null || b == null ? null : Math.round((b - a) / 86400000);
  }

  function salarioReferencia(v) {
    const lo = num(v.salarioMin), hi = num(v.salarioMax);
    if (lo != null && hi != null) return Math.round((lo + hi) / 2);
    return lo ?? hi;
  }

  const MODALIDAD_CASO = { remoto: ["remoto"], ciudad: ["ciudad"], remoto_ciudad: ["remoto", "ciudad"], mudanza: ["mudanza"],
    cualquiera: ["remoto", "ciudad", "mudanza"] };

  /* Texto en minúsculas, sin tildes ni signos: "Analista Contable (Sr.)" -> "analista contable sr". */
  function plano(s) { return sinTildes(s).replace(/[^a-z0-9]+/g, " ").trim(); }

  /* Palabras clave de un caso, ya planas. */
  function palabrasDe(c) { return String(c.palabras || "").split(",").map(plano).filter(Boolean); }

  /* Índice del caso de búsqueda de la vacante (-1 si ninguno). Sin contrato publicado se asume tiempo completo.
     Una palabra clave coincide si cada una de sus palabras es el inicio de una palabra del cargo
     ("revisor fiscal" sirve para "Revisor(a) Fiscal" y "Revisora fiscal"; "contable" para "contables"). */
  function casoDe(v, modo, casos) {
    const contrato = v.contrato || "tiempo_completo";
    const cargo = plano(v.cargo).split(" ");
    const coincide = p => p.split(" ").every(w => cargo.some(x => x.startsWith(w)));
    return casos.findIndex(c => (c.contrato === "cualquiera" || c.contrato === contrato)
      && (MODALIDAD_CASO[c.modalidad] || []).indexOf(modo) >= 0
      && (palabrasDe(c).length === 0 || palabrasDe(c).some(coincide)));
  }

  /* Salario de la vacante frente al mínimo del caso que le aplica. La ciudad decide si es en tu ciudad o con mudanza. */
  function presupuesto(v, ajustes) {
    const a = Object.assign({}, AJUSTES_BASE, ajustes || {});
    const ref = salarioReferencia(v);
    const nivel = v.nivel || inferirNivel(v.cargo);
    let modo;
    if (v.modalidad === "remoto") modo = "remoto";
    else if (mismaCiudad(v.ciudad, a.ciudadBase)) modo = "ciudad";
    else modo = "mudanza";
    const supuesto = modo === "mudanza" && (v.modalidad === "no_especificado" || !v.ciudad);
    const casos = a.casos || [];
    const iCaso = casoDe(v, modo, casos);
    const minimo = iCaso >= 0 ? num(casos[iCaso].salarioMinimo) : null;
    return {
      salarioRef: ref, neto: ref, minimo: minimo, nivel: nivel, caso: iCaso >= 0 ? iCaso + 1 : null,
      modo: modo, supuesto: supuesto,
      cumple: ref == null || minimo == null ? null : ref >= minimo
    };
  }

  function puntaje(v, ajustes, hoy) {
    const p = presupuesto(v, ajustes);
    const alertas = v.alertas || [];
    const partes = {};

    partes.perfil = PUNTOS_PERFIL[v.perfil] ?? 10;

    const exp = num(v.experienciaAnios);
    if (p.nivel === "auxiliar") partes.experiencia = 6;
    else if (exp == null) partes.experiencia = 14;
    else if (exp <= 3) partes.experiencia = 20;
    else if (exp <= 4) partes.experiencia = 12;
    else partes.experiencia = 4;

    if (p.salarioRef == null || p.minimo == null) partes.economico = 15;
    else if (p.salarioRef < p.minimo) partes.economico = 0;
    else if (!p.minimo) partes.economico = 25;
    else partes.economico = Math.round(20 + Math.min(10, 10 * (p.salarioRef / p.minimo - 1) / 0.4));

    partes.modalidad = p.supuesto ? 5 : { remoto: 10, ciudad: 9, mudanza: 3 }[p.modo];

    const dias = diasEntre(v.fechaPublicacion, hoy);
    if (dias == null) partes.frescura = 5;
    else if (dias <= 7) partes.frescura = 10;
    else if (dias <= 14) partes.frescura = 8;
    else if (dias <= 30) partes.frescura = 5;
    else partes.frescura = 2;

    let total = partes.perfil + partes.experiencia + partes.economico + partes.modalidad + partes.frescura;
    let bloqueo = null;
    if (alertas.indexOf("posible_estafa") >= 0) bloqueo = "Posible estafa";
    else if (alertas.indexOf("no_aplica") >= 0) bloqueo = "No cumples un requisito excluyente";
    else if (!p.caso) bloqueo = "Ningún caso de búsqueda la acepta";
    if (bloqueo) total = 0;
    return { total: Math.max(0, Math.min(100, total)), partes: partes, bloqueo: bloqueo, presupuesto: p };
  }

  const api = { AJUSTES_BASE, PUNTOS_PERFIL, inferirNivel, presupuesto, puntaje, diasEntre, salarioReferencia, sinTildes };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.Motor = api;
})(typeof window !== "undefined" ? window : globalThis);
