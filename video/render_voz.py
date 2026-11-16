#!/usr/bin/env python3
"""Habla el Derecho · reel de voz (sin avatar).

Lee una pieza de bot/piezas/<id>.json (tipo "reel"), genera la voz clonada de
Juan Camilo con ElevenLabs v4 (con marcas de tiempo) y arma un MP4 vertical
1080x1920 con la etiqueta de la serie, el titular, el texto grande sincronizado
con la voz (palabras clave en rojo lacre), la fuente al final y música debajo.

Sin ELEVENLABS_API_KEY usa audio en silencio y tiempos estimados (para probar el diseño).

Uso: python video/render_voz.py bot/piezas/<id>.json [salida.mp4]
"""
import base64, json, os, re, subprocess, sys, unicodedata, urllib.request
from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUENTES = os.path.join(RAIZ, "video", "fonts")
W, H, FPS = 1080, 1920, 30
INK, INK2 = (15, 27, 45), (22, 37, 60)
IVORY, MUTED, LACRE = (244, 239, 230), (160, 170, 186), (214, 84, 64)
ETIQUETA = re.compile(r"\[[^\]]*\]")
VOCES = json.load(open(os.path.join(RAIZ, "video", "voces.json"), encoding="utf-8"))
VOZ = VOCES["principal"]["voice_id"]
PRONUNCIACION = VOCES.get("pronunciacion", {})


def f(nombre, s): return ImageFont.truetype(os.path.join(FUENTES, nombre), s)
SERIF = lambda s: f("Gloock-Regular.ttf", s)
SANS = lambda s: f("InstrumentSans-Regular.ttf", s)
SANSB = lambda s: f("InstrumentSans-Bold.ttf", s)


# ---------- texto ----------
def escrito(t):
    return re.sub(r"\s+", " ", ETIQUETA.sub("", t)).strip()

def hablado(t):
    for k, v in PRONUNCIACION.items():
        t = re.sub(rf"(?<!\w){re.escape(k)}(?!\w)", v, t)
    return t

def _norm(w):
    w = unicodedata.normalize("NFD", w.lower())
    return re.sub(r"[^a-z0-9%]", "", "".join(c for c in w if unicodedata.category(c) != "Mn"))


# ---------- voz ----------
def tts(texto, salida_mp3):
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        return None
    body = {"text": hablado(texto), "model_id": VOCES["principal"].get("modelo", "eleven_v4")}
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOZ}/with-timestamps?output_format=mp3_44100_128",
        data=json.dumps(body).encode(), method="POST",
        headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=240) as r:
        j = json.load(r)
    al = j.get("alignment") or j.get("normalized_alignment")
    with open(salida_mp3, "wb") as fh:
        fh.write(base64.b64decode(j["audio_base64"]))
    return al

def duracion(ruta):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", ruta], capture_output=True, text=True).stdout
    return float(out.strip())

def tiempos_palabras(palabras, al, total):
    n = len(palabras)
    res = [None] * n
    if al:
        chars, ini, fin = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
        aw, cur, t0, t1, dentro = [], "", None, None, 0
        for c, a, b in zip(chars, ini, fin):
            if c == "[":
                dentro += 1
            if dentro:
                if c == "]":
                    dentro -= 1
                continue
            if c.isspace():
                if cur:
                    aw.append((_norm(cur), t0, t1)); cur = ""
            else:
                if not cur:
                    t0 = a
                cur += c; t1 = b
        if cur:
            aw.append((_norm(cur), t0, t1))
        j = 0
        for i, w in enumerate(palabras):
            nw = _norm(w)
            if not nw:
                continue
            for k in range(j, min(j + 6, len(aw))):
                if aw[k][0] == nw or aw[k][0].startswith(nw) or (aw[k][0] and nw.startswith(aw[k][0])):
                    res[i] = (aw[k][1], aw[k][2]); j = k + 1
                    break
    if not any(res):
        pesos = [len(w) + (6 if w[-1:] in ".:?" else 3 if w[-1:] == "," else 1) for w in palabras]
        k = (total - 0.3) / sum(pesos); t = 0.15
        for i, p in enumerate(pesos):
            res[i] = (t, t + p * k * 0.9); t += p * k
        return res
    for i in range(n):
        if res[i] is None:
            prev = next((res[k][1] for k in range(i - 1, -1, -1) if res[k]), 0.0)
            nxt = next((res[k][0] for k in range(i + 1, n) if res[k]), total)
            res[i] = (prev, max(prev + 0.15, (prev + nxt) / 2))
    return res


# ---------- dibujo ----------
def fondo(pieza):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    for y in range(0, H, 46):
        d.line([(0, y), (W, y)], fill=INK2, width=1)
    capa = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(capa).text((W - 140, H - 420), "§", font=SERIF(1100), fill=(244, 239, 230, 12), anchor="mm")
    img = Image.alpha_composite(img.convert("RGBA"), capa).convert("RGB")
    d = ImageDraw.Draw(img)
    fu = SANSB(34)
    tw = d.textlength(pieza["serie"], font=fu)
    d.rounded_rectangle([(W - tw) / 2 - 28, 170, (W + tw) / 2 + 28, 234], radius=32, fill=LACRE)
    d.text((W / 2, 202), pieza["serie"], font=fu, fill=IVORY, anchor="mm")
    ft = SERIF(84)
    y = 290
    for linea in pieza["titular"]:
        d.text((W / 2, y), linea, font=ft, fill=IVORY, anchor="mt")
        y += 104
    d.rectangle([W / 2 - 60, y + 26, W / 2 + 60, y + 32], fill=LACRE)
    d.text((W / 2, H - 150), "@hablaelderecho", font=SANSB(34), fill=IVORY, anchor="mm")
    d.text((W / 2, H - 100), "Voz generada con IA", font=SANS(26), fill=MUTED, anchor="mm")
    return img

def ease(p):
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3

def bloque(img, palabras, t, clave):
    """Texto grande centrado: el bloque que suena ahora, con entrada suave."""
    d = ImageDraw.Draw(img)
    fu = SANSB(96)
    lineas, actual = [], []
    for p in palabras:
        prueba = " ".join(x[0] for x in actual + [p])
        if actual and d.textlength(prueba, font=fu) > W - 160:
            lineas.append(actual); actual = [p]
        else:
            actual.append(p)
    if actual:
        lineas.append(actual)
    a = ease((t - palabras[0][1] + 0.05) / 0.25)
    dy = int(30 * (1 - a))
    y = 1000 - len(lineas) * 62 + dy
    for linea in lineas:
        ancho = d.textlength(" ".join(x[0] for x in linea), font=fu)
        x = (W - ancho) / 2
        for w, a0, a1 in linea:
            limpio = re.sub(r"[^\wáéíóúñü%$-]", "", w.lower())
            base = LACRE if limpio and any(limpio.startswith(c) for c in clave) else IVORY
            col = base if t >= a0 - 0.05 else tuple(int(c * 0.45 + k * 0.55) for c, k in zip(base, INK))
            col = tuple(int(k + (c - k) * a) for c, k in zip(col, INK))
            d.text((x, y), w, font=fu, fill=col)
            x += d.textlength(w + " ", font=fu)
        y += 124

def fuente_final(img, texto, a):
    d = ImageDraw.Draw(img)
    col = tuple(int(k + (c - k) * a) for c, k in zip(MUTED, INK))
    d.text((W / 2, H - 260), texto, font=SANS(30), fill=col, anchor="mm")


# ---------- música ----------
def musica(perfil, total):
    import datetime as dt, glob
    pistas = sorted(glob.glob(os.path.join(RAIZ, "video", "musica", perfil, "*.mp3")))
    if not pistas:
        return None, 0.0
    pista = pistas[dt.date.today().timetuple().tm_yday % len(pistas)]
    ofs = 0.0
    try:
        cat = json.load(open(os.path.join(RAIZ, "video", "musica", "catalogo.json"), encoding="utf-8"))
        info = next(c for c in cat if c["archivo"].endswith(os.path.basename(pista)))
        ofs = max(info.get("entrada", 0), min(info.get("climax", 0) - total, duracion(pista) - total - 1))
        previos = [b for b in info.get("compases", []) if b <= ofs + 0.05]
        ofs = previos[-1] if previos else ofs
    except Exception:
        pass
    return pista, max(0.0, ofs)


# ---------- principal ----------
def main():
    pieza = json.load(open(sys.argv[1], encoding="utf-8"))
    salida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, "redes", pieza["id"], "reel.mp4")
    tmp = os.path.join(RAIZ, "video", "salida", pieza["id"])
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(os.path.dirname(salida), exist_ok=True)

    mp3 = os.path.join(tmp, "voz.mp3")
    al = tts(pieza["guion"], mp3)
    if al is None:
        est = len(escrito(pieza["guion"])) / 15.0
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                        "-t", f"{est:.2f}", mp3], check=True)
        print("Sin ELEVENLABS_API_KEY: audio en silencio y tiempos estimados")
    # La voz se procesa aparte: corta graves de golpe, nivela a -14 LUFS y limita picos.
    voz = os.path.join(tmp, "voz.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-af",
                    VOCES["principal"].get("procesado", "highpass=f=80,loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.89")
                    + ",aresample=48000", "-ac", "2", voz], check=True)
    dur_voz = duracion(voz)
    total = dur_voz + 1.2

    palabras = escrito(pieza["guion"]).split()
    tw = tiempos_palabras(palabras, al, dur_voz)
    bloques, actual = [], []
    for w, (a, b) in zip(palabras, tw):
        actual.append((w, a, b))
        if len(actual) >= 4 or w[-1] in ".,:?":
            bloques.append(actual); actual = []
    if actual:
        bloques.append(actual)
    clave = {re.sub(r"[^\wáéíóúñü%$-]", "", c.lower()) for c in pieza.get("clave", [])}

    pista, ofs = musica(pieza.get("musica", "institucional"), total)
    mezcla = os.path.join(tmp, "mezcla.wav")
    if pista:
        mus = os.path.join(tmp, "mus.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ofs:.2f}", "-t", f"{total:.2f}", "-i", pista,
                        "-af", f"aresample=48000,volume=0.22,afade=t=in:d=0.8,afade=t=out:st={total - 1.2:.2f}:d=1.2",
                        "-ac", "2", mus], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voz, "-i", mus, "-filter_complex",
                        "[0:a]apad=whole_dur=" + f"{total:.2f}" + ",asplit=2[v][sc];"
                        "[1:a][sc]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[m];"
                        "[v][m]amix=inputs=2:normalize=0:duration=longest[a]",
                        "-map", "[a]", "-t", f"{total:.2f}", mezcla], check=True)
        print(f"Música: {os.path.basename(pista)} desde el segundo {ofs:.1f}")
    else:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", voz, "-af", f"apad=whole_dur={total:.2f}", mezcla], check=True)

    base = fondo(pieza)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", mezcla, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", salida]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    inicio_fuente = max(0.0, dur_voz - 4.0)
    for fr in range(int(total * FPS)):
        t = fr / FPS
        img = base.copy()
        activo = None
        for bl in bloques:
            if bl[0][1] - 0.08 <= t:
                activo = bl
        if activo:
            bloque(img, activo, t, clave)
        if pieza.get("fuente") and t >= inicio_fuente:
            fuente_final(img, pieza["fuente"], ease((t - inicio_fuente) / 0.5))
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    print(f"Listo: {os.path.relpath(salida, RAIZ)} ({total:.1f} s)")


if __name__ == "__main__":
    main()
