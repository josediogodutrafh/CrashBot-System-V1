# Seguranca do Executavel (.exe)

## Problema Atual

PyInstaller empacota o bytecode Python (.pyc) dentro do .exe. Ferramentas como
`pyinstxtractor` + `uncompyle6`/`decompyle3` recuperam o codigo-fonte quase intacto
em minutos. Isso expoe:

- Logica da estrategia (martingale, trigger, targets)
- Chaves de API e endpoints do backend
- Mecanismo de validacao de licenca (HWID + chave)
- Comunicacao WebSocket com Chrome DevTools

## Solucoes por Nivel de Protecao

### Nivel 1: Obfuscacao (Rapido, Gratuito)

**PyArmor** - Ofusca bytecode Python antes de empacotar.

```bash
pip install pyarmor
pyarmor gen --pack onefile run.py
```

Vantagens:
- Facil de integrar, compativel com PyInstaller
- Renomeia variaveis, ofusca strings, protege imports
- Versao gratuita ja dificulta bastante

Limitacoes:
- Bytecode ainda e Python (reversivel com esforco)
- Performance levemente impactada (~5%)

### Nivel 2: Compilacao Nativa (Recomendado)

**Nuitka** - Compila Python para C, depois para binario nativo.

```bash
pip install nuitka
python -m nuitka --standalone --onefile --windows-console-mode=disable ^
    --include-package=src --include-data-dir=config=config ^
    --include-data-dir=tools=tools ^
    --output-filename=CrashBot.exe run.py
```

Vantagens:
- Codigo compilado para assembly nativo (nao tem .pyc dentro)
- Ferramentas Python de decompilacao NAO funcionam
- Performance 10-30% melhor que CPython
- Gratuito e open source

Limitacoes:
- Build mais lento (~5-10 min)
- Requer compilador C (MSVC ou MinGW no Windows)
- Engenharia reversa com IDA/Ghidra ainda possivel (mas muito mais dificil)

### Nivel 3: Protecao Anti-Tamper (Maximo)

Combinar Nuitka + protecoes adicionais:

1. **Assinatura de Codigo (Code Signing)**
   - Certificado digital (~$70-200/ano via Sectigo, DigiCert)
   - Windows SmartScreen nao bloqueia .exe assinados
   - Detecta se o binario foi modificado

2. **Verificacao de Integridade em Runtime**
   ```python
   import hashlib
   import sys

   def verificar_integridade():
       """Verifica se o .exe nao foi modificado."""
       if not getattr(sys, "frozen", False):
           return True
       exe_path = sys.executable
       with open(exe_path, "rb") as f:
           hash_atual = hashlib.sha256(f.read()).hexdigest()
       # Hash esperado (atualizar a cada build)
       HASH_ESPERADO = "abc123..."  # placeholder
       return hash_atual == HASH_ESPERADO
   ```

3. **Anti-Debug**
   ```python
   import ctypes

   def detectar_debugger():
       """Detecta se esta rodando em debugger."""
       return ctypes.windll.kernel32.IsDebuggerPresent() != 0
   ```

## Protecao de Segredos

### NAO fazer (atual):
```python
# Segredos hardcoded no codigo
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API_BASE_URL = "https://crash-api-jose.onrender.com"
```

### Fazer:
1. **Segredos no backend** - Bot nunca deve ter tokens de admin
2. **API intermediaria** - Bot se comunica com sua API, nao direto com Telegram
3. **Chave de licenca como auth** - Toda request do bot inclui a chave como Bearer token
4. **Endpoint de config** - Bot busca configuracoes do servidor ao iniciar

```python
# Bot busca config do servidor (sem segredos locais)
async def obter_config(chave_licenca: str) -> dict:
    response = await httpx.get(
        "https://api.tucunarebot.com.br/api/v1/bot/config",
        headers={"Authorization": f"Bearer {chave_licenca}"},
    )
    return response.json()
```

## Protecao do HWID

O HWID atual (`src/security/hwid.py`) provavelmente usa:
- Serial do disco
- MAC address
- Nome do computador

Recomendacoes:
1. **Combinar multiplos fatores** (CPU ID + Disco + MAC + Motherboard serial)
2. **Hash no servidor** - Enviar hash do HWID, servidor valida
3. **Binding de licenca** - Chave so funciona com 1 HWID (ja implementado)
4. **Rate limiting** - Limitar tentativas de validacao por IP/chave

## Fluxo de Validacao Recomendado

```
Bot inicia
  |
  v
Envia chave + HWID para API
  |
  v
API valida:
  - Chave existe e esta ativa?
  - HWID corresponde ao registrado?
  - Licenca nao expirou?
  - IP nao esta em blacklist?
  |
  v
Retorna token JWT (valido por 1h)
  |
  v
Bot usa JWT em todas as requests
  |
  v
A cada 1h, renova o token (heartbeat)
  |
  v
Se token expira sem renovar → bot para
```

## Prioridade de Implementacao

| Prioridade | Acao                          | Esforco | Impacto |
|------------|-------------------------------|---------|---------|
| 1          | Migrar para Nuitka            | Medio   | Alto    |
| 2          | Remover segredos do .exe      | Baixo   | Alto    |
| 3          | JWT com heartbeat             | Medio   | Alto    |
| 4          | Code signing                  | Baixo   | Medio   |
| 5          | Anti-debug + integridade      | Baixo   | Baixo   |
| 6          | PyArmor (se ficar no PyInst.) | Baixo   | Medio   |

## Resumo

A combinacao **Nuitka + segredos no backend + JWT com heartbeat** resolve 90% do
problema de seguranca. O custo de engenharia reversa em binario nativo compilado
com Nuitka e ordens de magnitude maior do que extrair .pyc de PyInstaller.
