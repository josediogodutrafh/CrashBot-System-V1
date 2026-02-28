# -*- coding: utf-8 -*-
"""
Script de Build e Deploy - TucunareBot
Compila com Nuitka + Versionamento Git + GitHub Releases
"""
import contextlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# =============================================================================
# CONFIGURACOES
# =============================================================================
PROJECT_DIR = Path(r"C:\IA\Tucunare_bot\Crash")
SRC_DIR = PROJECT_DIR / "src"
MAIN_FILE = "bot_controller.py"
OUTPUT_NAME = "TucunareBot"

# Diretorios de saida (substitui o antigo dist/)
DIST_DIR = PROJECT_DIR / "dist"
BUILD_DIR = PROJECT_DIR / "build"

# Arquivo de versao
VERSION_FILE = PROJECT_DIR / "version.json"


# =============================================================================
# FUNCOES AUXILIARES
# =============================================================================
def print_separator():
    """Imprime a linha separadora padrao para evitar duplicacao de codigo"""
    print("=" * 70)


def print_section(text):
    """Imprime um cabecalho formatado usando o separador padrao"""
    print()
    print_separator()
    print(f"  {text}")
    print_separator()
    print()


# =============================================================================
# FUNCOES DE VERSAO
# =============================================================================
def get_git_tag():
    """Obtem a tag mais recente do Git"""
    with contextlib.suppress(Exception):
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip().lstrip("v")
    return None


def get_git_commit():
    """Obtem o commit atual"""
    with contextlib.suppress(Exception):
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    return "unknown"


def load_version():
    """Carrega versao do arquivo version.json"""
    if VERSION_FILE.exists():
        with open(VERSION_FILE, "r") as f:
            return json.load(f)
    return {"major": 2, "minor": 0, "patch": 0, "build": 0}


def save_version(version):
    """Salva versao no arquivo version.json"""
    with open(VERSION_FILE, "w") as f:
        json.dump(version, f, indent=2)


def increment_version(version, part="patch"):
    """Incrementa a versao"""
    if part == "major":
        version["major"] += 1
        version["minor"] = 0
        version["patch"] = 0
    elif part == "minor":
        version["minor"] += 1
        version["patch"] = 0
    elif part == "patch":
        version["patch"] += 1
    version["build"] += 1
    return version


def get_version_string(version):
    """Retorna string da versao"""
    return f"{version['major']}.{version['minor']}.{version['patch']}"


def get_full_version_string(version):
    """Retorna string completa da versao"""
    return (
        f"{version['major']}.{version['minor']}."
        f"{version['patch']}.{version['build']}"
    )


# =============================================================================
# FUNCOES DE BUILD
# =============================================================================
def clean_build():
    """Limpa diretorios de build anteriores"""
    patterns = [
        DIST_DIR,
        BUILD_DIR,
        SRC_DIR / "*.build",
        SRC_DIR / "*.dist",
        SRC_DIR / "*.onefile-build",
    ]

    for pattern in patterns[:2]:  # Apenas DIST e BUILD
        if pattern.exists():
            shutil.rmtree(pattern)
            print(f"[CLEAN] Removido: {pattern}")

    # Limpar arquivos .build do Nuitka no src
    for item in SRC_DIR.glob("*.build"):
        shutil.rmtree(item)
        print(f"[CLEAN] Removido: {item}")
    for item in SRC_DIR.glob("*.dist"):
        shutil.rmtree(item)
        print(f"[CLEAN] Removido: {item}")
    for item in SRC_DIR.glob("*.onefile-build"):
        shutil.rmtree(item)
        print(f"[CLEAN] Removido: {item}")


def build_exe(version_str, full_version_str):
    """Compila o executavel com Nuitka"""

    os.chdir(SRC_DIR)

    # Criar pasta dist se nao existir
    DIST_DIR.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        # Modo de compilacao
        "--onefile",
        # Compilador
        "--mingw64",
        "--assume-yes-for-downloads",
        # Otimizacoes
        "--lto=no",
        "--jobs=4",
        # Informacoes do executavel
        f"--output-filename={OUTPUT_NAME}.exe",
        "--company-name=Tucunare Locacao de Maquinas",
        "--product-name=TucunareBot",
        f"--file-version={full_version_str}",
        f"--product-version={full_version_str}",
        "--file-description=Bot de Trading Automatizado",
        "--copyright=2024-2025 Tucunare LTDA",
        # Windows - console para ver output
        "--windows-console-mode=force",
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
        "--include-module=joblib",
        "--include-module=pandas",
        # Incluir pacotes completos
        "--include-package=vision",
        "--include-package=scipy",
        "--include-package=skimage",
        # Incluir dados necessarios
        "--include-data-dir=vision=vision",
        # Incluir Tesseract-OCR
        f"--include-data-dir={PROJECT_DIR / 'Tesseract-OCR'}=Tesseract-OCR",
        # Incluir templates extras
        "--include-data-dir=vision/templates=src/vision/templates",
        # Plugin tk-inter
        "--enable-plugin=tk-inter",
        # Remover bloat
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-unittest-mode=allow",
        "--noinclude-IPython-mode=nofollow",
        # Output na pasta dist
        f"--output-dir={DIST_DIR}",
        # Remover build apos concluir
        "--remove-output",
        # Arquivo principal
        MAIN_FILE,
    ]

    # --- CORREÇÃO: Usando print_separator aqui ---
    print_separator()
    print(f"  BUILD: {OUTPUT_NAME} v{version_str}")
    print(f"  Data:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Git:   {get_git_commit()}")
    print_separator()
    # ---------------------------------------------
    print()

    result = subprocess.run(cmd)

    return result.returncode == 0


def create_release_notes(version_str):
    """Cria arquivo de release notes"""
    notes_file = DIST_DIR / f"RELEASE_NOTES_v{version_str}.md"

    content = f"""# TucunareBot v{version_str}

## Data de Release
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Git Commit
{get_git_commit()}

## Mudancas
- Build seguro com Nuitka (protecao contra engenharia reversa)
- Codigo compilado para C nativo

## Instalacao
1. Baixe o arquivo TucunareBot.exe
2. Execute como administrador
3. Siga as instrucoes de configuracao

## Requisitos
- Windows 10/11 64-bit
- Tesseract OCR instalado
- Conexao com internet

## Suporte
- Email: suporte@tucunarebot.com
- Telegram: @tucunare_suporte
"""

    with open(notes_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[NOTES] Release notes criado: {notes_file}")
    return notes_file


# =============================================================================
# FUNCOES DE DEPLOY (GitHub)
# =============================================================================
def create_git_tag(version_str):
    """Cria tag no Git"""
    tag = f"v{version_str}"

    # Verificar se tag ja existe
    result = subprocess.run(
        ["git", "tag", "-l", tag], capture_output=True, text=True, cwd=PROJECT_DIR
    )

    if tag in result.stdout:
        print(f"[GIT] Tag {tag} ja existe")
        return False

    # Criar tag
    subprocess.run(["git", "tag", "-a", tag, "-m", f"Release {tag}"], cwd=PROJECT_DIR)
    print(f"[GIT] Tag criada: {tag}")
    return True


def push_tag(version_str):
    """Envia tag para o GitHub"""
    tag = f"v{version_str}"
    result = subprocess.run(["git", "push", "origin", tag], cwd=PROJECT_DIR)
    if result.returncode == 0:
        print(f"[GIT] Tag {tag} enviada para GitHub")
    return result.returncode == 0


def create_github_release(version_str):
    """Instrucoes para criar release no GitHub"""
    exe_path = DIST_DIR / f"{OUTPUT_NAME}.exe"
    notes_path = DIST_DIR / f"RELEASE_NOTES_v{version_str}.md"

    print_section("INSTRUCOES PARA GITHUB RELEASE")

    print("1. Acesse: https://github.com/SEU_USUARIO/SEU_REPO/releases/new")
    print()
    print(f"2. Selecione a tag: v{version_str}")
    print()
    print(f"3. Titulo: TucunareBot v{version_str}")
    print()
    print("4. Anexe o arquivo:")
    print(f"   {exe_path}")
    print()
    print("5. Cole o conteudo de:")
    print(f"   {notes_path}")
    print()

    # --- CORREÇÃO: Usando print_separator aqui ---
    print_separator()
    # ---------------------------------------------


# =============================================================================
# MAIN
# =============================================================================
def main():
    print_section("TUCUNAREBOT - BUILD & DEPLOY SYSTEM")

    # Menu
    print("Opcoes:")
    print("  1. Build apenas (incrementa patch: 2.0.0 -> 2.0.1)")
    print("  2. Build + Minor (incrementa minor: 2.0.x -> 2.1.0)")
    print("  3. Build + Major (incrementa major: 2.x.x -> 3.0.0)")
    print("  4. Build + Tag Git + Push")
    print("  5. Build completo + Deploy GitHub")
    print("  0. Sair")
    print()

    choice = input("Escolha [1-5, 0 para sair]: ").strip()

    if choice == "0":
        print("Saindo...")
        return

    # Carregar versao atual
    version = load_version()
    print(f"\nVersao atual: {get_version_string(version)}")

    # Incrementar versao baseado na escolha
    if choice in ["1", "4", "5"]:
        version = increment_version(version, "patch")
    elif choice == "2":
        version = increment_version(version, "minor")
    elif choice == "3":
        version = increment_version(version, "major")
    else:
        print("Opcao invalida!")
        return

    version_str = get_version_string(version)
    full_version_str = get_full_version_string(version)

    print(f"Nova versao: {version_str} (build {version['build']})")
    print()

    confirm = input("Confirma? [s/N]: ").strip().lower()
    if confirm != "s":
        print("Cancelado!")
        return

    # Limpar builds anteriores
    print()
    print("[STEP 1] Limpando builds anteriores...")
    clean_build()

    # Salvar nova versao
    save_version(version)
    print(f"[VERSION] Salvo: {VERSION_FILE}")

    # Build
    print()
    print("[STEP 2] Compilando com Nuitka (isso pode demorar 15-30 min)...")
    print()

    success = build_exe(version_str, full_version_str)

    if not success:
        print()
        print("[ERRO] Falha na compilacao!")
        return

    print()
    print(f"[OK] Build concluido: {DIST_DIR / f'{OUTPUT_NAME}.exe'}")

    # Release notes
    print()
    print("[STEP 3] Criando release notes...")
    create_release_notes(version_str)

    # Git tag e push
    if choice in ["4", "5"]:
        print()
        print("[STEP 4] Criando tag Git...")
        create_git_tag(version_str)

        push_confirm = input("Enviar tag para GitHub? [s/N]: ").strip().lower()
        if push_confirm == "s":
            push_tag(version_str)

    # Instrucoes GitHub Release
    if choice == "5":
        create_github_release(version_str)

    print_section(f"BUILD CONCLUIDO - v{version_str}")

    print(f"Executavel: {DIST_DIR / f'{OUTPUT_NAME}.exe'}")
    print()


if __name__ == "__main__":
    main()
