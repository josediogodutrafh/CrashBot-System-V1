# -*- coding: utf-8 -*-
"""
Script de Build Seguro - TucunareBot
Compila o bot usando Nuitka para protecao contra engenharia reversa
"""
import os
import subprocess
import sys
import shutil
from datetime import datetime

# Configuracoes
PROJECT_DIR = r"C:\IA\Crash\Projetos\Crash\src"
MAIN_FILE = "bot_controller.py"
OUTPUT_NAME = "TucunareBot"
VERSION = "2.0.0"

# Diretorios
BUILD_DIR = os.path.join(PROJECT_DIR, "..", "build_secure")
DIST_DIR = os.path.join(PROJECT_DIR, "..", "dist_secure")

def clean_build():
    """Limpa diretorios de build anteriores"""
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"[CLEAN] Removido: {d}")

def build_exe():
    """Compila o executavel com Nuitka"""
    
    os.chdir(PROJECT_DIR)
    
    cmd = [
        sys.executable, "-m", "nuitka",
        
        # Modo de compilacao
        "--onefile",
        "--standalone",
        
        # Compilador
        "--mingw64",
        "--assume-yes-for-downloads",
        
        # Otimizacoes
        "--lto=yes",
        "--jobs=4",
        
        # Informacoes do executavel
        f"--output-filename={OUTPUT_NAME}.exe",
        f"--company-name=Tucunare Locacao de Maquinas",
        f"--product-name=TucunareBot",
        f"--file-version={VERSION}",
        f"--product-version={VERSION}",
        f"--file-description=Bot de Trading Automatizado",
        f"--copyright=2024-2025 Tucunare",
        
        # Windows - sem console visivel durante execucao normal
        "--windows-console-mode=attach",
        
        # Incluir modulos necessarios
        "--include-module=cv2",
        "--include-module=numpy",
        "--include-module=PIL",
        "--include-module=pytesseract",
        "--include-module=pyautogui",
        "--include-module=requests",
        "--include-module=rich",
        "--include-module=sklearn",
        "--include-module=mss",
        
        # Incluir pacotes completos
        "--include-package=vision",
        
        # Incluir dados necessarios
        "--include-data-dir=vision=vision",
        
        # Remover bloat
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-unittest-mode=nofollow",
        
        # Output
        f"--output-dir={DIST_DIR}",
        
        # Arquivo principal
        MAIN_FILE,
    ]
    
    print("=" * 60)
    print(f"[BUILD] Iniciando compilacao do {OUTPUT_NAME}")
    print(f"[BUILD] Versao: {VERSION}")
    print(f"[BUILD] Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print("[CMD]", " ".join(cmd))
    print()
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print(f"[OK] Build concluido com sucesso!")
        print(f"[OK] Executavel: {DIST_DIR}\\{OUTPUT_NAME}.exe")
        print("=" * 60)
    else:
        print()
        print("[ERRO] Falha na compilacao!")
        sys.exit(1)

if __name__ == "__main__":
    print()
    print("  TucunareBot - Build Seguro com Nuitka")
    print()
    
    # Limpar builds anteriores
    clean_build()
    
    # Compilar
    build_exe()
