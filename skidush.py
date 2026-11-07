#!/usr/bin/env python3
"""SKIDUSH · cliente del alumno (solo biblioteca estándar de Python).

Habla con el servidor de SKIDUSH usando el código del alumno. Sin un código activo no entrega nada.

    python3 skidush.py estado                  ¿mi acceso está activo?
    python3 skidush.py codigo SKI-XXXX-XXXX    guarda el código en este repo (skidush.codigo)
    python3 skidush.py instrucciones <pieza>   instrucciones actuales de una skill
    python3 skidush.py contenido <ruta>        banco de ideas, plantillas, estilos («ruta/» lista una carpeta)
    python3 skidush.py motor [--forzar]        baja el motor (guardar, analizar, editar)
    python3 skidush.py preparar                lo corre el hook al abrir cada sesión
    python3 skidush.py m <comando> [...]       corre un comando del motor (p. ej. «m guardar <link>»)

Códigos de salida: 0 bien · 3 acceso terminado o código con problema (mostrar el mensaje y detenerse) · 1 otro error.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
URL = os.environ.get("SKIDUSH_URL", "https://skidush.vercel.app").rstrip("/")
ARCHIVO_CODIGO = RAIZ / "skidush.codigo"
MOTOR = Path(os.environ.get("SKIDUSH_MOTOR_DIR", Path.home() / ".skidush" / "motor"))
LOG_INSTALAR = Path(tempfile.gettempdir()) / "skidush_instalar.log"
SIN_ACCESO = 3


class SinAcceso(Exception):
    pass


def codigo() -> str:
    c = os.environ.get("SKIDUSH_CODIGO", "").strip()
    if not c and ARCHIVO_CODIGO.exists():
        c = ARCHIVO_CODIGO.read_text(encoding="utf-8").strip()
    return c


def cuenta() -> str:
    """Dueño del repo en GitHub (a esa cuenta se amarra el código)."""
    try:
        url = subprocess.run(["git", "-C", str(RAIZ), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""
    m = re.search(r"[/:]([A-Za-z0-9-]+)/[^/]+?(?:\.git)?/?$", url)
    return m.group(1).lower() if m else ""


def pedir(accion: str, **datos) -> dict:
    cuerpo = json.dumps({"accion": accion, "codigo": codigo(), "cuenta": cuenta(), **datos}).encode()
    req = urllib.request.Request(f"{URL}/api/alumno", data=cuerpo, method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "skidush-cliente/1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            j = json.loads(e.read().decode())
        except Exception:
            j = {"mensaje": f"El servidor de SKIDUSH respondió {e.code}"}
        if e.code == 403:
            raise SinAcceso(j.get("mensaje", "Tu acceso a SKIDUSH no está activo."))
        raise RuntimeError(j.get("mensaje", f"Error {e.code}"))
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"No pude conectar con SKIDUSH ({e.reason}). Revisa que el acceso a la red de tu entorno esté en "
            "«Completo» (o que permita el dominio de SKIDUSH)."
        )


# ---------- comandos ----------

def cmd_estado(_args) -> int:
    j = pedir("acceso")
    nombre = f" · {j['alumno']}" if j.get("alumno") else ""
    print(f"✔ SKIDUSH activo{nombre} · nivel {j.get('nivel', 'general')} · vale hasta el {j.get('vence_texto')}")
    return 0


def cmd_codigo(args) -> int:
    if not args:
        print("Uso: python3 skidush.py codigo SKI-XXXX-XXXX")
        return 1
    c = re.sub(r"\s+", "", args[0]).upper()
    ARCHIVO_CODIGO.write_text(c + "\n", encoding="utf-8")
    print(f"Código guardado en {ARCHIVO_CODIGO.name}. Revisando…")
    return cmd_estado([])


def cmd_instrucciones(args) -> int:
    if not args:
        print("Uso: python3 skidush.py instrucciones <pieza>")
        return 1
    print(pedir("instrucciones", pieza=args[0])["texto"])
    return 0


def cmd_contenido(args) -> int:
    ruta = args[0] if args else ""
    j = pedir("contenido", ruta=ruta)
    print("\n".join(j["lista"]) if "lista" in j else j["texto"])
    return 0


def version_motor() -> str:
    v = MOTOR / ".version"
    return v.read_text().strip() if v.exists() else ""


def bajar_motor(forzar: bool = False) -> str:
    j = pedir("motor")
    if version_motor() == j["version"] and not forzar and (MOTOR / "skidush_motor").exists():
        return f"Motor al día ({j['version'][:7]}) en {MOTOR}"
    with tempfile.TemporaryDirectory() as tmp:
        tgz = Path(tmp) / "motor.tar.gz"
        req = urllib.request.Request(j["url"], headers={"User-Agent": "skidush-cliente/1"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tgz, "wb") as f:
            shutil.copyfileobj(r, f)
        destino = Path(tmp) / "x"
        with tarfile.open(tgz) as t:
            kw = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
            t.extractall(destino, **kw)
        hijos = [p for p in destino.iterdir() if p.is_dir()]
        origen = hijos[0] if len(hijos) == 1 else destino  # GitHub mete todo en una carpeta «dueño-repo-sha»
        if MOTOR.exists():
            shutil.rmtree(MOTOR)
        MOTOR.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(origen, MOTOR)
    (MOTOR / ".version").write_text(j["version"])
    return f"Motor listo ({j['version'][:7]}) en {MOTOR}"


def cmd_motor(args) -> int:
    print(bajar_motor("--forzar" in args))
    return 0


def cmd_preparar(_args) -> int:
    """Hook SessionStart: lo que imprime lo lee Claude al empezar la sesión."""
    if not codigo():
        print("SKIDUSH: falta el código del alumno. Pídeselo («pega aquí tu código de SKIDUSH») y guárdalo con "
              "`python3 skidush.py codigo <CODIGO>`. Después usa la skill skidush.")
        return 0
    try:
        j = pedir("acceso")
    except SinAcceso as e:
        print(f"SKIDUSH: sin acceso. Dile esto al alumno tal cual y no trabajes en nada más: «{e}»")
        return 0
    except RuntimeError as e:
        print(f"SKIDUSH: {e}")
        return 0
    try:
        bajar_motor()
        instalar = MOTOR / "instalar.sh"
        if instalar.exists():
            with open(LOG_INSTALAR, "w") as log:
                subprocess.Popen(["bash", str(instalar)], stdout=log, stderr=subprocess.STDOUT,
                                 cwd=str(MOTOR), start_new_session=True)
            motor_txt = f"motor listo; sus dependencias se instalan en segundo plano (log: {LOG_INSTALAR})"
        else:
            motor_txt = "motor listo"
    except Exception as e:  # el motor no impide escribir guiones
        motor_txt = f"no se pudo bajar el motor ({e}); guion y entrevista funcionan igual"
    nombre = f" de {j['alumno']}" if j.get("alumno") else ""
    print(f"SKIDUSH{nombre} activo hasta el {j.get('vence_texto')} · {motor_txt}. "
          "Para cualquier cosa usa las skills skidush-*; si es la primera vez, la skill skidush (bienvenida).")
    return 0


def cmd_m(args) -> int:
    if not args:
        print("Uso: python3 skidush.py m <comando> [...]")
        return 1
    pedir("uso", detalle=" ".join(args)[:200])
    if not (MOTOR / "skidush_motor").exists():
        bajar_motor()
    env = {**os.environ, "PYTHONPATH": f"{MOTOR}{os.pathsep}{os.environ.get('PYTHONPATH', '')}",
           "SKIDUSH_REPO": str(RAIZ)}
    return subprocess.call([sys.executable, "-m", "skidush_motor", *args], cwd=str(RAIZ), env=env)


COMANDOS = {
    "estado": cmd_estado, "codigo": cmd_codigo, "instrucciones": cmd_instrucciones, "contenido": cmd_contenido,
    "motor": cmd_motor, "preparar": cmd_preparar, "m": cmd_m,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMANDOS:
        print(__doc__)
        return 1
    if argv[0] not in ("codigo", "preparar") and not codigo():
        print("Falta tu código de SKIDUSH. Guárdalo con: python3 skidush.py codigo SKI-XXXX-XXXX")
        return SIN_ACCESO
    try:
        return COMANDOS[argv[0]](argv[1:])
    except SinAcceso as e:
        print(f"⛔ {e}")
        return SIN_ACCESO
    except RuntimeError as e:
        print(f"✘ {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
