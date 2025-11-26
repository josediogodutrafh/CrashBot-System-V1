#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para criar um novo perfil de monitor completo
Calibra todas as áreas e salva no config.json
"""

import pyautogui
import time
import json
import os
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


def calibrate_area(name):
    """Calibra uma área retangular pedindo as coordenadas dos cantos"""
    print(f"\n{Fore.CYAN}=== CALIBRANDO ÁREA: {name.upper()} ===")

    print(
        f"\nPosicione o mouse no {Fore.YELLOW}canto superior esquerdo{Fore.RESET} da área {name}."
    )
    print("Quando estiver pronto, pressione Enter para capturar a coordenada...")
    input()
    top_left = pyautogui.position()
    print(f"{Fore.GREEN}✓ Canto superior esquerdo: x={top_left[0]}, y={top_left[1]}")

    print(
        f"\nPosicione o mouse no {Fore.YELLOW}canto inferior direito{Fore.RESET} da área {name}."
    )
    print("Quando estiver pronto, pressione Enter para capturar a coordenada...")
    input()
    bottom_right = pyautogui.position()
    print(
        f"{Fore.GREEN}✓ Canto inferior direito: x={bottom_right[0]}, y={bottom_right[1]}"
    )

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


def main():
    # Carregar configuração atual
    config = load_config()
    if not config:
        print(
            f"{Fore.RED}❌ Não foi possível carregar a configuração. Criando uma nova."
        )
        config = {
            "jogadores": [],
            "tempo_horas": 5,
            "max_rodadas": 1800,
            "meta_lucro_total": 155220,
            "horario_inicio": "08:00",
            "profiles": {},
        }

    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}   CRIAÇÃO DE NOVO PERFIL DE MONITOR")
    print(f"{Fore.CYAN}{'='*60}")

    # Solicitar nome do novo perfil
    while True:
        profile_name = input(
            "\nDigite o nome do novo perfil (ex: 'Monitor Pessoal'): "
        ).strip()
        if not profile_name:
            print(f"{Fore.RED}❌ O nome do perfil não pode estar vazio.")
            continue

        if profile_name in config.get("profiles", {}):
            overwrite = input(
                f"{Fore.YELLOW}⚠️ Perfil '{profile_name}' já existe. Sobrescrever? (s/N): "
            ).lower()
            if overwrite != "s":
                continue

        break

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.YELLOW}PREPARAÇÃO:")
    print(
        f"{Fore.WHITE}1. Certifique-se de que a página do jogo está aberta com zoom de 90%"
    )
    print(f"{Fore.WHITE}2. Maximize a janela do navegador")
    print(
        f"{Fore.WHITE}3. Posicione o jogo para que todos os elementos estejam visíveis"
    )
    print(f"{Fore.CYAN}{'='*60}")

    input("\nPressione Enter para começar a calibração...")

    # Calibrar áreas principais
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}   CALIBRAÇÃO DE ÁREAS PRINCIPAIS")
    print(f"{Fore.CYAN}{'='*60}")

    # Área do multiplicador
    multiplier_area = calibrate_area("multiplicador central")
    if not multiplier_area:
        return

    # Área do "Bet 8s"
    bet_area = calibrate_area("botão 'Bet 8s'")
    if not bet_area:
        return

    # Área do saldo
    balance_area = calibrate_area("saldo")
    if not balance_area:
        return

    # Calibrar pontos de clique para apostas
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}   CALIBRAÇÃO DE PONTOS DE CLIQUE (APOSTA 1)")
    print(f"{Fore.CYAN}{'='*60}")

    bet_value_click_1 = calibrate_point("campo de valor da aposta 1")
    target_click_1 = calibrate_point("campo de alvo (multiplicador) da aposta 1")

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}   CALIBRAÇÃO DE PONTOS DE CLIQUE (APOSTA 2)")
    print(f"{Fore.CYAN}{'='*60}")

    bet_value_click_2 = calibrate_point("campo de valor da aposta 2")
    target_click_2 = calibrate_point("campo de alvo (multiplicador) da aposta 2")

    # Opção para calibrar áreas avançadas
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}   CALIBRAÇÃO DE ÁREAS AVANÇADAS (OPCIONAL)")
    print(f"{Fore.CYAN}{'='*60}")

    calibrate_advanced = (
        input(
            "\nDeseja calibrar áreas avançadas para detecção de campos? (s/N): "
        ).lower()
        == "s"
    )

    bet_value_area_1 = None
    target_area_1 = None
    bet_value_area_2 = None
    target_area_2 = None
    bet_button_area_1 = None
    bet_button_area_2 = None

    if calibrate_advanced:
        print(f"\n{Fore.YELLOW}Vamos calibrar as áreas dos campos de entrada e botões:")

        # Áreas da aposta 1
        bet_value_area_1 = calibrate_area("campo de valor da aposta 1")
        target_area_1 = calibrate_area("campo de alvo (multiplicador) da aposta 1")
        bet_button_area_1 = calibrate_area("botão de apostar 1")

        # Áreas da aposta 2
        bet_value_area_2 = calibrate_area("campo de valor da aposta 2")
        target_area_2 = calibrate_area("campo de alvo (multiplicador) da aposta 2")
        bet_button_area_2 = calibrate_area("botão de apostar 2")

    # Criar o perfil
    profile = {
        "multiplier_area": multiplier_area,
        "balance_area": balance_area,
        "bet_area": bet_area,
        "bet_value_click_1": bet_value_click_1,
        "target_click_1": target_click_1,
        "bet_value_click_2": bet_value_click_2,
        "target_click_2": target_click_2,
        "bet_value_area_1": bet_value_area_1,
        "target_area_1": target_area_1,
        "bet_value_area_2": bet_value_area_2,
        "target_area_2": target_area_2,
        "bet_button_area_1": bet_button_area_1,
        "bet_button_area_2": bet_button_area_2,
    }

    # Adicionar perfil à configuração
    if "profiles" not in config:
        config["profiles"] = {}

    config["profiles"][profile_name] = profile

    # Salvar configuração
    if save_config(config):
        print(f"\n{Fore.GREEN}{'='*60}")
        print(f"{Fore.GREEN}✅ PERFIL '{profile_name}' CRIADO COM SUCESSO!")
        print(f"{Fore.GREEN}{'='*60}")
        print(f"\n{Fore.YELLOW}Áreas calibradas:")
        print(f"   Multiplicador: {multiplier_area}")
        print(f"   Saldo: {balance_area}")
        print(f"   Bet: {bet_area}")
        print(f"\n{Fore.YELLOW}Pontos de clique:")
        print(f"   Valor aposta 1: {bet_value_click_1}")
        print(f"   Alvo aposta 1: {target_click_1}")
        print(f"   Valor aposta 2: {bet_value_click_2}")
        print(f"   Alvo aposta 2: {target_click_2}")

        if calibrate_advanced:
            print(f"\n{Fore.YELLOW}Áreas avançadas:")
            print(f"   Área valor aposta 1: {bet_value_area_1}")
            print(f"   Área alvo aposta 1: {target_area_1}")
            print(f"   Área valor aposta 2: {bet_value_area_2}")
            print(f"   Área alvo aposta 2: {target_area_2}")
            print(f"   Área botão aposta 1: {bet_button_area_1}")
            print(f"   Área botão aposta 2: {bet_button_area_2}")
    else:
        print(f"\n{Fore.RED}❌ Falha ao salvar o perfil.")


if __name__ == "__main__":
    main()
