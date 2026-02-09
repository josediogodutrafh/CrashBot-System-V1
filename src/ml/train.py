#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SCRIPT DE TREINAMENTO (MODO TREINAMENTO)

Este script é usado para treinar manualmente o LearningEngine
usando os dados mais recentes do banco de dados (crash_bot_historico.db).
"""

import time
import traceback

from src.ml.engine import LearningEngine

# Importar 'rich' para uma saída bonita (opcional)
try:
    from rich.console import Console

    console = Console()
except ImportError:
    # Fallback simples se 'rich' não estiver instalado
    class _FallbackConsole:
        def print(self, text, style=None):
            print(text)

        def print_exception(self, show_locals=False):
            """Método print_exception de fallback usando traceback."""
            print("\n[ERRO FATAL - Traceback abaixo]")
            traceback.print_exc()

    console = _FallbackConsole()


def _execute_training_workflow():
    """
    Função auxiliar que executa o pipeline de treinamento e imprime os resultados.
    """
    start_time = time.time()

    console.print("⏳ Inicializando LearningEngine...")
    engine = LearningEngine()

    console.print("🧠 Treinando modelo...")
    engine.train_model()

    end_time = time.time()
    duration = end_time - start_time

    console.print("\n[green]✅ TREINAMENTO CONCLUÍDO COM SUCESSO[/green]")
    console.print(f"   - Modelo salvo em: [cyan]{engine.model_path}[/cyan]")
    console.print(f"   - Scaler salvo em: [cyan]{engine.scaler_path}[/cyan]")
    console.print(f"   - Duração: {duration:.2f} segundos")

    return engine


def run_training():
    """
    Orquestra o processo de treinamento.
    """
    console.print("[yellow]=== INICIANDO MODO DE TREINAMENTO ===[/yellow]")

    try:
        _execute_training_workflow()

    except Exception:
        console.print("\n[bold red]❌ ERRO FATAL DURANTE O TREINAMENTO:[/bold red]")
        console.print_exception(show_locals=True)


if __name__ == "__main__":
    run_training()
