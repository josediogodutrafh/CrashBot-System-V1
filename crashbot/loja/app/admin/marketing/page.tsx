"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Periodo = "7d" | "30d" | "90d" | "all";

interface MarketingData {
  periodo: string;
  funil: {
    trials_criados: number;
    trials_ativos: number;
    trials_expirados: number;
    convertidos: number;
    taxa_conversao: number;
  };
  aquisicao_diaria: Array<{ dia: string; trials: number; pagos: number }>;
  trials_ativos: Array<{
    id: number;
    nome: string;
    email: string;
    whatsapp: string;
    dias_restantes: number;
    hwid_vinculado: boolean;
  }>;
  expirando_sem_renovar: Array<{
    id: number;
    nome: string;
    email: string;
    plano: string;
    dias_restantes: number;
  }>;
}

export default function MarketingPage() {
  const [data, setData] = useState<MarketingData | null>(null);
  const [periodo, setPeriodo] = useState<Periodo>("30d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [periodo]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await apiFetch<MarketingData>(
        `/api/v1/telemetria/marketing?periodo=${periodo}`
      );
      setData(result);
    } catch (error) {
      console.error("Erro ao buscar marketing:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  const { funil } = data;

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Marketing</h1>
          <p className="text-gray-400">Funil de conversao, aquisicao e trials</p>
        </div>
        <div className="flex gap-2 bg-[#12121a] rounded-xl p-1 border border-blue-900/30">
          {(["7d", "30d", "90d", "all"] as Periodo[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriodo(p)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                periodo === p
                  ? "bg-blue-600/30 text-blue-400"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              {p === "all" ? "Tudo" : p}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        {[
          { label: "Trials Criados", value: funil.trials_criados, color: "text-blue-400" },
          { label: "Trials Ativos", value: funil.trials_ativos, color: "text-cyan-400" },
          { label: "Expirados", value: funil.trials_expirados, color: "text-gray-400" },
          { label: "Convertidos", value: funil.convertidos, color: "text-emerald-400" },
          { label: "Taxa Conversao", value: `${funil.taxa_conversao}%`, color: "text-yellow-400" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-5 border border-blue-900/30 hover:border-blue-500/50 transition-all"
          >
            <p className="text-gray-400 text-xs mb-2">{kpi.label}</p>
            <p className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      {/* Funil visual */}
      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-blue-900/30 p-6 mb-6">
        <h2 className="text-lg font-bold text-white mb-6">Funil de Conversao</h2>
        <div className="flex flex-col gap-3 max-w-lg mx-auto">
          {[
            { label: "Trials Criados", value: funil.trials_criados, color: "bg-blue-500", width: "100%" },
            { label: "Trials Ativos", value: funil.trials_ativos, color: "bg-cyan-500", width: funil.trials_criados ? `${(funil.trials_ativos / funil.trials_criados * 100).toFixed(0)}%` : "0%" },
            { label: "Convertidos", value: funil.convertidos, color: "bg-emerald-500", width: funil.trials_criados ? `${(funil.convertidos / funil.trials_criados * 100).toFixed(0)}%` : "0%" },
          ].map((step) => (
            <div key={step.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300">{step.label}</span>
                <span className="text-gray-400">{step.value}</span>
              </div>
              <div className="h-8 bg-white/5 rounded-lg overflow-hidden">
                <div
                  className={`h-full ${step.color} rounded-lg flex items-center justify-center transition-all duration-500`}
                  style={{ width: step.width, minWidth: step.value > 0 ? "2rem" : "0" }}
                >
                  {step.value > 0 && (
                    <span className="text-xs text-white font-medium">{step.width}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Aquisicao diaria */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-blue-900/30 p-6">
          <h2 className="text-lg font-bold text-white mb-4">Aquisicao Diaria</h2>
          {data.aquisicao_diaria.length === 0 ? (
            <p className="text-gray-500 text-sm">Sem dados no periodo</p>
          ) : (
            <div className="space-y-2">
              {data.aquisicao_diaria.slice(-14).map((d) => (
                <div key={d.dia} className="flex items-center gap-3">
                  <span className="text-xs text-gray-500 w-12">{d.dia}</span>
                  <div className="flex-1 flex gap-1">
                    {d.trials > 0 && (
                      <div
                        className="h-5 bg-blue-500/60 rounded flex items-center justify-center"
                        style={{ width: `${Math.max(d.trials * 20, 20)}px` }}
                      >
                        <span className="text-[10px] text-white">{d.trials}t</span>
                      </div>
                    )}
                    {d.pagos > 0 && (
                      <div
                        className="h-5 bg-emerald-500/60 rounded flex items-center justify-center"
                        style={{ width: `${Math.max(d.pagos * 20, 20)}px` }}
                      >
                        <span className="text-[10px] text-white">{d.pagos}p</span>
                      </div>
                    )}
                    {d.trials === 0 && d.pagos === 0 && (
                      <span className="text-xs text-gray-600">--</span>
                    )}
                  </div>
                </div>
              ))}
              <div className="flex gap-4 pt-2 border-t border-blue-900/20 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-blue-500/60 rounded"></span> Trial
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 bg-emerald-500/60 rounded"></span> Pago
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Trials ativos */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-cyan-900/30 overflow-hidden">
          <div className="p-5 border-b border-cyan-900/30">
            <h2 className="text-lg font-bold text-white">
              Trials Ativos
              <span className="ml-2 text-sm text-cyan-400 font-normal">
                ({data.trials_ativos.length})
              </span>
            </h2>
          </div>
          {data.trials_ativos.length === 0 ? (
            <p className="p-5 text-gray-500 text-sm">Nenhum trial ativo</p>
          ) : (
            <div className="divide-y divide-cyan-900/20 max-h-80 overflow-y-auto">
              {data.trials_ativos.map((t) => (
                <div key={t.id} className="px-5 py-3 hover:bg-white/5 transition-colors flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">{t.nome}</p>
                    <p className="text-xs text-gray-500">{t.email}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {t.hwid_vinculado && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/20 text-green-400">HWID</span>
                    )}
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      t.dias_restantes <= 1 ? "bg-red-500/20 text-red-400" :
                      t.dias_restantes <= 3 ? "bg-yellow-500/20 text-yellow-400" :
                      "bg-cyan-500/20 text-cyan-400"
                    }`}>
                      {t.dias_restantes}d
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Expirando sem renovar */}
      {data.expirando_sem_renovar.length > 0 && (
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-red-900/30 overflow-hidden">
          <div className="p-5 border-b border-red-900/30">
            <h2 className="text-lg font-bold text-white">
              Expirando sem Renovar
              <span className="ml-2 text-sm text-red-400 font-normal">
                ({data.expirando_sem_renovar.length})
              </span>
            </h2>
            <p className="text-xs text-gray-500 mt-1">Licencas pagas expirando em ate 3 dias</p>
          </div>
          <div className="divide-y divide-red-900/20">
            {data.expirando_sem_renovar.map((e) => (
              <div key={e.id} className="px-5 py-3 hover:bg-white/5 transition-colors flex items-center justify-between">
                <div>
                  <p className="text-white text-sm font-medium">{e.nome}</p>
                  <p className="text-xs text-gray-500">{e.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 capitalize">{e.plano}</span>
                  <span className="text-xs px-2 py-1 rounded-full bg-red-500/20 text-red-400">
                    {e.dias_restantes}d
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
