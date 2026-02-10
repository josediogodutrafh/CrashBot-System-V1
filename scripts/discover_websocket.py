#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script auxiliar para descobrir e testar WebSocket do jogo Crash.

Uso:
    1. Abra o jogo no Chrome
    2. Execute: python discover_websocket.py
    3. Siga as instruções
"""

import json
import time
from datetime import datetime

print("=" * 70)
print("🔍 DESCOBRIR WEBSOCKET - CRASH GAME")
print("=" * 70)
print()

print("📋 PASSO A PASSO:")
print()
print("1️⃣  Abra o jogo Crash no Chrome")
print("2️⃣  Pressione F12 (abre DevTools)")
print("3️⃣  Clique na aba 'Network' (Rede)")
print("4️⃣  No filtro, clique em 'WS' (WebSocket)")
print("5️⃣  Atualize a página do jogo (F5)")
print("6️⃣  Você verá conexões WebSocket aparecerem")
print("7️⃣  Clique na conexão WebSocket")
print("8️⃣  Na aba 'Headers', procure 'Request URL'")
print("9️⃣  Copie a URL completa (ex: wss://exemplo.com/ws)")
print()
print("=" * 70)
print()

# Pedir URL
url = input("🔗 Cole a URL do WebSocket aqui: ").strip()

if not url:
    print("❌ Nenhuma URL fornecida!")
    exit(1)

if not (url.startswith("ws://") or url.startswith("wss://")):
    print("⚠️  URL deve começar com ws:// ou wss://")
    print(f"   Você digitou: {url}")

    # Tentar corrigir
    if url.startswith("http://"):
        url = url.replace("http://", "ws://")
        print(f"   Corrigido para: {url}")
    elif url.startswith("https://"):
        url = url.replace("https://", "wss://")
        print(f"   Corrigido para: {url}")
    else:
        print("   Adicionando wss:// automaticamente...")
        url = f"wss://{url}"
        print(f"   URL final: {url}")

print()
print("=" * 70)
print("🔌 TESTANDO CONEXÃO...")
print("=" * 70)
print()

try:
    from engine.vision.websocket_sniffer import WebSocketSniffer, SnifferMethod

    print("✅ Módulo WebSocketSniffer importado")
    print()

    # Criar sniffer
    sniffer = WebSocketSniffer(
        method=SnifferMethod.DIRECT,
        websocket_url=url
    )

    print(f"📡 Conectando a: {url}")
    print("⏳ Aguarde... (máximo 30 segundos)")
    print()

    # Contador de eventos
    explosion_count = 0
    multiplier_count = 0

    # Callbacks
    def on_explosion(event):
        global explosion_count
        explosion_count += 1

        print(f"💥 [{datetime.now().strftime('%H:%M:%S')}] EXPLOSÃO #{explosion_count}: {event.multiplier}x")

        # Salvar em arquivo
        with open("websocket_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} | EXPLOSION | {event.multiplier}x\n")

    def on_multiplier(update):
        global multiplier_count
        multiplier_count += 1

        # Mostrar a cada 10 updates (não poluir)
        if multiplier_count % 10 == 0:
            print(f"📈 [{datetime.now().strftime('%H:%M:%S')}] Multiplicador: {update.current_multiplier:.2f}x")

    sniffer.on_explosion = on_explosion
    sniffer.on_multiplier = on_multiplier

    print("✅ Callbacks configurados")
    print()
    print("=" * 70)
    print("🚀 INICIANDO MONITORAMENTO...")
    print("=" * 70)
    print()
    print("💡 DICA: Pressione Ctrl+C para parar")
    print()

    # Iniciar
    success = sniffer.start()

    if not success:
        print("❌ Falha ao iniciar sniffer!")
        exit(1)

    # Aguardar eventos
    try:
        while True:
            time.sleep(1)

            # Mostrar stats a cada 30 segundos
            if int(time.time()) % 30 == 0:
                stats = sniffer.get_stats()
                print()
                print("📊 ESTATÍSTICAS:")
                print(f"   Total de explosões: {stats.get('total_explosions', 0)}")
                if stats.get('mean'):
                    print(f"   Média: {stats['mean']:.2f}x")
                    print(f"   Mínimo: {stats['min']:.2f}x")
                    print(f"   Máximo: {stats['max']:.2f}x")
                print()

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("⏹️  PARANDO...")
        print("=" * 70)
        print()

        sniffer.stop()

        # Estatísticas finais
        stats = sniffer.get_stats()

        print("📊 ESTATÍSTICAS FINAIS:")
        print(f"   Total de explosões capturadas: {stats.get('total_explosions', 0)}")

        if stats.get('mean'):
            print(f"   Média: {stats['mean']:.2f}x")
            print(f"   Mediana: {stats['median']:.2f}x")
            print(f"   Mínimo: {stats['min']:.2f}x")
            print(f"   Máximo: {stats['max']:.2f}x")

        print()
        print("💾 Log salvo em: websocket_log.txt")
        print()
        print("=" * 70)
        print("✅ TESTE CONCLUÍDO!")
        print("=" * 70)
        print()
        print("📋 PRÓXIMOS PASSOS:")
        print("   1. Salvar esta URL em config.json")
        print("   2. Integrar com o resto do bot")
        print("   3. Substituir OCR por WebSocket")
        print()

except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print()
    print("💡 Instale as dependências:")
    print("   pip install websocket-client")
    exit(1)

except Exception as e:
    print(f"❌ Erro: {e}")
    print()
    print("💡 POSSÍVEIS CAUSAS:")
    print("   - URL incorreta")
    print("   - WebSocket requer autenticação")
    print("   - Firewall bloqueando conexão")
    print("   - Formato das mensagens diferente")
    print()
    print("🔍 TENTE:")
    print("   1. Verificar URL no DevTools")
    print("   2. Ver aba 'Messages' no DevTools")
    print("   3. Copiar formato exato das mensagens")
    exit(1)
