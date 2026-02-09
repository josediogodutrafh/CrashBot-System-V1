#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WEBSOCKET SNIFFER - Captura tráfego WS do jogo via Chrome DevTools Protocol
===========================================================================

Pré-requisito:
  Abra o Chrome com remote debugging:
    chrome.exe --remote-debugging-port=9222

  Ou adicione ao atalho do Chrome:
    "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

  Depois abra o jogo normalmente no Chrome e rode este script.

Uso:
  python tools/ws_sniffer.py
"""

import json
import sys
import time
from datetime import datetime

import requests
import websocket


def get_chrome_ws_url(port=9222):
    """Descobre o WebSocket URL do Chrome DevTools."""
    try:
        resp = requests.get(f"http://localhost:{port}/json", timeout=3)
        tabs = resp.json()

        print(f"\n{len(tabs)} abas encontradas:\n")
        game_tab = None
        for i, tab in enumerate(tabs):
            url = tab.get("url", "")
            title = tab.get("title", "")
            ws_url = tab.get("webSocketDebuggerUrl", "")
            is_page = tab.get("type") == "page"

            marker = ""
            # Procurar aba do jogo (ajuste os termos conforme necessario)
            keywords = ["crash", "blaze", "brabet", "game", "casino",
                        "double", "mines", "apostas", "bet"]
            if any(kw in url.lower() or kw in title.lower() for kw in keywords):
                marker = " <-- JOGO?"
                if not game_tab and is_page:
                    game_tab = tab

            print(f"  [{i}] {title[:60]}")
            print(f"      URL: {url[:80]}")
            if ws_url:
                print(f"      WS:  {ws_url[:80]}")
            if marker:
                print(f"      {marker}")
            print()

        if game_tab:
            return game_tab.get("webSocketDebuggerUrl")

        # Se nao encontrou automaticamente, pedir ao usuario
        print("Nenhuma aba do jogo detectada automaticamente.")
        try:
            idx = int(input(f"Numero da aba do jogo (0-{len(tabs)-1}): "))
            return tabs[idx].get("webSocketDebuggerUrl")
        except (ValueError, IndexError):
            if tabs:
                return tabs[0].get("webSocketDebuggerUrl")
            return None

    except requests.ConnectionError:
        print("ERRO: Chrome nao esta rodando com --remote-debugging-port=9222")
        print()
        print("Abra o Chrome assim:")
        print('  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"'
              ' --remote-debugging-port=9222')
        print()
        print("Ou adicione --remote-debugging-port=9222 ao atalho do Chrome.")
        return None
    except Exception as e:
        print(f"ERRO: {e}")
        return None


def sniff_websockets(devtools_url, duration=120):
    """Conecta ao DevTools e captura TODOS os frames WebSocket."""
    print(f"\nConectando ao DevTools...")
    print(f"URL: {devtools_url}")

    ws = websocket.create_connection(devtools_url, timeout=10)

    # Habilitar interceptacao de rede (Network domain)
    ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
    resp = json.loads(ws.recv())
    print(f"Network.enable: {resp.get('id', 'ok')}")

    # Contadores
    ws_frames = []
    ws_connections = {}
    frame_count = 0
    start_time = time.time()

    print(f"\nCapturando WebSocket frames por {duration}s...")
    print(f"Abra o jogo e jogue normalmente.\n")
    print("-" * 80)

    try:
        ws.settimeout(0.5)
        while time.time() - start_time < duration:
            try:
                msg = ws.recv()
                data = json.loads(msg)
                method = data.get("method", "")

                # WebSocket criado
                if method == "Network.webSocketCreated":
                    params = data.get("params", {})
                    req_id = params.get("requestId", "")
                    url = params.get("url", "")
                    ws_connections[req_id] = url
                    print(f"[WS CONNECT] {url[:100]}")

                # Frame recebido do servidor
                elif method == "Network.webSocketFrameReceived":
                    params = data.get("params", {})
                    req_id = params.get("requestId", "")
                    payload = params.get("response", {}).get(
                        "payloadData", "")
                    url = ws_connections.get(req_id, "unknown")
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                    frame_count += 1
                    frame_info = {
                        "timestamp": timestamp,
                        "direction": "RECV",
                        "url": url,
                        "payload": payload,
                        "request_id": req_id,
                    }
                    ws_frames.append(frame_info)

                    # Mostrar payload resumido
                    short = payload[:150] if len(payload) > 150 else payload
                    print(f"[{timestamp}] RECV #{frame_count} | {short}")

                # Frame enviado ao servidor
                elif method == "Network.webSocketFrameSent":
                    params = data.get("params", {})
                    req_id = params.get("requestId", "")
                    payload = params.get("response", {}).get(
                        "payloadData", "")
                    url = ws_connections.get(req_id, "unknown")
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

                    frame_info = {
                        "timestamp": timestamp,
                        "direction": "SENT",
                        "url": url,
                        "payload": payload,
                        "request_id": req_id,
                    }
                    ws_frames.append(frame_info)

                    short = payload[:150] if len(payload) > 150 else payload
                    print(f"[{timestamp}] SENT       | {short}")

                # WebSocket fechado
                elif method == "Network.webSocketClosed":
                    params = data.get("params", {})
                    req_id = params.get("requestId", "")
                    url = ws_connections.get(req_id, "unknown")
                    print(f"[WS CLOSE] {url[:80]}")

            except websocket.WebSocketTimeoutException:
                continue
            except Exception as e:
                if "timed out" not in str(e):
                    print(f"  Erro: {e}")
                continue

    except KeyboardInterrupt:
        print("\n\nInterrompido pelo usuario.")

    ws.close()

    # Salvar resultado
    elapsed = time.time() - start_time
    print("-" * 80)
    print(f"\nCaptura finalizada: {frame_count} frames em {elapsed:.0f}s")
    print(f"Conexoes WS encontradas: {len(ws_connections)}")

    for req_id, url in ws_connections.items():
        n = sum(1 for f in ws_frames if f["request_id"] == req_id)
        print(f"  {url[:80]} ({n} frames)")

    # Salvar em arquivo
    output_file = "data/debug/ws_capture.json"
    import os
    os.makedirs("data/debug", exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "capture_time": datetime.now().isoformat(),
            "duration_seconds": elapsed,
            "total_frames": frame_count,
            "connections": ws_connections,
            "frames": ws_frames,
        }, f, indent=2, ensure_ascii=False)

    print(f"\nDados salvos em: {output_file}")
    print("\nProximo passo: analise o arquivo para identificar")
    print("os eventos do jogo (multiplicador, resultado, apostas).")

    return ws_frames, ws_connections


def main():
    print("=" * 60)
    print("   WEBSOCKET SNIFFER - Crash Game")
    print("=" * 60)

    port = 9222
    devtools_url = get_chrome_ws_url(port)

    if not devtools_url:
        sys.exit(1)

    print(f"\nDuracao da captura (segundos) [120]: ", end="")
    try:
        dur_input = input().strip()
        duration = int(dur_input) if dur_input else 120
    except ValueError:
        duration = 120

    sniff_websockets(devtools_url, duration)


if __name__ == "__main__":
    main()
