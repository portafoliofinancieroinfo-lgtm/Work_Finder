# Lo que Claude no puede hacer

Prohibiciones de Claude en este proyecto. Valen en toda acción y en toda sesión. Cómo se hacen las acciones está en `CLAUDE.md`.
"El usuario" es la persona dueña del CRM.

1. **No escribas la base por fuera de `Programa del CRM/comandos.py`.** Nada de SQL a mano, ni editar, mover, copiar encima o borrar `postulaciones.db`.
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
9. **No trabajes con el CRM si hay una copia en conflicto** (`postulaciones (1).db` o parecida) en `Programa del CRM/`: avisa y no la borres.
10. **No escribas contraseñas ni códigos de verificación, no aceptes condiciones y no subas documentos** en ningún sitio sin el
    "sí" del usuario.
