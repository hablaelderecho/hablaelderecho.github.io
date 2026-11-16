#!/usr/bin/env python3
"""Habla el Derecho · carruseles de 1080x1350.

Lee una pieza de bot/piezas/<id>.json (tipo "carrusel") y deja las láminas en
redes/<id>/01.jpg, 02.jpg... (JPEG, que es lo que Instagram acepta por URL).

Uso: python video/render_carrusel.py bot/piezas/<id>.json
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(RAIZ, "video", "fonts")
W, H = 1080, 1350
INK = (15, 27, 45)
INK2 = (22, 37, 60)
IVORY = (244, 239, 230)
MUTED = (160, 170, 186)
LACRE = (214, 84, 64)


def f(nombre, s):
    return ImageFont.truetype(os.path.join(FUENTES, nombre), s)

SERIF = lambda s: f("Gloock-Regular.ttf", s)
SANS = lambda s: f("InstrumentSans-Regular.ttf", s)
SANSB = lambda s: f("InstrumentSans-Bold.ttf", s)


def envolver(d, texto, fuente, ancho):
    lineas, actual = [], ""
    for p in texto.split():
        prueba = (actual + " " + p).strip()
        if d.textlength(prueba, font=fuente) <= ancho:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
    if actual:
        lineas.append(actual)
    return lineas


def fondo():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 46):
        d.line([(0, y), (W, y)], fill=INK2, width=1)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((W - 120, H - 260), "§", font=SERIF(900), fill=(244, 239, 230, 12), anchor="mm")
    return Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")


def cabecera(d, serie, n, total):
    fu = SANSB(30)
    tw = d.textlength(serie, font=fu)
    d.rounded_rectangle([80, 80, 80 + tw + 48, 136], radius=28, fill=LACRE)
    d.text((80 + 24, 108), serie, font=fu, fill=IVORY, anchor="lm")
    d.text((W - 80, 108), f"{n}/{total}", font=SANS(30), fill=MUTED, anchor="rm")


def pie(d, cierre=False):
    d.text((80, H - 80), "@hablaelderecho", font=SANSB(30), fill=IVORY, anchor="lm")
    if cierre:
        d.text((W - 80, H - 80), "Información general, no asesoría", font=SANS(24), fill=MUTED, anchor="rm")


def bloque_texto(d, y, texto, fuente, color, ancho=W - 160, interlinea=1.32):
    for linea in envolver(d, texto, fuente, ancho):
        d.text((80, y), linea, font=fuente, fill=color)
        y += int(fuente.size * interlinea)
    return y


def lamina(pieza, i, lam, total):
    img = fondo()
    d = ImageDraw.Draw(img)
    cabecera(d, pieza["serie"], i + 1, total)
    if lam.get("portada"):
        fu = SERIF(92)
        lineas = envolver(d, lam["titulo"], fu, W - 160)
        alto = len(lineas) * int(92 * 1.15)
        y = (H - alto) // 2 - 80
        for linea in lineas:
            d.text((80, y), linea, font=fu, fill=IVORY)
            y += int(92 * 1.15)
        d.rectangle([80, y + 30, 200, y + 36], fill=LACRE)
        if lam.get("texto"):
            bloque_texto(d, y + 70, lam["texto"], SANS(44), IVORY)
        d.text((W - 80, H - 80), "Desliza  →", font=SANSB(30), fill=LACRE, anchor="rm")
        d.text((80, H - 80), "@hablaelderecho", font=SANSB(30), fill=IVORY, anchor="lm")
    else:
        fu, fc = SERIF(86), SANS(54)
        tit = envolver(d, lam["titulo"], fu, W - 160)
        cuerpo = len(envolver(d, lam.get("texto", ""), fc, W - 160)) if lam.get("texto") else 0
        alto = len(tit) * int(86 * 1.16) + 90 + cuerpo * int(54 * 1.32) + len(lam.get("lista", [])) * 96
        y = max(220, (H - alto) // 2 - 40)
        for linea in tit:
            d.text((80, y), linea, font=fu, fill=IVORY)
            y += int(86 * 1.16)
        d.rectangle([80, y + 24, 200, y + 30], fill=LACRE)
        y += 90
        if lam.get("texto"):
            y = bloque_texto(d, y, lam["texto"], fc, IVORY)
        for item in lam.get("lista", []):
            d.ellipse([80, y + 24, 100, y + 44], fill=LACRE)
            d.text((130, y), item, font=SANS(60), fill=IVORY)
            y += 96
        if lam.get("fuente"):
            fy = H - 190
            d.line([(80, fy - 24), (W - 80, fy - 24)], fill=INK2, width=2)
            bloque_texto(d, fy, "Fuente: " + lam["fuente"], SANS(28), MUTED)
        pie(d, cierre=lam.get("cierre", False))
    return img


def main():
    ruta = sys.argv[1]
    pieza = json.load(open(ruta, encoding="utf-8"))
    salida = os.path.join(RAIZ, "redes", pieza["id"])
    os.makedirs(salida, exist_ok=True)
    total = len(pieza["laminas"])
    for i, lam in enumerate(pieza["laminas"]):
        lamina(pieza, i, lam, total).save(os.path.join(salida, f"{i + 1:02d}.jpg"), quality=92)
    print(f"Listo: {total} láminas en redes/{pieza['id']}/")


if __name__ == "__main__":
    main()
