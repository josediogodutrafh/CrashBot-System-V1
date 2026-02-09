# Analise de RNG - Brabet Crash

## Estudo Estatistico sobre 3.964.265 Rounds (Dez/2022 a Fev/2026)

---

## 1. Objetivo

Investigar se o gerador de numeros aleatorios (RNG) do jogo Crash da Brabet
(via Tipminer) apresenta comportamento compativel com aleatoriedade pura ou
se existem padroes deterministicos embutidos.

**Hipotese inicial**: O RNG mantem o mesmo comportamento desde 2023, e sequencias
de multiplicadores abaixo de 2x (LOW) nao ultrapassam 15 consecutivos.

---

## 2. Dataset

| Metrica | Valor |
|---------|-------|
| Total de rounds | 3.964.265 |
| Periodo | 2022-12-08 a 2026-02-04 |
| Cobertura | 99.1% dos dias (2 gaps = indisponibilidade da plataforma) |
| Fonte | API Tipminer (`/api/v3/history/crash/{pid}`) |
| Formatos | CSV (490 MB), Parquet (257 MB), SQLite (991 MB) |

### Distribuicao por ano

| Ano | Rounds |
|-----|--------|
| 2022 (dezembro) | 60.000 |
| 2023 | 1.251.786 |
| 2024 | 1.270.644 |
| 2025 | 1.262.805 |
| 2026 (jan-fev) | 119.030 |

---

## 3. Constatacao 1: Distribuicao Estatistica Estavel entre Anos

A distribuicao dos multiplicadores e praticamente identica de ano a ano:

| Ano | Media | Mediana | Desvio Padrao | P25 | P75 | P95 | P99 |
|-----|-------|---------|---------------|-----|-----|-----|-----|
| 2022 | 5.27 | 1.88 | 16.63 | 1.26 | 3.86 | 9.71 | 94.78 |
| 2023 | 5.28 | 1.87 | 16.92 | 1.25 | 3.83 | 9.71 | 96.60 |
| 2024 | 5.41 | 1.89 | 17.38 | 1.27 | 3.89 | 9.82 | 100.29 |
| 2025 | 5.48 | 1.89 | 17.56 | 1.27 | 3.92 | 9.99 | 103.07 |
| 2026 | 5.50 | 1.89 | 17.63 | 1.27 | 3.93 | 9.99 | 107.94 |

A proporcao LOW/HIGH tambem e estavel:

| Ano | LOW (< 2x) | HIGH (>= 2x) |
|-----|------------|---------------|
| 2022 | 54.61% | 45.40% |
| 2023 | 55.01% | 44.99% |
| 2024 | 54.35% | 45.65% |
| 2025 | 54.32% | 45.68% |
| 2026 | 54.27% | 45.73% |

**Constatacao**: Os parametros fundamentais do RNG nao mudaram significativamente.
A distribuicao por faixas de multiplicador (< 1.0, 1.0-1.5, 1.5-2.0, 2.0-3.0, etc.)
e virtualmente identica entre todos os anos. Variacoes sao da ordem de decimos
de percentual.

---

## 4. Constatacao 2: O RNG Nao e Memoryless

Em um RNG puro, a probabilidade de cada round ser LOW (~54.5%) seria constante
e independente dos rounds anteriores. Os dados mostram que nao e o caso.

### Probabilidade de continuacao da streak LOW

Dado que os ultimos K rounds foram LOW, qual a probabilidade do proximo
tambem ser LOW?

| K (LOWs seguidos) | P(prox. LOW) | P(teorico) | Ratio | Interpretacao |
|--------------------|--------------|------------|-------|---------------|
| 0 (base) | 54.83% | 54.55% | 1.00 | Normal |
| 1 | 54.81% | 54.55% | 1.00 | Normal |
| 2 | 54.76% | 54.55% | 1.00 | Normal |
| 3 | 54.82% | 54.55% | 1.00 | Normal |
| 4 | 54.85% | 54.55% | 1.00 | Normal |
| **5** | **49.97%** | 54.55% | **0.92** | **Queda inicia** |
| **6** | **48.06%** | 54.55% | **0.88** | Freio ativo |
| 7 | 47.85% | 54.55% | 0.88 | Freio ativo |
| 8 | 46.59% | 54.55% | 0.85 | Degradacao |
| 9 | 48.63% | 54.55% | 0.89 | Degradacao |
| 10 | 46.28% | 54.55% | 0.85 | Degradacao |
| 11 | 48.03% | 54.55% | 0.88 | Degradacao |
| 12 | 44.86% | 54.55% | 0.82 | Degradacao forte |

**Constatacao**: O jogo tem memoria. De 0 a 4 LOWs consecutivos, o comportamento
e indistinguivel de RNG puro. A partir do **5o LOW consecutivo**, a probabilidade
do proximo round ser LOW cai de ~55% para ~50%, e continua degradando
progressivamente. O mecanismo nao e um "cap" binario — e um peso progressivo
contra a continuacao de streaks longas.

---

## 5. Constatacao 3: O Teto Pratico de Streaks LOW Diminuiu ao Longo do Tempo

### Streaks maximas por ano

| Ano | Max streak | E[max] teorico (RNG puro) | Deficit |
|-----|-----------|---------------------------|---------|
| 2022 | 15 | 18.2 | -3.2 |
| 2023 | 19 | 23.5 | -4.5 |
| 2024 | 16 | 23.1 | -7.1 |
| 2025 | 15 | 23.0 | -8.0 |
| 2026 | 14 | 19.1 | -5.1 |

### Streaks >= 16 por periodo

| Periodo | Quantidade | Comprimentos |
|---------|-----------|--------------|
| 2022 | 0 | - |
| 2023 | 5 | 19, 17, 17, 16, 16 |
| 2024 | 3 | 16, 16, 16 |
| 2025 | 0 | - |
| 2026 | 0 | - |

### Evolucao trimestral do max streak

| Trimestre | Max | Tendencia |
|-----------|-----|-----------|
| 2022-Q4 | 15 | |
| 2023-Q1 | 17 | |
| 2023-Q2 | 14 | |
| 2023-Q3 | 19 | pico historico |
| 2023-Q4 | 16 | |
| 2024-Q1 | 15 | |
| 2024-Q2 | 16 | |
| 2024-Q3 | 16 | |
| 2024-Q4 | 16 | |
| 2025-Q1 | 14 | queda |
| 2025-Q2 | 14 | estavel |
| 2025-Q3 | 14 | estavel |
| 2025-Q4 | 15 | |
| 2026-Q1 | 14 | |

**Constatacao**: O max streak observado caiu de 19 (ago/2023) para 14-15
(2025 em diante). Todas as 8 streaks >= 16 ocorreram entre marco/2023 e
novembro/2024. A partir de 2025, nenhuma streak ultrapassou 15.

A degradacao da P(LOW) a partir da posicao 6 existe em todos os anos,
mas a intensidade varia:

| Ano | P(cont.) na posicao 6 | P(cont.) na posicao 11 |
|-----|----------------------|------------------------|
| 2023 | 0.431 | 0.427 |
| 2024 | 0.465 | 0.264 |
| 2025 | 0.473 | 0.431 |

Em 2024, a queda na posicao 11 e muito mais agressiva (ratio 0.49), o que
impede que streaks passem de 16. Em 2025, a queda comeca mais cedo e de
forma mais suave, resultando em um teto pratico de 15.

---

## 6. Constatacao 4: Agosto de 2023 e um Outlier

Em agosto de 2023 foram registradas **15 streaks >= 13** em um unico mes
(113.311 rounds), incluindo:

- 1 streak de 19 (maior de todo o dataset)
- 1 streak de 17
- 1 streak de 16
- 2 streaks de 15

Nenhum outro mes em 3+ anos se aproxima disso. O segundo lugar e
julho/2023 com 8 streaks >= 13 (max 14). Isso pode indicar que o
mecanismo de freio estava com parametros mais permissivos nesse periodo,
ou que houve uma calibragem diferente entre julho-outubro de 2023.

---

## 7. Constatacao 5: A Inversao de EV na Posicao 5

O achado de maior impacto pratico: o Expected Value (EV) de uma aposta
em HIGH (cashout 2x) inverte de negativo para positivo a partir de 5
LOWs consecutivos.

### EV por posicao na streak

| Apos K LOWs | P(HIGH) | EV (cashout 2x) | Status |
|-------------|---------|-----------------|--------|
| 0 (base) | 45.17% | -0.0966 | Negativo (house edge) |
| 1 | 45.19% | -0.0963 | Negativo |
| 2 | 45.24% | -0.0952 | Negativo |
| 3 | 45.18% | -0.0965 | Negativo |
| 4 | 45.15% | -0.0970 | Negativo |
| **5** | **50.03%** | **+0.0006** | **Positivo** |
| **6** | **51.94%** | **+0.0389** | **Positivo** |
| **7** | **52.15%** | **+0.0431** | **Positivo** |
| **8** | **53.41%** | **+0.0682** | **Positivo** |
| **9** | **51.37%** | **+0.0274** | **Positivo** |
| **10** | **53.72%** | **+0.0743** | **Positivo** |
| **11** | **51.97%** | **+0.0394** | **Positivo** |
| **12** | **55.14%** | **+0.1027** | **Positivo** |

**Constatacao**: O jogo tem house edge de ~9.7% na base (rounds sem contexto).
Porem, apos 5+ LOWs consecutivos, o EV se torna positivo para o jogador.
Quanto maior a streak, maior o edge — chegando a +10% apos 12 LOWs.

### Mediana do multiplicador pos-streak

| Apos K LOWs | Mediana |
|-------------|---------|
| 5 | 2.00x |
| 6 | 2.09x |
| 7 | 2.10x |
| 8 | 2.15x |
| 10 | 2.15x |
| 12 | 2.25x |

A mediana sobe de 1.88x (base) para 2.00-2.25x apos streaks longas.
Isso confirma que o mecanismo nao apenas reduz a probabilidade de LOW
mas tambem eleva a magnitude dos HIGH compensatorios.

---

## 8. Constatacao 6: Backtest Historico

Simulacao sobre os 3.964.265 rounds, apostando 1 unidade em cada oportunidade
com cashout em 2x:

| Trigger | Apostas | Winrate | ROI | Lucro total |
|---------|---------|---------|-----|-------------|
| >= 5 LOWs | 178.015 | 50.16% | +0.3% | +579 un. |
| >= 6 LOWs | 88.718 | 55.35% | +10.7% | +9.494 un. |
| >= 7 LOWs | 39.612 | 56.82% | +13.6% | +5.404 un. |
| >= 8 LOWs | 17.104 | 56.87% | +13.7% | +2.350 un. |
| >= 9 LOWs | 7.377 | 58.32% | +16.6% | +1.227 un. |
| >= 10 LOWs | 3.075 | 59.51% | +19.0% | +585 un. |

Com cashout em 1.5x:

| Trigger | Apostas | Winrate | ROI | Lucro total |
|---------|---------|---------|-----|-------------|
| >= 6 LOWs | 88.718 | 71.38% | +7.1% | +6.268 un. |
| >= 7 LOWs | 39.612 | 72.23% | +8.4% | +3.306 un. |
| >= 10 LOWs | 3.075 | 73.76% | +10.6% | +327 un. |

**Constatacao**: O sweet spot e **trigger >= 6 LOWs com cashout em 2x**.
Oferece o maior volume de oportunidades (88.718 em 3 anos = ~80/dia) com
ROI consistente de +10.7%. Triggers mais altos dao ROI maior mas com
muito menos oportunidades.

---

## 9. Verificacao: As Streaks Longas de 2023 Sao Reais?

As 8 streaks > 15 (todas em 2023-2024) foram verificadas individualmente:

- **ExternalIDs sequenciais** (formato inteiro em 2023): confirmado que sao
  rounds consecutivos sem gaps
- **Timestamps consecutivos**: intervalos de ~15 segundos entre rounds,
  compativel com a duracao de um round de Crash
- **IDs (UUID v7)**: ordenacao cronologica confirmada

Exemplo: a streak de 19 em 2023-08-04 tem externalIDs 109038 a 109056
(span de 18 = 19-1, exatamente correto), com timestamps de 08:29:16 a
08:34:22 (~5 minutos para 19 rounds de ~16s cada).

---

## 10. Sintese

### O que o RNG e

Nao e um RNG puro. O gerador tem dois modos de operacao:

1. **Modo normal** (0-4 LOWs consecutivos): Comporta-se como RNG puro com
   P(LOW) ~ 54.5%. Rounds sao independentes. House edge de ~9.7%.

2. **Modo freio** (5+ LOWs consecutivos): A probabilidade de LOW cai
   progressivamente (~50% na posicao 5, ~45% na posicao 12). Isso cria
   um edge positivo para o jogador que aposta em HIGH.

### O que mudou entre anos

O mecanismo fundamental e o mesmo desde 2022. A diferenca e na
**intensidade do freio**: em 2023 era mais permissivo (permitiu streaks
de ate 19), e a partir de 2025 ficou mais agressivo (teto pratico de 15).
Agosto de 2023 e um outlier historico com 15 streaks longas em um mes.

### O que isso implica

1. O jogo recompensa paciencia: esperar por 5+ LOWs consecutivos antes
   de apostar elimina o house edge e cria EV positivo.

2. A frequencia de oportunidades e alta: ~80 triggers de >= 6 LOWs por dia.

3. O mecanismo de freio garante que streaks muito longas sao raras,
   limitando o risco de drawdowns extensos para quem adota essa estrategia.

4. A compensacao e bilateral: apos streaks longas de LOW, nao apenas a
   probabilidade de HIGH aumenta, mas a magnitude do multiplicador
   tambem sobe (mediana de 1.88x base para 2.00-2.25x pos-streak).

---

## 11. Exploracao Estrategica

### 11.1 Otimizacao do Cashout

Trigger fixo em >= 6 LOWs, flat bet de 1 unidade. Qual cashout maximiza retorno?

| Cashout | Winrate | ROI | Lucro total |
|---------|---------|-----|-------------|
| 1.3x | 78.2% | +1.6% | +1.425 |
| 1.5x | 71.4% | +7.1% | +6.268 |
| 1.7x | 65.0% | +10.5% | +9.323 |
| **2.0x** | **55.4%** | **+10.7%** | **+9.494** |
| **2.5x** | **45.2%** | **+12.9%** | **+11.424** |
| 3.0x | 35.5% | +6.6% | +5.824 |
| 4.0x | 19.7% | -21.1% | -18.674 |
| 5.0x | 13.4% | -33.1% | -29.393 |

**Constatacao**: O ROI maximo e em **cashout 2.5x** (+12.9%), mas com winrate
de apenas 45%. O **cashout 2.0x** e o equilibrio ideal: ROI alto (+10.7%) com
winrate de 55% (maioria das apostas ganha). Acima de 3.0x o ROI inverte
para negativo — o mecanismo de freio favorece HIGHs moderados (2-3x),
nao explosoes.

### 11.2 Estabilidade: Zero Meses Negativos

Em 39 meses de backtest (dez/2022 a fev/2026), a estrategia trigger >= 6 /
cashout 2x / flat bet produziu **0 meses negativos**. Todo mes foi lucrativo.

| Metrica | Valor |
|---------|-------|
| Meses testados | 39 |
| Meses negativos | 0 |
| Lucro mensal medio | ~244 unidades |
| Melhor mes | Jan/2023: +561 un. |
| Pior mes | Fev/2026: +31 un. (parcial) |
| Max drawdown | 69 unidades |
| Max perdas seguidas | 13 |
| Bankroll minimo | -5 unidades (inicio) |

O drawdown maximo de 69 unidades em 88.718 apostas significa que um bankroll
de 100 unidades seria suficiente para operar com seguranca ao longo de 3 anos.

### 11.3 Horario Influencia o Rendimento

A estrategia rende mais de madrugada e menos no horario comercial:

| Faixa horaria | ROI medio | Melhor hora |
|---------------|-----------|-------------|
| 00h - 07h | +13.7% | 00h (+17.1%) |
| 08h - 15h | +8.3% | 15h (+10.0%) |
| 16h - 23h | +10.1% | 23h (+14.6%) |

**Constatacao**: O ROI de madrugada (00h-07h) e ~65% maior que no horario
de pico (08h-15h). Isso pode indicar que o mecanismo de rebalanceamento
opera com mais intensidade em horarios de menor volume, ou simplesmente
variancia estatistica.

### 11.4 Filtro por Valor do Ultimo LOW

A hipotese de que LOWs muito baixos (< 1.2x) ou muito altos (> 1.7x)
sinalizam o proximo HIGH nao se confirmou:

| Filtro | Apostas | ROI |
|--------|---------|-----|
| Ultimo LOW <= 1.2x | 37.017 | +11.1% |
| Ultimo LOW <= 1.5x | 57.518 | +10.8% |
| Sem filtro | 88.718 | +10.7% |

O ROI e praticamente o mesmo independente do valor do ultimo LOW.
O mecanismo nao e sensivel ao valor do multiplicador, apenas a
**quantidade** de LOWs consecutivos.

---

## 12. Nota sobre Martingale

Martingale classico com 3 niveis exige base = banca / 7. Com banca de 1000,
a aposta base e ~142 (niveis: 142, 284, 568). Um BUST (perder os 3 niveis)
consome ~100% da banca.

Com P(BUST) = 8.8% por ciclo, a vida media e ~12 ciclos antes de quebrar.
O pico medio antes de quebrar e ~3.500 (partindo de 1.000), mas a quebra
e inevitavel sem disciplina de saque.

**Martingale so faz sentido com gestao de risco separada** — por exemplo,
operar com fracao da banca total, ou definir metas de saque antes que o
BUST aconteca. Sem isso, a matematica garante que a quebra ocorre.

---

## 13. Limitacoes e Ressalvas

1. **Backtest nao e garantia**: Os dados cobrem 3 anos, mas a casa pode
   alterar o algoritmo a qualquer momento. O aperto progressivo dos
   streaks maximos (19 em 2023 -> 15 em 2025) sugere ajustes ativos.

2. **Latencia de execucao**: A estrategia exige entrar na rodada imediatamente
   apos detectar o trigger. Qualquer delay reduz o edge.

3. **Limites da plataforma**: A casa pode impor limites de aposta, cooldowns,
   ou bloqueios a jogadores que exibam padroes consistentes de aposta
   pos-streak.

4. **Variancia de curto prazo**: Apesar de 0 meses negativos em 39 meses,
   periodos de dias ou semanas negativos existem. O max de 13 perdas
   seguidas exige disciplina para manter a estrategia.

5. **Volume real vs backtest**: As 88.718 apostas em 3 anos pressupoe
   monitoramento continuo 24h. Na pratica, o volume sera menor.

---

*Analise realizada em 2026-02-04 sobre dados extraidos via API Tipminer.*
*Dataset completo: 3.964.265 rounds, Brabet Crash, dez/2022 a fev/2026.*
