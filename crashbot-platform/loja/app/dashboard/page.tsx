'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

// URL da API
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface User {
  id: number;
  email: string;
  nome: string;
  is_admin: boolean;
}

interface Licenca {
  id: number;
  chave: string;
  ativa: boolean;
  data_expiracao: string;
  plano_tipo: string;
  cliente_nome: string;
  email_cliente: string;
  hwid: string | null;
  created_at: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [licencas, setLicencas] = useState<Licenca[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAlterarSenha, setShowAlterarSenha] = useState(false);
  const [senhaAtual, setSenhaAtual] = useState('');
  const [novaSenha, setNovaSenha] = useState('');
  const [confirmarSenha, setConfirmarSenha] = useState('');
  const [senhaLoading, setSenhaLoading] = useState(false);
  const [senhaMsg, setSenhaMsg] = useState({ tipo: '', texto: '' });

  const fetchLicencas = useCallback(
    async (token: string) => {
      try {
        const response = await fetch(`${API_URL}/api/v1/minhas-licencas`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.status === 401) {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          router.push('/login');
          return;
        }

        if (!response.ok) {
          throw new Error('Erro ao buscar licenças');
        }

        const data = await response.json();
        setLicencas(data);
      } catch (err) {
        console.error('Erro:', err);
        setError('Erro ao carregar licenças');
      } finally {
        setLoading(false);
      }
    },
    [router]
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      const token = localStorage.getItem('token');
      const userData = localStorage.getItem('user');

      console.log('Dashboard - Token:', token ? 'existe' : 'null');

      if (!token || !userData) {
        router.push('/login');
        return;
      }

      setUser(JSON.parse(userData));
      fetchLicencas(token);
    }, 100);

    return () => clearTimeout(timer);
  }, [router, fetchLicencas]);

  const handleAlterarSenha = async (e: React.FormEvent) => {
    e.preventDefault();
    setSenhaMsg({ tipo: '', texto: '' });

    if (novaSenha !== confirmarSenha) {
      setSenhaMsg({ tipo: 'erro', texto: 'As senhas não coincidem' });
      return;
    }

    if (novaSenha.length < 6) {
      setSenhaMsg({
        tipo: 'erro',
        texto: 'A nova senha deve ter pelo menos 6 caracteres',
      });
      return;
    }

    setSenhaLoading(true);
    const token = localStorage.getItem('token');

    try {
      const response = await fetch(
        `${API_URL}/api/v1/auth/change-password?senha_atual=${encodeURIComponent(
          senhaAtual
        )}&nova_senha=${encodeURIComponent(novaSenha)}`,
        {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Erro ao alterar senha');
      }

      setSenhaMsg({ tipo: 'sucesso', texto: 'Senha alterada com sucesso!' });
      setSenhaAtual('');
      setNovaSenha('');
      setConfirmarSenha('');

      setTimeout(() => {
        setShowAlterarSenha(false);
        setSenhaMsg({ tipo: '', texto: '' });
      }, 2000);
    } catch (err) {
      setSenhaMsg({
        tipo: 'erro',
        texto: err instanceof Error ? err.message : 'Erro ao alterar senha',
      });
    } finally {
      setSenhaLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/');
  };

  const calcularDiasRestantes = (dataExpiracao: string) => {
    const hoje = new Date();
    const expiracao = new Date(dataExpiracao);
    const diffTime = expiracao.getTime() - hoje.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  };

  const formatarData = (data: string) => {
    return new Date(data).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-white text-xl flex items-center gap-3">
          <svg className="animate-spin h-8 w-8" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Carregando...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-800">
        <div className="container mx-auto px-4 py-4">
          <nav className="flex items-center justify-between">
            <Link href="/" className="text-2xl font-bold text-white">
              🤖 CrashBot
            </Link>
            <div className="flex items-center gap-4">
              <span className="text-slate-400">
                Olá, <span className="text-white">{user?.nome}</span>
              </span>
              <Button
                variant="outline"
                onClick={handleLogout}
                className="border-slate-700 text-slate-300 hover:bg-slate-800"
              >
                Sair
              </Button>
            </div>
          </nav>
        </div>
      </header>

      {/* Dashboard Content */}
      <main className="container mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold text-white mb-8">Meu Painel</h1>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 p-4 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Estatísticas */}
        <div className="grid md:grid-cols-3 gap-6 mb-10">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-6">
              <div className="text-slate-400 text-sm mb-1">
                Total de Licenças
              </div>
              <div className="text-3xl font-bold text-white">
                {licencas.length}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-6">
              <div className="text-slate-400 text-sm mb-1">Licenças Ativas</div>
              <div className="text-3xl font-bold text-green-400">
                {licencas.filter((l) => l.ativa).length}
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="p-6">
              <div className="text-slate-400 text-sm mb-1">
                Licenças Expiradas
              </div>
              <div className="text-3xl font-bold text-red-400">
                {licencas.filter((l) => !l.ativa).length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Lista de Licenças */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">Minhas Licenças</CardTitle>
              <Link href="/#planos">
                <Button className="bg-purple-600 hover:bg-purple-700">
                  + Nova Licença
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {licencas.length === 0 ? (
              <div className="text-center py-10">
                <div className="text-6xl mb-4">📋</div>
                <p className="text-slate-400 mb-4">
                  Você ainda não tem nenhuma licença
                </p>
                <Link href="/#planos">
                  <Button className="bg-purple-600 hover:bg-purple-700">
                    Comprar Licença
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {licencas.map((licenca) => {
                  const diasRestantes = calcularDiasRestantes(
                    licenca.data_expiracao
                  );
                  const expirada = diasRestantes <= 0;

                  return (
                    <div
                      key={licenca.id}
                      className="bg-slate-900/50 border border-slate-700 rounded-lg p-4"
                    >
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        {/* Info Principal */}
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <code className="text-purple-400 font-mono text-lg">
                              {licenca.chave}
                            </code>
                            <Badge
                              className={
                                licenca.ativa && !expirada
                                  ? 'bg-green-500/20 text-green-400 border-green-500/50'
                                  : 'bg-red-500/20 text-red-400 border-red-500/50'
                              }
                            >
                              {licenca.ativa && !expirada
                                ? 'Ativa'
                                : 'Expirada'}
                            </Badge>
                            {licenca.plano_tipo && (
                              <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/50">
                                {licenca.plano_tipo}
                              </Badge>
                            )}
                          </div>

                          <div className="text-slate-400 text-sm space-y-1">
                            <p>
                              📅 Expira em:{' '}
                              <span className="text-white">
                                {formatarData(licenca.data_expiracao)}
                              </span>
                            </p>
                            {licenca.hwid && (
                              <p>
                                💻 HWID:{' '}
                                <span className="text-white font-mono text-xs">
                                  {licenca.hwid}
                                </span>
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Dias Restantes */}
                        <div className="text-center md:text-right">
                          {expirada ? (
                            <div>
                              <div className="text-red-400 text-2xl font-bold">
                                Expirada
                              </div>
                              <Link href="/#planos">
                                <Button
                                  size="sm"
                                  className="mt-2 bg-purple-600 hover:bg-purple-700"
                                >
                                  Renovar
                                </Button>
                              </Link>
                            </div>
                          ) : (
                            <div>
                              <div
                                className={`text-2xl font-bold ${
                                  diasRestantes <= 3
                                    ? 'text-yellow-400'
                                    : 'text-green-400'
                                }`}
                              >
                                {diasRestantes} dias
                              </div>
                              <div className="text-slate-500 text-sm">
                                restantes
                              </div>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Barra de Progresso */}
                      {!expirada && (
                        <div className="mt-4">
                          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                diasRestantes <= 3
                                  ? 'bg-yellow-500'
                                  : 'bg-green-500'
                              }`}
                              style={{
                                width: `${Math.min(
                                  (diasRestantes / 30) * 100,
                                  100
                                )}%`,
                              }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Seção de Ajuda */}
        <div className="mt-10 grid md:grid-cols-3 gap-6">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                📥 Download do Bot
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-400 mb-4">
                Baixe a versão mais recente do CrashBot para Windows.
              </p>
              <Button className="w-full bg-slate-700 hover:bg-slate-600">
                Baixar CrashBot v2.0
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">💬 Suporte</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-400 mb-4">
                Precisa de ajuda? Entre em contato pelo WhatsApp.
              </p>
              <a
                href="https://wa.me/5565992727497"
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button className="w-full bg-green-600 hover:bg-green-700">
                  Abrir WhatsApp
                </Button>
              </a>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                ⚙️ Minha Conta
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-slate-400 mb-4">
                Gerencie suas configurações de conta.
              </p>
              <Button
                onClick={() => setShowAlterarSenha(true)}
                className="w-full bg-slate-700 hover:bg-slate-600"
              >
                Alterar Senha
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>

      {/* Modal Alterar Senha */}
      {showAlterarSenha && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <Card className="bg-slate-800 border-slate-700 w-full max-w-md">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">🔐 Alterar Senha</CardTitle>
                <button
                  onClick={() => {
                    setShowAlterarSenha(false);
                    setSenhaMsg({ tipo: '', texto: '' });
                    setSenhaAtual('');
                    setNovaSenha('');
                    setConfirmarSenha('');
                  }}
                  className="text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleAlterarSenha} className="space-y-4">
                {senhaMsg.texto && (
                  <div
                    className={`p-3 rounded-lg text-sm ${
                      senhaMsg.tipo === 'erro'
                        ? 'bg-red-500/20 border border-red-500 text-red-300'
                        : 'bg-green-500/20 border border-green-500 text-green-300'
                    }`}
                  >
                    {senhaMsg.texto}
                  </div>
                )}

                <div>
                  <label className="block text-slate-300 mb-2 text-sm">
                    Senha Atual
                  </label>
                  <input
                    type="password"
                    value={senhaAtual}
                    onChange={(e) => setSenhaAtual(e.target.value)}
                    required
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 mb-2 text-sm">
                    Nova Senha
                  </label>
                  <input
                    type="password"
                    value={novaSenha}
                    onChange={(e) => setNovaSenha(e.target.value)}
                    required
                    minLength={6}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 mb-2 text-sm">
                    Confirmar Nova Senha
                  </label>
                  <input
                    type="password"
                    value={confirmarSenha}
                    onChange={(e) => setConfirmarSenha(e.target.value)}
                    required
                    minLength={6}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div className="flex gap-3 pt-4">
                  <Button
                    type="button"
                    onClick={() => {
                      setShowAlterarSenha(false);
                      setSenhaMsg({ tipo: '', texto: '' });
                    }}
                    className="flex-1 bg-slate-700 hover:bg-slate-600"
                  >
                    Cancelar
                  </Button>
                  <Button
                    type="submit"
                    disabled={senhaLoading}
                    className="flex-1 bg-purple-600 hover:bg-purple-700"
                  >
                    {senhaLoading ? 'Alterando...' : 'Alterar Senha'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 mt-10">
        <div className="container mx-auto px-4 text-center text-slate-400 text-sm">
          <p>© 2025 CrashBot. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
}
