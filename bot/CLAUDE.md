# Crash Lab - P&D Multi-plataforma

## O que é este projeto
Ambiente de pesquisa e desenvolvimento para estratégias de crash game em múltiplas plataformas.
Clonado do Crash_AI (produção), mas SEM infraestrutura comercial (API, loja, licenciamento).

## Estrutura

```
src/
  bot/          # Core: strategy, bankroll, controller, setups, setups_stat
  ws/
    capture.py  # Chrome DevTools Protocol (genérico)
    parsers/    # Adaptadores por plataforma
      base.py   # Interface BaseParser
      brabet.py # Parser Brabet (extraído do capture.py original)
  gui/          # Interface Flet (licença desabilitada no Lab)
  ml/           # Machine learning (engine, train)
  data/         # Database manager
  vision/       # OCR + templates
  config.py     # Paths e constantes
notebooks/      # Pipeline de análise (01-15)
config/         # .env, profiles.json
```

## Parsers de Plataforma
Cada plataforma tem um parser em `src/ws/parsers/` que implementa `BaseParser`:
- `parse_frame(payload, opcode)` → lista de `ParsedEvent`
- Eventos padronizados: round_end, betting_phase, game_start, balance_update, bet_placed, cashout

Para adicionar nova plataforma:
1. Criar `src/ws/parsers/nova_plataforma.py`
2. Implementar `BaseParser` com parsing específico do protocolo WS
3. Registrar em `src/ws/parsers/__init__.py` no dict `PARSERS`

## Convenções
- Python 3.11
- Imports absolutos: `from src.xxx import`
- Rodar do diretório raiz: `python run.py` ou `python run_stat.py`
- Sem licenciamento - GUI auto-valida no Lab
