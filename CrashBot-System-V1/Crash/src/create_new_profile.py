#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para criar um novo perfil de monitor completo
Calibra todas as áreas e salva no config.json
"""

import json
import os

import pyautogui
from colorama import Fore, init

init(autoreset=True)


def load_config():
    """Carrega a configuração atual"""
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao carregar configuração: {e}")
        return None


def save_config(config):
    """Salva a configuração atualizada"""
    try:
        # Criar backup do arquivo original
        if os.path.exists("config.json"):
            with open("config.json.bak", "w") as f:
                json.dump(config, f, indent=4)
            print(f"{Fore.GREEN}✅ Backup da configuração criado em config.json.bak")

        # Salvar a nova configuração
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        print(f"{Fore.GREEN}✅ Configuração salva com sucesso em config.json")
        return True
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao salvar configuração: {e}")
        return False


def _capturar_canto(nome_canto: str, nome_area: str):
    """
    Função auxiliar para capturar a coordenada de um canto.
    (Resolve o problema de código duplicado apontado pelo Sourcery)
    """
    print(
        f"\nPosicione o mouse no {Fore.YELLOW}{nome_canto}{Fore.RESET} da área {nome_area}."
    )
    print("Quando estiver pronto, pressione Enter para capturar a coordenada...")
    input()
    pos = pyautogui.position()
    print(f"{Fore.GREEN}✓ {nome_canto.capitalize()}: x={pos[0]}, y={pos[1]}")
    return pos


def calibrate_area(name):
    """Calibra uma área retangular pedindo as coordenadas dos cantos"""
    print(f"\n{Fore.CYAN}=== CALIBRANDO ÁREA: {name.upper()} ===")

    # Usa a função auxiliar para evitar duplicação
    top_left = _capturar_canto("canto superior esquerdo", name)
    bottom_right = _capturar_canto("canto inferior direito", name)

    # Calcular dimensões da área
    x = top_left[0]
    y = top_left[1]
    width = bottom_right[0] - top_left[0]
    height = bottom_right[1] - top_left[1]

    # Verificar se as dimensões são válidas
    if width <= 0 or height <= 0:
        print(
            f"{Fore.RED}❌ ERRO: Dimensões inválidas (largura={width}, altura={height})."
        )
        print(
            "O canto inferior direito deve estar abaixo e à direita do canto superior esquerdo."
        )
        return None

    print(
        f"{Fore.GREEN}✅ Área calibrada: x={x}, y={y}, largura={width}, altura={height}"
    )

    return {"x": x, "y": y, "width": width, "height": height}


def calibrate_point(name):
    """Calibra um ponto de clique"""
    print(f"\n{Fore.CYAN}=== CALIBRANDO PONTO: {name.upper()} ===")

    print(f"\nPosicione o mouse no ponto de clique para {name}.")
    print("Quando estiver pronto, pressione Enter para capturar a coordenada...")
    input()
    point = pyautogui.position()
    print(f"{Fore.GREEN}✓ Ponto calibrado: x={point[0]}, y={point[1]}")

    return {"x": point[0], "y": point[1]}


def _get_valid_profile_name(existing_profiles: dict) -> str:
    """Solicita e valida o nome do perfil."""
    while True:
        name = input("\nDigite o nome do novo perfil (ex: 'Monitor 1'): ").strip()
        if not name:
            print(f"{Fore.RED}❌ Nome inválido.")
            continue

        if name in existing_profiles and input(...) != "s":
            continue
        return name


def _print_instructions():
    """Imprime instruções iniciais."""
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}PREPARAÇÃO:")
    print("1. Jogo aberto com zoom 90%")
    print("2. Janela maximizada")
    print("3. Todos elementos visíveis")
    print(f"{Fore.CYAN}{'='*60}")
    input("\nPressione Enter para começar...")


def _perform_calibration_sequence() -> dict:
    """Executa a sequência completa de calibração."""
    profile = {}

    # 1. Áreas Principais
    print(f"\n{Fore.CYAN}>> ETAPA 1: ÁREAS PRINCIPAIS")
    if not (mult := calibrate_area("multiplicador central")):
        return {}
    if not (bet := calibrate_area("botão 'Bet 8s'")):
        return {}
    if not (bal := calibrate_area("saldo")):
        return {}

    profile |= {"multiplier_area": mult, "bet_area": bet, "balance_area": bal}

    # 2. Pontos de Clique
    print(f"\n{Fore.CYAN}>> ETAPA 2: CLIQUES APOSTA 1")
    profile["bet_value_click_1"] = calibrate_point("campo valor aposta 1")
    profile["target_click_1"] = calibrate_point("campo alvo aposta 1")

    print(f"\n{Fore.CYAN}>> ETAPA 3: CLIQUES APOSTA 2")
    profile["bet_value_click_2"] = calibrate_point("campo valor aposta 2")
    profile["target_click_2"] = calibrate_point("campo alvo aposta 2")

    # 3. Avançado (Opcional)
    print(f"\n{Fore.CYAN}>> ETAPA 4: AVANÇADO (OCR)")
    if input("\nCalibrar áreas de OCR para campos? (s/N): ").lower() == "s":
        profile["bet_value_area_1"] = calibrate_area("OCR valor 1")
        profile["target_area_1"] = calibrate_area("OCR alvo 1")
        profile["bet_button_area_1"] = calibrate_area("OCR botão 1")

        profile["bet_value_area_2"] = calibrate_area("OCR valor 2")
        profile["target_area_2"] = calibrate_area("OCR alvo 2")
        profile["bet_button_area_2"] = calibrate_area("OCR botão 2")
    else:
        # Preenche com None para evitar erros de chave
        for key in [
            "bet_value_area_1",
            "target_area_1",
            "bet_button_area_1",
            "bet_value_area_2",
            "target_area_2",
            "bet_button_area_2",
        ]:
            profile[key] = None

    return profile


def main():
    """Função principal orquestradora."""
    print(f"{Fore.CYAN}{'='*60}\n   CRIADOR DE PERFIL v2.0\n{'='*60}")

    config = load_config() or {"profiles": {}}

    # 1. Obter Nome
    profile_name = _get_valid_profile_name(config.get("profiles", {}))

    # 2. Instruções
    _print_instructions()

    # 3. Executar Calibração
    new_profile_data = _perform_calibration_sequence()

    if not new_profile_data:
        print(f"\n{Fore.RED}❌ Calibração cancelada ou falhou.")
        return

    # 4. Salvar
    if "profiles" not in config:
        config["profiles"] = {}

    config["profiles"][profile_name] = new_profile_data

    if save_config(config):
        print(f"\n{Fore.GREEN}✅ PERFIL '{profile_name}' CRIADO COM SUCESSO!")
        print(f"{Fore.YELLOW}Reinicie o bot para usar este perfil.")


if __name__ == "__main__":
    main()
