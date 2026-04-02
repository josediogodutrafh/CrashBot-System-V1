'use client';

import { useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Versao {
  id: number;
  versao: string;
  download_url: string;
  changelog: string | null;
  obrigatoria: boolean;
  ativa: boolean;
  created_at: string;
}

export default function AdminVersoes() {
  const [versoes, setVersoes] = useState<Versao[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    versao: '',
    download_url: '',
    changelog: '',
    obrigatoria: false,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchVersoes();
  }, []);

  const fetchVersoes = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/bot/versoes`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        setVersoes(data);
      }
    } catch (error) {
      console.error('Erro ao buscar versoes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/bot/versao`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        setShowModal(false);
        setFormData({
          versao: '',
          download_url: '',
          changelog: '',
          obrigatoria: false,
        });
        fetchVersoes();
      } else {
        const error = await response.json();
        alert(error.detail || 'Erro ao criar versao');
      }
    } catch (error) {
      console.error('Erro ao criar versao:', error);
    } finally {
      setSaving(false);
    }
  };

  const toggleVersao = async (id: number) => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(
        `${API_URL}/api/v1/bot/versao/${id}/toggle`,
        {
          method: 'PATCH',
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      if (response.ok) {
        fetchVersoes();
      }
    } catch (error) {
      console.error('Erro ao toggle versao:', error);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Versões do Bot</h1>
          <p className="text-gray-400">
            Gerenciar versões e atualizações do CrashBot
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          Nova Versão
        </button>
      </div>

      <div className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 overflow-hidden">
        {versoes.length > 0 ? (
          <table className="w-full">
            <thead>
              <tr className="border-b border-purple-900/30">
                <th className="text-left p-4 text-gray-400 font-medium">
                  Versão
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  URL Download
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  Changelog
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  Obrigatória
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  Status
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  Criada em
                </th>
                <th className="text-left p-4 text-gray-400 font-medium">
                  Ações
                </th>
              </tr>
            </thead>
            <tbody>
              {versoes.map((versao) => (
                <tr
                  key={versao.id}
                  className="border-b border-purple-900/20 hover:bg-white/5"
                >
                  <td className="p-4">
                    <span className="text-purple-400 font-mono font-bold">
                      v{versao.versao}
                    </span>
                    {versao.changelog && (
                      <p className="text-gray-500 text-sm mt-1 truncate max-w-[150px]">
                        {versao.changelog}
                      </p>
                    )}
                  </td>
                  <td className="p-4">
                    {/* CORREÇÃO: A tag <a> estava incompleta no seu código original */}
                    <a
                      href={versao.download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 text-sm"
                    >
                      {versao.download_url.length > 35
                        ? versao.download_url.substring(0, 35) + '...'
                        : versao.download_url}
                    </a>
                  </td>
                  <td className="p-4">
                    {versao.obrigatoria ? (
                      <span className="px-2 py-1 bg-red-500/20 text-red-400 rounded-full text-xs font-medium">
                        Sim
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium">
                        Não
                      </span>
                    )}
                  </td>
                  <td className="p-4">
                    {versao.ativa ? (
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
                        Ativa
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full text-xs font-medium">
                        Inativa
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-gray-400 text-sm">
                    {formatDate(versao.created_at)}
                  </td>
                  <td className="p-4">
                    <button
                      onClick={() => toggleVersao(versao.id)}
                      className={`p-2 rounded-lg transition-colors ${
                        versao.ativa
                          ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                          : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                      }`}
                      title={versao.ativa ? 'Desativar' : 'Ativar'}
                    >
                      {versao.ativa ? 'Desativar' : 'Ativar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-12 text-center">
            <p className="text-gray-500 mb-2">Nenhuma versão cadastrada</p>
            {/* CORREÇÃO: Uso de &quot; para evitar erro do ESLint */}
            <p className="text-gray-600 text-sm">
              Clique em &quot;Nova Versão&quot; para adicionar
            </p>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#12121a] rounded-2xl border border-purple-900/30 w-full max-w-lg">
            <div className="p-6 border-b border-purple-900/30 flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Nova Versão</h2>
              <button
                onClick={() => setShowModal(false)}
                className="text-gray-400 hover:text-white"
              >
                X
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Versão *
                </label>
                <input
                  type="text"
                  value={formData.versao}
                  onChange={(e) =>
                    setFormData({ ...formData, versao: e.target.value })
                  }
                  placeholder="Ex: 2.1.0"
                  required
                  className="w-full px-4 py-3 bg-[#0a0a0f] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  URL de Download *
                </label>
                <input
                  type="url"
                  value={formData.download_url}
                  onChange={(e) =>
                    setFormData({ ...formData, download_url: e.target.value })
                  }
                  placeholder="https://exemplo.com/crashbot-2.1.0.zip"
                  required
                  className="w-full px-4 py-3 bg-[#0a0a0f] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50"
                />
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">
                  Changelog
                </label>
                <textarea
                  value={formData.changelog}
                  onChange={(e) =>
                    setFormData({ ...formData, changelog: e.target.value })
                  }
                  placeholder="Descreva as novidades desta versão..."
                  rows={3}
                  className="w-full px-4 py-3 bg-[#0a0a0f] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50 resize-none"
                />
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="obrigatoria"
                  checked={formData.obrigatoria}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      obrigatoria: e.target.checked,
                    })
                  }
                  className="w-5 h-5 rounded"
                />
                <label htmlFor="obrigatoria" className="text-gray-300">
                  Atualização obrigatória
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-4 py-3 text-gray-400 hover:text-white border border-purple-900/30 rounded-xl transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 px-4 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl transition-colors disabled:opacity-50"
                >
                  {saving ? 'Salvando...' : 'Criar Versão'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
