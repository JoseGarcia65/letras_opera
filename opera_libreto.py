#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
opera_libretto.py — Extrae el texto de un aria para foobar2000 (foo_run)
Uso: python opera_libretto.py "%artist%" "%title%" "%path%"
"""

import sys, os, re, time, urllib.parse, urllib.request, traceback

# Verificar que mutagen está instalado
try:
    from mutagen.flac import FLAC
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, USLT, Encoding, TXXX
    from mutagen.oggvorbis import OggVorbis
    MUTAGEN_AVAILABLE = True
except ImportError as e:
    MUTAGEN_AVAILABLE = False
    MUTAGEN_ERROR = str(e)

# Log en el Escritorio
LOG_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "opera_log.txt")

def log(msg):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg, file=sys.stderr)

log("="*60)
log(f"[DIAG] mutagen disponible: {MUTAGEN_AVAILABLE}")
if not MUTAGEN_AVAILABLE:
    log(f"[DIAG] Error: {MUTAGEN_ERROR}")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# ──────────────────────────────────────────────
# Utilidades (sin cambios)
# ──────────────────────────────────────────────

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            enc = r.headers.get_content_charset("utf-8")
            return raw.decode(enc, errors="replace")
    except Exception as e:
        log(f"[DEBUG] fetch error: {type(e).__name__}: {e} → {url}")
        return ""

def strip_tags(html):
    html = re.sub(r"<br\s*/?>",  "\n", html, flags=re.I)
    html = re.sub(r"<p[^>]*>",   "\n", html, flags=re.I)
    html = re.sub(r"<[^>]+>",    "",   html)
    for ent, rep in [("&nbsp;"," "),("&amp;","&"),("&lt;","<"),("&gt;",">"),
                     ("&quot;",'"'),("&#039;","'"),("&auml;","ä"),("&ouml;","ö"),
                     ("&uuml;","ü"),("&szlig;","ß"),("&agrave;","à"),("&egrave;","è"),
                     ("&#8217;","'"),("&#8220;",'"'),("&#8221;",'"')]:
        html = html.replace(ent, rep)
    return re.sub(r"\n{3,}", "\n\n", html).strip()

def slugify_composer(name):
    name = name.lower().strip().replace(".", "")
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return f"{parts[0]}-{parts[1]}"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[-1]}-{parts[0][0]}"
    return parts[0]

def slugify_opera(name):
    # Primero normalizar apóstrofos: L'amico → lamico, L'elisir → lelisir
    name = re.sub(r"\b(\w)'(\w)", r"\1\2", name)  # contrae apóstrofo interno
    name = name.lower()
    for a, b in [("ä","a"),("ö","o"),("ü","u"),("ß","ss"),("à","a"),("á","a"),
                 ("â","a"),("è","e"),("é","e"),("ê","e"),("ì","i"),("í","i"),
                 ("ò","o"),("ó","o"),("ù","u"),("ú","u"),("ñ","n"),("ç","c"),
                 ("'",""),("'",""),("'","")]:
        name = name.replace(a, b)
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    return re.sub(r"\s+", "-", name.strip())
# ──────────────────────────────────────────────
# Aliases de compositores (sin cambios)
# ──────────────────────────────────────────────

COMPOSER_ALIASES = {
    "strauss, r":      ("Richard Strauss",           "strauss-r"),
    "strauss, r.":     ("Richard Strauss",           "strauss-r"),
    "strauss, j":      ("Johann Strauss",            "strauss-j"),
    "bach, j.s.":      ("Johann Sebastian Bach",     "bach-js"),
    "bach, js":        ("Johann Sebastian Bach",     "bach-js"),
    "mozart, w.a.":    ("Wolfgang Amadeus Mozart",   "mozart"),
    "mozart, wa":      ("Wolfgang Amadeus Mozart",   "mozart"),
    "handel":          ("Georg Friedrich Handel",    "handel"),
    "händel":          ("Georg Friedrich Handel",    "handel"),
    "verdi":           ("Giuseppe Verdi",            "verdi"),
    "puccini":         ("Giacomo Puccini",           "puccini"),
    "rossini":         ("Gioachino Rossini",         "rossini"),
    "donizetti":       ("Gaetano Donizetti",         "donizetti"),
    "bellini":         ("Vincenzo Bellini",          "bellini"),
    "wagner":          ("Richard Wagner",            "wagner"),
    "bizet":           ("Georges Bizet",             "bizet"),
    "tchaikovsky":     ("Pyotr Ilyich Tchaikovsky",  "tchaikovsky"),
    "monteverdi":      ("Claudio Monteverdi",        "monteverdi"),
    "vivaldi":         ("Antonio Vivaldi",           "vivaldi"),
    "gluck":           ("Christoph Willibald Gluck", "gluck"),
    "haydn":           ("Joseph Haydn",              "haydn"),
    "beethoven":       ("Ludwig van Beethoven",      "beethoven"),
    "schubert":        ("Franz Schubert",            "schubert"),
    "janacek":         ("Leos Janacek",              "janacek"),
    "janáček":         ("Leos Janacek",              "janacek"),
    "bartok":          ("Bela Bartok",               "bartok"),
    "britten":         ("Benjamin Britten",          "britten"),
    "berg":            ("Alban Berg",                "berg"),
    "leoncavallo":     ("Ruggero Leoncavallo",       "leoncavallo"),
    "mascagni":        ("Pietro Mascagni",           "mascagni"),
    "gounod":          ("Charles Gounod",            "gounod"),
    "massenet":        ("Jules Massenet",            "massenet"),
    "mussorgsky":      ("Modest Mussorgsky",         "mussorgsky"),
    "dvorak":          ("Antonin Dvorak",            "dvorak"),
    "dvořák":          ("Antonin Dvorak",            "dvorak"),
    "smetana":         ("Bedrich Smetana",           "smetana"),
    "offenbach":       ("Jacques Offenbach",         "offenbach"),
    "saint-saens":     ("Camille Saint-Saens",       "saint-saens"),
    "rimsky-korsakov": ("Nikolai Rimsky-Korsakov",   "rimsky-korsakov"),
    "cilea":           ("Francesco Cilea",           "cilea"),
    "giordano":        ("Umberto Giordano",          "giordano"),
    "ponchielli":      ("Amilcare Ponchielli",       "ponchielli"),
}

# ──────────────────────────────────────────────
# Parser del título de foobar2000 (sin cambios)
# ──────────────────────────────────────────────

def parse_title(artist_tag, title_tag):
    info = {
        "composer": "", "composer_slug": "",
        "opera": "",    "opera_slug": "",
        "act": "",      "aria_text": "",  "character": ""
    }
    t = title_tag.strip()
    log(f"[DEBUG] Título raw repr: {repr(t)}")

    # 1. Personaje al final entre paréntesis
    m = re.search(r'\(([^)]+)\)\s*$', t)
    if m:
        info["character"] = m.group(1).strip()
        t = t[:m.start()].strip()
        log(f"[DEBUG] Personaje: {info['character']}")

    # 2. Texto del aria
    m = re.search(r'[\u201c\u201e\u00ab\u2018](.+?)[\u201d\u00bb\u2019]', t, re.DOTALL)
    if not m:
        m = re.search(r'"([^"]+)"', t)
    if m:
        info["aria_text"] = m.group(1).strip()
        t = t[:m.start()].strip().rstrip(":").strip()
        log(f"[DEBUG] Aria: {info['aria_text'][:70]}")

    # 3. Acto
    m = re.search(r'\b(act|akt|acte|atto|scene|szene|scena)\s*([\divxlc]+)\b', t, re.I)
    if m:
        info["act"] = m.group(0).strip()
        t = t[:m.start()].strip().rstrip(",").strip()

    # 4. Eliminar catálogos
    t = re.sub(
        r',?\s*\b(?:op|opus|trv|hwv|bwv|k|kv|rv|hob|d|wab|sz|bb)\b\.?\s*'
        r'[\divxlc]+(?:\s*/\s*[\divxlc]+)?',
        '', t, flags=re.I
    ).strip()

    # 5. Separar compositor y ópera
    m = re.search(r'^(.+?):\s*(.+)$', t)
    if m:
        cand_comp  = m.group(1).strip()
        cand_opera = m.group(2).strip(" ,")
        if re.search(r',|^[A-ZÁÉÍÓÚÄÖÜ][a-záéíóúäöüß]+$', cand_comp):
            key = cand_comp.lower().rstrip(". ")
            if key in COMPOSER_ALIASES:
                info["composer"], info["composer_slug"] = COMPOSER_ALIASES[key]
            else:
                info["composer"]      = cand_comp
                info["composer_slug"] = slugify_composer(cand_comp)
            info["opera"] = cand_opera
        else:
            info["opera"] = t.strip(" ,:")
    else:
        info["opera"] = t.strip(" ,:")

    # 6. Si no hay compositor, usar artist_tag
    if not info["composer"]:
        key = artist_tag.strip().lower().rstrip(". ")
        if key in COMPOSER_ALIASES:
            info["composer"], info["composer_slug"] = COMPOSER_ALIASES[key]
        else:
            info["composer"]      = artist_tag.strip()
            info["composer_slug"] = slugify_composer(artist_tag.strip())

    info["opera"]      = re.sub(r'\s{2,}', ' ', info["opera"]).strip(" ,:")
    info["opera_slug"] = slugify_opera(info["opera"])

    log(f"[INFO] Compositor : {info['composer']}")
    log(f"[INFO] Ópera      : {info['opera']}")
    log(f"[INFO] Aria       : {info['aria_text']}")
    return info

# ──────────────────────────────────────────────
# Extractor del aria (sin cambios)
# ──────────────────────────────────────────────

def normalize(s):
    s = re.sub(r'[^\w\s]', ' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()

def extract_aria(full_text, aria_start, character=""):
    if not aria_start or not full_text:
        return full_text

    anchor_words = normalize(aria_start).split()
    lines = full_text.split('\n')
    start_idx = None

    for n in [min(6, len(anchor_words)), 4, 3, 2]:
        if n > len(anchor_words):
            continue
        pat = r'\s+'.join(re.escape(w) for w in anchor_words[:n])
        for i, line in enumerate(lines):
            if re.search(pat, normalize(line), re.I):
                start_idx = i
                break
        if start_idx is not None:
            break

    if start_idx is None:
        log("[DEBUG] Comienzo del aria no encontrado")
        return full_text

    log(f"[DEBUG] Aria localizada en línea {start_idx}: {lines[start_idx][:80]}")

    extracted = []
    for i, line in enumerate(lines[start_idx:], start=start_idx):
        s = line.strip()
        if i > start_idx + 2 and len(extracted) > 4:
            if s and s == s.upper() and 2 < len(s) < 40:
                break
            if re.match(r'^\s*(act|akt|acte|atto|scene|szene|scena)\b', s, re.I):
                break
        extracted.append(line)

    return '\n'.join(extracted).strip()

# ──────────────────────────────────────────────
# Fuentes de libretos (sin cambios)
# ──────────────────────────────────────────────

def search_opera_arias(composer_slug, opera_slug):
    url = f"https://www.opera-arias.com/{composer_slug}/{opera_slug}/libretto/"
    log(f"[DEBUG] opera-arias.com → {url}")
    html = fetch(url)
    if not html or len(html) < 500:
        return ""

    html_clean = re.sub(r'<(nav|header|footer|script|style)[^>]*>.*?</\1>',
                        '', html, flags=re.DOTALL | re.I)

    for pat in [
        r'<div[^>]*class="[^"]*libretto[^"]*"[^>]*>(.*?)</div\s*>',
        r'<article[^>]*>(.*?)</article>',
        r'<div[^>]*id="content"[^>]*>(.*?)</div\s*>',
    ]:
        m = re.search(pat, html_clean, re.DOTALL | re.I)
        if m:
            text = strip_tags(m.group(1))
            if len(text) > 500:
                log(f"[DEBUG] opera-arias.com ✓ {len(text)} chars")
                return text

    body = re.search(r"<body[^>]*>(.*?)</body>", html_clean, re.DOTALL | re.I)
    if body:
        text = strip_tags(body.group(1))
        lines = [l for l in text.split('\n') if len(l.strip()) > 20]
        text = '\n'.join(lines)
        if len(text) > 500:
            log(f"[DEBUG] opera-arias.com fallback ✓")
            return text
    return ""

def search_opera_arias_variants(composer_slug, opera_slug):
    variants = [
        re.sub(r'^(il|la|le|les|der|die|das|gli|l)-', '', opera_slug),
        opera_slug.split("-")[0],
        opera_slug.replace("-", ""),
        # Variante específica para títulos con apóstrofo: l'amico → lamico
        re.sub(r"^l-", "l", opera_slug),
    ]
    # Eliminar duplicados manteniendo orden
    seen = set()
    variants = [v for v in variants if v not in seen and not seen.add(v)]
    
    for v in variants:
        if v == opera_slug:
            continue
        url = f"https://www.opera-arias.com/{composer_slug}/{v}/libretto/"
        log(f"[DEBUG] opera-arias variante → {url}")
        html = fetch(url)
        if html and len(html) > 1000 and "libretto" in html.lower():
            html_clean = re.sub(r'<(nav|header|footer|script|style)[^>]*>.*?</\1>',
                                '', html, flags=re.DOTALL | re.I)
            text = strip_tags(html_clean)
            lines = [l for l in text.split('\n') if len(l.strip()) > 20]
            text = '\n'.join(lines)
            if len(text) > 500:
                log(f"[DEBUG] opera-arias variante ✓")
                return text
        time.sleep(0.3)
    return ""

def search_stanford(opera, opera_slug):
    slugs = [opera_slug, opera_slug.replace("-", "_"),
             slugify_opera(opera.split(",")[0])]
    for slug in set(slugs):
        for sep in ["-", "_"]:
            s = slug.replace("-", sep)
            url = f"http://opera.stanford.edu/opera/{s}.html"
            log(f"[DEBUG] Stanford → {url}")
            html = fetch(url)
            if not html or len(html) < 500:
                continue
            m = re.search(r"<pre[^>]*>(.*?)</pre>", html, re.DOTALL | re.I)
            if m:
                t = strip_tags(m.group(1))
                if len(t) > 300:
                    return t
            body = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.I)
            if body:
                t = strip_tags(body.group(1))
                if len(t) > 300:
                    return t
    return ""

def search_librettidopera(composer, opera):
    query = urllib.parse.quote_plus(f"{opera} {composer}")
    html  = fetch(f"https://www.librettidopera.it/ricerca.php?cerca={query}")
    if not html:
        return ""
    first_word = opera.split()[0].lower()
    link = (re.search(rf'href="(/[^"]+\.php[^"]*)"[^>]*>[^<]*{re.escape(first_word)}',
                      html, re.I)
            or re.search(r'href="(/zplet/[^"]+\.php[^"]*)"', html, re.I))
    if not link:
        return ""
    page_url = "https://www.librettidopera.it" + link.group(1)
    log(f"[DEBUG] librettidopera.it → {page_url}")
    page = fetch(page_url)
    if not page:
        return ""
    for pat in [r'<div[^>]*id="testo"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*testo[^"]*"[^>]*>(.*?)</div>',
                r'<pre[^>]*>(.*?)</pre>']:
        m = re.search(pat, page, re.DOTALL | re.I)
        if m:
            t = strip_tags(m.group(1))
            if len(t) > 200:
                return t
    return ""

def buscar_libreto(info):
    cs    = info["composer_slug"]
    os_   = info["opera_slug"]
    comp  = info["composer"]
    opera = info["opera"]

    fuentes = [
        ("opera-arias.com",           lambda: search_opera_arias(cs, os_)),
        ("opera-arias.com variantes", lambda: search_opera_arias_variants(cs, os_)),
        ("Stanford",                  lambda: search_stanford(opera, os_)),
        ("librettidopera.it",         lambda: search_librettidopera(comp, opera)),
    ]
    for nombre, fn in fuentes:
        log(f"\n[opera_libretto] → {nombre}")
        try:
            r = fn()
            if r and len(r) > 150:
                log(f"[DEBUG] ✓ Libreto encontrado en {nombre}")
                return r
        except Exception as e:
            log(f"[DEBUG] Error {nombre}: {e}")
        time.sleep(0.4)
    return ""

# ──────────────────────────────────────────────
# NUEVO: Leer FILE_PATH del tag del archivo
# ──────────────────────────────────────────────

def get_file_path_from_audio_tags(audio_file):
    """
    Lee el tag FILE_PATH (o variantes) de un archivo de audio.
    Este tag contiene la ruta real del archivo en el sistema.
    """
    log(f"\n[DIAG] === LEYENDO FILE_PATH TAG ===")
    log(f"[DIAG] Archivo: {audio_file}")
    
    if not os.path.exists(audio_file):
        log(f"[DIAG] El archivo no existe: {audio_file}")
        return None
    
    try:
        ext = os.path.splitext(audio_file)[1].lower()
        
        # Posibles nombres del tag que contiene la ruta
        path_tag_names = [
            'file_path', 'filepath', 'path', 
            'FILE_PATH', 'FILEPATH', 'PATH',
            'File Path', 'File path', 'file path',
            'filename', 'FILENAME', 'file_name', 'FILE_NAME'
        ]
        
        if ext == '.flac':
            audio = FLAC(audio_file)
            log(f"[DIAG] Tags FLAC encontrados: {list(audio.keys())}")
            
            # Buscar el tag que contiene la ruta
            for tag_name in path_tag_names:
                if tag_name in audio:
                    path = audio[tag_name][0]
                    log(f"[DIAG] Tag '{tag_name}' encontrado: {path}")
                    if os.path.exists(path):
                        log(f"[DIAG] ✓ Ruta válida desde tag '{tag_name}': {path}")
                        return path
                    else:
                        log(f"[DIAG] ⚠️ Ruta en tag '{tag_name}' no existe: {path}")
            
            # Si no encontramos un tag específico, mostrar todos los tags para debug
            log("[DIAG] No se encontró tag de ruta. Mostrando todos los tags:")
            for key, value in audio.items():
                log(f"[DIAG]   {key}: {value}")
        
        elif ext == '.mp3':
            try:
                audio = ID3(audio_file)
            except:
                log("[DIAG] No se pudieron leer tags ID3")
                return None
            
            log(f"[DIAG] Tags ID3 encontrados: {list(audio.keys())}")
            
            # Buscar en TXXX (tags personalizados)
            for key in audio.keys():
                if key.startswith('TXXX:'):
                    txxx = audio[key]
                    desc = str(txxx.desc).lower() if hasattr(txxx, 'desc') else ''
                    log(f"[DIAG] TXXX encontrado: desc='{desc}', text='{txxx.text}'")
                    
                    for tag_name in path_tag_names:
                        if tag_name.lower() in desc:
                            path = str(txxx.text[0])
                            log(f"[DIAG] Tag '{desc}' encontrado: {path}")
                            if os.path.exists(path):
                                log(f"[DIAG] ✓ Ruta válida desde tag personalizado: {path}")
                                return path
                            else:
                                log(f"[DIAG] ⚠️ Ruta en tag personalizado no existe: {path}")
        
        elif ext == '.ogg':
            audio = OggVorbis(audio_file)
            log(f"[DIAG] Tags OGG encontrados: {list(audio.keys())}")
            
            for tag_name in path_tag_names:
                if tag_name in audio:
                    path = audio[tag_name][0]
                    log(f"[DIAG] Tag '{tag_name}' encontrado: {path}")
                    if os.path.exists(path):
                        log(f"[DIAG] ✓ Ruta válida desde tag '{tag_name}': {path}")
                        return path
                    else:
                        log(f"[DIAG] ⚠️ Ruta en tag '{tag_name}' no existe: {path}")
        
        log("[DIAG] No se encontró tag FILE_PATH en el archivo")
        
    except Exception as e:
        log(f"[DIAG] Error leyendo tags: {type(e).__name__}: {e}")
        log(traceback.format_exc())
    
    return None

def find_audio_with_file_path_tag(artist_tag, title_tag):
    """
    Busca el archivo de audio que coincida con artist/title
    y que tenga un tag FILE_PATH válido.
    """
    log(f"\n[DIAG] === BUSCANDO ARCHIVO CON FILE_PATH TAG ===")
    log(f"[DIAG] Artista: {artist_tag}")
    log(f"[DIAG] Título: {title_tag}")
    
    # Primero, obtener la ruta real del archivo que foobar2000 está reproduciendo
    # Podemos usar el hecho de que foobar2000 pasó artist y title
    
    # Buscar en ubicaciones comunes
    search_paths = [
        os.path.join(os.path.expanduser("~"), "Music"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        "C:\\Music", "D:\\Music", "E:\\Music",
    ]
    
    audio_extensions = ('.flac', '.mp3', '.ogg', '.m4a', '.wma', '.ape', '.wv')
    
    for search_path in search_paths:
        if not os.path.exists(search_path):
            continue
        
        log(f"[DIAG] Buscando en: {search_path}")
        
        for root, dirs, files in os.walk(search_path):
            depth = root[len(search_path):].count(os.sep)
            if depth > 3:
                continue
            
            for filename in files:
                if filename.lower().endswith(audio_extensions):
                    filepath = os.path.join(root, filename)
                    
                    # Verificar si los tags coinciden
                    try:
                        if verify_and_get_path_tag(filepath, artist_tag, title_tag):
                            return filepath
                    except:
                        continue
    
    return None

def verify_and_get_path_tag(filepath, expected_artist, expected_title):
    """Verifica que el archivo coincida con los tags esperados"""
    try:
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == '.flac':
            audio = FLAC(filepath)
            artist = audio.get('artist', [''])[0].lower()
            title = audio.get('title', [''])[0].lower()
        elif ext == '.mp3':
            try:
                audio = ID3(filepath)
            except:
                return False
            artist = str(audio.get('TPE1', '')).lower()
            title = str(audio.get('TIT2', '')).lower()
        elif ext == '.ogg':
            audio = OggVorbis(filepath)
            artist = audio.get('artist', [''])[0].lower()
            title = audio.get('title', [''])[0].lower()
        else:
            return False
        
        artist_match = expected_artist.lower() in artist or artist in expected_artist.lower()
        title_match = expected_title.lower() in title or title in expected_title.lower()
        
        return artist_match and title_match
        
    except:
        return False

# ──────────────────────────────────────────────
# Escribir en tags
# ──────────────────────────────────────────────

def escribir_tags(audio_path, texto, info):
    """Escribe el texto del aria en los metadatos del archivo de audio"""
    
    log(f"\n[DIAG] === ESCRIBIENDO TAGS ===")
    log(f"[DIAG] Ruta: {audio_path}")
    
    if not os.path.exists(audio_path):
        log(f"[ERROR] Archivo no encontrado: {audio_path}")
        return False
    
    ext = os.path.splitext(audio_path)[1].lower()
    
    metadata = f"""Compositor: {info.get('composer', '')}
Ópera: {info.get('opera', '')}
Acto: {info.get('act', '')}
Personaje: {info.get('character', '')}
Aria: {info.get('aria_text', '')}
{'=' * 60}

{texto}"""
    
    if not MUTAGEN_AVAILABLE:
        log(f"[ERROR] mutagen no instalado")
        return False
    
    try:
        if ext == '.flac':
            audio = FLAC(audio_path)
            audio['lyrics'] = metadata
            if info.get('composer'):
                audio['composer'] = info['composer']
            if info.get('opera'):
                audio['album'] = info['opera']
            # Guardar también la ruta real del archivo
            audio['file_path'] = audio_path
            audio.save()
            log("[INFO] ✅ Tags FLAC guardados (incluyendo file_path)")
            return True
            
        elif ext == '.mp3':
            try:
                audio = ID3(audio_path)
            except:
                audio = ID3()
            
            uslt = USLT(encoding=Encoding.UTF8, lang='eng', desc='Libretto', text=metadata)
            
            for key in list(audio.keys()):
                if key.startswith('USLT'):
                    del audio[key]
            
            audio['USLT::eng'] = uslt
            audio.save(audio_path)
            log("[INFO] ✅ Tags MP3 guardados")
            return True
            
        elif ext == '.ogg':
            audio = OggVorbis(audio_path)
            audio['lyrics'] = metadata
            if info.get('composer'):
                audio['composer'] = info['composer']
            if info.get('opera'):
                audio['album'] = info['opera']
            audio['file_path'] = audio_path
            audio.save()
            log("[INFO] ✅ Tags OGG guardados (incluyendo file_path)")
            return True
        
        return False
        
    except Exception as e:
        log(f"[ERROR] Error: {e}")
        return False

# ──────────────────────────────────────────────
# Guardar resultado
# ──────────────────────────────────────────────

def guardar_aria(audio_path, texto, info):
    tags_escritos = False
    
    if audio_path and MUTAGEN_AVAILABLE:
        log("\n[INFO] Escribiendo tags en archivo de audio...")
        tags_escritos = escribir_tags(audio_path, texto, info)
    
    # Archivo de respaldo
    aria  = info.get("aria_text", "aria")[:50]
    opera = info.get("opera", "opera")
    safe  = re.sub(r'[\\/*?:"<>|]', "_", f"{opera} - {aria}")
    folder = os.path.join(os.path.expanduser("~"), "Desktop")
    out    = os.path.join(folder, f"{safe}.aria.txt")
    
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"Compositor : {info.get('composer','')}\n")
        f.write(f"Ópera      : {opera}\n")
        f.write(f"Acto       : {info.get('act','')}\n")
        f.write(f"Personaje  : {info.get('character','')}\n")
        f.write(f"Aria       : {info.get('aria_text','')}\n")
        f.write(f"Tags escritos: {'Sí' if tags_escritos else 'No'}\n")
        f.write(f"Archivo audio: {audio_path}\n")
        f.write("=" * 60 + "\n\n")
        f.write(texto)
    
    log(f"[INFO] 📄 Respaldo guardado: {out}")
    return out

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.write("=== opera_libretto.py (FILE_PATH tag) ===\n")

    log(f"[INFO] argv: {sys.argv}")

    if len(sys.argv) < 3:
        log("[ERROR] Faltan argumentos")
        return

    artist_tag = sys.argv[1]
    title_tag = ", ".join(sys.argv[2:-1])
    audio_path = sys.argv[-1] if len(sys.argv) > 3 else ""
    aria_text = ", ".join(sys.argv[3:-1])

    log(f"[INFO] Artista: {artist_tag}")
    log(f"[INFO] Título: {title_tag}")
    log(f"[INFO] Ruta foobar2000: '{audio_path}'")

 # ↓ PEGA AQUÍ EL CAMBIO 1
    if audio_path and os.path.exists(audio_path):
        try:
            ext = os.path.splitext(audio_path)[1].lower()
            if ext == '.flac' and MUTAGEN_AVAILABLE:
                from mutagen.flac import FLAC as _FLAC
                _audio = _FLAC(audio_path)
                tag_title = _audio.get('title', [''])[0]
                if tag_title:
                    log(f"[INFO] Título desde tag FLAC: {repr(tag_title)}")
                    title_tag = tag_title
            elif ext == '.mp3' and MUTAGEN_AVAILABLE:
                from mutagen.id3 import ID3 as _ID3
                _audio = _ID3(audio_path)
                tag_title = str(_audio.get('TIT2', ''))
                if tag_title:
                    log(f"[INFO] Título desde tag MP3: {repr(tag_title)}")
                    title_tag = tag_title
        except Exception as e:
            log(f"[WARN] No se pudo leer tag title: {e}")



    # Parsear título
    info = parse_title(artist_tag, title_tag)
    if not info["opera"]:
        return

    # ESTRATEGIA PARA OBTENER LA RUTA REAL:
    real_path = None
    
    # 1. Si la ruta de foobar2000 es válida, intentar leer su tag FILE_PATH
    if audio_path and os.path.exists(audio_path) and len(audio_path) > 5:
        log(f"\n[INFO] La ruta de foobar2000 es válida: {audio_path}")
        log("[INFO] Leyendo tag FILE_PATH del archivo...")
        path_from_tag = get_file_path_from_audio_tags(audio_path)
        if path_from_tag:
            real_path = path_from_tag
            log(f"[INFO] ✅ Ruta desde FILE_PATH tag: {real_path}")
        else:
            log("[INFO] No se encontró FILE_PATH tag, usando ruta de foobar2000")
            real_path = audio_path
    
    # 2. Si no, buscar archivo con FILE_PATH tag que coincida con artist/title
    if not real_path:
        log("\n[INFO] Buscando archivo con FILE_PATH tag en biblioteca...")
        real_path = find_audio_with_file_path_tag(artist_tag, title_tag)
        if real_path:
            log(f"[INFO] ✅ Encontrado por tags: {real_path}")
    
    # 3. Si aún no tenemos ruta, no podemos escribir tags
    if not real_path:
        log("[WARN] No se encontró archivo de audio con FILE_PATH tag")
        log("[INFO] Se guardará solo archivo de texto")

    # Buscar libreto
    libreto = buscar_libreto(info)
    if not libreto:
        return

    aria_texto = (extract_aria(libreto, info["aria_text"], info["character"])
                  if info["aria_text"] else libreto)
    
    guardar_aria(real_path, aria_texto, info)
    print(aria_texto)

if __name__ == "__main__":
    main()