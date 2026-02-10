"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LogBot {
  id: number;
  sessao_id: string;
  hwid: string;
  tipo: string;
  dados: Record<string, unknown>;
  lucro: number | null;
  timestamp: string;
}

export default function AdminLogs() {
  const [logs, setLogs] = useState<LogBot[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [autoRefresh, setAutoRefresh] = useState(false);

  useEffect(() => {
    fetchLogs();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchLogs, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const fetchLogs = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/telemetria/logs`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setLogs(data);
      }
    } catch (error) {
      console.error("Erro ao buscar logs:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return "-";
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  const getLogColor = (tipo: string) => {
    switch (tipo.toLowerCase()) {
      case "vitoria": return "text-green-400";
      case "derrota": return "text-red-400";
      case "erro": return "text-yellow-400";
      case "aposta": return "text-blue-400";
      case "inicio": return "text-purple-400";
      case "pausa": return "text-orange-400";
      default: return "text-gray-400";
    }
  };

  const getLogBg = (tipo: string) => {
    switch (tipo.toLowerCase()) {
      case "vitoria": return "bg-green-600/20";
      case "derrota": return "bg-red-600/20";
      case "erro": return "bg-yellow-600/20";
      case "aposta": return "bg-blue-600/20";
      case "inicio": return "bg-purple-600/20";
      case "pausa": return "bg-orange-600/20";
      default: return "bg-gray-600/20";
    }
  };

  const tiposUnicos = ["all", ...new Set(logs.map((l) => l.tipo))];
  const filteredLogs = filter === "all" ? logs : logs.filter((l) => l.tipo === filter);

  const stats = {
    total: logs.length,
    vitorias: logs.filter((l) => l.tipo === "vitoria").length,
    derrotas: logs.filter((l) => l.tipo === "derrota").length,
    lucroTotal: logs.reduce((acc, l) => acc + (l.lucro || 0), 0),
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Telemetria</h1>
          <p className="text-gray-400">Logs de atividade do bot em tempo real</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl border transition-all ${autoRefresh ? "bg-green-600/20 border-green-500/30 text-green-400" : "bg-[#12121a] border-purple-900/30 text-gray-400 hover:text-white"}`}
          >
            <div className={`w-2 h-2 rounded-full ${autoRefresh ? "bg-green-400 animate-pulse" : "bg-gray-500"}`}></div>
            {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
          </button>
          <button onClick={fetchLogs} className="flex items-center gap-2 px-4 py-2 bg-[#12121a] border border-purple-900/30 text-gray-400 hover:text-white rounded-xl transition-colors">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Atualizar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-purple-900/30">
          <p className="text-gray-400 text-sm">Total de Logs</p>
          <p className="text-2xl font-bold text-white">{stats.total}</p>
        </div>
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-green-900/30">
          <p className="text-gray-400 text-sm">Vitorias</p>
          <p className="text-2xl font-bold text-green-400">{stats.vitorias}</p>
        </div>
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-red-900/30">
          <p className="text-gray-400 text-sm">Derrotas</p>
          <p className="text-2xl font-bold text-red-400">{stats.derrotas}</p>
        </div>
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-xl p-4 border border-emerald-900/30">
          <p className="text-gray-400 text-sm">Lucro Total</p>
          <p className={`text-2xl font-bold ${stats.lucroTotal >= 0 ? "text-emerald-400" : "text-red-400"}`}>{formatCurrency(stats.lucroTotal)}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {tiposUnicos.map((tipo) => (
          <button
            key={tipo}
            onClick={() => setFilter(tipo)}
            className={`px-4 py-2 rounded-xl font-medium capitalize transition-all ${filter === tipo ? "bg-purple-600 text-white" : "bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50"}`}
          >
            {tipo === "all" ? "Todos" : tipo}
          </button>
        ))}
      </div>

      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
        {filteredLogs.length > 0 ? (
          <div className="divide-y divide-purple-900/20">
            {filteredLogs.map((log) => (
              <div key={log.id} className="p-4 hover:bg-white/5 transition-colors">
                <div className="flex items-start gap-4">
                  <div className={`w-10 h-10 ${getLogBg(log.tipo)} rounded-lg flex items-center justify-center shrink-0`}>
                    <span className={`text-sm font-bold ${getLogColor(log.tipo)}`}>{log.tipo.charAt(0).toUpperCase()}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <span className={`font-semibold capitalize ${getLogColor(log.tipo)}`}>{log.tipo}</span>
                      <span className="text-xs text-gray-500">{formatDate(log.timestamp)}</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      <span className="text-gray-500">Sessao: <code className="text-purple-400">{log.sessao_id}</code></span>
                      <span className="text-gray-500">HWID: <code className="text-gray-400">{log.hwid?.substring(0, 12)}...</code></span>
                      {log.lucro !== null && (
                        <span className={`font-medium ${log.lucro >= 0 ? "text-green-400" : "text-red-400"}`}>{formatCurrency(log.lucro)}</span>
                      )}
                    </div>
                    {log.dados && Object.keys(log.dados).length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">Ver dados</summary>
                        <pre className="mt-2 p-3 bg-[#0a0a0f] rounded-lg text-xs text-gray-400 overflow-x-auto">{JSON.stringify(log.dados, null, 2)}</pre>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center">
            <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <p className="text-gray-500 mb-2">Nenhum log de telemetria encontrado</p>
            <p className="text-gray-600 text-sm">Os logs aparecerao aqui quando o bot comecar a enviar telemetria</p>
          </div>
        )}
      </div>
    </div>
  );
}
