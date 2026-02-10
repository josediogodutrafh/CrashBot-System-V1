#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Calibrador de Perfil de Tela
=============================

Calibra as 3 areas necessarias para o bot executar apostas:
  1. Campo de valor da aposta (onde digitar o valor em R$)
  2. Campo de multiplicador alvo (onde digitar o target, ex: 2.00)
  3. Botao apostar (onde clicar para confirmar)

Uso:
  python -m src.bot.profiles
"""

import json
import time

import pyautogui
from colorama import Fore, init

from src.config import PROFILES_PATH

init(autoreset=True)


def carregar_config():
    """Carrega a configuracao atual do profiles.json."""
    try:
        with open(PROFILES_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"{Fore.RED}Erro ao carregar configuracao: {e}")
        return None


def salvar_config(config):
    """Salva a configuracao atualizada com backup."""
    try:
        if PROFILES_PATH.exists():
            backup = PROFILES_PATH.with_suffix(".json.bak")
            with open(backup, "w") as f:
                json.dump(config, f, indent=4)

        with open(PROFILES_PATH, "w") as f:
            json.dump(config, f, indent=4)
        print(f"{Fore.GREEN}Configuracao salva em {PROFILES_PATH}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Erro ao salvar: {e}")
        return False


def calibrar_area(nome):
    """Calibra uma area retangular (canto superior esquerdo + canto inferior direito).

    Args:
        nome: Nome descritivo da area sendo calibrada.

    Returns:
        Dict com {x, y, width, height} ou None se cancelado.
    """
    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}  CALIBRANDO: {nome.upper()}")
    print(f"{Fore.CYAN}{'='*50}")

    print(
        f"\n  Posicione o mouse no {Fore.YELLOW}CANTO SUPERIOR ESQUERDO"
        f"{Fore.RESET} do campo."
    )
    print(f"  Pressione {Fore.GREEN}ENTER{Fore.RESET} para capturar...")
    input()
    topo_esq = pyautogui.position()
    print(f"{Fore.GREEN}  Capturado: x={topo_esq[0]}, y={topo_esq[1]}")

    print(
        f"\n  Posicione o mouse no {Fore.YELLOW}CANTO INFERIOR DIREITO"
        f"{Fore.RESET} do campo."
    )
    print(f"  Pressione {Fore.GREEN}ENTER{Fore.RESET} para capturar...")
    input()
    baixo_dir = pyautogui.position()
    print(f"{Fore.GREEN}  Capturado: x={baixo_dir[0]}, y={baixo_dir[1]}")

    x = topo_esq[0]
    y = topo_esq[1]
    largura = baixo_dir[0] - topo_esq[0]
    altura = baixo_dir[1] - topo_esq[1]

    if largura <= 0 or altura <= 0:
        print(
            f"{Fore.RED}  ERRO: Dimensoes invalidas "
            f"(largura={largura}, altura={altura})."
        )
        print(
            f"  O canto inferior direito deve estar ABAIXO e A DIREITA "
            f"do canto superior esquerdo."
        )
        return None

    print(
        f"{Fore.GREEN}  Area calibrada: "
        f"{largura}x{altura} em ({x}, {y})"
    )
    return {"x": x, "y": y, "width": largura, "height": altura}


def listar_perfis(config):
    """Lista perfis existentes."""
    perfis = config.get("profiles", {})
    if not perfis:
        print(f"\n{Fore.YELLOW}  Nenhum perfil cadastrado.")
        return

    print(f"\n{Fore.CYAN}  Perfis existentes:")
    for i, (nome, dados) in enumerate(perfis.items(), 1):
        campos = len([v for v in dados.values() if v])
        print(f"    {i}. {nome} ({campos} campos calibrados)")


def deletar_perfil(config):
    """Deleta um perfil existente."""
    perfis = config.get("profiles", {})
    if not perfis:
        print(f"{Fore.YELLOW}  Nenhum perfil para deletar.")
        return

    nomes = list(perfis.keys())
    print(f"\n{Fore.CYAN}  Qual perfil deseja deletar?")
    for i, nome in enumerate(nomes, 1):
        print(f"    {i}. {nome}")
    print(f"    0. Cancelar")

    try:
        escolha = int(input(f"\n{Fore.GREEN}  Selecione: {Fore.RESET}"))
        if escolha == 0:
            return
        if 1 <= escolha <= len(nomes):
            nome = nomes[escolha - 1]
            del perfis[nome]
            salvar_config(config)
            print(f"{Fore.GREEN}  Perfil '{nome}' deletado!")
        else:
            print(f"{Fore.RED}  Numero invalido.")
    except ValueError:
        print(f"{Fore.RED}  Digite um numero valido.")


def main():
    config = carregar_config()
    if not config:
        print(f"{Fore.YELLOW}  Criando configuracao nova...")
        config = {
            "jogadores": [],
            "tempo_horas": 5,
            "max_rodadas": 1800,
            "meta_lucro_total": 155220,
            "horario_inicio": "08:00",
            "profiles": {},
        }

    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.CYAN}  CALIBRADOR DE PERFIL DE TELA")
    print(f"{Fore.CYAN}  TucunareBot v2.0")
    print(f"{Fore.CYAN}{'='*50}")

    listar_perfis(config)

    print(f"\n{Fore.CYAN}  O que deseja fazer?")
    print(f"    1. Criar novo perfil")
    print(f"    2. Deletar perfil existente")
    print(f"    0. Sair")

    try:
        opcao = int(input(f"\n{Fore.GREEN}  Selecione: {Fore.RESET}"))
    except ValueError:
        return

    if opcao == 2:
        deletar_perfil(config)
        return
    elif opcao != 1:
        return

    # --- Criar novo perfil ---

    while True:
        nome_perfil = input(
            f"\n{Fore.CYAN}  Nome do perfil (ex: 'Meu PC'): {Fore.RESET}"
        ).strip()
        if not nome_perfil:
            print(f"{Fore.RED}  Nome nao pode ser vazio.")
            continue

        if nome_perfil in config.get("profiles", {}):
            sobrescrever = input(
                f"{Fore.YELLOW}  Perfil '{nome_perfil}' ja existe. "
                f"Sobrescrever? (s/N): {Fore.RESET}"
            ).lower()
            if sobrescrever != "s":
                continue
        break

    print(f"\n{Fore.CYAN}{'='*50}")
    print(f"{Fore.YELLOW}  PREPARACAO:")
    print(f"{Fore.WHITE}  1. Abra o jogo no Chrome")
    print(f"{Fore.WHITE}  2. Deixe a area de apostas visivel")
    print(f"{Fore.WHITE}  3. Voce vai calibrar 3 campos:")
    print(f"{Fore.WHITE}     - Campo de VALOR DA APOSTA (onde digitar R$)")
    print(f"{Fore.WHITE}     - Campo de MULTIPLICADOR ALVO (onde digitar 2.00x)")
    print(f"{Fore.WHITE}     - BOTAO APOSTAR (onde clicar para confirmar)")
    print(f"{Fore.CYAN}{'='*50}")

    input(f"\n{Fore.GREEN}  Pressione ENTER para comecar...{Fore.RESET}")

    # 1. Campo de valor da aposta
    valor_aposta = calibrar_area("Campo de Valor da Aposta (R$)")
    if not valor_aposta:
        print(f"{Fore.RED}  Calibracao cancelada.")
        return

    # 2. Campo de multiplicador alvo
    multiplicador = calibrar_area("Campo de Multiplicador Alvo (ex: 2.00x)")
    if not multiplicador:
        print(f"{Fore.RED}  Calibracao cancelada.")
        return

    # 3. Botao apostar
    botao = calibrar_area("Botao Apostar")
    if not botao:
        print(f"{Fore.RED}  Calibracao cancelada.")
        return

    # Montar perfil (apenas os 3 campos necessarios)
    perfil = {
        "bet_value_area_1": valor_aposta,
        "target_area_1": multiplicador,
        "bet_button_area_1": botao,
    }

    if "profiles" not in config:
        config["profiles"] = {}

    config["profiles"][nome_perfil] = perfil

    if salvar_config(config):
        print(f"\n{Fore.GREEN}{'='*50}")
        print(f"{Fore.GREEN}  PERFIL '{nome_perfil}' CRIADO COM SUCESSO!")
        print(f"{Fore.GREEN}{'='*50}")
        print(f"\n{Fore.YELLOW}  Campos calibrados:")
        print(f"    Valor aposta: {valor_aposta}")
        print(f"    Multiplicador: {multiplicador}")
        print(f"    Botao apostar: {botao}")
        print(f"\n{Fore.CYAN}  Agora inicie o bot e selecione este perfil!")
    else:
        print(f"\n{Fore.RED}  Falha ao salvar o perfil.")


if __name__ == "__main__":
    main()
