'use client';

import { useState, useEffect, useCallback } from 'react';

// =============================================================================
// INTERFACES V3
// =============================================================================

interface NegocioData {
  periodo: string;
  clientes: {
    total: number;
    ativos: number;
    novos_periodo: number;
    churn_rate: number;
  };
  conversao: {
    trials_ativos: number;
    trials_convertidos: number;
    taxa_conversao: number;
  };
  receita: {
    total_periodo: number;
    recorrente: number;
    ticket_medio: number;
    crescimento_percent: number;
  };
  vendas_por_plano: Array<{
    plano: string;
    quantidade: number;
    receita: number;
  }>;
}

interface BotAtivo {
  hwid: string;
  cliente_nome: string;
  status: string;
  ultima_atividade: string;
  lucro_sessao: number;
  apostas_sessao: number;
  modo_risco: string;
  tempo_online: number;
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
    win_rate: number;
    lucro_total: number;
    volume_apostado: number;
  };
  bots_ativos: BotAtivo[];
  alertas: Alerta[];
  top_clientes: Array<{
    cliente_nome: string;
    lucro: number;
    apostas: number;
    win_rate: number;
  }>;
}

interface ClienteTelemetria {
  licenca: {
    id: number;
    cliente_nome: string;
    email_cliente: string;
    plano_tipo: string;
    dias_restantes: number | null;
    ativa: boolean;
    hwid: string | null;
  };
  telemetria: {
    total_apostas: number;
    lucro_total: number;
    win_rate: number;
    ultima_atividade: string | null;
    status_bot: string;
    tempo_uso_horas: number;
  };
}

interface ClientesData {
  periodo: string;
  total: number;
  clientes: ClienteTelemetria[];
}

interface LogEntry {
  id: number;
  timestamp: string;
  tipo: string;
  hwid: string;
  cliente_nome: string;
  dados: Record<string, unknown>;
  lucro: number;
}

interface LogsData {
  periodo: string;
  total: number;
  pagina: number;
  por_pagina: number;
  logs: LogEntry[];
}

interface PerformanceModo {
  modo: string;
  apostas: number;
  lucro: number;
  win_rate: number;
}

interface ClienteDetalhes {
  licenca: {
    id: number;
    cliente_nome: string;
    email_cliente: string;
    plano_tipo: string;
    dias_restantes: number | null;
    created_at: string;
  };
  estatisticas: {
    total_apostas: number;
    total_sessoes: number;
    lucro_total: number;
    win_rate: number;
    tempo_uso_total: number;
    media_apostas_sessao: number;
  };
  historico_diario: Array<{
    dia: string;
    apostas: number;
    lucro: number;
    win_rate: number;
  }>;
  ultimas_sessoes: Array<{
    sessao_id: string;
    inicio: string;
    fim: string | null;
    duracao_minutos: number;
    apostas: number;
    lucro: number;
  }>;
  performance_modos: PerformanceModo[];
}

type TabType = 'negocio' | 'operacao' | 'clientes' | 'logs';

// =============================================================================
// COMPONENTES AUXILIARES
// =============================================================================

function StatCard({
  icon,
  label,
  value,
  subvalue,
  color = 'purple',
  trend,
}: {
  icon: string;
  label: string;
  value: string | number;
  subvalue?: string;
  color?: string;
  trend?: 'up' | 'down' | 'neutral';
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

  const trendIcon = trend === 'up' ? '' : trend === 'down' ? '' : '';
  const trendColor = trend === 'up' ? 'text-green-400' : trend === 'down' ? 'text-red-400' : '';

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} rounded-xl p-4 border`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-2xl">{icon}</span>
        {trend && <span className={`text-sm ${trendColor}`}>{trendIcon}</span>}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-400">{label}</p>
      {subvalue && <p className="text-xs text-gray-500 mt-1">{subvalue}</p>}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; text: string; pulse?: boolean }> = {
    online: { color: 'bg-green-500', text: 'Online', pulse: true },
    recente: { color: 'bg-yellow-500', text: 'Recente' },
    hoje: { color: 'bg-blue-500', text: 'Hoje' },
    inativo: { color: 'bg-gray-500', text: 'Inativo' },
    nunca_usado: { color: 'bg-gray-700', text: 'Nunca usado' },
  };

  const { color, text, pulse } = config[status] || config.nunca_usado;

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2.5 h-2.5 rounded-full ${color} ${pulse ? 'animate-pulse' : ''}`} />
      <span className="text-sm text-gray-400">{text}</span>
    </div>
  );
}

function AlertBadge({ severidade }: { severidade: string }) {
  const config: Record<string, { bg: string; text: string; icon: string }> = {
    critico: { bg: 'bg-red-500/20', text: 'text-red-400', icon: '' },
    alto: { bg: 'bg-orange-500/20', text: 'text-orange-400', icon: '' },
    medio: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', icon: '' },
    baixo: { bg: 'bg-blue-500/20', text: 'text-blue-400', icon: 'ℹ' },
  };

  const { bg, text, icon } = config[severidade] || config.baixo;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${bg} ${text}`}>
      {icon} {severidade}
    </span>
  );
}

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center p-12">
      <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
    </div>
  );
}

function EmptyState({ message, icon = '' }: { message: string; icon?: string }) {
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
  // Estados de dados
  const [negocioData, setNegocioData] = useState<NegocioData | null>(null);
  const [operacaoData, setOperacaoData] = useState<OperacaoData | null>(null);
  const [clientesData, setClientesData] = useState<ClientesData | null>(null);
  const [logsData, setLogsData] = useState<LogsData | null>(null);
  const [clienteDetalhes, setClienteDetalhes] = useState<ClienteDetalhes | null>(null);

  // Estados de UI
  const [activeTab, setActiveTab] = useState<TabType>('operacao');
  const [periodo, setPeriodo] = useState('24h');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Estados específicos
  const [clienteSelecionado, setClienteSelecionado] = useState<number | null>(null);
  const [buscaCliente, setBuscaCliente] = useState('');
  const [filtroTipoLog, setFiltroTipoLog] = useState('all');
  const [paginaLogs, setPaginaLogs] = useState(1);

  // =============================================================================
  // HELPERS
  // =============================================================================

  const getToken = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('token');
    }
    return null;
  };

  const formatCurrency = (value: number) => {
    return value.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) return `${minutes}min`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}min`;
  };

  const getTipoIcon = (tipo: string) => {
    const icons: Record<string, string> = {
      bet: '',
      round: '',
      sessao_inicio: '',
      sessao_fim: '',
      hit: '',
      win: '',
      miss: '',
      loss: '',
      error: '',
    };
    return icons[tipo.toLowerCase()] || '';
  };

  const getTipoColor = (tipo: string) => {
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

  const getModoColor = (modo: string) => {
    const colors: Record<string, string> = {
      CONSERVADOR: 'text-green-400',
      MODERADO: 'text-yellow-400',
      AGRESSIVO: 'text-red-400',
    };
    return colors[modo] || 'text-gray-400';
  };

  // =============================================================================
  // FETCH FUNCTIONS
  // =============================================================================

  const fetchData = useCallback(async <T,>(endpoint: string): Promise<T | null> => {
    const token = getToken();
    if (!token) {
      setError('Token não encontrado. Faça login novamente.');
      return null;
    }

    try {
      const response = await fetch(
        `https://crash-api-jose.onrender.com/api/v1/telemetria/${endpoint}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.status === 401) {
        setError('Sessão expirada. Faça login novamente.');
        localStorage.removeItem('token');
        return null;
      }

      if (!response.ok) {
        throw new Error(`Erro ${response.status}`);
      }

      return await response.json();
    } catch (err) {
      console.error(`Erro ao buscar ${endpoint}:`, err);
      return null;
    }
  }, []);

  const loadTabData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      switch (activeTab) {
        case 'negocio': {
          const data = await fetchData<NegocioData>(`negocio?periodo=${periodo}`);
          if (data) setNegocioData(data);
          break;
        }
        case 'operacao': {
          const data = await fetchData<OperacaoData>(`operacao?periodo=${periodo}`);
          if (data) setOperacaoData(data);
          break;
        }
        case 'clientes': {
          const data = await fetchData<ClientesData>(`clientes?periodo=${periodo}`);
          if (data) setClientesData(data);
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

  const loadClienteDetalhes = useCallback(async (licencaId: number) => {
    setLoading(true);
    const data = await fetchData<ClienteDetalhes>(`cliente/${licencaId}?periodo=${periodo}`);
    if (data) setClienteDetalhes(data);
    setLoading(false);
  }, [fetchData, periodo]);

  // =============================================================================
  // EFFECTS
  // =============================================================================

  useEffect(() => {
    loadTabData();
  }, [loadTabData]);

  // Auto-refresh apenas para aba operação (a cada 30s)
  useEffect(() => {
    if (activeTab !== 'operacao') return;

    const interval = setInterval(() => {
      loadTabData();
    }, 30000);

    return () => clearInterval(interval);
  }, [activeTab, loadTabData]);

  // Carregar detalhes quando cliente selecionado
  useEffect(() => {
    if (clienteSelecionado) {
      loadClienteDetalhes(clienteSelecionado);
    }
  }, [clienteSelecionado, loadClienteDetalhes]);


  // =============================================================================
  // RENDER FUNCTIONS
  // =============================================================================

  const renderNegocio = () => {
    if (!negocioData) return <EmptyState message="Carregando dados de negócio..." />;

    return (
      <div className="space-y-6">
        {/* Cards Principais */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            icon=""
            label="Clientes Ativos"
            value={negocioData.clientes.ativos}
            subvalue={`${negocioData.clientes.novos_periodo} novos no período`}
            color="purple"
          />
          <StatCard
            icon=""
            label="Taxa Conversão"
            value={`${negocioData.conversao.taxa_conversao.toFixed(1)}%`}
            subvalue={`${negocioData.conversao.trials_convertidos}/${negocioData.conversao.trials_ativos} trials`}
            color="green"
          />
          <StatCard
            icon=""
            label="Receita Período"
            value={formatCurrency(negocioData.receita.total_periodo)}
            subvalue={`Ticket médio: ${formatCurrency(negocioData.receita.ticket_medio)}`}
            color="emerald"
            trend={negocioData.receita.crescimento_percent > 0 ? 'up' : 'down'}
          />
          <StatCard
            icon=""
            label="Churn Rate"
            value={`${negocioData.clientes.churn_rate.toFixed(1)}%`}
            subvalue="Cancelamentos no período"
            color={negocioData.clientes.churn_rate > 10 ? 'red' : 'blue'}
          />
        </div>

        {/* Vendas por Plano */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-xl font-bold text-white mb-4"> Vendas por Plano</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {negocioData.vendas_por_plano.map((plano) => (
              <div
                key={plano.plano}
                className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400 capitalize">{plano.plano}</span>
                  <span className="px-2 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm">
                    {plano.quantidade} vendas
                  </span>
                </div>
                <p className="text-2xl font-bold text-white">{formatCurrency(plano.receita)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Métricas de Crescimento */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h3 className="text-lg font-bold text-white mb-4"> Resumo de Clientes</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Total de Clientes</span>
                <span className="text-white font-bold">{negocioData.clientes.total}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Clientes Ativos</span>
                <span className="text-green-400 font-bold">{negocioData.clientes.ativos}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Novos no Período</span>
                <span className="text-purple-400 font-bold">{negocioData.clientes.novos_periodo}</span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h3 className="text-lg font-bold text-white mb-4"> Resumo Financeiro</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Receita Total</span>
                <span className="text-emerald-400 font-bold">{formatCurrency(negocioData.receita.total_periodo)}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Receita Recorrente</span>
                <span className="text-white font-bold">{formatCurrency(negocioData.receita.recorrente)}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-[#0a0a0f] rounded-lg">
                <span className="text-gray-400">Crescimento</span>
                <span className={negocioData.receita.crescimento_percent >= 0 ? 'text-green-400' : 'text-red-400'}>
                  {negocioData.receita.crescimento_percent >= 0 ? '+' : ''}{negocioData.receita.crescimento_percent.toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderOperacao = () => {
    if (!operacaoData) return <EmptyState message="Carregando dados operacionais..." />;

    return (
      <div className="space-y-6">
        {/* Cards Principais */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <StatCard
            icon=""
            label="Bots Online"
            value={operacaoData.resumo.bots_online}
            color="green"
          />
          <StatCard
            icon=""
            label="Total Apostas"
            value={operacaoData.resumo.total_apostas}
            color="purple"
          />
          <StatCard
            icon=""
            label="Win Rate"
            value={`${operacaoData.resumo.win_rate.toFixed(1)}%`}
            color={operacaoData.resumo.win_rate >= 50 ? 'green' : 'yellow'}
          />
          <StatCard
            icon=""
            label="Lucro Total"
            value={formatCurrency(operacaoData.resumo.lucro_total)}
            color={operacaoData.resumo.lucro_total >= 0 ? 'emerald' : 'red'}
          />
          <StatCard
            icon=""
            label="Volume Apostado"
            value={formatCurrency(operacaoData.resumo.volume_apostado)}
            color="blue"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Bots Ativos */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4"> Bots Ativos Agora</h2>
            {operacaoData.bots_ativos.length > 0 ? (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {operacaoData.bots_ativos.map((bot) => (
                  <div
                    key={bot.hwid}
                    className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20 hover:border-purple-500/30 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="font-medium text-white">{bot.cliente_nome}</span>
                      </div>
                      <span className={`text-sm font-medium ${getModoColor(bot.modo_risco)}`}>
                        {bot.modo_risco}
                      </span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-sm">
                      <div>
                        <p className="text-gray-500">Apostas</p>
                        <p className="text-white font-medium">{bot.apostas_sessao}</p>
                      </div>
                      <div>
                        <p className="text-gray-500">Lucro</p>
                        <p className={bot.lucro_sessao >= 0 ? 'text-green-400' : 'text-red-400'}>
                          {formatCurrency(bot.lucro_sessao)}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500">Tempo</p>
                        <p className="text-white">{formatDuration(bot.tempo_online)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Nenhum bot online no momento" icon="" />
            )}
          </div>

          {/* Alertas */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4"> Alertas Recentes</h2>
            {operacaoData.alertas.length > 0 ? (
              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {operacaoData.alertas.map((alerta, idx) => (
                  <div
                    key={idx}
                    className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <AlertBadge severidade={alerta.severidade} />
                      <span className="text-xs text-gray-500">{formatDate(alerta.timestamp)}</span>
                    </div>
                    <p className="text-white text-sm mb-1">{alerta.mensagem}</p>
                    <p className="text-gray-500 text-xs">Cliente: {alerta.cliente}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Nenhum alerta no momento" icon="" />
            )}
          </div>
        </div>

        {/* Top Clientes */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-xl font-bold text-white mb-4"> Top Clientes do Período</h2>
          {operacaoData.top_clientes.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {operacaoData.top_clientes.map((cliente, idx) => (
                <div
                  key={idx}
                  className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20"
                >
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-2xl">{idx === 0 ? '' : idx === 1 ? '' : idx === 2 ? '' : ''}</span>
                    <span className="font-medium text-white truncate">{cliente.cliente_nome}</span>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Lucro</span>
                      <span className={cliente.lucro >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(cliente.lucro)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Apostas</span>
                      <span className="text-white">{cliente.apostas}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Win Rate</span>
                      <span className="text-purple-400">{cliente.win_rate.toFixed(1)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState message="Sem dados de clientes no período" icon="" />
          )}
        </div>
      </div>
    );
  };


  const renderClientes = () => {
    if (!clientesData) return <EmptyState message="Carregando lista de clientes..." />;

    // Filtrar clientes pela busca
    const clientesFiltrados = clientesData.clientes.filter((c) => {
      if (!buscaCliente) return true;
      const termo = buscaCliente.toLowerCase();
      return (
        c.licenca.cliente_nome?.toLowerCase().includes(termo) ||
        c.licenca.email_cliente?.toLowerCase().includes(termo)
      );
    });

    return (
      <div className="space-y-6">
        {/* Barra de Busca */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl border border-purple-900/30 p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <input
                type="text"
                placeholder="Buscar por nome ou email..."
                value={buscaCliente}
                onChange={(e) => setBuscaCliente(e.target.value)}
                className="w-full px-4 py-2 pl-10 bg-[#0a0a0f] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
              />
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"></span>
            </div>
            <span className="text-gray-400 text-sm">
              {clientesFiltrados.length} de {clientesData.total} clientes
            </span>
          </div>
        </div>

        {/* Tabela de Clientes */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#0a0a0f]">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Status</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Cliente</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Plano</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Apostas</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Win Rate</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Lucro</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Última Atividade</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-purple-900/20">
                {clientesFiltrados.map((item) => (
                  <tr key={item.licenca.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-6 py-4">
                      <StatusBadge status={item.telemetria.status_bot} />
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-white">{item.licenca.cliente_nome || 'Cliente'}</p>
                      <p className="text-sm text-gray-500">{item.licenca.email_cliente}</p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm capitalize">
                        {item.licenca.plano_tipo}
                      </span>
                      {item.licenca.dias_restantes !== null && (
                        <p className="text-xs text-gray-500 mt-1">{item.licenca.dias_restantes} dias</p>
                      )}
                    </td>
                    <td className="px-6 py-4 text-white font-medium">{item.telemetria.total_apostas}</td>
                    <td className="px-6 py-4">
                      <span className={item.telemetria.win_rate >= 50 ? 'text-green-400' : 'text-yellow-400'}>
                        {item.telemetria.win_rate.toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <span className={item.telemetria.lucro_total >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
                        {formatCurrency(item.telemetria.lucro_total)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-sm">
                      {formatDate(item.telemetria.ultima_atividade)}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => setClienteSelecionado(item.licenca.id)}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors"
                      >
                        Ver Detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {clientesFiltrados.length === 0 && (
            <EmptyState message="Nenhum cliente encontrado" icon="" />
          )}
        </div>
      </div>
    );
  };

  const renderLogs = () => {
    if (!logsData) return <EmptyState message="Carregando logs..." />;

    // Tipos únicos para filtro
    const tiposUnicos = [...new Set(logsData.logs.map((log) => log.tipo))];

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
              Todos
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
                {getTipoIcon(tipo)} {tipo}
              </button>
            ))}
          </div>
        </div>

        {/* Tabela de Logs */}
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
                {logsData.logs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-white text-sm">{formatDate(log.timestamp)}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm ${getTipoColor(log.tipo)}`}>
                        {getTipoIcon(log.tipo)} {log.tipo}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-white text-sm">{log.cliente_nome || 'N/A'}</p>
                      <p className="text-gray-500 text-xs font-mono">{log.hwid?.slice(0, 12)}...</p>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-gray-300 text-sm max-w-xs truncate">
                        {typeof log.dados === 'object' ? JSON.stringify(log.dados) : String(log.dados || '-')}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={log.lucro >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(log.lucro)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {logsData.logs.length === 0 && (
            <EmptyState message="Nenhum log encontrado" icon="" />
          )}
        </div>

        {/* Paginação */}
        {logsData.total > logsData.por_pagina && (
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={() => setPaginaLogs((p) => Math.max(1, p - 1))}
              disabled={paginaLogs === 1}
              className="px-4 py-2 bg-[#12121a] border border-purple-900/30 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed hover:border-purple-500/50 transition-colors"
            >
               Anterior
            </button>
            <span className="text-gray-400">
              Página {paginaLogs} de {Math.ceil(logsData.total / logsData.por_pagina)}
            </span>
            <button
              onClick={() => setPaginaLogs((p) => p + 1)}
              disabled={paginaLogs >= Math.ceil(logsData.total / logsData.por_pagina)}
              className="px-4 py-2 bg-[#12121a] border border-purple-900/30 rounded-lg text-white disabled:opacity-50 disabled:cursor-not-allowed hover:border-purple-500/50 transition-colors"
            >
              Próxima 
            </button>
          </div>
        )}
      </div>
    );
  };


  const renderClienteDetalhes = () => {
    if (!clienteDetalhes) return <LoadingSpinner />;

    return (
      <div className="space-y-6">
        {/* Botão Voltar */}
        <button
          onClick={() => {
            setClienteSelecionado(null);
            setClienteDetalhes(null);
          }}
          className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
        >
           Voltar para lista
        </button>

        {/* Header do Cliente */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                {clienteDetalhes.licenca.cliente_nome || 'Cliente'}
              </h2>
              <p className="text-gray-400">{clienteDetalhes.licenca.email_cliente}</p>
              <div className="flex items-center gap-4 mt-3">
                <span className="px-3 py-1 bg-purple-600/20 text-purple-400 rounded-full text-sm capitalize">
                  {clienteDetalhes.licenca.plano_tipo}
                </span>
                {clienteDetalhes.licenca.dias_restantes !== null && (
                  <span className="text-sm text-gray-500">
                    {clienteDetalhes.licenca.dias_restantes} dias restantes
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className="text-gray-500 text-sm">Cliente desde</p>
              <p className="text-white">{formatDate(clienteDetalhes.licenca.created_at)}</p>
            </div>
          </div>
        </div>

        {/* Cards de Estatísticas */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            icon=""
            label="Total Apostas"
            value={clienteDetalhes.estatisticas.total_apostas}
            color="purple"
          />
          <StatCard
            icon=""
            label="Total Sessões"
            value={clienteDetalhes.estatisticas.total_sessoes}
            color="blue"
          />
          <StatCard
            icon=""
            label="Win Rate"
            value={`${clienteDetalhes.estatisticas.win_rate.toFixed(1)}%`}
            color={clienteDetalhes.estatisticas.win_rate >= 50 ? 'green' : 'yellow'}
          />
          <StatCard
            icon=""
            label="Lucro Total"
            value={formatCurrency(clienteDetalhes.estatisticas.lucro_total)}
            color={clienteDetalhes.estatisticas.lucro_total >= 0 ? 'emerald' : 'red'}
          />
          <StatCard
            icon=""
            label="Tempo de Uso"
            value={`${clienteDetalhes.estatisticas.tempo_uso_total}h`}
            color="cyan"
          />
          <StatCard
            icon=""
            label="Média/Sessão"
            value={clienteDetalhes.estatisticas.media_apostas_sessao.toFixed(0)}
            subvalue="apostas"
            color="purple"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Performance por Modo */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h3 className="text-lg font-bold text-white mb-4"> Performance por Modo de Risco</h3>
            {clienteDetalhes.performance_modos.length > 0 ? (
              <div className="space-y-3">
                {clienteDetalhes.performance_modos.map((modo) => (
                  <div key={modo.modo} className="bg-[#0a0a0f] rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className={`font-medium ${getModoColor(modo.modo)}`}>{modo.modo}</span>
                      <span className="text-gray-500 text-sm">{modo.apostas} apostas</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className={modo.lucro >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(modo.lucro)}
                      </span>
                      <span className="text-purple-400">{modo.win_rate.toFixed(1)}% win</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Sem dados de modos" icon="" />
            )}
          </div>

          {/* Últimas Sessões */}
          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h3 className="text-lg font-bold text-white mb-4"> Últimas Sessões</h3>
            {clienteDetalhes.ultimas_sessoes.length > 0 ? (
              <div className="space-y-3 max-h-[300px] overflow-y-auto">
                {clienteDetalhes.ultimas_sessoes.map((sessao) => (
                  <div key={sessao.sessao_id} className="bg-[#0a0a0f] rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white text-sm">{formatDate(sessao.inicio)}</span>
                      <span className="text-gray-500 text-sm">{formatDuration(sessao.duracao_minutos)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">{sessao.apostas} apostas</span>
                      <span className={sessao.lucro >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrency(sessao.lucro)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState message="Sem sessões registradas" icon="" />
            )}
          </div>
        </div>

        {/* Histórico Diário */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h3 className="text-lg font-bold text-white mb-4"> Histórico Diário</h3>
          {clienteDetalhes.historico_diario.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-gray-500 text-sm">
                    <th className="pb-3">Data</th>
                    <th className="pb-3">Apostas</th>
                    <th className="pb-3">Win Rate</th>
                    <th className="pb-3 text-right">Lucro</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-purple-900/20">
                  {clienteDetalhes.historico_diario.map((dia) => (
                    <tr key={dia.dia} className="text-sm">
                      <td className="py-3 text-white">{dia.dia}</td>
                      <td className="py-3 text-gray-400">{dia.apostas}</td>
                      <td className="py-3 text-purple-400">{dia.win_rate.toFixed(1)}%</td>
                      <td className={`py-3 text-right ${dia.lucro >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(dia.lucro)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState message="Sem histórico disponível" icon="" />
          )}
        </div>
      </div>
    );
  };

  // =============================================================================
  // RETURN PRINCIPAL
  // =============================================================================

  if (loading && !operacaoData && !negocioData && !clientesData && !logsData) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2"> Telemetria V3</h1>
          <p className="text-gray-400">
            Dashboard completo de análise do CrashBot
            {activeTab === 'operacao' && (
              <span className="ml-2 text-green-400"> Atualização automática ativa</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="px-4 py-2 bg-[#12121a] border border-purple-900/30 text-white rounded-xl focus:outline-none focus:border-purple-500"
          >
            <option value="24h">Últimas 24h</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
            <option value="all">Todo período</option>
          </select>
          <button
            onClick={() => loadTabData()}
            disabled={loading}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-xl transition-colors flex items-center gap-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              ''
            )}
            Atualizar
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-400">
           {error}
        </div>
      )}

      {/* Tabs */}
      {!clienteSelecionado && (
        <div className="flex gap-2 mb-8 flex-wrap">
          <button
            onClick={() => setActiveTab('negocio')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'negocio'
                ? 'bg-purple-600 text-white'
                : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
            }`}
          >
             Negócio
          </button>
          <button
            onClick={() => setActiveTab('operacao')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'operacao'
                ? 'bg-purple-600 text-white'
                : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
            }`}
          >
             Operação
          </button>
          <button
            onClick={() => setActiveTab('clientes')}
            className={`px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'clientes'
                ? 'bg-purple-600 text-white'
                : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
            }`}
          >
             Clientes
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
      )}

      {/* Conteúdo */}
      {clienteSelecionado ? (
        renderClienteDetalhes()
      ) : (
        <>
          {activeTab === 'negocio' && renderNegocio()}
          {activeTab === 'operacao' && renderOperacao()}
          {activeTab === 'clientes' && renderClientes()}
          {activeTab === 'logs' && renderLogs()}
        </>
      )}
    </div>
  );
}
