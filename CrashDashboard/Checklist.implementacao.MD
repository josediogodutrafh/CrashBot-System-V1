# ✅ CHECKLIST DE IMPLEMENTAÇÃO - CrashBot Admin Center V2

Use este checklist para garantir uma implementação completa e sem erros.

---

## 📦 PRÉ-INSTALAÇÃO

### Ambiente

- [ ] Python 3.8+ instalado
- [ ] pip atualizado (`pip install --upgrade pip`)
- [ ] Git instalado (opcional, para controle de versão)
- [ ] Acesso ao servidor/máquina de deploy

### Banco de Dados

- [ ] PostgreSQL 12+ disponível
- [ ] URL de conexão em mãos
- [ ] Tabelas `log_bot` e `licenca` criadas
- [ ] Colunas novas adicionadas:
  - [ ] `whatsapp` (VARCHAR)
  - [ ] `telegram_chat_id` (VARCHAR)
  - [ ] `plano_tipo` (VARCHAR)
  - [ ] `email_cliente` (VARCHAR)
  - [ ] `payment_id` (VARCHAR)
- [ ] IP do servidor na whitelist (Render/AWS/etc)

---

## 🔧 INSTALAÇÃO

### 1. Download dos Arquivos

- [ ] `dashboard_v2.py` baixado
- [ ] `requirements.txt` baixado
- [ ] Documentação baixada (opcional):
  - [ ] `README.md`
  - [ ] `DOCUMENTACAO.md`
  - [ ] `GUIA_RAPIDO.md`
  - [ ] `QUERIES_SQL_UTEIS.md`

### 2. Instalação de Dependências

```bash
# Execute no terminal:
pip install -r requirements.txt
```

- [ ] Streamlit instalado
- [ ] Pandas instalado
- [ ] SQLAlchemy instalado
- [ ] psycopg2-binary instalado
- [ ] Sem erros na instalação

### 3. Verificação

```bash
# Teste se foi instalado corretamente:
python -c "import streamlit; import pandas; import sqlalchemy; print('✅ Tudo OK!')"
```

- [ ] Comando executado sem erros

---

## ⚙️ CONFIGURAÇÃO

### 1. Ajustar URL do Banco

📍 Abra `dashboard_v2.py` - **Linha 51**

```python
DB_URL = "postgresql://usuario:senha@host:porta/database"
```

- [ ] URL configurada
- [ ] Formato correto: `postgresql://` (não `postgres://`)
- [ ] Credenciais corretas
- [ ] Host e porta corretos

### 2. Configurar Preços dos Planos

📍 Abra `dashboard_v2.py` - **Linha 215**

```python
PRECOS_PLANOS = {
    "Experimental": 49.90,   # ← Seu preço aqui
    "Semanal": 149.00,       # ← Seu preço aqui
    "Mensal": 499.00,        # ← Seu preço aqui
}
```

- [ ] Preços ajustados para valores reais
- [ ] Nomes dos planos correspondem ao banco

### 3. Ajustes Opcionais

**Cache TTL** (Linha 69):

```python
@st.cache_data(ttl=60)  # Padrão: 60 segundos
```

- [ ] TTL configurado (60s recomendado)

**Alerta de Expiração** (Linha 172):

```python
elif dias_restantes <= 3:  # Padrão: 3 dias
```

- [ ] Dias de alerta configurados

---

## 🧪 TESTES

### Teste 1: Conexão com Banco

```bash
streamlit run dashboard_v2.py
```

- [ ] Aplicação iniciou sem erros
- [ ] Não apareceu erro de conexão
- [ ] Dashboard carregou

### Teste 2: Carregamento de Dados

No dashboard:

- [ ] Sidebar aparece corretamente
- [ ] Filtro de dias funciona
- [ ] Dados aparecem nas abas

### Teste 3: Visão Macro (Aba 1)

- [ ] Cartões de métricas aparecem:
  - [ ] Faturamento Recorrente
  - [ ] Clientes Ativos
  - [ ] Vencidas
  - [ ] Expirando
- [ ] Gráfico de distribuição de planos aparece
- [ ] Métricas operacionais aparecem
- [ ] Gráfico de tendência de lucro aparece

### Teste 4: Auditoria Individual (Aba 2)

- [ ] Dropdown de clientes funciona
- [ ] Pode selecionar um cliente
- [ ] Card de informações aparece
- [ ] KPIs individuais calculam corretamente
- [ ] Gráfico de evolução aparece
- [ ] Tabela de atividades mostra logs

### Teste 5: CRM (Aba 3)

- [ ] Filtros aparecem:
  - [ ] Status (multi-select)
  - [ ] Plano (multi-select)
  - [ ] Canal (dropdown)
- [ ] Filtros funcionam corretamente
- [ ] Estatísticas rápidas atualizam
- [ ] Tabela de clientes aparece
- [ ] Botão de exportação funciona
- [ ] CSV baixa corretamente

### Teste 6: Funcionalidades Especiais

- [ ] Botão "Atualizar Dados" limpa cache
- [ ] Status temporal aparece corretamente:
  - [ ] 🟢 Ativa (>3 dias)
  - [ ] 🟡 Expirando (≤3 dias)
  - [ ] 🔴 Vencida (<0 dias)
- [ ] Campos vazios aparecem como "Não informado"

---

## 🔒 SEGURANÇA

### Verificações de Segurança

- [ ] Senha do banco NÃO está commitada no Git
- [ ] URL do banco em variável de ambiente (produção)
- [ ] HTTPS configurado (se em produção)
- [ ] Acesso restrito ao dashboard (firewall/VPN)
- [ ] Backup do banco configurado

### Boas Práticas

```python
# Recomendado para produção:
import os
DB_URL = os.environ.get('DATABASE_URL')

# Ou usar Streamlit Secrets:
import streamlit as st
DB_URL = st.secrets["database"]["url"]
```

- [ ] Credenciais em arquivo .env (não commitado)
- [ ] .gitignore configurado

---

## 🚀 DEPLOY

### Deploy Local

```bash
streamlit run dashboard_v2.py
```

- [ ] Aplicação rodando em http://localhost:8501
- [ ] Acesso via navegador funciona

### Deploy Streamlit Cloud (Opcional)

1. Criar conta no streamlit.io
2. Conectar repositório GitHub
3. Configurar secrets (DB_URL)
4. Deploy automático

- [ ] App deployado no Streamlit Cloud
- [ ] URL pública funcionando
- [ ] Secrets configurados

### Deploy em Servidor (VPS/Cloud)

```bash
# Instalar no servidor:
pip install -r requirements.txt

# Executar em background:
nohup streamlit run dashboard_v2.py --server.port 8501 &

# Ou usar PM2:
pm2 start "streamlit run dashboard_v2.py" --name crashbot-dashboard
```

- [ ] Aplicação rodando em servidor
- [ ] Porta 8501 liberada no firewall
- [ ] Processo rodando em background
- [ ] Auto-restart configurado

---

## 📊 VALIDAÇÃO FINAL

### Dados

- [ ] Faturamento calculado está correto
- [ ] Número de clientes ativos confere
- [ ] Status das licenças está correto
- [ ] Lucro da rede confere com banco
- [ ] Logs aparecem corretamente

### Performance

- [ ] Dashboard carrega em <5 segundos
- [ ] Filtros respondem instantaneamente
- [ ] Gráficos renderizam sem lag
- [ ] Cache funciona (segundo acesso é rápido)

### UX/UI

- [ ] Cores da marca aplicadas (#00FFA3)
- [ ] Textos em português corretos
- [ ] Ícones aparecem corretamente
- [ ] Layout responsivo (funciona em telas menores)
- [ ] Sem erros no console do navegador

---

## 📚 DOCUMENTAÇÃO

### Para a Equipe

- [ ] README compartilhado
- [ ] Guia rápido acessível
- [ ] Queries SQL documentadas
- [ ] Vídeo/tutorial criado (opcional)

### Treinamento

- [ ] Equipe treinada na Aba 1 (Visão Macro)
- [ ] Equipe treinada na Aba 2 (Auditoria)
- [ ] Equipe treinada na Aba 3 (CRM)
- [ ] Casos de uso comuns documentados

---

## 🔄 PÓS-DEPLOY

### Monitoramento (Primeira Semana)

- [ ] Verificar logs diariamente
- [ ] Confirmar cálculos financeiros
- [ ] Coletar feedback da equipe
- [ ] Identificar bugs/melhorias

### Backup

- [ ] Backup do código atual
- [ ] Backup do banco de dados
- [ ] Documentação versionada

### Otimização

- [ ] Índices criados no banco:

```sql
CREATE INDEX idx_log_bot_timestamp ON log_bot(timestamp);
CREATE INDEX idx_log_bot_hwid ON log_bot(hwid);
CREATE INDEX idx_licenca_ativa_expiracao ON licenca(ativa, data_expiracao);
```

- [ ] Performance monitorada
- [ ] Cache TTL ajustado conforme uso

---

## 🎯 PRÓXIMOS PASSOS

### Curto Prazo (Semana 1-2)

- [ ] Coletar feedback da equipe
- [ ] Ajustar preços/configurações conforme necessário
- [ ] Criar relatório de uso

### Médio Prazo (Mês 1)

- [ ] Implementar automação de renovação
- [ ] Criar bot de WhatsApp/Telegram
- [ ] Expandir métricas de BI

### Longo Prazo (Trimestre 1)

- [ ] API REST para integrações
- [ ] Dashboard mobile
- [ ] Relatórios automatizados

---

## ⚠️ TROUBLESHOOTING RÁPIDO

### Erro Comum 1: "Cannot connect to database"

```bash
# Verificar:
1. URL do banco está correta?
2. IP está na whitelist?
3. Credenciais estão corretas?
4. Banco está online?

# Testar manualmente:
psql postgresql://usuario:senha@host/db
```

### Erro Comum 2: "Module not found"

```bash
pip install -r requirements.txt
```

### Erro Comum 3: Tabela vazia

```bash
# Verificar:
1. Há dados no período selecionado?
2. Filtros não estão muito restritivos?
3. Bots estão enviando dados?
```

### Erro Comum 4: Cálculos incorretos

```bash
# Verificar:
1. PRECOS_PLANOS estão corretos?
2. Nomes dos planos coincidem com banco?
3. Dados do banco estão corretos?
```

---

## 📞 SUPORTE

### Recursos

- 📚 [README.md](README.md) - Visão geral
- 📚 [DOCUMENTACAO.md](DOCUMENTACAO.md) - Técnico
- 📚 [GUIA_RAPIDO.md](GUIA_RAPIDO.md) - Uso prático
- 📚 [QUERIES_SQL_UTEIS.md](QUERIES_SQL_UTEIS.md) - Análises

### Contato

- 💬 Equipe de desenvolvimento
- 📧 Email de suporte
- 💻 GitHub Issues (se aplicável)

---

## ✅ CHECKLIST FINAL

Antes de marcar como "CONCLUÍDO", verifique:

- [ ] ✅ Todos os testes passaram
- [ ] ✅ Configurações ajustadas
- [ ] ✅ Deploy realizado com sucesso
- [ ] ✅ Equipe treinada
- [ ] ✅ Documentação distribuída
- [ ] ✅ Backup criado
- [ ] ✅ Monitoramento ativo

---

## 🎉 IMPLEMENTAÇÃO CONCLUÍDA!

Parabéns! O CrashBot Admin Center V2 está rodando!

**Data de Conclusão:** \_**\_/\_\_**/**\_\_\_\_**  
**Responsável:** **********\_\_\_**********  
**Versão:** 2.0

---

**Próximas revisões:** Mensal  
**Última atualização deste checklist:** 27/11/2025
