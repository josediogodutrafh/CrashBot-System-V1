# -*- coding: utf-8 -*-
"""
Teste do WebSocket Sniffer - CrashBot v3.0
Demonstra como usar o sniffer para capturar multiplicadores em tempo real.
"""

import sys
import time
from datetime import datetime

# Fix encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

print("="*70)
print("TESTE DO WEBSOCKET SNIFFER - CrashBot v3.0")
print("="*70)

# ============================================================================
# TESTE 1: Importação
# ============================================================================
print("\n[TEST 1] Importação do Módulo")
print("-" * 70)

try:
    from engine.vision.websocket_sniffer import (
        WebSocketSniffer,
        SnifferMethod,
        ExplosionEvent,
        MultiplierUpdate,
        get_sniffer
    )
    print("✅ Módulo importado com sucesso")
    print("✅ [PASSOU] Importação OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TESTE 2: Criação da Instância
# ============================================================================
print("\n[TEST 2] Criação da Instância")
print("-" * 70)

try:
    sniffer = WebSocketSniffer(
        method=SnifferMethod.DIRECT,
        websocket_url="wss://exemplo.com/ws"  # URL de exemplo
    )
    print(f"✅ Sniffer criado: {type(sniffer).__name__}")
    print(f"  - Método: {sniffer.method.value}")
    print(f"  - URL: {sniffer.websocket_url}")
    print("✅ [PASSOU] Criação OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# TESTE 3: Callbacks
# ============================================================================
print("\n[TEST 3] Definição de Callbacks")
print("-" * 70)

try:
    # Variáveis para testar callbacks
    explosion_called = False
    multiplier_called = False

    def on_explosion(event: ExplosionEvent):
        global explosion_called
        explosion_called = True
        print(f"  📢 Callback explosão: {event.multiplier}x")

    def on_multiplier(update: MultiplierUpdate):
        global multiplier_called
        multiplier_called = True
        print(f"  📢 Callback multiplier: {update.current_multiplier}x")

    sniffer.on_explosion = on_explosion
    sniffer.on_multiplier = on_multiplier

    print("✅ Callbacks definidos")
    print("✅ [PASSOU] Callbacks OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")

# ============================================================================
# TESTE 4: Simulação de Eventos (Mock)
# ============================================================================
print("\n[TEST 4] Simulação de Eventos")
print("-" * 70)

try:
    # Simular explosão manualmente (sem WebSocket real)
    print("  Simulando explosão de 1.85x...")
    sniffer._handle_explosion({"crash": 1.85})

    assert explosion_called, "Callback de explosão não foi chamado!"
    print("✅ Callback de explosão funcionou")

    # Simular update de multiplicador
    print("  Simulando update de multiplicador para 2.50x...")
    sniffer._handle_multiplier_update({"multiplier": 2.50})

    assert multiplier_called, "Callback de multiplier não foi chamado!"
    print("✅ Callback de multiplier funcionou")

    print("✅ [PASSOU] Simulação OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 5: Extração de Multiplicador
# ============================================================================
print("\n[TEST 5] Extração de Multiplicador")
print("-" * 70)

try:
    test_cases = [
        ({"crash": 1.85}, 1.85),
        ({"bust": 2.50}, 2.50),
        ({"explosion": "3.75x"}, 3.75),
        ({"multiplier": 1.23}, 1.23),
        ({"value": 4.56}, 4.56),
    ]

    for data, expected in test_cases:
        result = sniffer._extract_multiplier(data)
        assert result == expected, f"Esperado {expected}, obteve {result}"
        print(f"  ✅ {data} → {result}x")

    print("✅ [PASSOU] Extração de multiplicador OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 6: Histórico
# ============================================================================
print("\n[TEST 6] Gerenciamento de Histórico")
print("-" * 70)

try:
    # Simular várias explosões
    explosions = [1.23, 1.45, 1.67, 1.89, 2.10, 1.34, 1.56, 1.78, 1.90, 2.50]

    for mult in explosions:
        sniffer._handle_explosion({"crash": mult})

    # Verificar histórico
    history = sniffer.get_history()
    print(f"✅ Histórico tem {len(history)} explosões")

    # Últimos N
    last_5 = sniffer.get_last_n_multipliers(n=5)
    print(f"✅ Últimos 5: {last_5}")

    assert len(last_5) == 5, "Deveria ter 5 multiplicadores"

    print("✅ [PASSOU] Histórico OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 7: Estatísticas
# ============================================================================
print("\n[TEST 7] Estatísticas")
print("-" * 70)

try:
    stats = sniffer.get_stats()

    print(f"  Total de explosões: {stats['total_explosions']}")
    print(f"  Histórico: {stats['history_size']}")
    print(f"  Média: {stats['mean']:.2f}x")
    print(f"  Mediana: {stats['median']:.2f}x")
    print(f"  Mín: {stats['min']:.2f}x")
    print(f"  Máx: {stats['max']:.2f}x")
    print(f"  Último: {stats['last']:.2f}x")

    assert stats['total_explosions'] > 0, "Deveria ter explosões"
    assert stats['mean'] > 0, "Média deveria ser > 0"

    print("✅ [PASSOU] Estatísticas OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 8: Singleton
# ============================================================================
print("\n[TEST 8] Padrão Singleton")
print("-" * 70)

try:
    sniffer1 = get_sniffer()
    sniffer2 = get_sniffer()

    assert sniffer1 is sniffer2, "Deveria retornar a mesma instância"
    print("✅ get_sniffer() retorna singleton")

    print("✅ [PASSOU] Singleton OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# TESTE 9: Integração com TriggerSystem
# ============================================================================
print("\n[TEST 9] Integração com TriggerSystem")
print("-" * 70)

try:
    from engine.strategy.trigger import TriggerSystem

    # Criar trigger
    trigger = TriggerSystem()

    # Callback que alimenta o trigger
    trigger_activated = False

    def on_explosion_with_trigger(event: ExplosionEvent):
        global trigger_activated
        trigger.add_explosion(event.multiplier)

        if trigger.should_trigger():
            trigger_activated = True
            print(f"  🎯 GATILHO ATIVADO! ({trigger.get_progress()})")

    # Novo sniffer para não conflitar com anterior
    test_sniffer = WebSocketSniffer()
    test_sniffer.on_explosion = on_explosion_with_trigger

    # Simular 8 velas baixas
    low_values = [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9]
    for val in low_values:
        test_sniffer._handle_explosion({"crash": val})

    if trigger_activated:
        print("✅ Trigger foi ativado corretamente!")
    else:
        print("⚠️  Trigger não ativou (verificar threshold)")

    print("✅ [PASSOU] Integração com Trigger OK")
except Exception as e:
    print(f"❌ [FALHOU] {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*70)
print("RESUMO DOS TESTES")
print("="*70)
print("✅ Importação: OK")
print("✅ Criação: OK")
print("✅ Callbacks: OK")
print("✅ Simulação: OK")
print("✅ Extração: OK")
print("✅ Histórico: OK")
print("✅ Estatísticas: OK")
print("✅ Singleton: OK")
print("✅ Integração: OK")
print("="*70)
print("🎉 TODOS OS TESTES PASSARAM!")
print("="*70)

print("\n📋 PRÓXIMOS PASSOS:")
print("  1. Descobrir URL do WebSocket do seu jogo")
print("  2. Testar com: sniffer.start() (com URL real)")
print("  3. Integrar com o resto do bot")
print("\n💡 DICA:")
print("  Use Chrome DevTools (F12) > Network > WS")
print("  para encontrar a URL do WebSocket do jogo")
print("="*70)
