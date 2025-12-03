"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stats {
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

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats>({
    totalLicencas: 0,
    licencasAtivas: 0,
    licencasExpiradas: 0,
    licencasHoje: 0,
    receitaMes: 0,
    clientesUnicos: 0,
  });
  const [recentLicencas, setRecentLicencas] = useState<Licenca[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/licencas`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
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
          if (l.plano_tipo === "mensal") return acc + 97;
          if (l.plano_tipo === "semanal") return acc + 47;
          return acc;
        }, 0);

        setStats({
          totalLicencas: licencas.length,
          licencasAtivas: ativas.length,
          licencasExpiradas: expiradas.length,
          licencasHoje: criadasHoje.length,
          receitaMes: receita,
          clientesUnicos: emailsUnicos.size,
        });

        setRecentLicencas(licencas.slice(0, 5));
      }
    } catch (error) {
      console.error("Erro ao buscar dados:", error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number) => {
    return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Visao geral do sistema CrashBot</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-purple-900/30 hover:border-purple-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-purple-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Total Licencas</p>
          <p className="text-3xl font-bold text-white">{stats.totalLicencas}</p>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-green-900/30 hover:border-green-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-green-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Ativas</p>
          <p className="text-3xl font-bold text-green-400">{stats.licencasAtivas}</p>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-red-900/30 hover:border-red-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-red-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Expiradas</p>
          <p className="text-3xl font-bold text-red-400">{stats.licencasExpiradas}</p>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-blue-900/30 hover:border-blue-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-blue-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Hoje</p>
          <p className="text-3xl font-bold text-blue-400">{stats.licencasHoje}</p>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-yellow-900/30 hover:border-yellow-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-yellow-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Clientes</p>
          <p className="text-3xl font-bold text-yellow-400">{stats.clientesUnicos}</p>
        </div>

        <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl p-6 border border-emerald-900/30 hover:border-emerald-500/50 transition-all duration-300">
          <div className="w-12 h-12 bg-emerald-600/20 rounded-xl flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <p className="text-gray-400 text-sm mb-1">Receita Total</p>
          <p className="text-2xl font-bold text-emerald-400">{formatCurrency(stats.receitaMes)}</p>
        </div>
      </div>

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
                    <p className="text-xs text-gray-500 mt-1">{formatDate(licenca.created_at)}</p>
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
            <a href="/admin/licencas?action=new" className="flex items-center gap-3 p-4 bg-purple-600/10 hover:bg-purple-600/20 border border-purple-500/30 rounded-xl transition-all duration-200 group">
              <div className="w-10 h-10 bg-purple-600/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Nova Licenca</p>
                <p className="text-xs text-gray-500">Criar licenca manualmente</p>
              </div>
            </a>

            <a href="/admin/clientes" className="flex items-center gap-3 p-4 bg-blue-600/10 hover:bg-blue-600/20 border border-blue-500/30 rounded-xl transition-all duration-200 group">
              <div className="w-10 h-10 bg-blue-600/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Ver Clientes</p>
                <p className="text-xs text-gray-500">Gerenciar clientes</p>
              </div>
            </a>

            <a href="/admin/logs" className="flex items-center gap-3 p-4 bg-yellow-600/10 hover:bg-yellow-600/20 border border-yellow-500/30 rounded-xl transition-all duration-200 group">
              <div className="w-10 h-10 bg-yellow-600/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Telemetria</p>
                <p className="text-xs text-gray-500">Logs do bot em tempo real</p>
              </div>
            </a>

            <a href="/" target="_blank" className="flex items-center gap-3 p-4 bg-gray-600/10 hover:bg-gray-600/20 border border-gray-500/30 rounded-xl transition-all duration-200 group">
              <div className="w-10 h-10 bg-gray-600/30 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
                <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </div>
              <div>
                <p className="text-white font-medium">Abrir Loja</p>
                <p className="text-xs text-gray-500">Ver pagina publica</p>
              </div>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
