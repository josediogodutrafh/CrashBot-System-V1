"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type Periodo = "7d" | "30d" | "all";

interface NegocioData {
  receita_mensal_estimada: number;
  total_clientes: number;
  clientes_ativos: number;
  clientes_trial: number;
  clientes_pagos: number;
  clientes_expirados: number;
  taxa_conversao: number;
  novos_ultimos_7d: number;
  expirando_3d: number;
  distribuicao_planos: Record<string, number>;
  ultimas_vendas: Array<{
    nome: string;
    email: string;
    plano: string;
    data: string;
    valor: number;
  }>;
}

interface LicencaBasic {
  id: number;
  cliente_nome: string;
  chave: string;
  plano_tipo: string;
  ativa: boolean;
  esta_expirada: boolean;
  dias_restantes: number;
  created_at: string;
}

export default function AdminDashboard() {
  const [negocio, setNegocio] = useState<NegocioData | null>(null);
  const [recentLicencas, setRecentLicencas] = useState<LicencaBasic[]>([]);
  const [periodo, setPeriodo] = useState<Periodo>("30d");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [periodo]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [negocioData, licencasData] = await Promise.all([
        apiFetch<NegocioData>("/api/v1/telemetria/negocio"),
        apiFetch<LicencaBasic[]>("/api/v1/licencas"),
      ]);
      setNegocio(negocioData);
      setRecentLicencas(licencasData.slice(0, 5));
    } catch (error) {
      console.error("Erro ao buscar dados:", error);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (loading || !negocio) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
      </div>
    );
  }

  const kpis = [
    { label: "Receita Estimada", value: fmt(negocio.receita_mensal_estimada), color: "emerald" },
    { label: "Clientes Ativos", value: negocio.clientes_ativos, color: "green" },
    { label: "Pagos", value: negocio.clientes_pagos, color: "purple" },
    { label: "Trials", value: negocio.clientes_trial, color: "blue" },
    { label: "Conversao", value: `${negocio.taxa_conversao.toFixed(1)}%`, color: "yellow" },
    { label: "Expirando 3d", value: negocio.expirando_3d, color: "red" },
  ];

  const colorMap: Record<string, { border: string; iconBg: string; text: string; hoverBorder: string }> = {
    emerald: { border: "border-emerald-900/30", iconBg: "bg-emerald-600/20", text: "text-emerald-400", hoverBorder: "hover:border-emerald-500/50" },
    green: { border: "border-green-900/30", iconBg: "bg-green-600/20", text: "text-green-400", hoverBorder: "hover:border-green-500/50" },
    purple: { border: "border-purple-900/30", iconBg: "bg-purple-600/20", text: "text-purple-400", hoverBorder: "hover:border-purple-500/50" },
    blue: { border: "border-blue-900/30", iconBg: "bg-blue-600/20", text: "text-blue-400", hoverBorder: "hover:border-blue-500/50" },
    yellow: { border: "border-yellow-900/30", iconBg: "bg-yellow-600/20", text: "text-yellow-400", hoverBorder: "hover:border-yellow-500/50" },
    red: { border: "border-red-900/30", iconBg: "bg-red-600/20", text: "text-red-400", hoverBorder: "hover:border-red-500/50" },
  };

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-1">Dashboard</h1>
          <p className="text-gray-400">Visao geral do CrashBot</p>
        </div>
        <div className="flex gap-2 bg-[#12121a] rounded-xl p-1 border border-purple-900/30">
          {(["7d", "30d", "all"] as Periodo[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriodo(p)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                periodo === p
                  ? "bg-purple-600/30 text-purple-400"
                  : "text-gray-500 hover:text-white"
              }`}
            >
              {p === "7d" ? "7 dias" : p === "30d" ? "30 dias" : "Tudo"}
            </button>
          ))}
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        {kpis.map((kpi) => {
          const c = colorMap[kpi.color];
          return (
            <div
              key={kpi.label}
              className={`bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-5 border ${c.border} ${c.hoverBorder} transition-all duration-300`}
            >
              <p className="text-gray-400 text-xs mb-2">{kpi.label}</p>
              <p className={`text-2xl font-bold ${c.text}`}>{kpi.value}</p>
            </div>
          );
        })}
      </div>

      {/* Distribuicao + Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Distribuicao por plano */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-lg font-bold text-white mb-4">Planos</h2>
          <div className="space-y-3">
            {Object.entries(negocio.distribuicao_planos).map(([plano, qtd]) => {
              const total = negocio.total_clientes || 1;
              const pct = ((qtd / total) * 100).toFixed(0);
              const planoColor =
                plano === "mensal" ? "bg-purple-500" :
                plano === "semanal" ? "bg-blue-500" :
                plano === "trial" ? "bg-yellow-500" : "bg-gray-500";
              return (
                <div key={plano}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-300 capitalize">{plano}</span>
                    <span className="text-gray-400">{qtd} ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full ${planoColor} rounded-full`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Licencas recentes */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="p-5 border-b border-purple-900/30">
            <h2 className="text-lg font-bold text-white">Ultimas Licencas</h2>
          </div>
          <div className="divide-y divide-purple-900/20">
            {recentLicencas.map((l) => (
              <div key={l.id} className="px-5 py-3 hover:bg-white/5 transition-colors flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-purple-600/20 rounded-lg flex items-center justify-center">
                    <span className="text-purple-400 font-bold text-sm">{l.cliente_nome?.charAt(0).toUpperCase() || "?"}</span>
                  </div>
                  <div>
                    <p className="text-white text-sm font-medium">{l.cliente_nome}</p>
                    <p className="text-xs text-gray-500 capitalize">{l.plano_tipo}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${l.esta_expirada ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"}`}>
                  {l.esta_expirada ? "Expirada" : `${l.dias_restantes}d`}
                </span>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-purple-900/30">
            <Link href="/admin/licencas" className="text-purple-400 hover:text-purple-300 text-sm font-medium">
              Ver todas
            </Link>
          </div>
        </div>

        {/* Acoes Rapidas */}
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-lg font-bold text-white mb-4">Acoes Rapidas</h2>
          <div className="space-y-2">
            {[
              { href: "/admin/faturamento", label: "Faturamento", desc: "Receita e vendas", color: "emerald" },
              { href: "/admin/marketing", label: "Marketing", desc: "Funil e conversao", color: "blue" },
              { href: "/admin/telemetria", label: "Telemetria", desc: "Bots e logs", color: "yellow" },
              { href: "/admin/licencas?action=new", label: "Nova Licenca", desc: "Criar manualmente", color: "purple" },
            ].map((a) => (
              <Link
                key={a.href}
                href={a.href}
                className={`flex items-center gap-3 p-3 bg-${a.color}-600/10 hover:bg-${a.color}-600/20 border border-${a.color}-500/30 rounded-xl transition-all duration-200`}
              >
                <div>
                  <p className="text-white text-sm font-medium">{a.label}</p>
                  <p className="text-xs text-gray-500">{a.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Ultimas vendas */}
      {negocio.ultimas_vendas.length > 0 && (
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="p-5 border-b border-purple-900/30 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Ultimas Vendas</h2>
            <Link href="/admin/faturamento" className="text-purple-400 hover:text-purple-300 text-sm">
              Ver detalhes
            </Link>
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
                {negocio.ultimas_vendas.slice(0, 5).map((v, i) => (
                  <tr key={i} className="hover:bg-white/5 transition-colors">
                    <td className="px-5 py-3">
                      <p className="text-white text-sm">{v.nome}</p>
                      <p className="text-xs text-gray-500">{v.email}</p>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`text-xs px-2 py-1 rounded-full capitalize ${
                        v.plano === "mensal" ? "bg-purple-500/20 text-purple-400" : "bg-blue-500/20 text-blue-400"
                      }`}>
                        {v.plano}
                      </span>
                    </td>
                    <td className="px-5 py-3 text-emerald-400 text-sm font-medium">{fmt(v.valor)}</td>
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
