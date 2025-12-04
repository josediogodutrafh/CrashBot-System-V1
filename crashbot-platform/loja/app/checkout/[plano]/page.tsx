'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useState } from 'react';

// Dados dos planos
const planos = {
  experimental: {
    nome: 'Experimental',
    preco: 29.9,
    dias: 3,
    descricao: 'Ideal para testar o bot',
  },
  semanal: {
    nome: 'Semanal',
    preco: 149.9,
    dias: 7,
    descricao: 'Melhor custo-benefício',
    popular: true,
  },
  mensal: {
    nome: 'Mensal',
    preco: 499.9,
    dias: 30,
    descricao: 'Para profissionais',
  },
};

// URL da API
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function CheckoutPage() {
  const params = useParams();
  const planoId = params.plano as string;
  const plano = planos[planoId as keyof typeof planos];

  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    whatsapp: '',
  });
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Se plano não existir
  if (!plano) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <Card className="bg-slate-800/50 border-slate-700 p-8 text-center">
          <CardTitle className="text-white mb-4">
            Plano não encontrado
          </CardTitle>
          <Link href="/#planos">
            <Button className="bg-purple-600 hover:bg-purple-700">
              Ver Planos Disponíveis
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Chamar API para criar pagamento
      const response = await fetch(`${API_URL}/api/v1/pagamento/criar`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plano: planoId,
          nome: formData.nome,
          email: formData.email,
          whatsapp: formData.whatsapp,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao criar pagamento');
      }

      const data = await response.json();

      // Redirecionar para o Mercado Pago
      window.location.href = data.init_point;
    } catch (err) {
      console.error('Erro:', err);
      setError(
        err instanceof Error ? err.message : 'Erro ao processar pagamento'
      );
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold text-white">
            🤖 CrashBot
          </Link>
          <Link href="/#planos">
            <Button
              variant="ghost"
              className="text-white hover:text-purple-300"
            >
              ← Voltar aos Planos
            </Button>
          </Link>
        </nav>
      </header>

      {/* Checkout */}
      <section className="container mx-auto px-4 py-10">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-white text-center mb-10">
            Finalizar Compra
          </h1>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Resumo do Pedido */}
            <Card className="bg-slate-800/50 border-slate-700 h-fit">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white">Resumo do Pedido</CardTitle>
                  {'popular' in plano && plano.popular && (
                    <Badge className="bg-purple-600 text-white">
                      Mais Popular
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between text-slate-300">
                  <span>Plano</span>
                  <span className="font-semibold text-white">{plano.nome}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Duração</span>
                  <span className="font-semibold text-white">
                    {plano.dias} dias
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Descrição</span>
                  <span className="text-white">{plano.descricao}</span>
                </div>

                <hr className="border-slate-700" />

                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Total</span>
                  <span className="text-3xl font-bold text-purple-400">
                    R$ {plano.preco.toFixed(2)}
                  </span>
                </div>

                <div className="bg-slate-900/50 p-4 rounded-lg mt-4">
                  <p className="text-sm text-slate-400 text-center">
                    🔒 Pagamento seguro via Mercado Pago
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Formulário */}
            <Card className="bg-slate-800/50 border-slate-700">
              <CardHeader>
                <CardTitle className="text-white">Seus Dados</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="bg-red-500/20 border border-red-500 text-red-300 p-3 rounded-lg text-sm">
                      {error}
                    </div>
                  )}

                  <div>
                    <label className="block text-slate-300 mb-2">
                      Nome Completo
                    </label>
                    <Input
                      type="text"
                      placeholder="Seu nome"
                      required
                      value={formData.nome}
                      onChange={(e) =>
                        setFormData({ ...formData, nome: e.target.value })
                      }
                      className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div>
                    <label className="block text-slate-300 mb-2">E-mail</label>
                    <Input
                      type="email"
                      placeholder="seu@email.com"
                      required
                      value={formData.email}
                      onChange={(e) =>
                        setFormData({ ...formData, email: e.target.value })
                      }
                      className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      A licença será enviada para este e-mail
                    </p>
                  </div>

                  <div>
                    <label className="block text-slate-300 mb-2">
                      WhatsApp
                    </label>
                    <Input
                      type="tel"
                      placeholder="(11) 99999-9999"
                      required
                      value={formData.whatsapp}
                      onChange={(e) =>
                        setFormData({ ...formData, whatsapp: e.target.value })
                      }
                      className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Para suporte e notificações
                    </p>
                  </div>

                  <hr className="border-slate-700 my-6" />

                  <Button
                    type="submit"
                    disabled={loading || !aceitouTermos}
                    className="w-full bg-purple-600 hover:bg-purple-700 text-white py-6 text-lg"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <svg
                          className="animate-spin h-5 w-5"
                          viewBox="0 0 24 24"
                        >
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
                        Redirecionando para pagamento...
                      </span>
                    ) : (
                      `Pagar R$ ${plano.preco.toFixed(2)}`
                    )}
                  </Button>

                  <div className="flex items-start gap-3 mt-4">
                    <input
                      type="checkbox"
                      id="termos"
                      checked={aceitouTermos}
                      onChange={(e) => setAceitouTermos(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900 text-purple-600 focus:ring-purple-500"
                      required
                    />
                    <label htmlFor="termos" className="text-sm text-slate-400">
                      Li e aceito a{' '}
                      <Link
                        href="/privacidade"
                        target="_blank"
                        className="text-purple-400 hover:underline"
                      >
                        Política de Privacidade
                      </Link>{' '}
                      e os{' '}
                      <Link
                        href="/termos"
                        target="_blank"
                        className="text-purple-400 hover:underline"
                      >
                        Termos de Uso
                      </Link>
                    </label>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>

          {/* Benefícios */}
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="text-3xl mb-2">🔒</div>
              <h3 className="text-white font-semibold mb-1">
                Pagamento Seguro
              </h3>
              <p className="text-slate-400 text-sm">
                Processado pelo Mercado Pago
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">⚡</div>
              <h3 className="text-white font-semibold mb-1">
                Entrega Imediata
              </h3>
              <p className="text-slate-400 text-sm">
                Licença enviada por e-mail
              </p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">💬</div>
              <h3 className="text-white font-semibold mb-1">
                Suporte Dedicado
              </h3>
              <p className="text-slate-400 text-sm">Via WhatsApp 24/7</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-6 mt-10">
        <div className="container mx-auto px-4 text-center text-slate-400 text-sm">
          <p>© 2025 CrashBot. Todos os direitos reservados.</p>
        </div>
      </footer>
    </div>
  );
}
