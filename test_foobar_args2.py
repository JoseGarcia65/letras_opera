#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
diagnostico_foobar.py
Uso en foobar2000 Run Service:
  Path: python
  Parameters: "D:\vscode\diagnostico_foobar.py" "%artist%" "%title%" "%path%"
"""

import sys
import os
from datetime import datetime

# Guardar en el Escritorio
log_path = os.path.join(os.path.expanduser("~"), "Desktop", "diagnostico_foobar.txt")

with open(log_path, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write(f"DIAGNÓSTICO DE FOOBAR2000 - {datetime.now()}\n")
    f.write("=" * 80 + "\n\n")
    
    f.write(f"Número total de argumentos: {len(sys.argv)}\n")
    f.write(f"Nombre del script: {sys.argv[0]}\n\n")
    
    f.write("ARGUMENTOS RECIBIDOS:\n")
    f.write("-" * 40 + "\n")
    
    for i, arg in enumerate(sys.argv):
        f.write(f"\nArgumento #{i}:\n")
        f.write(f"  Valor: '{arg}'\n")
        f.write(f"  Tipo: {type(arg).__name__}\n")
        f.write(f"  Longitud: {len(arg)} caracteres\n")
        f.write(f"  Repr: {repr(arg)}\n")
        f.write(f"  ¿Está vacío?: {len(arg.strip()) == 0}\n")
        
        # Si es una ruta, verificar
        if i >= 1 and len(arg) > 2:
            f.write(f"  ¿Existe como archivo?: {os.path.isfile(arg)}\n")
            f.write(f"  ¿Existe como directorio?: {os.path.isdir(arg)}\n")
            
            if os.path.isfile(arg):
                f.write(f"  Extensión: {os.path.splitext(arg)[1]}\n")
                f.write(f"  Tamaño: {os.path.getsize(arg)} bytes\n")
            elif len(arg) < 5:
                f.write(f"  ⚠️ Demasiado corto para ser una ruta válida\n")
    
    f.write("\n\nRESUMEN:\n")
    f.write("-" * 40 + "\n")
    
    if len(sys.argv) > 1:
        f.write(f"Artista (argv[1]): '{sys.argv[1]}'\n")
    else:
        f.write("⚠️ No se recibió artista\n")
    
    if len(sys.argv) > 2:
        f.write(f"Título (argv[2]): '{sys.argv[2]}'\n")
    else:
        f.write("⚠️ No se recibió título\n")
    
    if len(sys.argv) > 3:
        f.write(f"Ruta (argv[3]): '{sys.argv[3]}'\n")
        
        path = sys.argv[3]
        if os.path.isfile(path):
            f.write("✅ La ruta es un archivo válido\n")
        elif os.path.isdir(path):
            f.write("⚠️ La ruta es un directorio, no un archivo\n")
        elif len(path) < 5:
            f.write(f"❌ La ruta es inválida (muy corta: '{path}')\n")
            f.write("   Posibles causas:\n")
            f.write("   1. %path% no se está expandiendo correctamente\n")
            f.write("   2. cmd /c está interpretando %path% como variable de entorno\n")
            f.write("   3. Las comillas no están bien escapadas\n")
        else:
            f.write(f"❌ La ruta no existe: '{path}'\n")
    else:
        f.write("⚠️ No se recibió ruta\n")
    
    f.write("\n\nCONFIGURACIÓN RECOMENDADA:\n")
    f.write("-" * 40 + "\n")
    f.write("Opción 1 (SIN cmd):\n")
    f.write('  Path: python\n')
    f.write('  Parameters: "D:\\vscode\\busca5.py" "%artist%" "%title%" "%path%"\n\n')
    f.write("Opción 2 (CON cmd, escapando %):\n")
    f.write('  Path: cmd\n')
    f.write('  Parameters: /c python "D:\\vscode\\busca5.py" "%artist%" "%title%" "%%path%%"\n\n')
    f.write("Opción 3 (variables alternativas):\n")
    f.write('  Parameters: ... "%_path%" ...\n')
    f.write('  Parameters: ... "%_filename_ext%" ...\n')

print(f"✅ Diagnóstico completado. Revisa: {log_path}")