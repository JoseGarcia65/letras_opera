import sys
import os
import re

try:
    import requests
    from bs4 import BeautifulSoup
    from mutagen import File
    from mutagen.id3 import ID3, USLT
    try:
        from ddgs import DDGS
    except ImportError:
        from duckduckgo_search import DDGS
except ImportError as e:
    print(f"Faltan librerías: {e}")
    print("Instálalas con: pip install ddgs beautifulsoup4 mutagen requests")
    input("Presiona ENTER para salir...")
    sys.exit()

def limpiar_titulo(texto):
    if not texto: return ""
    # Eliminar contenido entre paréntesis/corchetes, números de catálogo y actos
    texto = re.sub(r'\(.*?\)|\[.*?\]', '', texto)
    texto = re.sub(r'\b[Kk]\.?\s?\d+\b', '', texto)
    texto = re.sub(r'\b(Act|Acto|Scene|No|Part|Symphony|Concerto)\.?\s?\d+\b', '', texto, flags=re.IGNORECASE)
    # Quitar comillas y dos puntos que rompen la búsqueda
    texto = texto.replace('"', '').replace(':', '').replace('«', '').replace('»', '')
    return ' '.join(texto.split()).strip()

def extraer_letra(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        if 'genius.com' in url:
            div = soup.select_one('div[class^="Lyrics__Container"]') or soup.select_one('.lyrics')
        elif 'azlyrics.com' in url:
            # AZLyrics tiene la letra en un div sin clase ni id entre comentarios HTML
            div = soup.find('div', class_=None, id=None)
        else:
            div = None
        
        if div:
            for br in div.find_all("br"): br.replace_with("\n")
            # Limpiar etiquetas de scripts o estilos que puedan colarse
            for s in div(["script", "style"]): s.extract()
            return div.get_text().strip()
    except Exception as e:
        print(f"Error al extraer de la web: {e}")
    return None

def guardar_letra(file_path, letra):
    ext = file_path.lower()
    try:
        if ext.endswith('.mp3'):
            # Forzar el marco USLT para máxima compatibilidad con foobar2000
            try:
                tags = ID3(file_path)
            except Exception:
                tags = ID3()
            
            tags.add(USLT(encoding=3, lang='eng', desc='', text=letra))
            tags.save(file_path)
        else:
            # Para FLAC, M4A, OGG
            audio = File(file_path)
            if audio is not None:
                audio['LYRICS'] = letra
                audio.save()
        return True
    except Exception as e:
        print(f"Error al escribir en el archivo: {e}")
        return False

def buscar_y_taggear(file_path):
    try:
        audio = File(file_path)
        if not audio:
            print(f"Formato no soportado: {os.path.basename(file_path)}")
            return

        title_raw = audio.get('title', audio.get('TITLE', ['']))[0]
        artist_raw = audio.get('artist', audio.get('ARTIST', ['']))[0]
        
        titulo = limpiar_titulo(title_raw)
        artista = limpiar_titulo(artist_raw)
        
        # Varias estrategias de búsqueda
        busquedas = [
            f"{artista} {titulo} lyrics genius",
            f"{titulo} lyrics azlyrics",
            f"{titulo} genius lyrics"
        ]

        url_final = None
        for b in busquedas:
            print(f"Intentando búsqueda: {b}")
            with DDGS() as ddgs:
                results = list(ddgs.text(b, max_results=5))
            
            for r in results:
                link = r['href']
                if 'genius.com' in link or 'azlyrics.com' in link:
                    url_final = link
                    break
            if url_final: break

        if url_final:
            print(f"Enlace encontrado: {url_final}")
            letra = extraer_letra(url_final)
            if letra and len(letra) > 50: # Evitar textos vacíos o errores
                if guardar_letra(file_path, letra):
                    print(">>> ¡ÉXITO! Letra guardada correctamente.")
                else:
                    print("No se pudo guardar la letra en el archivo.")
            else:
                print("La letra extraída es demasiado corta o no es válida.")
        else:
            print("No se encontró ningún enlace de Genius o AZLyrics.")

    except Exception as e:
        print(f"Fallo general: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        buscar_y_taggear(sys.argv[1])
    else:
        print("No se recibió ruta de archivo.")
    
    print("\n" + "-"*40)

#input("Presiona ENTER para cerrar y volver a foobar...")
