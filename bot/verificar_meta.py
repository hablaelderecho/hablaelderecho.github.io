"""Prueba la conexión con Meta sin publicar nada.

Lee META_TOKEN del entorno y muestra el usuario del sistema, sus permisos,
la página de Facebook y la cuenta de Instagram que puede administrar.
Nunca imprime el token.
"""
import json
import os
import sys
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com"
TOKEN = os.environ.get("META_TOKEN", "").strip()

NECESARIOS = {
    "pages_show_list", "pages_read_engagement", "pages_manage_posts",
    "business_management", "read_insights", "instagram_basic",
    "instagram_content_publish", "instagram_manage_insights",
}


def get(path, **params):
    params["access_token"] = TOKEN
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        cuerpo = json.load(e)
        print(f"Error en {path}: {cuerpo.get('error', {}).get('message', cuerpo)}")
        sys.exit(1)


if not TOKEN:
    print("Falta el secreto META_TOKEN.")
    sys.exit(1)

yo = get("me", fields="id,name")
print(f"Usuario del sistema: {yo.get('name')} ({yo.get('id')})")

permisos = get("me/permissions").get("data", [])
concedidos = {p["permission"] for p in permisos if p.get("status") == "granted"}
faltan = sorted(NECESARIOS - concedidos)
print("Permisos concedidos:", ", ".join(sorted(concedidos)) or "ninguno")
print("Permisos que faltan:", ", ".join(faltan) if faltan else "ninguno")

paginas = get("me/accounts", fields="id,name,instagram_business_account{id,username}").get("data", [])
if not paginas:
    print("No hay páginas asignadas al usuario del sistema.")
    sys.exit(1)
for p in paginas:
    ig = p.get("instagram_business_account")
    ig_txt = f"@{ig.get('username')} ({ig.get('id')})" if ig else "sin Instagram conectado"
    print(f"Página: {p.get('name')} ({p.get('id')}) -> Instagram: {ig_txt}")

if faltan or not any(p.get("instagram_business_account") for p in paginas):
    sys.exit(1)
print("Conexión con Meta: OK")
