from deep_translator import GoogleTranslator

def traducir_a_espanol(texto_original):
    try:
        # Configuramos el traductor: detecta el idioma origen automáticamente y traduce a español ('es')
        traduccion = GoogleTranslator(source='auto', target='es').translate(texto_original)
        return traduccion
    except Exception as e:
        return f"Error al traducir: {e}"