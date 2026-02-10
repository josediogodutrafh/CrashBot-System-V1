# 🔌 WebSocket Sniffer - Guia Completo

## 📋 **O Que É?**

O WebSocket Sniffer intercepta a comunicação do jogo Crash para obter **multiplicadores em tempo real** diretamente do servidor, sem precisar de OCR.

**Funciona igual ao TipMiner!** ✨

---

## ✅ **Vantagens sobre OCR**

| Aspecto | OCR (Atual) | WebSocket Sniffer |
|---------|-------------|-------------------|
| **Precisão** | ~95-98% | **100%** ✅ |
| **Velocidade** | ~50-200ms | **<10ms** ⚡ |
| **CPU** | Alto (processamento) | **Baixo** 💚 |
| **Dependências** | Posição da janela | **Nenhuma** 🎯 |
| **Confiabilidade** | Depende de iluminação | **Sempre** 💯 |

---

## 🎯 **Métodos de Interceptação**

### **1. Direct Connection (Recomendado para início)**
Conecta diretamente ao WebSocket do jogo se você souber a URL.

**Prós:**
- ✅ Simples
- ✅ Rápido
- ✅ Não precisa proxy

**Contras:**
- ⚠️ Precisa descobrir URL do WebSocket
- ⚠️ Pode precisar autenticação

### **2. Proxy Local (Mais Comum)**
Usa mitmproxy para interceptar tráfego.

**Prós:**
- ✅ Funciona com qualquer site
- ✅ Vê todas as mensagens
- ✅ Pode modificar tráfego

**Contras:**
- ⚠️ Precisa configurar proxy no browser
- ⚠️ Sites com SSL pinning não funcionam

### **3. Chrome DevTools Protocol**
Usa API do Chrome para interceptar.

**Prós:**
- ✅ Não precisa proxy
- ✅ Acesso total ao browser
- ✅ Pode executar JavaScript

**Contras:**
- ⚠️ Só funciona com Chrome/Chromium
- ⚠️ Precisa iniciar Chrome com flags especiais

### **4. Packet Sniffing**
Captura pacotes de rede diretamente.

**Prós:**
- ✅ Vê TODO o tráfego
- ✅ Não precisa modificar browser

**Contras:**
- ⚠️ Requer permissões de admin
- ⚠️ HTTPS criptografado é difícil

---

## 🚀 **Como Usar**

### **Método 1: Direct Connection (Se souber a URL)**

```python
from engine.vision.websocket_sniffer import WebSocketSniffer, SnifferMethod

# Criar sniffer
sniffer = WebSocketSniffer(
    method=SnifferMethod.DIRECT,
    websocket_url="wss://exemplo.com/crash/ws"  # URL do jogo
)

# Definir callback para explosões
def on_explosion(event):
    print(f"💥 Crash em {event.multiplier}x!")
    print(f"   Timestamp: {event.timestamp}")

sniffer.on_explosion = on_explosion

# Iniciar
sniffer.start()

# Aguardar (ou fazer outras coisas)
import time
time.sleep(60)  # Roda por 60 segundos

# Parar
sniffer.stop()

# Ver estatísticas
stats = sniffer.get_stats()
print(f"Total de explosões: {stats['total_explosions']}")
print(f"Média: {stats['mean']:.2f}x")
```

### **Método 2: Com Updates em Tempo Real**

```python
from engine.vision.websocket_sniffer import WebSocketSniffer

sniffer = WebSocketSniffer(
    method=SnifferMethod.DIRECT,
    websocket_url="wss://crash.exemplo.com/ws"
)

# Callback para cada update de multiplicador
def on_multiplier_update(update):
    print(f"📈 {update.current_multiplier:.2f}x", end='\r')

# Callback para explosão
def on_explosion(event):
    print(f"\n💥 CRASH em {event.multiplier}x!")

sniffer.on_multiplier = on_multiplier_update
sniffer.on_explosion = on_explosion

sniffer.start()
```

### **Método 3: Integrado com TriggerSystem**

```python
from engine.vision.websocket_sniffer import get_sniffer, SnifferMethod
from engine.strategy.trigger import TriggerSystem

# Criar sniffer
sniffer = get_sniffer(
    method=SnifferMethod.DIRECT,
    websocket_url="wss://crash.exemplo.com/ws"
)

# Criar trigger
trigger = TriggerSystem()

# Callback: alimenta o trigger automaticamente
def on_explosion(event):
    trigger.add_explosion(event.multiplier)

    if trigger.should_trigger():
        print("🎯 GATILHO ATIVADO! Hora de apostar!")
        trigger.reset()

sniffer.on_explosion = on_explosion
sniffer.start()
```

---

## 🔍 **Como Descobrir a URL do WebSocket?**

### **Opção 1: Chrome DevTools (Mais Fácil)**

1. Abra o jogo no Chrome
2. Pressione `F12` (DevTools)
3. Vá na aba **Network**
4. Filtre por **WS** (WebSocket)
5. Atualize a página
6. Veja a conexão WebSocket
7. Copie a URL (ex: `wss://crash.exemplo.com/ws`)

![DevTools WS](https://i.imgur.com/example.png)

### **Opção 2: mitmproxy**

```bash
# Instalar mitmproxy
pip install mitmproxy

# Executar
mitmweb --listen-port 8080

# Configurar proxy no browser:
# HTTP Proxy: localhost:8080

# Jogar no site
# Ver WebSocket connections no mitmweb
```

### **Opção 3: Wireshark**

1. Instale Wireshark
2. Capture na interface de rede
3. Filtre: `websocket`
4. Veja handshake HTTP Upgrade
5. Copie URL

---

## 📦 **Instalação de Dependências**

### **Método Direct Connection**
```bash
pip install websocket-client
```

### **Método Proxy (mitmproxy)**
```bash
pip install mitmproxy
```

### **Método CDP (Chrome DevTools)**
```bash
pip install pychrome
# ou
pip install playwright
```

### **Método Packet Sniffing**
```bash
pip install scapy
# Requer permissões de admin
```

---

## 🎛️ **Configuração Avançada**

### **Custom Message Parser**

Se o formato das mensagens for diferente:

```python
class CustomSniffer(WebSocketSniffer):
    def _extract_multiplier(self, data):
        # Lógica customizada
        if 'custom_field' in data:
            return float(data['custom_field'])
        return super()._extract_multiplier(data)

sniffer = CustomSniffer(
    method=SnifferMethod.DIRECT,
    websocket_url="wss://..."
)
```

### **Filtros de Eventos**

```python
def on_explosion(event):
    # Só processa se multiplicador baixo
    if event.multiplier < 2.0:
        print(f"Vela baixa: {event.multiplier}x")

sniffer.on_explosion = on_explosion
```

### **Salvar Histórico**

```python
import json
from datetime import datetime

def on_explosion(event):
    # Salva em arquivo
    with open('historico.jsonl', 'a') as f:
        f.write(json.dumps(event.to_dict()) + '\n')

sniffer.on_explosion = on_explosion
```

---

## 🧪 **Testando**

### **Teste Simples (Mock)**

```python
# test_websocket_sniffer.py
from engine.vision.websocket_sniffer import WebSocketSniffer, ExplosionEvent
from datetime import datetime

# Criar sniffer (sem conectar)
sniffer = WebSocketSniffer()

# Simular explosão manualmente
event = ExplosionEvent(
    multiplier=1.85,
    timestamp=datetime.now()
)

# Testar callback
called = False
def test_callback(e):
    global called
    called = True
    print(f"Callback chamado: {e.multiplier}x")

sniffer.on_explosion = test_callback
sniffer._handle_explosion({"crash": 1.85})

assert called, "Callback não foi chamado!"
print("✅ Teste passou!")
```

---

## 🔐 **Segurança e Ética**

### **⚠️ IMPORTANTE:**

1. **Interceptar tráfego pode violar ToS** do site
2. **Use apenas para fins educacionais** ou com permissão
3. **Não compartilhe credenciais** capturadas
4. **Respeite privacidade** de outros usuários
5. **WebSocket pode ter autenticação** - respeite

### **Boas Práticas:**

- ✅ Use em ambiente de teste próprio
- ✅ Não abuse da frequência de requisições
- ✅ Implemente rate limiting
- ✅ Log apenas dados necessários
- ✅ Proteja dados sensíveis

---

## 🐛 **Troubleshooting**

### **Erro: "Connection refused"**
- Verifique se a URL está correta
- Teste a URL no browser primeiro
- Veja se precisa de headers específicos

### **Erro: "SSL Certificate verify failed"**
```python
# Desabilitar verificação SSL (não recomendado)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### **Não detecta explosões**
- Verifique formato das mensagens (DevTools)
- Customize `_extract_multiplier()`
- Adicione logs: `logger.setLevel(logging.DEBUG)`

### **Performance ruim**
- Use threading para callbacks pesados
- Limite histórico: `sniffer._max_history = 100`
- Desabilite callbacks desnecessários

---

## 📊 **Comparação com TipMiner**

| Feature | TipMiner | CrashBot Sniffer |
|---------|----------|------------------|
| WebSocket | ✅ | ✅ |
| Histórico | ✅ | ✅ |
| Stats | ✅ | ✅ |
| Callbacks | ✅ | ✅ |
| Múltiplos sites | ✅ | ⚠️ Customizar |
| Open Source | ❌ | ✅ |
| Grátis | ❌ | ✅ |

---

## 🔄 **Integração com CrashBot**

### **Substituir OCR por WebSocket**

```python
# Em detector.py ou main.py

from engine.vision.websocket_sniffer import get_sniffer, SnifferMethod

# Criar sniffer
sniffer = get_sniffer(
    method=SnifferMethod.DIRECT,
    websocket_url="wss://crash.site/ws"
)

# Integrar com EventBus
from core.events import emit, BotEvent

def on_explosion(event):
    # Emitir evento no EventBus
    emit(
        BotEvent.EXPLOSION_DETECTED,
        value=event.multiplier,
        timestamp=event.timestamp
    )

sniffer.on_explosion = on_explosion
sniffer.start()

# Agora o resto do bot funciona normalmente!
```

---

## 📚 **Próximos Passos**

1. **Descobrir URL do WebSocket** do seu jogo
2. **Testar conexão** com método DIRECT
3. **Implementar callbacks** customizados
4. **Integrar com TriggerSystem**
5. **Substituir OCR** gradualmente

---

**🎉 Pronto! Agora você tem captura de dados em tempo real como o TipMiner!**

📝 **Dúvidas?** Leia o código em `websocket_sniffer.py`
