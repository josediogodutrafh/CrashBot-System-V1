"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Periodo = "7d" | "30d" | "90d" | "all";

interface FaturamentoData {
  periodo: string;
  receita_estimada_mensal: number;
  vendas_por_dia: Array<{ dia: string; quantidade: number; receita: number }>;
  vendas_por_plano: Record<string, { quantidade: number; receita: number }>;
  ticket_medio: number;
  churn_rate: number;
  distribuicao_planos: Record<string, number>;
  ultimas_vendas: Array<{
    id: number;
    cliente: string;
    email: string;
    plano: string;
    data: string;
    valor: number;
  }>;
}

export default function FaturamentoPage() {
  const [data, setData] = useState<FaturamentoData | null>(null);
  const [periodo, setPeriodo] = useState<Periodo>("30d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [periodo]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await apiFetch<FaturamentoData>(
        `/api/v1/telemetria/faturamento?periodo=${periodo}`
      );
      setData(result);
    } catch (error) {
      console.error("Erro ao buscar faturamento:", error);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const fmtDate = (d: string | null | undefined): string => {
    if (!d) return '-';
    try {
      const date = new Date(d);
      if (isNaN(date.getTime())) return '-';
      return date.toLocaleDateString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return '-';
    }
  };

  if (loading || !data) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  const totalVendas = Object.values(data.vendas_por_plano).reduce(
    (acc, p) => acc + p.quantidade,
    0
  );
  const totalReceita = Object.values(data.vendas_por_plano).reduce(
    (acc, p) => acc + p.receita,
    0
  );

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Faturamento</h1>
          <p className="text-gray-400">Receita, vendas e indicadores financeiros</p>
        </div>
        <div className="flex gap-2 bg-[#12121a] rounded-xl p-1 border border-emerald-900/30">
          {(["7d", "30d", "90d", "all"] as Periodo[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriodo(p)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                periodo === p
                  ? "bg-emerald-600/30 text-emerald-400"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              {p === "all" ? "Tudo" : p}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: "Receita Mensal Est.", value: fmt(data.receita_estimada_mensal), color: "emerald" },
          { label: "Vendas no Periodo", value: totalVendas, color: "purple" },
          { label: "Ticket Medio", value: fmt(data.ticket_medio), color: "blue" },
          { label: "Churn Rate", value: `${data.churn_rate}%`, color: data.churn_rate > 20 ? "red" : "yellow" },
        ].map((kpi) => (
          <div
            key={kpi.label}
            className={`bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-5 border border-${kpi.color}-900/30 hover:border-${kpi.color}-500/50 transition-all`}
          >
            <p className="text-gray-400 text-xs mb-2">{kpi.label}</p>
            <p className={`text-2xl font-bold text-${kpi.color}-400`}>{kpi.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Vendas por plano */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-lg font-bold text-white mb-4">Vendas por Plano</h2>
          {Object.keys(data.vendas_por_plano).length === 0 ? (
            <p className="text-gray-500 text-sm">Nenhuma venda no periodo</p>
          ) : (
            <div className="space-y-4">
              {Object.entries(data.vendas_por_plano).map(([plano, info]) => {
                const pct = totalVendas > 0 ? ((info.quantidade / totalVendas) * 100).toFixed(0) : "0";
                const barColor =
                  plano === "mensal" ? "bg-purple-500" :
                  plano === "semanal" ? "bg-blue-500" : "bg-gray-500";
                return (
                  <div key={plano}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-300 capitalize">{plano}</span>
                      <span className="text-gray-400">
                        {info.quantidade} vendas - {fmt(info.receita)}
                      </span>
                    </div>
                    <div className="h-3 bg-white/5 rounded-full overflow-hidden">
                      <div className={`h-full ${barColor} rounded-full`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
              <div className="pt-3 border-t border-purple-900/20 flex justify-between text-sm">
                <span className="text-white font-medium">Total</span>
                <span className="text-emerald-400 font-bold">{fmt(totalReceita)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Vendas por dia (mini chart) */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-lg font-bold text-white mb-4">Vendas por Dia</h2>
          {data.vendas_por_dia.length === 0 ? (
            <p className="text-gray-500 text-sm">Nenhuma venda no periodo</p>
          ) : (
            <div className="space-y-1">
              {data.vendas_por_dia.slice(-14).map((d) => {
                const maxR = Math.max(...data.vendas_por_dia.map((v) => v.receita), 1);
                const pct = ((d.receita / maxR) * 100).toFixed(0);
                return (
                  <div key={d.dia} className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-12">{d.dia}</span>
                    <div className="flex-1 h-4 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-400 w-20 text-right">{fmt(d.receita)}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Distribuicao de planos */}
      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6 mb-6">
        <h2 className="text-lg font-bold text-white mb-4">Distribuicao de Planos (base total)</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(data.distribuicao_planos).map(([plano, qtd]) => {
            const totalDist = Object.values(data.distribuicao_planos).reduce((a, b) => a + b, 0);
            const pct = totalDist > 0 ? ((qtd / totalDist) * 100).toFixed(1) : "0";
            return (
              <div key={plano} className="text-center p-4 bg-white/5 rounded-xl">
                <p className="text-2xl font-bold text-white">{qtd}</p>
                <p className="text-sm text-gray-400 capitalize">{plano}</p>
                <p className="text-xs text-gray-500 mt-1">{pct}%</p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Ultimas vendas */}
      {data.ultimas_vendas.length > 0 && (
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="p-5 border-b border-purple-900/30">
            <h2 className="text-lg font-bold text-white">Ultimas Vendas</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 uppercase">
                  <th className="px-5 py-3">Cliente</th>
                  <th className="px-5 py-3">Plano</th>
                  <th className="px-5 py-3">Valor</th>
                  <th className="px-5 py-3">Data</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-purple-900/20">
                {data.ultimas_vendas.map((v, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="px-5 py-3">
                      <p className="text-white text-sm">{v.cliente}</p>
                      <p className="text-xs text-gray-500">{v.email}</p>
                    </td>
                    <td className="px-5 py-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full capitalize ${
                          v.plano === "mensal"
                            ? "bg-purple-500/20 text-purple-400"
                            : "bg-blue-500/20 text-blue-400"
                        }`}
                      >
                        {v.plano}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-emerald-400 text-sm font-medium">
                      {fmt(v.valor)}
                    </td>
                    <td className="px-5 py-3 text-gray-400 text-sm">{fmtDate(v.data)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
