'use client';

import { useCallback, useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface DashboardData {
  periodo: string;
  resumo: {
    total_logs: number;
    bots_unicos: number;
    sessoes: number;
    lucro_total: number;
    total_rounds: number;
    bots_ativos_agora: number;
  };
  por_tipo: Record<string, number>;
  atividade_por_hora: Array<{ hora: string; quantidade: number }>;
  top_licencas: Array<{
    hwid: string;
    cliente: string;
    lucro_total: number;
    total_rounds: number;
  }>;
}

interface LicencaStats {
  licenca: {
    id: number;
    chave: string;
    cliente_nome: string;
    email_cliente: string;
    plano_tipo: string;
    ativa: boolean;
    dias_restantes: number;
  };
  telemetria: {
    total_rounds: number;
    lucro_total: number;
    ultima_atividade: string | null;
    status_bot: string;
  };
}

interface LicencaDetalhes {
  licenca: Record<string, unknown>;
  periodo: string;
  estatisticas: {
    total_logs: number;
    total_sessoes: number;
    total_rounds: number;
    lucro_total: number;
    vitorias: number;
    derrotas: number;
    win_rate: number;
    primeira_atividade: string | null;
    ultima_atividade: string | null;
  } | null;
  historico_diario: Array<{ dia: string; lucro: number; rounds: number }>;
  ultimas_sessoes: Array<{
    sessao_id: string;
    inicio: string;
    fim: string;
    duracao_minutos: number;
    lucro: number;
    eventos: number;
  }>;
  mensagem?: string;
}

type TabType = 'dashboard' | 'licencas' | 'detalhes';

export default function TelemetriaPage() {
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [periodo, setPeriodo] = useState('7d');
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);

  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [licencas, setLicencas] = useState<LicencaStats[]>([]);
  const [licencaSelecionada, setLicencaSelecionada] = useState<number | null>(
    null
  );
  const [detalhes, setDetalhes] = useState<LicencaDetalhes | null>(null);

  const fetchDashboard = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(
        `${API_URL}/api/v1/telemetria/dashboard?periodo=${periodo}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const data = await response.json();
        setDashboard(data);
      }
    } catch (error) {
      console.error('Erro ao buscar dashboard:', error);
    } finally {
      setLoading(false);
    }
  }, [periodo]);

  const fetchLicencas = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(
        `${API_URL}/api/v1/telemetria/licencas-stats`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (response.ok) {
        const data = await response.json();
        setLicencas(data);
      }
    } catch (error) {
      console.error('Erro ao buscar licenças:', error);
    }
  }, []);

  const fetchDetalhes = useCallback(
    async (licencaId: number) => {
      const token = localStorage.getItem('token');
      if (!token) return;

      setLoading(true);
      try {
        const response = await fetch(
          `${API_URL}/api/v1/telemetria/licenca/${licencaId}?periodo=${periodo}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (response.ok) {
          const data = await response.json();
          setDetalhes(data);
        }
      } catch (error) {
        console.error('Erro ao buscar detalhes:', error);
      } finally {
        setLoading(false);
      }
    },
    [periodo]
  );

  useEffect(() => {
    if (activeTab === 'dashboard') {
      fetchDashboard();
    } else if (activeTab === 'licencas') {
      fetchLicencas();
    }
  }, [activeTab, periodo, fetchDashboard, fetchLicencas]);

  useEffect(() => {
    if (licencaSelecionada) {
      fetchDetalhes(licencaSelecionada);
    }
  }, [licencaSelecionada, periodo, fetchDetalhes]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(() => {
        if (activeTab === 'dashboard') fetchDashboard();
        else if (activeTab === 'licencas') fetchLicencas();
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, activeTab, fetchDashboard, fetchLicencas]);

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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'bg-green-500';
      case 'recente':
        return 'bg-yellow-500';
      case 'hoje':
        return 'bg-blue-500';
      case 'inativo':
        return 'bg-gray-500';
      default:
        return 'bg-gray-700';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'online':
        return 'Online agora';
      case 'recente':
        return 'Ativo recentemente';
      case 'hoje':
        return 'Ativo hoje';
      case 'inativo':
        return 'Inativo';
      default:
        return 'Nunca usado';
    }
  };

  const verDetalhes = (licencaId: number) => {
    setLicencaSelecionada(licencaId);
    setActiveTab('detalhes');
  };

  if (loading && !dashboard && !licencas.length) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">
            📊 Telemetria Avançada
          </h1>
          <p className="text-gray-400">Análise completa de uso do CrashBot</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={periodo}
            onChange={(e) => setPeriodo(e.target.value)}
            className="px-4 py-2 bg-[#12121a] border border-purple-900/30 text-white rounded-xl"
          >
            <option value="24h">Últimas 24h</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
            <option value="all">Todo período</option>
          </select>

          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${
              autoRefresh
                ? 'bg-green-600/20 border-green-500/30 text-green-400'
                : 'bg-[#12121a] border-purple-900/30 text-gray-400 hover:text-white'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full ${
                autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
              }`}
            ></div>
            {autoRefresh ? 'Auto ON' : 'Auto OFF'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-8">
        <button
          onClick={() => {
            setActiveTab('dashboard');
            setLicencaSelecionada(null);
          }}
          className={`px-6 py-3 rounded-xl font-medium transition-all ${
            activeTab === 'dashboard'
              ? 'bg-purple-600 text-white'
              : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
          }`}
        >
          🎯 Dashboard Geral
        </button>
        <button
          onClick={() => {
            setActiveTab('licencas');
            setLicencaSelecionada(null);
          }}
          className={`px-6 py-3 rounded-xl font-medium transition-all ${
            activeTab === 'licencas'
              ? 'bg-purple-600 text-white'
              : 'bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50'
          }`}
        >
          👥 Por Licença
        </button>
        {activeTab === 'detalhes' && (
          <button className="px-6 py-3 rounded-xl font-medium bg-purple-600 text-white">
            📋 Detalhes
          </button>
        )}
      </div>

      {/* Dashboard Geral */}
      {activeTab === 'dashboard' && dashboard && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-green-900/30">
              <p className="text-gray-400 text-sm">🟢 Bots Online</p>
              <p className="text-3xl font-bold text-green-400">
                {dashboard.resumo.bots_ativos_agora}
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-purple-900/30">
              <p className="text-gray-400 text-sm">🤖 Bots Únicos</p>
              <p className="text-3xl font-bold text-purple-400">
                {dashboard.resumo.bots_unicos}
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-blue-900/30">
              <p className="text-gray-400 text-sm">📊 Total Sessões</p>
              <p className="text-3xl font-bold text-blue-400">
                {dashboard.resumo.sessoes}
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-yellow-900/30">
              <p className="text-gray-400 text-sm">🎰 Total Rounds</p>
              <p className="text-3xl font-bold text-yellow-400">
                {dashboard.resumo.total_rounds}
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-cyan-900/30">
              <p className="text-gray-400 text-sm">📝 Total Logs</p>
              <p className="text-3xl font-bold text-cyan-400">
                {dashboard.resumo.total_logs}
              </p>
            </div>
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-emerald-900/30">
              <p className="text-gray-400 text-sm">💰 Lucro Total</p>
              <p
                className={`text-2xl font-bold ${
                  dashboard.resumo.lucro_total >= 0
                    ? 'text-emerald-400'
                    : 'text-red-400'
                }`}
              >
                {formatCurrency(dashboard.resumo.lucro_total)}
              </p>
            </div>
          </div>

          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-xl font-bold text-white mb-4">
              🏆 Top 5 Licenças por Lucro
            </h2>
            {dashboard.top_licencas.length > 0 ? (
              <div className="space-y-3">
                {dashboard.top_licencas.map((item, index) => (
                  <div
                    key={item.hwid}
                    className="flex items-center justify-between p-4 bg-[#0a0a0f] rounded-xl"
                  >
                    <div className="flex items-center gap-4">
                      <span
                        className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                          index === 0
                            ? 'bg-yellow-500 text-black'
                            : index === 1
                            ? 'bg-gray-400 text-black'
                            : index === 2
                            ? 'bg-amber-700 text-white'
                            : 'bg-gray-700 text-white'
                        }`}
                      >
                        {index + 1}
                      </span>
                      <div>
                        <p className="font-medium text-white">{item.cliente}</p>
                        <p className="text-sm text-gray-500">
                          {item.total_rounds} rounds
                        </p>
                      </div>
                    </div>
                    <p
                      className={`text-xl font-bold ${
                        item.lucro_total >= 0
                          ? 'text-green-400'
                          : 'text-red-400'
                      }`}
                    >
                      {formatCurrency(item.lucro_total)}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">
                Nenhum dado disponível
              </p>
            )}
          </div>

          {Object.keys(dashboard.por_tipo).length > 0 && (
            <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
              <h2 className="text-xl font-bold text-white mb-4">
                📈 Eventos por Tipo
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {Object.entries(dashboard.por_tipo).map(
                  ([tipo, quantidade]) => (
                    <div
                      key={tipo}
                      className="bg-[#0a0a0f] rounded-xl p-4 text-center"
                    >
                      <p className="text-2xl font-bold text-purple-400">
                        {quantidade}
                      </p>
                      <p className="text-sm text-gray-400 capitalize">{tipo}</p>
                    </div>
                  )
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Lista de Licenças */}
      {activeTab === 'licencas' && (
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#0a0a0f]">
                <tr>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Status
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Cliente
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Plano
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Rounds
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Lucro
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Última Atividade
                  </th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-gray-400">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-purple-900/20">
                {licencas.map((item) => (
                  <tr
                    key={item.licenca.id}
                    className="hover:bg-white/5 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-3 h-3 rounded-full ${getStatusColor(
                            item.telemetria.status_bot
                          )}`}
                        ></div>
                        <span className="text-sm text-gray-400">
                          {getStatusText(item.telemetria.status_bot)}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="font-medium text-white">
                        {item.licenca.cliente_nome}
                      </p>
                      <p className="text-sm text-gray-500">
                        {item.licenca.email_cliente}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-purple-600/20 text-purple-400 rounded text-sm capitalize">
                        {item.licenca.plano_tipo}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-white">
                      {item.telemetria.total_rounds}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`font-medium ${
                          item.telemetria.lucro_total >= 0
                            ? 'text-green-400'
                            : 'text-red-400'
                        }`}
                      >
                        {formatCurrency(item.telemetria.lucro_total)}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-gray-400 text-sm">
                      {formatDate(item.telemetria.ultima_atividade)}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => verDetalhes(item.licenca.id)}
                        className="px-3 py-1 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg transition-colors"
                      >
                        Ver Detalhes
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {licencas.length === 0 && (
            <div className="p-12 text-center">
              <p className="text-gray-500">Nenhuma licença encontrada</p>
            </div>
          )}
        </div>
      )}

      {/* Detalhes da Licença */}
      {activeTab === 'detalhes' && detalhes && (
        <div className="space-y-6">
          <button
            onClick={() => {
              setActiveTab('licencas');
              setLicencaSelecionada(null);
            }}
            className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
          >
            ← Voltar para lista
          </button>

          <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
            <h2 className="text-2xl font-bold text-white mb-2">
              {(detalhes.licenca as { cliente_nome?: string }).cliente_nome ||
                'Cliente'}
            </h2>
            <p className="text-gray-400">
              {(detalhes.licenca as { email_cliente?: string }).email_cliente}
            </p>
            <p className="text-purple-400 mt-2">
              Chave:{' '}
              <code className="bg-[#0a0a0f] px-2 py-1 rounded">
                {(detalhes.licenca as { chave?: string }).chave}
              </code>
            </p>
          </div>

          {detalhes.mensagem ? (
            <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-xl p-6 text-center">
              <p className="text-yellow-400">{detalhes.mensagem}</p>
            </div>
          ) : (
            detalhes.estatisticas && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-purple-900/30">
                    <p className="text-gray-400 text-sm">Total Rounds</p>
                    <p className="text-2xl font-bold text-white">
                      {detalhes.estatisticas.total_rounds}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-green-900/30">
                    <p className="text-gray-400 text-sm">Vitórias</p>
                    <p className="text-2xl font-bold text-green-400">
                      {detalhes.estatisticas.vitorias}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-red-900/30">
                    <p className="text-gray-400 text-sm">Derrotas</p>
                    <p className="text-2xl font-bold text-red-400">
                      {detalhes.estatisticas.derrotas}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-blue-900/30">
                    <p className="text-gray-400 text-sm">Win Rate</p>
                    <p className="text-2xl font-bold text-blue-400">
                      {detalhes.estatisticas.win_rate}%
                    </p>
                  </div>
                </div>

                <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-6 border border-emerald-900/30 text-center">
                  <p className="text-gray-400 text-sm mb-2">💰 Lucro Total</p>
                  <p
                    className={`text-4xl font-bold ${
                      detalhes.estatisticas.lucro_total >= 0
                        ? 'text-emerald-400'
                        : 'text-red-400'
                    }`}
                  >
                    {formatCurrency(detalhes.estatisticas.lucro_total)}
                  </p>
                </div>

                {detalhes.historico_diario.length > 0 && (
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
                    <h3 className="text-xl font-bold text-white mb-4">
                      📅 Histórico Diário
                    </h3>
                    <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
                      {detalhes.historico_diario.map((dia, index) => (
                        <div
                          key={index}
                          className="bg-[#0a0a0f] rounded-lg p-3 text-center"
                        >
                          <p className="text-xs text-gray-500">{dia.dia}</p>
                          <p
                            className={`font-bold ${
                              dia.lucro >= 0 ? 'text-green-400' : 'text-red-400'
                            }`}
                          >
                            {formatCurrency(dia.lucro)}
                          </p>
                          <p className="text-xs text-gray-600">
                            {dia.rounds} rounds
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {detalhes.ultimas_sessoes.length > 0 && (
                  <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
                    <h3 className="text-xl font-bold text-white mb-4">
                      🕐 Últimas Sessões
                    </h3>
                    <div className="space-y-3">
                      {detalhes.ultimas_sessoes.map((sessao) => (
                        <div
                          key={sessao.sessao_id}
                          className="flex items-center justify-between p-4 bg-[#0a0a0f] rounded-xl"
                        >
                          <div>
                            <p className="text-sm text-gray-500">
                              {formatDate(sessao.inicio)} -{' '}
                              {sessao.duracao_minutos} min
                            </p>
                            <p className="text-xs text-gray-600">
                              {sessao.eventos} eventos
                            </p>
                          </div>
                          <p
                            className={`font-bold ${
                              sessao.lucro >= 0
                                ? 'text-green-400'
                                : 'text-red-400'
                            }`}
                          >
                            {formatCurrency(sessao.lucro)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-6 border border-purple-900/30">
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div>
                      <p className="text-gray-400 text-sm">
                        Primeira Atividade
                      </p>
                      <p className="text-white">
                        {formatDate(detalhes.estatisticas.primeira_atividade)}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-400 text-sm">Última Atividade</p>
                      <p className="text-white">
                        {formatDate(detalhes.estatisticas.ultima_atividade)}
                      </p>
                    </div>
                  </div>
                </div>
              </>
            )
          )}
        </div>
      )}
    </div>
  );
}
