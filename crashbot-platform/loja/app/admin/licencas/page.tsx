"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Licenca {
  id: number;
  chave: string;
  hwid: string | null;
  ativa: boolean;
  created_at: string;
  data_expiracao: string;
  cliente_nome: string;
  email_cliente: string;
  whatsapp: string;
  plano_tipo: string;
  esta_expirada: boolean;
  dias_restantes: number;
}

export default function AdminLicencas() {
  const [licencas, setLicencas] = useState<Licenca[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "active" | "expired">("all");
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchLicencas();
  }, []);

  const fetchLicencas = async () => {
    const token = localStorage.getItem("token");
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/licencas`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setLicencas(data);
      }
    } catch (error) {
      console.error("Erro ao buscar licencas:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAtiva = async (licenca: Licenca) => {
    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_URL}/api/v1/licencas/${licenca.id}/toggle`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        fetchLicencas();
        setMessage({ type: "success", text: `Licenca ${licenca.ativa ? "desativada" : "ativada"} com sucesso` });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Erro ao atualizar licenca" });
    }
  };

  const handleResetHWID = async (licenca: Licenca) => {
    if (!confirm(`Resetar HWID da licenca ${licenca.chave}?`)) return;
    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`${API_URL}/api/v1/licencas/${licenca.id}/reset-hwid`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        fetchLicencas();
        setMessage({ type: "success", text: "HWID resetado com sucesso" });
      }
    } catch (error) {
      setMessage({ type: "error", text: "Erro ao resetar HWID" });
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(text);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("pt-BR", {
      day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit",
    });
  };

  const filteredLicencas = licencas.filter((l) => {
    const matchSearch = l.cliente_nome?.toLowerCase().includes(search.toLowerCase()) ||
      l.email_cliente?.toLowerCase().includes(search.toLowerCase()) ||
      l.chave.toLowerCase().includes(search.toLowerCase());
    const matchFilter = filter === "all" ||
      (filter === "active" && l.ativa && !l.esta_expirada) ||
      (filter === "expired" && l.esta_expirada);
    return matchSearch && matchFilter;
  });

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
          <h1 className="text-3xl font-bold text-white mb-2">Licencas</h1>
          <p className="text-gray-400">Gerenciar todas as licencas do sistema</p>
        </div>
      </div>

      {message && (
        <div className={`mb-6 p-4 rounded-xl border ${message.type === "success" ? "bg-green-500/10 border-green-500/30 text-green-400" : "bg-red-500/10 border-red-500/30 text-red-400"}`}>
          {message.text}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1 relative">
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Buscar por nome, email ou chave..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-[#12121a] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50"
          />
        </div>
        <div className="flex gap-2">
          {[{ value: "all", label: "Todas" }, { value: "active", label: "Ativas" }, { value: "expired", label: "Expiradas" }].map((option) => (
            <button
              key={option.value}
              onClick={() => setFilter(option.value as typeof filter)}
              className={`px-4 py-3 rounded-xl font-medium transition-all ${filter === option.value ? "bg-purple-600 text-white" : "bg-[#12121a] text-gray-400 border border-purple-900/30 hover:border-purple-500/50"}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-900/30">
                <th className="text-left p-4 text-gray-400 font-medium">Cliente</th>
                <th className="text-left p-4 text-gray-400 font-medium">Chave</th>
                <th className="text-left p-4 text-gray-400 font-medium">Plano</th>
                <th className="text-left p-4 text-gray-400 font-medium">Status</th>
                <th className="text-left p-4 text-gray-400 font-medium">Expira em</th>
                <th className="text-left p-4 text-gray-400 font-medium">HWID</th>
                <th className="text-right p-4 text-gray-400 font-medium">Acoes</th>
              </tr>
            </thead>
            <tbody>
              {filteredLicencas.map((licenca) => (
                <tr key={licenca.id} className="border-b border-purple-900/20 hover:bg-white/5 transition-colors">
                  <td className="p-4">
                    <div>
                      <p className="text-white font-medium">{licenca.cliente_nome}</p>
                      <p className="text-sm text-gray-500">{licenca.email_cliente}</p>
                    </div>
                  </td>
                  <td className="p-4">
                    <div className="flex items-center gap-2">
                      <code className="text-purple-400 font-mono text-sm">{licenca.chave}</code>
                      <button onClick={() => copyToClipboard(licenca.chave)} className="text-gray-500 hover:text-purple-400 transition-colors" title="Copiar chave">
                        {copiedKey === licenca.chave ? (
                          <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className="px-2 py-1 bg-purple-500/20 text-purple-400 rounded-full text-xs font-medium">{licenca.plano_tipo}</span>
                  </td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${licenca.esta_expirada ? "bg-red-500/20 text-red-400" : licenca.ativa ? "bg-green-500/20 text-green-400" : "bg-gray-500/20 text-gray-400"}`}>
                      {licenca.esta_expirada ? "Expirada" : licenca.ativa ? "Ativa" : "Desativada"}
                    </span>
                  </td>
                  <td className="p-4">
                    <div>
                      <p className="text-white">{formatDate(licenca.data_expiracao)}</p>
                      <p className={`text-sm ${licenca.dias_restantes <= 7 ? "text-red-400" : "text-gray-500"}`}>
                        {licenca.dias_restantes > 0 ? `${licenca.dias_restantes} dias` : "Expirado"}
                      </p>
                    </div>
                  </td>
                  <td className="p-4">
                    {licenca.hwid ? (
                      <code className="text-xs text-gray-500 font-mono">{licenca.hwid.substring(0, 12)}...</code>
                    ) : (
                      <span className="text-gray-600 text-sm">Nao vinculado</span>
                    )}
                  </td>
                  <td className="p-4">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleToggleAtiva(licenca)}
                        className={`p-2 rounded-lg transition-colors ${licenca.ativa ? "text-red-400 hover:bg-red-500/10" : "text-green-400 hover:bg-green-500/10"}`}
                        title={licenca.ativa ? "Desativar" : "Ativar"}
                      >
                        {licenca.ativa ? (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                          </svg>
                        ) : (
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        )}
                      </button>
                      {licenca.hwid && (
                        <button
                          onClick={() => handleResetHWID(licenca)}
                          className="p-2 text-yellow-400 hover:bg-yellow-500/10 rounded-lg transition-colors"
                          title="Resetar HWID"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filteredLicencas.length === 0 && (
          <div className="p-12 text-center">
            <p className="text-gray-500">Nenhuma licenca encontrada</p>
          </div>
        )}
      </div>
    </div>
  );
}
