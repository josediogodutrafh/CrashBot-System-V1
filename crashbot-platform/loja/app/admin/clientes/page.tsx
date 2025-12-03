'use client';

import { useEffect, useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Licenca {
  id: number;
  chave: string;
  cliente_nome: string;
  email_cliente: string;
  whatsapp: string;
  plano_tipo: string;
  ativa: boolean;
  esta_expirada: boolean;
  dias_restantes: number;
  created_at: string;
}

interface Cliente {
  email: string;
  nome: string;
  whatsapp: string;
  licencas: Licenca[];
  totalLicencas: number;
  licencasAtivas: number;
}

export default function AdminClientes() {
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedCliente, setSelectedCliente] = useState<Cliente | null>(null);

  useEffect(() => {
    fetchClientes();
  }, []);

  const fetchClientes = async () => {
    const token = localStorage.getItem('token');
    if (!token) return;

    try {
      const response = await fetch(`${API_URL}/api/v1/licencas`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        const licencas: Licenca[] = await response.json();
        const clientesMap = new Map<string, Cliente>();

        licencas.forEach((l) => {
          const email = l.email_cliente;
          if (!clientesMap.has(email)) {
            clientesMap.set(email, {
              email,
              nome: l.cliente_nome,
              whatsapp: l.whatsapp,
              licencas: [],
              totalLicencas: 0,
              licencasAtivas: 0,
            });
          }

          const cliente = clientesMap.get(email)!;
          cliente.licencas.push(l);
          cliente.totalLicencas++;
          if (l.ativa && !l.esta_expirada) {
            cliente.licencasAtivas++;
          }
          if (l.cliente_nome && l.cliente_nome !== 'manual@sem_email.com') {
            cliente.nome = l.cliente_nome;
          }
        });

        setClientes(Array.from(clientesMap.values()));
      }
    } catch (error) {
      console.error('Erro ao buscar clientes:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  };

  const filteredClientes = clientes.filter(
    (c) =>
      c.nome?.toLowerCase().includes(search.toLowerCase()) ||
      c.email?.toLowerCase().includes(search.toLowerCase()) ||
      c.whatsapp?.includes(search)
  );

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
        <h1 className="text-3xl font-bold text-white mb-2">Clientes</h1>
        <p className="text-gray-400">
          {clientes.length} cliente{clientes.length !== 1 ? 's' : ''} cadastrado
          {clientes.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="mb-6 relative">
        <svg
          className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
        <input
          type="text"
          placeholder="Buscar por nome, email ou WhatsApp..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full max-w-md pl-12 pr-4 py-3 bg-[#12121a] border border-purple-900/30 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-purple-500/50"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredClientes.map((cliente) => (
          <div
            key={cliente.email}
            onClick={() => setSelectedCliente(cliente)}
            className="bg-gradient-to-br from-[#12121a] to-[#1a1a2e] rounded-2xl border border-purple-900/30 p-6 hover:border-purple-500/50 transition-all duration-300 cursor-pointer group"
          >
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl flex items-center justify-center text-white text-xl font-bold shrink-0">
                {cliente.nome?.charAt(0).toUpperCase() || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-white font-semibold truncate group-hover:text-purple-400 transition-colors">
                  {cliente.nome || 'Sem nome'}
                </h3>
                <p className="text-sm text-gray-500 truncate">
                  {cliente.email}
                </p>
                {cliente.whatsapp && cliente.whatsapp !== 'Nao informado' && (
                  <p className="text-sm text-gray-500">{cliente.whatsapp}</p>
                )}
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-purple-900/30 flex gap-4">
              <div>
                <p className="text-2xl font-bold text-white">
                  {cliente.totalLicencas}
                </p>
                <p className="text-xs text-gray-500">Licencas</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-400">
                  {cliente.licencasAtivas}
                </p>
                <p className="text-xs text-gray-500">Ativas</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {filteredClientes.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500">Nenhum cliente encontrado</p>
        </div>
      )}

      {selectedCliente && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-[#12121a] rounded-2xl border border-purple-900/30 w-full max-w-2xl max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-purple-900/30 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-gradient-to-br from-purple-600 to-pink-600 rounded-xl flex items-center justify-center text-white text-xl font-bold">
                  {selectedCliente.nome?.charAt(0).toUpperCase() || '?'}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">
                    {selectedCliente.nome}
                  </h2>
                  <p className="text-gray-500">{selectedCliente.email}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedCliente(null)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <h3 className="text-lg font-semibold text-white mb-4">
                Licencas ({selectedCliente.licencas.length})
              </h3>
              <div className="space-y-3">
                {selectedCliente.licencas.map((licenca) => (
                  <div
                    key={licenca.id}
                    className="bg-[#0a0a0f] rounded-xl p-4 border border-purple-900/20"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <code className="text-purple-400 font-mono text-sm">
                        {licenca.chave}
                      </code>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          licenca.esta_expirada
                            ? 'bg-red-500/20 text-red-400'
                            : licenca.ativa
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}
                      >
                        {licenca.esta_expirada
                          ? 'Expirada'
                          : licenca.ativa
                          ? 'Ativa'
                          : 'Desativada'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-gray-500">
                      <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">
                        {licenca.plano_tipo}
                      </span>
                      <span>Criada: {formatDate(licenca.created_at)}</span>
                      {!licenca.esta_expirada && (
                        <span
                          className={
                            licenca.dias_restantes <= 7 ? 'text-red-400' : ''
                          }
                        >
                          {licenca.dias_restantes} dias restantes
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="p-6 border-t border-purple-900/30 flex gap-3">
              {selectedCliente.whatsapp &&
                selectedCliente.whatsapp !== 'Nao informado' && (
                  <a
                    href={`https://wa.me/55${selectedCliente.whatsapp.replace(
                      /\D/g,
                      ''
                    )}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2 bg-green-600/20 text-green-400 border border-green-500/30 rounded-xl hover:bg-green-600/30 transition-colors"
                  >
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
                    </svg>
                    WhatsApp
                  </a>
                )}
              <button
                onClick={() => setSelectedCliente(null)}
                className="flex-1 px-4 py-2 text-gray-400 hover:text-white border border-purple-900/30 rounded-xl transition-colors"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
