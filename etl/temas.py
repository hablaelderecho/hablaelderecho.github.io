#!/usr/bin/env python3
"""Habla el Derecho · robot de temas.

Cada madrugada busca noticias jurídicas recientes de Colombia (Google News RSS)
por serie y deja bot/temas/AAAA-MM-DD.json con titular, fuente, enlace y fecha.
Marca como alerta de conflicto de interés lo que mencione a GECOLSA, Relianz,
Caterpillar, el sector minero-energético o clientes conocidos: eso no se vuelve
contenido, se le avisa a Juan Camilo.
No inventa: si una búsqueda falla, lo deja anotado y sigue.
"""
import datetime as dt, email.utils, json, os, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERIES = {
    "Fallo de la semana (constitucional)": ["Corte Constitucional sentencia", "Corte Constitucional tutela fallo"],
    "Cláusula trampa (comercial)": ["Superintendencia de Industria y Comercio sanción consumidor", "contrato cláusula abusiva Colombia", "Supersociedades"],
    "Aduana sin cuento (aduanero)": ["DIAN aduana importaciones", "DIAN compras internacionales", "aranceles Colombia decreto"],
    "El Estado te debe (administrativo)": ["Consejo de Estado fallo", "derecho de petición entidad", "silencio administrativo"],
    "Mito civil (civil)": ["Corte Suprema sala civil herencia", "arrendamiento ley inquilinos Colombia", "unión marital de hecho Corte"],
}
CONFLICTO = ["gecolsa", "relianz", "caterpillar", "cerro matoso", "cerrejón", "cerrejon", "minería", "mineria",
             "minero", "carbón", "carbon", "continental gold", "buriticá", "repsol", "slb", "schlumberger"]
DIAS = 4


def rss(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": f"{q} when:{DIAS}d", "hl": "es-419", "gl": "CO", "ceid": "CO:es-419"})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (hablaelderecho-bot)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raiz = ET.fromstring(r.read())
    for it in raiz.iter("item"):
        fecha = it.findtext("pubDate")
        try:
            fecha = email.utils.parsedate_to_datetime(fecha).date().isoformat()
        except Exception:
            pass
        fuente = it.find("source")
        yield {"titular": it.findtext("title"), "enlace": it.findtext("link"),
               "fuente": fuente.text if fuente is not None else "", "fecha": fecha}


def main():
    hoy = dt.date.today().isoformat()
    vistos, salida, alertas, errores = set(), {}, [], []
    for serie, consultas in SERIES.items():
        salida[serie] = []
        for q in consultas:
            try:
                for n in rss(q):
                    clave = (n["titular"] or "").lower()[:90]
                    if not clave or clave in vistos:
                        continue
                    vistos.add(clave)
                    if any(c in clave for c in CONFLICTO):
                        alertas.append({**n, "serie": serie, "motivo": "posible conflicto de interés"})
                        continue
                    salida[serie].append({**n, "consulta": q})
            except Exception as e:
                errores.append(f"{q}: {e}")
        salida[serie] = salida[serie][:12]
    os.makedirs(os.path.join(RAIZ, "bot", "temas"), exist_ok=True)
    doc = {"fecha": hoy, "dias": DIAS, "series": salida, "alertas_conflicto": alertas, "errores": errores}
    with open(os.path.join(RAIZ, "bot", "temas", f"{hoy}.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
    print(f"{hoy}: {sum(len(v) for v in salida.values())} noticias, {len(alertas)} alertas, {len(errores)} errores")


if __name__ == "__main__":
    main()
