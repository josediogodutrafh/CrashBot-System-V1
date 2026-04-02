"use client";

import { useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface LicencaStats {
  totalLicencas: number;
  licencasAtivas: number;
  licencasExpiradas: number;
  licencasHoje: number;
  receitaMes: number;
  clientesUnicos: number;
}

interface Licenca {
  id: number;
  chave: string;
  cliente_nome: string;
  email_cliente: string;
  plano_tipo: string;
  ativa: boolean;
  esta_expirada: boolean;
  dias_restantes: number;
  created_at: string;
  data_expiracao: string;
}

interface BotAtivo {
  hwid: string;
  cliente: string;
  plano: string;
  status: string;
  ultima_atividade: string | null;
  minutos_inativo: number;
  modo_risco: string;
  saldo_atual: number;
  banca_inicial: number;
  lucro_sessao: number;
  apostas_sessao: number;
  hits_sessao: number;
  win_rate: number;
  estrategia: string;
}

interface OperacaoResumo {
  bots_online: number;
  total_apostas: number;
  total_hits: number;
  total_misses: number;
  win_rate: number;
  lucro_total: number;
}

export default function AdminDashboard() {
  const [licStats, setLicStats] = useState<LicencaStats>({
    totalLicencas: 0, licencasAtivas: 0, licencasExpiradas: 0,
    licencasHoje: 0, receitaMes: 0, clientesUnicos: 0,
  });
  const [recentLicencas, setRecentLicencas] = useState<Licenca[]>([]);
  const [botsAtivos, setBotsAtivos] = useState<BotAtivo[]>([]);
  const [opResumo, setOpResumo] = useState<OperacaoResumo>({
    bots_online: 0, total_apostas: 0, total_hits: 0,
    total_misses: 0, win_rate: 0, lucro_total: 0,
  });
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  const fetchLicencas = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/licencas`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) return;

      const licencas: Licenca[] = await response.json();
      const hoje = new Date();
      hoje.setHours(0, 0, 0, 0);

      const ativas = licencas.filter((l) => l.ativa && !l.esta_expirada);
      const expiradas = licencas.filter((l) => l.esta_expirada);
      const criadasHoje = licencas.filter((l) => {
        const created = new Date(l.created_at);
        created.setHours(0, 0, 0, 0);
        return created.getTime() === hoje.getTime();
      });
      const emailsUnicos = new Set(licencas.map((l) => l.email_cliente));
      const receita = licencas.reduce((acc, l) => {
        if (l.plano_tipo === "mensal") return acc + 2000;
        return acc;
      }, 0);

      setLicStats({
        totalLicencas: licencas.length,
        licencasAtivas: ativas.length,
        licencasExpiradas: expiradas.length,
        licencasHoje: criadasHoje.length,
        receitaMes: receita,
        clientesUnicos: emailsUnicos.size,
      });
      setRecentLicencas(licencas.slice(0, 5));
    } catch (error) {
      console.error("Erro ao buscar licencas:", error);
    }
  }, []);

  const fetchOperacao = useCallback(async (token: string) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/telemetria/operacao?periodo=24h`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) return;

      const data = await response.json();
      if (data.resumo) setOpResumo(data.resumo);
      if (data.bots_ativos) setBotsAtivos(data.bots_ativos);
      setLastUpdate(new Date().toLocaleTimeString("pt-BR"));
    } catch (error) {
      console.error("Erro ao buscar operacao:", error);
    }
  }, []);

  const fetchAll = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    await Promise.all([fetchLicencas(token), fetchOperacao(token)]);
    setLoading(false);
  }, [fetchLicencas, fetchOperacao]);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => {
      const token = localStorage.getItem("token");
      if (token) fetchOperacao(token);
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchAll, fetchOperacao]);

  const fmt = (v: number) =>
    v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

  const fmtDate = (s: string) =>
    new Date(s).toLocaleDateString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });

  const statusBadge = (status: string) => {
    const styles: Record<string, string> = {
      online: "bg-green-500/20 text-green-400 border-green-500/30",
      recente: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
      inativo: "bg-gray-500/20 text-gray-400 border-gray-500/30",
    };
    const labels: Record<string, string> = {
      online: "Online", recente: "Recente", inativo: "Inativo",
    };
    return (
      <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${styles[status] || styles.inativo}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${status === "online" ? "bg-green-400 animate-pulse" : status === "recente" ? "bg-yellow-400" : "bg-gray-400"}`} />
        {labels[status] || status}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-screen">
        <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
      </div>
    );
  }

  const botsOnline = botsAtivos.filter((b) => b.status === "online");

  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-gray-400">Visao geral do TucunareBot</p>
        </div>
        {lastUpdate && (
          <p className="text-xs text-gray-500">Atualizado: {lastUpdate}</p>
        )}
      </div>

      {/* Cards Operacionais */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <StatCard icon="bot" label="Bots Online" value={opResumo.bots_online} color="green" />
        <StatCard icon="license" label="Licencas Ativas" value={licStats.licencasAtivas} color="purple" />
        <StatCard icon="bet" label="Apostas (24h)" value={opResumo.total_apostas} color="blue" />
        <StatCard icon="rate" label="Win Rate" value={`${opResumo.win_rate}%`} color="yellow" />
        <StatCard icon="profit" label="Lucro Total" value={fmt(opResumo.lucro_total)} color="emerald" small />
        <StatCard icon="revenue" label="Receita Est." value={fmt(licStats.receitaMes)} color="pink" small />
      </div>

      {/* Bots em Operacao */}
      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden mb-6">
        <div className="p-6 border-b border-purple-900/30 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white">Bots em Operacao</h2>
            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
              {botsOnline.length} online
            </span>
          </div>
          <a href="/admin/telemetria" className="text-purple-400 hover:text-purple-300 text-sm transition-colors">
            Ver telemetria completa
          </a>
        </div>

        {botsAtivos.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-gray-500">Nenhum bot ativo nas ultimas 24h</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-purple-900/20">
                  <th className="text-left p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Cliente</th>
                  <th className="text-left p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                  <th className="text-right p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Saldo</th>
                  <th className="text-right p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Banca</th>
                  <th className="text-right p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Lucro</th>
                  <th className="text-right p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Apostas</th>
                  <th className="text-right p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Win Rate</th>
                  <th className="text-left p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Modo</th>
                  <th className="text-left p-4 text-xs font-medium text-gray-400 uppercase tracking-wider">Estrategia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-purple-900/10">
                {botsAtivos.map((bot, i) => {
                  const lucro = bot.lucro_sessao;
                  const lucroColor = lucro > 0 ? "text-green-400" : lucro < 0 ? "text-red-400" : "text-gray-400";
                  const wrColor = bot.win_rate >= 60 ? "text-green-400" : bot.win_rate >= 40 ? "text-yellow-400" : "text-red-400";

                  return (
                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-purple-600/20 rounded-lg flex items-center justify-center text-purple-400 font-bold text-sm">
                            {bot.cliente?.charAt(0).toUpperCase() || "?"}
                          </div>
                          <div>
                            <p className="text-white text-sm font-medium">{bot.cliente}</p>
                            <p className="text-gray-500 text-xs">{bot.plano}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4">{statusBadge(bot.status)}</td>
                      <td className="p-4 text-right text-white text-sm font-mono">{fmt(bot.saldo_atual)}</td>
                      <td className="p-4 text-right text-gray-400 text-sm font-mono">{fmt(bot.banca_inicial)}</td>
                      <td className={`p-4 text-right text-sm font-mono font-medium ${lucroColor}`}>
                        {lucro > 0 ? "+" : ""}{fmt(lucro)}
                      </td>
                      <td className="p-4 text-right text-gray-300 text-sm">
                        {bot.apostas_sessao}
                        <span className="text-gray-500 text-xs ml-1">({bot.hits_sessao}W)</span>
                      </td>
                      <td className={`p-4 text-right text-sm font-medium ${wrColor}`}>
                        {bot.win_rate}%
                      </td>
                      <td className="p-4">
                        <span className="text-xs px-2 py-0.5 bg-purple-500/10 text-purple-300 rounded">
                          {bot.modo_risco}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="text-xs text-gray-400">{bot.estrategia}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Licencas Recentes + Acoes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
          <div className="p-6 border-b border-purple-900/30">
            <h2 className="text-xl font-bold text-white">Licencas Recentes</h2>
          </div>
          <div className="divide-y divide-purple-900/20">
            {recentLicencas.map((licenca) => (
              <div key={licenca.id} className="p-4 hover:bg-white/5 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-purple-600/20 rounded-lg flex items-center justify-center">
                      <span className="text-purple-400 font-bold">{licenca.cliente_nome?.charAt(0).toUpperCase() || "?"}</span>
                    </div>
                    <div>
                      <p className="text-white font-medium">{licenca.cliente_nome}</p>
                      <p className="text-sm text-gray-500 font-mono">{licenca.chave}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-block px-2 py-1 rounded-full text-xs font-medium ${licenca.esta_expirada ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"}`}>
                      {licenca.esta_expirada ? "Expirada" : "Ativa"}
                    </span>
                    <p className="text-xs text-gray-500 mt-1">{fmtDate(licenca.created_at)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="p-4 border-t border-purple-900/30">
            <a href="/admin/licencas" className="text-purple-400 hover:text-purple-300 text-sm font-medium transition-colors">
              Ver todas as licencas
            </a>
          </div>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6">
          <h2 className="text-xl font-bold text-white mb-6">Acoes Rapidas</h2>
          <div className="space-y-3">
            <QuickAction href="/admin/licencas?action=new" color="purple" label="Nova Licenca" desc="Criar licenca manualmente" icon="plus" />
            <QuickAction href="/admin/clientes" color="blue" label="Ver Clientes" desc="Gerenciar clientes" icon="users" />
            <QuickAction href="/admin/telemetria" color="yellow" label="Telemetria" desc="Logs e metricas em tempo real" icon="chart" />
            <QuickAction href="/" color="gray" label="Abrir Loja" desc="Ver pagina publica" icon="link" external />
          </div>
        </div>
      </div>
    </div>
  );
}

/* =========== Sub-components =========== */

const STAT_STYLES: Record<string, { border: string; hoverBorder: string; iconBg: string; iconText: string; valueText: string }> = {
  green:   { border: "border-green-900/30",   hoverBorder: "hover:border-green-500/50",   iconBg: "bg-green-600/20",   iconText: "text-green-400",   valueText: "text-green-400" },
  purple:  { border: "border-purple-900/30",  hoverBorder: "hover:border-purple-500/50",  iconBg: "bg-purple-600/20",  iconText: "text-purple-400",  valueText: "text-purple-400" },
  blue:    { border: "border-blue-900/30",    hoverBorder: "hover:border-blue-500/50",    iconBg: "bg-blue-600/20",    iconText: "text-blue-400",    valueText: "text-blue-400" },
  yellow:  { border: "border-yellow-900/30",  hoverBorder: "hover:border-yellow-500/50",  iconBg: "bg-yellow-600/20",  iconText: "text-yellow-400",  valueText: "text-yellow-400" },
  emerald: { border: "border-emerald-900/30", hoverBorder: "hover:border-emerald-500/50", iconBg: "bg-emerald-600/20", iconText: "text-emerald-400", valueText: "text-emerald-400" },
  pink:    { border: "border-pink-900/30",    hoverBorder: "hover:border-pink-500/50",    iconBg: "bg-pink-600/20",    iconText: "text-pink-400",    valueText: "text-pink-400" },
  gray:    { border: "border-gray-700/30",    hoverBorder: "hover:border-gray-500/50",    iconBg: "bg-gray-600/20",    iconText: "text-gray-400",    valueText: "text-gray-400" },
};

const ICON_PATHS: Record<string, string> = {
  bot: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z",
  license: "M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z",
  bet: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  rate: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  profit: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  revenue: "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
  plus: "M12 6v6m0 0v6m0-6h6m-6 0H6",
  users: "M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z",
  chart: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  link: "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14",
};

function StatCard({ icon, label, value, color, small }: {
  icon: string; label: string; value: string | number; color: string; small?: boolean;
}) {
  const s = STAT_STYLES[color] || STAT_STYLES.gray;
  return (
    <div className={`bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-5 border ${s.border} ${s.hoverBorder} transition-all duration-300`}>
      <div className={`w-10 h-10 ${s.iconBg} rounded-xl flex items-center justify-center mb-3`}>
        <svg className={`w-5 h-5 ${s.iconText}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICON_PATHS[icon] || ICON_PATHS.bot} />
        </svg>
      </div>
      <p className="text-gray-400 text-xs mb-1">{label}</p>
      <p className={`${small ? "text-xl" : "text-2xl"} font-bold ${s.valueText}`}>{value}</p>
    </div>
  );
}

const ACTION_STYLES: Record<string, { bg: string; hoverBg: string; border: string; iconBg: string; iconText: string }> = {
  purple: { bg: "bg-purple-600/10", hoverBg: "hover:bg-purple-600/20", border: "border-purple-500/30", iconBg: "bg-purple-600/30", iconText: "text-purple-400" },
  blue:   { bg: "bg-blue-600/10",   hoverBg: "hover:bg-blue-600/20",   border: "border-blue-500/30",   iconBg: "bg-blue-600/30",   iconText: "text-blue-400" },
  yellow: { bg: "bg-yellow-600/10", hoverBg: "hover:bg-yellow-600/20", border: "border-yellow-500/30", iconBg: "bg-yellow-600/30", iconText: "text-yellow-400" },
  gray:   { bg: "bg-gray-600/10",   hoverBg: "hover:bg-gray-600/20",   border: "border-gray-500/30",   iconBg: "bg-gray-600/30",   iconText: "text-gray-400" },
};

function QuickAction({ href, color, label, desc, icon, external }: {
  href: string; color: string; label: string; desc: string; icon: string; external?: boolean;
}) {
  const s = ACTION_STYLES[color] || ACTION_STYLES.gray;
  return (
    <a
      href={href}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
      className={`flex items-center gap-3 p-4 ${s.bg} ${s.hoverBg} border ${s.border} rounded-xl transition-all duration-200 group`}
    >
      <div className={`w-10 h-10 ${s.iconBg} rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform`}>
        <svg className={`w-5 h-5 ${s.iconText}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={ICON_PATHS[icon] || ICON_PATHS.bot} />
        </svg>
      </div>
      <div>
        <p className="text-white font-medium">{label}</p>
        <p className="text-xs text-gray-500">{desc}</p>
      </div>
    </a>
  );
}
