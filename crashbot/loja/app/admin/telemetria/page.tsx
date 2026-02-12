'use client';

import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// =============================================================================
// INTERFACES
// =============================================================================

interface BotAtivo {
  hwid: string;
  cliente: string;
  plano: string;
  status: string;
  ultima_atividade: string | null;
  minutos_inativo: number;
  lucro_sessao: number;
  apostas_sessao: number;
  modo_risco: string | null;
  saldo_atual: number;
}

interface Alerta {
  tipo: string;
  mensagem: string;
  cliente: string;
  timestamp: string;
  severidade: string;
}

interface OperacaoData {
  periodo: string;
  resumo: {
    bots_online: number;
    total_apostas: number;
    total_explosoes: number;
    total_hits: number;
    total_misses: number;
    win_rate: number;
    lucro_total: number;
  };
  atividade_por_hora: Array<{
    hora: string;
    total: number;
    apostas: number;
  }>;
  bots_ativos: BotAtivo[];
  distribuicao_modos: Array<{
    modo: string;
    quantidade: number;
    lucro: number;
  }>;
  alertas: Alerta[];
  top_clientes: Array<{
    cliente: string;
    lucro: number;
    apostas: number;
    win_rate: number;
  }>;
}

interface LogEntry {
  id: number;
  timestamp: string;
  tipo: string;
  hwid: string | null;
  cliente_nome: string | null;
  dados: string | Record<string, unknown> | null;
  lucro: number;
}

interface LogsData {
  periodo: string;
  total: number;
  pagina: number;
  por_pagina: number;
  logs: LogEntry[];
  contagem_por_tipo: Record<string, number>;
}

type TabType = 'operacao' | 'logs';

// =============================================================================
// COMPONENTES AUXILIARES
// =============================================================================

function StatCard({
  icon,
  label,
  value,
  subvalue,
  color = 'purple',
}: {
  icon: string;
  label: string;
  value: string | number;
  subvalue?: string;
  color?: string;
}) {
  const colorClasses: Record<string, string> = {
    purple: 'from-purple-600/20 to-purple-900/10 border-purple-500/30',
    green: 'from-green-600/20 to-green-900/10 border-green-500/30',
    blue: 'from-blue-600/20 to-blue-900/10 border-blue-500/30',
    yellow: 'from-yellow-600/20 to-yellow-900/10 border-yellow-500/30',
    red: 'from-red-600/20 to-red-900/10 border-red-500/30',
    cyan: 'from-cyan-600/20 to-cyan-900/10 border-cyan-500/30',
    emerald: 'from-emerald-600/20 to-emerald-900/10 border-emerald-500/30',
  };

  return (
    <div
      className={`bg-gradient-to-br ${
        colorClasses[color] || colorClasses.purple
      } rounded-xl p-4 border`}
    >
      <span className="text-2xl">{icon}</span>
      <p className="text-2xl font-bold text-white mt-2">{value}</p>
      <p className="text-sm text-gray-400">{label}</p>
      {subvalue && <p className="text-xs text-gray-500 mt-1">{subvalue}</p>}
    </div>
  );
}

function AlertBadge({ severidade }: { severidade: string }) {
  const config: Record<string, { bg: string; text: string; icon: string }> = {
    critico: { bg: 'bg-red-500/20', text: 'text-red-400', icon: '!!' },
    alto: { bg: 'bg-orange-500/20', text: 'text-orange-400', icon: '!' },
    medio: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: '*' },
    baixo: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: 'i' },
  };

  const { bg, text, icon } = config[severidade] || config.baixo;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${bg} ${text}`}
    >
      {icon} {severidade}
    </span>
  );
}

function EmptyState({
  message,
  icon = '--',
}: {
  message: string;
  icon?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <span className="text-4xl mb-4">{icon}</span>
      <p className="text-gray-500">{message}</p>
    </div>
  );
}

// =============================================================================
// COMPONENTE PRINCIPAL
// =============================================================================

export default function TelemetriaPage() {
  const [operacaoData, setOperacaoData] = useState<OperacaoData | null>(null);
  const [logsData, setLogsData] = useState<LogsData | null>(null);

  const [activeTab, setActiveTab] = useState<TabType>('operacao');
  const [periodo, setPeriodo] = useState('24h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filtroTipoLog, setFiltroTipoLog] = useState('all');
  const [paginaLogs, setPaginaLogs] = useState(1);

  // =============================================================================
  // HELPERS
  // =============================================================================

  const getToken = () => {
    if (typeof window !== 'undefined') return localStorage.getItem('token');
    return null;
  };

  const formatCurrency = (value: number | null | undefined): string => {
    if (value === null || value === undefined || isNaN(value)) return 'R$ 0,00';
    try {
      return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    } catch {
      return 'R$ 0,00';
    }
  };

  const safeNumber = (value: number | null | undefined, decimals: number = 1): string => {
    if (value === null || value === undefined || isNaN(value)) return '0';
    try {
      return value.toFixed(decimals);
    } catch {
      return '0';
    }
  };

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return '-';
    try {
      const date = new Date(dateString);
      if (isNaN(date.getTime())) return '-';
      return date.toLocaleDateString('pt-BR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit',
      });
    } catch {
      return '-';
    }
  };

  const getTipoIcon = (tipo: string | null | undefined): string => {
    if (!tipo) return '--';
    const icons: Record<string, string> = {
      bet: 'BET', round: 'RND', sessao_inicio: 'INI', sessao_fim: 'FIM',
      hit: 'HIT', win: 'WIN', miss: 'MIS', loss: 'LOS', error: 'ERR',
    };
    return icons[tipo.toLowerCase()] || tipo.toUpperCase().slice(0, 3);
  };

  const getTipoColor = (tipo: string | null | undefined): string => {
    if (!tipo) return 'bg-gray-500/20 text-gray-400';
    const colors: Record<string, string> = {
      bet: 'bg-purple-500/20 text-purple-400',
      round: 'bg-blue-500/20 text-blue-400',
      sessao_inicio: 'bg-green-500/20 text-green-400',
      sessao_fim: 'bg-yellow-500/20 text-yellow-400',
      hit: 'bg-emerald-500/20 text-emerald-400',
      win: 'bg-emerald-500/20 text-emerald-400',
      miss: 'bg-red-500/20 text-red-400',
      loss: 'bg-red-500/20 text-red-400',
      error: 'bg-orange-500/20 text-orange-400',
    };
    return colors[tipo.toLowerCase()] || 'bg-gray-500/20 text-gray-400';
  };

  const getModoColor = (modo: string | null | undefined): string => {
    if (!modo) return 'text-gray-400';
    const colors: Record<string, string> = {
      CONSERVADOR: 'text-green-400',
      MODERADO: 'text-yellow-400',
      AGRESSIVO: 'text-red-400',
    };
    return colors[modo.toUpperCase()] || 'text-gray-400';
  };

  // =============================================================================
  // FETCH
  // =============================================================================

  const fetchData = useCallback(
    async <T,>(endpoint: string): Promise<T | null> => {
      const token = getToken();
      if (!token) {
        setError('Token nao encontrado. Faca login novamente.');
        return null;
      }
      try {
        const response = await fetch(`${API_URL}/api/v1/telemetria/${endpoint}`, {
          headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        });
        if (response.status === 401) {
          setError('Sessao expirada. Faca login novamente.');
          localStorage.removeItem('token');
          return null;
        }
        if (!response.ok) throw new Error(`Erro ${response.status}`);
        return await response.json();
      } catch (err) {
        console.error(`Erro ao buscar ${endpoint}:`, err);
        return null;
      }
    },
    []
  );

  const loadTabData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      switch (activeTab) {
        case 'operacao': {
          const data = await fetchData<OperacaoData>(`operacao?periodo=${periodo}`);
          if (data) setOperacaoData(data);
          break;
        }
        case 'logs': {
          const params = new URLSearchParams({
            periodo,
            pagina: paginaLogs.toString(),
            ...(filtroTipoLog !== 'all' && { tipo: filtroTipoLog }),
          });
          const data = await fetchData<LogsData>(`logs?${params}`);
          if (data) setLogsData(data);
          break;
        }
      }
    } finally {
      setLoading(false);
    }
  }, [activeTab, periodo, paginaLogs, filtroTipoLog, fetchData]);

  // =============================================================================
  // EFFECTS
  // =============================================================================

  useEffect(() => {
    loadTabData();
  }, [loadTabData]);

  // Auto-refresh operacao a cada 30s
  useEffect(() => {
    if (activeTab !== 'operacao') return;
    const interval = setInterval(() => loadTabData(), 30000);
    return () => clearInterval(interval);
  }, [activeTab, loadTabData]);

  // =============================================================================
  // RENDER: OPERACAO
  // =============================================================================

  const renderOperacao = () => {
    if (!operacaoData)
      return <EmptyState message="Carregando dados operacionais..." icon="--" />;

    const resumo = operacaoData.resumo || {};
    const botsAtivos = operacaoData.bots_ativos || [];
    const alertas = operacaoData.alertas || [];
    const topClientes = operacaoData.top_clientes || [];

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard icon="BOT" label="Bots Online" value={resumo.bots_online || 0} color="green" />
          <StatCard icon="BET" label="Total Apostas" value={resumo.total_apostas || 0} color="purple" />
          <StatCard icon="%" label="Win Rate" value={`${safeNumber(resumo.win_rate)}%`} color={(resumo.win_rate || 0) >= 50 ? 'green' : 'yellow'} />
          <StatCard icon="R$" label="Lucro Total" value={formatCurrency(resumo.lucro_total)} color={(resumo.lucro_total || 0) >= 0 ? 'emerald' : 'red'} />
          <StatCard icon="RND" label="Total Explosoes" value={resumo.total_explosoes || 0} color="blue" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bots Ativos */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4">Bots Ativos Agora</h2>
            {botsAtivos.length > 0 ? (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {botsAtivos.map((bot, idx) => (
                  <div
                    key={bot.hwid || idx}
                    className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20 hover:border-purple-500/30 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${bot.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
                        <span className="font-medium text-white">{bot.cliente || 'Cliente'}</span>
                      </div>
                      <span className={`text-sm font-medium ${getModoColor(bot.modo_risco)}`}>
                        {bot.modo_risco || 'N/A'}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <p className="text-gray-500">Apostas</p>
                        <p className="text-white font-medium">{bot.apostas_sessao || 0}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Lucro</p>
                        <p className={(bot.lucro_sessao || 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {formatCurrency(bot.lucro_sessao)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Saldo</p>
                        <p className="text-white">{formatCurrency(bot.saldo_atual)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Nenhum bot online no momento" icon="--" />
            )}
          </div>

          {/* Alertas */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4">Alertas Recentes</h2>
            {alertas.length > 0 ? (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {alertas.map((alerta, idx) => (
                  <div key={idx} className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20">
                    <div className="flex items-center justify-between mb-2">
                      <AlertBadge severidade={alerta.severidade || 'baixo'} />
                      <span className="text-xs text-gray-500">{formatDate(alerta.timestamp)}</span>
                    </div>
                    <p className="text-white text-sm mb-1">{alerta.mensagem || 'Sem mensagem'}</p>
                    <p className="text-gray-500 text-xs">Cliente: {alerta.cliente || 'N/A'}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Nenhum alerta no momento" icon="OK" />
            )}
          </div>
        </div>

        {/* Top Clientes */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-xl font-bold text-white mb-4">Top Clientes do Periodo</h2>
          {topClientes.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {topClientes.map((cliente, idx) => (
                <div key={idx} className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg font-bold text-purple-400">#{idx + 1}</span>
                    <span className="font-medium text-white truncate">{cliente.cliente || 'Cliente'}</span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Lucro</span>
                      <span className={(cliente.lucro || 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(cliente.lucro)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Apostas</span>
                      <span className="text-white">{cliente.apostas || 0}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="Sem dados de clientes no periodo" icon="--" />
          )}
        </div>
      </div>
    );
  };

  // =============================================================================
  // RENDER: LOGS
  // =============================================================================

  const renderLogs = () => {
    if (!logsData) return <EmptyState message="Carregando logs..." icon="--" />;

    const logs = logsData.logs || [];
    const contagemPorTipo = logsData.contagem_por_tipo || {};
    const tiposUnicos = Object.keys(contagemPorTipo);

    return (
      <div className="space-y-6">
        {/* Filtros */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl border border-purple-900/30 p-4">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="text-gray-400">Filtrar por tipo:</span>
            <button
              onClick={() => { setFiltroTipoLog('all'); setPaginaLogs(1); }}
              className={`px-4 py-2 rounded-lg transition-all ${
                filtroTipoLog === 'all'
                  ? 'bg-purple-600 text-white'
                  : 'bg-[#0a0a0f] text-gray-400 hover:text-white'
              }`}
            >
              Todos ({logsData.total || 0})
            </button>
            {tiposUnicos.map((tipo) => (
              <button
                key={tipo}
                onClick={() => { setFiltroTipoLog(tipo); setPaginaLogs(1); }}
                className={`px-4 py-2 rounded-lg transition-all flex items-center gap-2 ${
                  filtroTipoLog === tipo
                    ? 'bg-purple-600 text-white'
                    : 'bg-[#0a0a0f] text-gray-400 hover:text-white'
                }`}
              >
                {getTipoIcon(tipo)} {tipo} ({contagemPorTipo[tipo] || 0})
              </button>
            ))}
          </div>
        </div>

        {/* Tabela */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
            <table className="w-full">
              <thead className="bg-[#0a0a0f] sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Data/Hora</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Tipo</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Cliente</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Detalhes</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Lucro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-purple-900/20">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 text-white text-sm">{formatDate(log.timestamp)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${getTipoColor(log.tipo)}`}>
                        {getTipoIcon(log.tipo)} {log.tipo || 'N/A'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-white text-sm">{log.cliente_nome || 'N/A'}</p>
                      <p className="text-gray-500 text-xs font-mono">
                        {log.hwid ? `${log.hwid.slice(0, 12)}...` : 'N/A'}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-gray-300 text-sm max-w-xs truncate">
                        {typeof log.dados === 'object' && log.dados !== null
                          ? JSON.stringify(log.dados)
                          : String(log.dados || '-')}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={(log.lucro || 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(log.lucro)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {logs.length === 0 && <EmptyState message="Nenhum log encontrado" icon="--" />}
        </div>

        {/* Paginacao */}
        {(logsData.total || 0) > (logsData.por_pagina || 50) && (
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => setPaginaLogs((p) => Math.max(1, p - 1))}
              disabled={paginaLogs === 1}
              className="px-4 py-2 bg-[#12121a] border border-purple-900/30 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed hover:border-purple-500/50 transition-colors"
            >
              Anterior
            </button>
            <span className="text-gray-400">
              Pagina {paginaLogs} de {Math.ceil((logsData.total || 0) / (logsData.por_pagina || 50))}
            </span>
            <button
              onClick={() => setPaginaLogs((p) => p + 1)}
              disabled={paginaLogs >= Math.ceil((logsData.total || 0) / (logsData.por_pagina || 50))}
              className="px-4 py-2 bg-[#12121a] border border-purple-900/30 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed hover:border-purple-500/50 transition-colors"
            >
              Proxima
            </button>
          </div>
        )}
      </div>
    );
  };

  // =============================================================================
  // RETURN
  // =============================================================================

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Telemetria</h1>
          <p className="text-gray-400">
            Operacao dos bots e logs em tempo real
            {activeTab === 'operacao' && (
              <span className="ml-2 text-green-400 text-sm">
                (auto-refresh 30s)
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="px-4 py-2 bg-[#12121a] border border-purple-900/30 text-white rounded-xl focus:outline-none focus:border-purple-500"
          >
            <option value="24h">24h</option>
            <option value="7d">7 dias</option>
            <option value="30d">30 dias</option>
            <option value="all">Tudo</option>
          </select>
          <button
            onClick={() => loadTabData()}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl transition-colors flex items-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              'Atualizar'
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
          {error}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-8">
        <button
          onClick={() => setActiveTab('operacao')}
          className={`px-6 py-3 rounded-xl font-medium transition-all ${
            activeTab === 'operacao'
              ? 'bg-purple-600 text-white'
              : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
          }`}
        >
          Operacao
        </button>
        <button
          onClick={() => setActiveTab('logs')}
          className={`px-6 py-3 rounded-xl font-medium transition-all ${
            activeTab === 'logs'
              ? 'bg-purple-600 text-white'
              : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
          }`}
        >
          Logs
        </button>
      </div>

      {/* Content */}
      {loading && !operacaoData && !logsData ? (
        <div className="flex items-center justify-center p-12">
          <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
        </div>
      ) : (
        <>
          {activeTab === 'operacao' && renderOperacao()}
          {activeTab === 'logs' && renderLogs()}
        </>
      )}
    </div>
  );
}
