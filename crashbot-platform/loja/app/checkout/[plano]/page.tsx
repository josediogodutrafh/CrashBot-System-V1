'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

// --- TIPAGEM ---
interface PlanoBaseComum {
  nome: string;
  dias: number;
  descricao: string;
  popular?: boolean;
}

interface PlanoTrial extends PlanoBaseComum {
  isTrial: true;
  preco: number;
}

interface PlanoPago extends PlanoBaseComum {
  isTrial?: false;
  precoNormal: number;
  precoPrimeiraAdesao: number;
}

type Plano = PlanoTrial | PlanoPago;

type PlanosMap = {
  [key: string]: Plano;
};

// Dados dos planos
const planosBase: PlanosMap = {
  trial: {
    nome: 'Trial Gratuito',
    preco: 0,
    dias: 7,
    descricao: 'Teste grátis por 7 dias',
    isTrial: true,
  },
  semanal: {
    nome: 'Semanal',
    precoNormal: 149.9,
    precoPrimeiraAdesao: 49.9,
    dias: 7,
    descricao: 'Acesso por 7 dias',
    popular: true,
  },
  quinzenal: {
    nome: 'Quinzenal',
    precoNormal: 249.9,
    precoPrimeiraAdesao: 89.9,
    dias: 15,
    descricao: 'Acesso por 15 dias',
  },
  mensal: {
    nome: 'Mensal',
    precoNormal: 449.9,
    precoPrimeiraAdesao: 149.9,
    dias: 30,
    descricao: 'Melhor custo-benefício',
  },
};

// URL da API
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Função para formatar CPF
const formatarCPF = (valor: string) => {
  const apenas_numeros = valor.replace(/\D/g, '');
  if (apenas_numeros.length <= 3) return apenas_numeros;
  if (apenas_numeros.length <= 6)
    return `${apenas_numeros.slice(0, 3)}.${apenas_numeros.slice(3)}`;
  if (apenas_numeros.length <= 9)
    return `${apenas_numeros.slice(0, 3)}.${apenas_numeros.slice(
      3,
      6
    )}.${apenas_numeros.slice(6)}`;
  return `${apenas_numeros.slice(0, 3)}.${apenas_numeros.slice(
    3,
    6
  )}.${apenas_numeros.slice(6, 9)}-${apenas_numeros.slice(9, 11)}`;
};

// Função para formatar WhatsApp
const formatarWhatsApp = (valor: string) => {
  const apenas_numeros = valor.replace(/\D/g, '');
  if (apenas_numeros.length <= 2) return apenas_numeros;
  if (apenas_numeros.length <= 7)
    return `(${apenas_numeros.slice(0, 2)}) ${apenas_numeros.slice(2)}`;
  return `(${apenas_numeros.slice(0, 2)}) ${apenas_numeros.slice(
    2,
    7
  )}-${apenas_numeros.slice(7, 11)}`;
};

export default function CheckoutPage() {
  const params = useParams();
  const planoId = params.plano as string;
  const planoBase = planosBase[planoId];

  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    whatsapp: '',
    cpf: '',
  });
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verificandoElegibilidade, setVerificandoElegibilidade] =
    useState(false);
  const [error, setError] = useState('');

  // Estado para elegibilidade e preços
  const [elegibilidade, setElegibilidade] = useState<{
    podeUsarTrial: boolean;
    motivoTrial: string | null;
    preco: number;
    precoOriginal: number;
    isPrimeiraAdesao: boolean;
    desconto: number;
  } | null>(null);

  // 1. Envolver a função em useCallback para resolver "exhaustive-deps"
  const verificarElegibilidade = useCallback(
    async (cpf: string) => {
      if (!planoBase) return; // Segurança
      if (cpf.replace(/\D/g, '').length !== 11) return;

      setVerificandoElegibilidade(true);
      try {
        const response = await fetch(
          `${API_URL}/api/v1/pagamento/verificar-elegibilidade`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cpf }),
          }
        );

        if (response.ok) {
          const data = await response.json();

          if ('isTrial' in planoBase && planoBase.isTrial) {
            // Plano trial
            setElegibilidade({
              podeUsarTrial: data.pode_usar_trial,
              motivoTrial: data.motivo_trial,
              preco: 0,
              precoOriginal: 0,
              isPrimeiraAdesao: false,
              desconto: 0,
            });
          } else {
            // Planos pagos
            const planoInfo = data.planos[planoId];
            if (planoInfo) {
              setElegibilidade({
                podeUsarTrial: data.pode_usar_trial,
                motivoTrial: data.motivo_trial,
                preco: planoInfo.preco,
                precoOriginal: planoInfo.preco_original,
                isPrimeiraAdesao: planoInfo.is_primeira_adesao,
                desconto: planoInfo.desconto,
              });
            }
          }
        }
      } catch (err) {
        console.error('Erro ao verificar elegibilidade:', err);
      } finally {
        setVerificandoElegibilidade(false);
      }
    },
    [planoBase, planoId]
  ); // Dependências do useCallback

  // 2. useEffect agora chama a função memoizada
  useEffect(() => {
    const timer = setTimeout(() => {
      if (formData.cpf.replace(/\D/g, '').length === 11) {
        verificarElegibilidade(formData.cpf);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.cpf, verificarElegibilidade]);

  // 3. Remover "as any" usando Type Guards ou verificação de propriedade
  const getPrecoExibir = () => {
    if (!planoBase) return 0;
    if ('isTrial' in planoBase && planoBase.isTrial) return 0;
    if (elegibilidade) return elegibilidade.preco;

    // Como temos certeza que não é trial aqui (pelo if acima), TypeScript infere PlanoPago
    // Mas para segurança total podemos fazer cast ou asserção
    const planoPago = planoBase as PlanoPago;
    return planoPago.precoPrimeiraAdesao || planoPago.precoNormal;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planoBase) return;

    setLoading(true);
    setError('');

    try {
      // Se for trial
      if ('isTrial' in planoBase && planoBase.isTrial) {
        const response = await fetch(`${API_URL}/api/v1/pagamento/trial`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nome: formData.nome,
            email: formData.email,
            whatsapp: formData.whatsapp,
            cpf: formData.cpf,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Erro ao criar trial');
        }

        // Redirecionar para página de sucesso
        window.location.href = '/pagamento/sucesso?trial=true';
        return;
      }

      // Planos pagos
      const response = await fetch(`${API_URL}/api/v1/pagamento/criar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plano: planoId,
          nome: formData.nome,
          email: formData.email,
          whatsapp: formData.whatsapp,
          cpf: formData.cpf,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao criar pagamento');
      }

      const data = await response.json();
      window.location.href = data.init_point;
    } catch (err) {
      console.error('Erro:', err);
      setError(err instanceof Error ? err.message : 'Erro ao processar');
      setLoading(false);
    }
  };

  // 4. Mover a verificação de existência do plano para DEPOIS dos hooks
  if (!planoBase) {
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

  const isTrial = 'isTrial' in planoBase && planoBase.isTrial;
  const precoFinal = getPrecoExibir();

  // 5. Corrigir a lógica booleana para o botão disabled
  // Se elegibilidade for null, a expressão 'isTrial && elegibilidade' retornaria null, o que quebra o disabled
  // Usamos optional chaining e comparação explícita
  const isTrialBloqueado = isTrial && elegibilidade?.podeUsarTrial === false;

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
            {isTrial ? 'Ativar Trial Gratuito' : 'Finalizar Compra'}
          </h1>

          <div className="grid md:grid-cols-2 gap-8">
            {/* Resumo do Pedido */}
            <Card className="bg-slate-800/50 border-slate-700 h-fit">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-white">Resumo do Pedido</CardTitle>
                  {planoBase.popular && (
                    <Badge className="bg-purple-600 text-white">
                      Mais Popular
                    </Badge>
                  )}
                  {isTrial && (
                    <Badge className="bg-green-600 text-white">Grátis</Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between text-slate-300">
                  <span>Plano</span>
                  <span className="font-semibold text-white">
                    {planoBase.nome}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Duração</span>
                  <span className="font-semibold text-white">
                    {planoBase.dias} dias
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span>Descrição</span>
                  <span className="text-white">{planoBase.descricao}</span>
                </div>

                <hr className="border-slate-700" />

                {/* Mostrar desconto se aplicável */}
                {elegibilidade?.isPrimeiraAdesao &&
                  elegibilidade.desconto > 0 && (
                    <div className="bg-green-900/30 border border-green-600 p-3 rounded-lg">
                      <p className="text-green-400 text-sm font-semibold">
                        🎉 Preço de Primeira Adesão!
                      </p>
                      <p className="text-green-300 text-xs">
                        Economia de R$ {elegibilidade.desconto.toFixed(2)}
                      </p>
                    </div>
                  )}

                <div className="flex justify-between items-center">
                  <span className="text-slate-300">Total</span>
                  <div className="text-right">
                    {elegibilidade?.isPrimeiraAdesao && (
                      <span className="text-slate-500 line-through text-lg mr-2">
                        R$ {elegibilidade.precoOriginal.toFixed(2)}
                      </span>
                    )}
                    <span className="text-3xl font-bold text-purple-400">
                      {isTrial ? 'GRÁTIS' : `R$ ${precoFinal.toFixed(2)}`}
                    </span>
                  </div>
                </div>

                <div className="bg-slate-900/50 p-4 rounded-lg mt-4">
                  <p className="text-sm text-slate-400 text-center">
                    {isTrial
                      ? '✨ Sem cartão de crédito necessário'
                      : '🔒 Pagamento seguro via Mercado Pago'}
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

                  {/* Aviso se não pode usar trial */}
                  {isTrial && elegibilidade && !elegibilidade.podeUsarTrial && (
                    <div className="bg-yellow-500/20 border border-yellow-500 text-yellow-300 p-3 rounded-lg text-sm">
                      {elegibilidade.motivoTrial}
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
                    <label className="block text-slate-300 mb-2">CPF</label>
                    <Input
                      type="text"
                      placeholder="000.000.000-00"
                      required
                      maxLength={14}
                      value={formData.cpf}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          cpf: formatarCPF(e.target.value),
                        })
                      }
                      className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                    />
                    {verificandoElegibilidade && (
                      <p className="text-xs text-purple-400 mt-1">
                        Verificando...
                      </p>
                    )}
                    <p className="text-xs text-slate-500 mt-1">
                      Usado para identificar sua licença
                    </p>
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
                      maxLength={15}
                      value={formData.whatsapp}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          whatsapp: formatarWhatsApp(e.target.value),
                        })
                      }
                      className="bg-slate-900 border-slate-700 text-white placeholder:text-slate-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">
                      Para suporte e notificações
                    </p>
                  </div>

                  <hr className="border-slate-700 my-6" />

                  <div className="flex items-start gap-3">
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

                  <Button
                    type="submit"
                    disabled={loading || !aceitouTermos || isTrialBloqueado}
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
                        {isTrial
                          ? 'Ativando trial...'
                          : 'Redirecionando para pagamento...'}
                      </span>
                    ) : isTrial ? (
                      'Ativar Trial Grátis'
                    ) : (
                      `Pagar R$ ${precoFinal.toFixed(2)}`
                    )}
                  </Button>
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
