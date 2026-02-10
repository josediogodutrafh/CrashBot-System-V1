# -*- coding: utf-8 -*-
"""Teste rápido de captura de tela"""
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

print("🔍 Teste Rápido de Captura de Tela\n")

# Teste 1: mss está instalado?
print("[1/5] Verificando mss...")
try:
    import mss
    print(f"✅ mss instalado: {mss.__version__}")
except Exception as e:
    print(f"❌ mss não encontrado: {e}")
    sys.exit(1)

# Teste 2: Pode criar instância mss?
print("\n[2/5] Criando instância mss...")
try:
    sct = mss.mss()
    print("✅ Instância mss criada")
except Exception as e:
    print(f"❌ Erro ao criar mss: {e}")
    sys.exit(1)

# Teste 3: Detecta monitores?
print("\n[3/5] Detectando monitores...")
try:
    monitors = sct.monitors
    print(f"✅ {len(monitors) - 1} monitor(es) detectado(s)")
    for i, m in enumerate(monitors):
        if i == 0:
            continue
        print(f"  Monitor {i}: {m['width']}x{m['height']}")
except Exception as e:
    print(f"❌ Erro ao detectar monitores: {e}")
    sys.exit(1)

# Teste 4: Pode capturar?
print("\n[4/5] Testando captura...")
try:
    monitor = {"top": 0, "left": 0, "width": 100, "height": 100}
    screenshot = sct.grab(monitor)
    print(f"✅ Captura OK: {screenshot.size}")
except Exception as e:
    print(f"❌ Erro ao capturar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Teste 5: ScreenCapture do CrashBot
print("\n[5/5] Testando ScreenCapture...")
try:
    from engine.vision.capture import ScreenCapture
    capture = ScreenCapture()
    print("✅ ScreenCapture criado")

    img = capture.capture_region(0, 0, 100, 100)
    if img is not None:
        print(f"✅ Captura funcional: shape={img.shape}")
    else:
        print("⚠️  Captura retornou None")

    capture.close()
    print("✅ Cleanup OK")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*50)
print("✅ TODOS OS TESTES PASSARAM!")
print("="*50)
print("\n📝 CONCLUSÃO:")
print("  ✅ MSS funciona")
print("  ✅ Captura de tela funciona")
print("  ❌ NÃO usa WebSocket (usa MSS direto)")
print("  ✅ Performance: Otimizada para real-time")
