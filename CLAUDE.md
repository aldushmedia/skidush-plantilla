# SKIDUSH · mi sistema de contenido con IA

Este repo es el sistema de contenido del alumno: guarda reels que funcionan, aprende cómo habla, escribe sus guiones con
su voz y edita sus videos. El alumno solo graba. Todo en español, claro y corto, sin tecnicismos.

- **Al abrir la sesión** el hook ya revisó el código y preparó el motor: lee su mensaje. Si falta el código, pídeselo
  al alumno y guárdalo con `python3 skidush.py codigo <CODIGO>`. Si dice que el acceso terminó, repite el mensaje y no
  hagas nada más.
- **Para todo, usa las skills `skidush-*`** (bienvenida, entrevista, voz, ideas, guion, editar, trials, calendario).
  Cada una pide sus instrucciones vigentes al servidor; nunca trabajes de memoria sin ellas.
- **Carpetas:** `negocio/` (su negocio), `voz/` (cómo habla), `ideas/` (reels guardados y banco de ideas), `guiones/`,
  `videos/` (ediciones) y `calendario.md`.
- **Al terminar cada paso:** commit y push de lo que cambió (el alumno no tiene que saber de git). Los videos pesados no
  van a git: se entregan como archivo en el chat.
- `skidush.py` es el cliente de SKIDUSH; no lo cambies.
