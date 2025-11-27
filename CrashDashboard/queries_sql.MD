# 🗄️ QUERIES SQL ÚTEIS - CrashBot Database

Este arquivo contém queries SQL prontas para análises diretas no banco de dados.

---

## 📊 ANÁLISES FINANCEIRAS

### 1. Faturamento Total Ativo

```sql
-- Soma o valor de todas as licenças ativas
-- (você precisa criar uma tabela de preços ou usar CASE)
SELECT
    plano_tipo,
    COUNT(*) as quantidade,
    CASE
        WHEN plano_tipo = 'Experimental' THEN COUNT(*) * 49.90
        WHEN plano_tipo = 'Semanal' THEN COUNT(*) * 149.00
        WHEN plano_tipo = 'Mensal' THEN COUNT(*) * 499.00
        ELSE 0
    END as faturamento
FROM licenca
WHERE ativa = TRUE
GROUP BY plano_tipo
ORDER BY faturamento DESC;
```

### 2. MRR (Monthly Recurring Revenue)

```sql
-- Apenas planos mensais ativos
SELECT
    COUNT(*) as clientes_mensais,
    COUNT(*) * 499.00 as mrr_total
FROM licenca
WHERE ativa = TRUE
  AND plano_tipo = 'Mensal';
```

### 3. Distribuição de Receita por Plano

```sql
-- Percentual de receita por tipo de plano
WITH receita_plano AS (
    SELECT
        plano_tipo,
        CASE
            WHEN plano_tipo = 'Experimental' THEN COUNT(*) * 49.90
            WHEN plano_tipo = 'Semanal' THEN COUNT(*) * 149.00
            WHEN plano_tipo = 'Mensal' THEN COUNT(*) * 499.00
            ELSE 0
        END as valor
    FROM licenca
    WHERE ativa = TRUE
    GROUP BY plano_tipo
)
SELECT
    plano_tipo,
    valor,
    ROUND(valor / SUM(valor) OVER () * 100, 2) as percentual
FROM receita_plano
ORDER BY valor DESC;
```

---

## 👥 ANÁLISES DE CLIENTES

### 4. Clientes por Status

```sql
-- Conta clientes ativos, vencidos e expirando
SELECT
    CASE
        WHEN data_expiracao < NOW() THEN 'Vencida'
        WHEN data_expiracao <= NOW() + INTERVAL '3 days' THEN 'Expirando'
        WHEN data_expiracao > NOW() + INTERVAL '3 days' THEN 'Ativa'
        ELSE 'Sem Data'
    END as status,
    COUNT(*) as quantidade
FROM licenca
GROUP BY status
ORDER BY
    CASE status
        WHEN 'Ativa' THEN 1
        WHEN 'Expirando' THEN 2
        WHEN 'Vencida' THEN 3
        ELSE 4
    END;
```

### 5. Top 10 Clientes por Lucro

```sql
-- Clientes que mais lucraram (últimos 30 dias)
SELECT
    l.cliente_nome,
    l.plano_tipo,
    l.email_cliente,
    l.whatsapp,
    SUM(lb.lucro) as lucro_total,
    COUNT(lb.id) as total_operacoes
FROM licenca l
JOIN log_bot lb ON l.hwid = lb.hwid
WHERE lb.timestamp >= NOW() - INTERVAL '30 days'
GROUP BY l.cliente_nome, l.plano_tipo, l.email_cliente, l.whatsapp
ORDER BY lucro_total DESC
LIMIT 10;
```

### 6. Clientes Inativos (Sem Logs)

```sql
-- Licenças ativas mas sem atividade nos últimos 7 dias
SELECT
    l.cliente_nome,
    l.email_cliente,
    l.whatsapp,
    l.plano_tipo,
    l.data_expiracao
FROM licenca l
LEFT JOIN log_bot lb ON l.hwid = lb.hwid
    AND lb.timestamp >= NOW() - INTERVAL '7 days'
WHERE l.ativa = TRUE
  AND lb.id IS NULL
ORDER BY l.data_expiracao;
```

### 7. Clientes com Contato (Para Campanhas)

```sql
-- Lista clientes com WhatsApp ou Telegram
SELECT
    cliente_nome,
    plano_tipo,
    data_expiracao,
    CASE
        WHEN whatsapp IS NOT NULL AND whatsapp != '' THEN 'Sim'
        ELSE 'Não'
    END as tem_whatsapp,
    CASE
        WHEN telegram_chat_id IS NOT NULL AND telegram_chat_id != '' THEN 'Sim'
        ELSE 'Não'
    END as tem_telegram,
    email_cliente
FROM licenca
WHERE ativa = TRUE
  AND (
    whatsapp IS NOT NULL AND whatsapp != ''
    OR telegram_chat_id IS NOT NULL AND telegram_chat_id != ''
  )
ORDER BY data_expiracao;
```

---

## 🤖 ANÁLISES OPERACIONAIS

### 8. Performance Global dos Bots (Hoje)

```sql
-- Resumo operacional do dia
SELECT
    DATE(timestamp) as data,
    COUNT(*) as total_operacoes,
    SUM(CASE WHEN tipo = 'bet' THEN 1 ELSE 0 END) as apostas,
    SUM(CASE WHEN tipo = 'error' THEN 1 ELSE 0 END) as erros,
    SUM(lucro) as lucro_total,
    ROUND(AVG(lucro), 2) as lucro_medio,
    ROUND(
        SUM(CASE WHEN tipo = 'error' THEN 1 ELSE 0 END)::decimal /
        COUNT(*)::decimal * 100,
        2
    ) as taxa_erro_percent
FROM log_bot
WHERE timestamp >= CURRENT_DATE
GROUP BY DATE(timestamp);
```

### 9. Horários de Maior Atividade

```sql
-- Distribuição de operações por hora do dia (últimos 7 dias)
SELECT
    EXTRACT(HOUR FROM timestamp) as hora,
    COUNT(*) as operacoes,
    SUM(lucro) as lucro_total,
    ROUND(AVG(lucro), 2) as lucro_medio
FROM log_bot
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY EXTRACT(HOUR FROM timestamp)
ORDER BY hora;
```

### 10. Taxa de Erro por Cliente

```sql
-- Identifica clientes com alta taxa de erro
SELECT
    l.cliente_nome,
    l.email_cliente,
    COUNT(*) as total_logs,
    SUM(CASE WHEN lb.tipo = 'error' THEN 1 ELSE 0 END) as erros,
    ROUND(
        SUM(CASE WHEN lb.tipo = 'error' THEN 1 ELSE 0 END)::decimal /
        COUNT(*)::decimal * 100,
        2
    ) as taxa_erro_percent
FROM licenca l
JOIN log_bot lb ON l.hwid = lb.hwid
WHERE lb.timestamp >= NOW() - INTERVAL '7 days'
GROUP BY l.cliente_nome, l.email_cliente
HAVING SUM(CASE WHEN lb.tipo = 'error' THEN 1 ELSE 0 END) > 0
ORDER BY taxa_erro_percent DESC;
```

### 11. Logs de Erro Recentes

```sql
-- Últimos 50 erros com contexto
SELECT
    lb.timestamp,
    l.cliente_nome,
    l.email_cliente,
    lb.dados,
    lb.hwid
FROM log_bot lb
LEFT JOIN licenca l ON lb.hwid = l.hwid
WHERE lb.tipo = 'error'
ORDER BY lb.timestamp DESC
LIMIT 50;
```

---

## 📈 ANÁLISES DE CRESCIMENTO

### 12. Novos Clientes por Período

```sql
-- Cadastros dos últimos 30 dias agrupados por dia
SELECT
    DATE(created_at) as data,
    plano_tipo,
    COUNT(*) as novos_clientes
FROM licenca
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at), plano_tipo
ORDER BY data DESC, plano_tipo;
```

### 13. Taxa de Conversão (Experimental → Pago)

```sql
-- Clientes que começaram no Experimental e upgradaram
-- (requer histórico de mudanças de plano - adaptar conforme estrutura)
SELECT
    plano_tipo,
    COUNT(*) as quantidade,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentual
FROM licenca
WHERE ativa = TRUE
GROUP BY plano_tipo;
```

### 14. Churn Rate (Últimos 30 dias)

```sql
-- Taxa de cancelamento/vencimento
WITH total_inicio AS (
    SELECT COUNT(*) as total
    FROM licenca
    WHERE created_at < NOW() - INTERVAL '30 days'
),
vencidos_periodo AS (
    SELECT COUNT(*) as vencidos
    FROM licenca
    WHERE data_expiracao BETWEEN NOW() - INTERVAL '30 days' AND NOW()
      AND ativa = FALSE
)
SELECT
    ti.total as clientes_inicio_periodo,
    vp.vencidos as clientes_perdidos,
    ROUND(vp.vencidos::decimal / ti.total::decimal * 100, 2) as churn_rate_percent
FROM total_inicio ti, vencidos_periodo vp;
```

---

## 🎯 ANÁLISES DE RENOVAÇÃO

### 15. Renovações Necessárias (Próximos 7 dias)

```sql
-- Lista de clientes para contato urgente
SELECT
    cliente_nome,
    plano_tipo,
    data_expiracao,
    DATE_PART('day', data_expiracao - NOW()) as dias_restantes,
    whatsapp,
    telegram_chat_id,
    email_cliente,
    CASE
        WHEN plano_tipo = 'Experimental' THEN 49.90
        WHEN plano_tipo = 'Semanal' THEN 149.00
        WHEN plano_tipo = 'Mensal' THEN 499.00
    END as valor_renovacao
FROM licenca
WHERE ativa = TRUE
  AND data_expiracao BETWEEN NOW() AND NOW() + INTERVAL '7 days'
ORDER BY data_expiracao;
```

### 16. Receita em Risco (Expirando)

```sql
-- Valor total em licenças expirando
SELECT
    plano_tipo,
    COUNT(*) as quantidade_expirando,
    CASE
        WHEN plano_tipo = 'Experimental' THEN COUNT(*) * 49.90
        WHEN plano_tipo = 'Semanal' THEN COUNT(*) * 149.00
        WHEN plano_tipo = 'Mensal' THEN COUNT(*) * 499.00
    END as receita_em_risco
FROM licenca
WHERE ativa = TRUE
  AND data_expiracao BETWEEN NOW() AND NOW() + INTERVAL '7 days'
GROUP BY plano_tipo;
```

### 17. Histórico de Renovações

```sql
-- Padrão de renovação (requer tracking de renovações - adaptar)
-- Esta query é um exemplo conceitual
SELECT
    cliente_nome,
    COUNT(*) as total_renovacoes,
    MAX(data_expiracao) as ultima_validade,
    MIN(created_at) as cliente_desde,
    DATE_PART('day', NOW() - MIN(created_at)) as dias_como_cliente
FROM licenca
WHERE ativa = TRUE
GROUP BY cliente_nome
ORDER BY total_renovacoes DESC;
```

---

## 🔍 ANÁLISES DE SUPORTE

### 18. Auditoria Completa de Cliente

```sql
-- Visão 360° de um cliente específico
-- Substitua 'CLIENTE_NOME' pelo nome real
SELECT
    l.*,
    COUNT(lb.id) as total_operacoes,
    SUM(CASE WHEN lb.tipo = 'bet' THEN 1 ELSE 0 END) as apostas,
    SUM(CASE WHEN lb.tipo = 'error' THEN 1 ELSE 0 END) as erros,
    SUM(lb.lucro) as lucro_total,
    MAX(lb.timestamp) as ultima_atividade
FROM licenca l
LEFT JOIN log_bot lb ON l.hwid = lb.hwid
WHERE l.cliente_nome = 'CLIENTE_NOME'
GROUP BY l.id;
```

### 19. Detalhes de Erros por Cliente

```sql
-- Lista todos os erros de um cliente específico
-- Substitua 'HWID_DO_CLIENTE'
SELECT
    timestamp,
    tipo,
    dados,
    lucro
FROM log_bot
WHERE hwid = 'HWID_DO_CLIENTE'
  AND tipo = 'error'
ORDER BY timestamp DESC
LIMIT 100;
```

### 20. Comparação de Performance (Cliente vs Média)

```sql
-- Performance do cliente vs média global
WITH media_global AS (
    SELECT
        AVG(lucro) as lucro_medio,
        COUNT(*) as ops_media
    FROM log_bot
    WHERE timestamp >= NOW() - INTERVAL '30 days'
),
performance_cliente AS (
    SELECT
        l.cliente_nome,
        AVG(lb.lucro) as lucro_medio_cliente,
        COUNT(lb.id) as ops_cliente
    FROM licenca l
    JOIN log_bot lb ON l.hwid = lb.hwid
    WHERE lb.timestamp >= NOW() - INTERVAL '30 days'
    GROUP BY l.cliente_nome
)
SELECT
    pc.cliente_nome,
    pc.lucro_medio_cliente,
    mg.lucro_medio as lucro_medio_global,
    pc.lucro_medio_cliente - mg.lucro_medio as diferenca,
    CASE
        WHEN pc.lucro_medio_cliente > mg.lucro_medio THEN 'Acima da Média'
        WHEN pc.lucro_medio_cliente < mg.lucro_medio THEN 'Abaixo da Média'
        ELSE 'Na Média'
    END as status
FROM performance_cliente pc, media_global mg
ORDER BY diferenca DESC;
```

---

## 📧 EXPORTAÇÕES PARA CAMPANHAS

### 21. Lista para Email Marketing (Expirando)

```sql
-- Email + nome para campanha de renovação
SELECT
    email_cliente as email,
    cliente_nome as nome,
    plano_tipo,
    data_expiracao,
    DATE_PART('day', data_expiracao - NOW()) as dias_restantes
FROM licenca
WHERE ativa = TRUE
  AND data_expiracao BETWEEN NOW() AND NOW() + INTERVAL '7 days'
  AND email_cliente IS NOT NULL
  AND email_cliente != ''
ORDER BY data_expiracao;
```

### 22. Lista para WhatsApp (Reativação)

```sql
-- WhatsApp + contexto para reativação manual
SELECT
    whatsapp,
    cliente_nome,
    plano_tipo,
    data_expiracao,
    DATE_PART('day', NOW() - data_expiracao) as dias_vencida,
    CASE
        WHEN plano_tipo = 'Experimental' THEN 49.90
        WHEN plano_tipo = 'Semanal' THEN 149.00
        WHEN plano_tipo = 'Mensal' THEN 499.00
    END as valor_plano
FROM licenca
WHERE ativa = FALSE
  AND data_expiracao >= NOW() - INTERVAL '30 days'
  AND whatsapp IS NOT NULL
  AND whatsapp != ''
ORDER BY valor_plano DESC, dias_vencida;
```

### 23. Lista para Telegram Bot (Upgrade)

```sql
-- Clientes Experimental ativos para oferta de upgrade
SELECT
    telegram_chat_id,
    cliente_nome,
    data_expiracao,
    DATE_PART('day', data_expiracao - NOW()) as dias_restantes
FROM licenca
WHERE ativa = TRUE
  AND plano_tipo = 'Experimental'
  AND telegram_chat_id IS NOT NULL
  AND telegram_chat_id != ''
  AND data_expiracao > NOW() + INTERVAL '3 days'
ORDER BY data_expiracao;
```

---

## 🛠️ MANUTENÇÃO E LIMPEZA

### 24. Logs Antigos para Arquivar

```sql
-- Identifica logs com mais de 90 dias
SELECT
    COUNT(*) as total_logs_antigos,
    MIN(timestamp) as log_mais_antigo,
    MAX(timestamp) as log_mais_recente,
    SUM(CASE WHEN tipo = 'error' THEN 1 ELSE 0 END) as erros,
    ROUND(
        pg_size_pretty(pg_total_relation_size('log_bot'))::text::numeric, 2
    ) as tamanho_tabela_mb
FROM log_bot
WHERE timestamp < NOW() - INTERVAL '90 days';
```

### 25. Licenças Órfãs (Sem Logs)

```sql
-- Licenças que nunca foram usadas
SELECT
    l.id,
    l.cliente_nome,
    l.chave,
    l.created_at,
    l.ativa,
    l.data_expiracao
FROM licenca l
LEFT JOIN log_bot lb ON l.hwid = lb.hwid
WHERE lb.id IS NULL
ORDER BY l.created_at DESC;
```

### 26. Duplicatas de HWID (Verificação)

```sql
-- Identifica HWIDs compartilhados (possível fraude)
SELECT
    hwid,
    COUNT(DISTINCT id) as numero_licencas,
    STRING_AGG(cliente_nome, ', ') as clientes
FROM licenca
GROUP BY hwid
HAVING COUNT(DISTINCT id) > 1
ORDER BY numero_licencas DESC;
```

---

## 💡 DICAS DE USO

### Exportar para CSV no PostgreSQL

```bash
# No terminal do servidor
psql $DB_URL -c "\COPY (SELECT * FROM sua_query) TO '/tmp/resultado.csv' CSV HEADER"
```

### Usar no pgAdmin

1. Abra o Query Tool
2. Cole a query
3. Execute (F5)
4. Clique em "Export" para salvar CSV

### Usar no Python (Script)

```python
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine(DB_URL)
df = pd.read_sql(sua_query, engine)
df.to_csv('resultado.csv', index=False)
```

### Performance

- Sempre use `WHERE` com datas para filtrar
- Crie índices em `timestamp`, `hwid`, `tipo`
- Use `LIMIT` para testes iniciais
- Agregações pesadas: execute fora do horário de pico

---

## 📊 ÍNDICES RECOMENDADOS

```sql
-- Melhorar performance das queries

-- Índice em timestamp (para filtros temporais)
CREATE INDEX IF NOT EXISTS idx_log_bot_timestamp
ON log_bot(timestamp);

-- Índice em hwid (para joins)
CREATE INDEX IF NOT EXISTS idx_log_bot_hwid
ON log_bot(hwid);

-- Índice em tipo (para contagens de erro/bet)
CREATE INDEX IF NOT EXISTS idx_log_bot_tipo
ON log_bot(tipo);

-- Índice composto em licenca (filtros comuns)
CREATE INDEX IF NOT EXISTS idx_licenca_ativa_expiracao
ON licenca(ativa, data_expiracao);

-- Índice em hwid da licenca (para joins)
CREATE INDEX IF NOT EXISTS idx_licenca_hwid
ON licenca(hwid);
```

---

**🎯 Use estas queries como base e adapte conforme necessário!**

Todas as queries foram testadas conceitualmente e devem funcionar no PostgreSQL 12+.
