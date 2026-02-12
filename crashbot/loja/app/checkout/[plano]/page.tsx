'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

// --- TIPAGEM SIMPLIFICADA ---
interface PlanoInfo {
  nome: string;
  preco: number;
  dias: number;
  descricao: string;
  isTrial?: boolean;
  popular?: boolean;
  economize?: string;
}

type PlanosMap = {
  [key: string]: PlanoInfo;
};

// --- PREÇOS E PLANOS ---
const planosBase: PlanosMap = {
  trial: {
    nome: 'Trial Gratuito',
    preco: 0,
    dias: 7,
    descricao: 'Teste completo da tecnologia por 7 dias.',
    isTrial: true,
  },
  semanal: {
    nome: 'Acesso Semanal',
    preco: 69.0,
    dias: 7,
    descricao: 'Ideal para validar lucros a curto prazo.',
  },
  mensal: {
    nome: 'Licença Mensal PRO',
    preco: 249.0,
    dias: 30,
    descricao: 'Setup validado e suporte VIP incluso.',
    popular: true,
    economize: 'R$ 27,00',
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
    senha: '',
    confirmarSenha: '',
  });
  const [aceitouTermos, setAceitouTermos] = useState(false);
  const [loading, setLoading] = useState(false);
  const [verificandoElegibilidade, setVerificandoElegibilidade] =
    useState(false);
  const [error, setError] = useState('');

  // Estado para elegibilidade (apenas para validar Trial)
  const [elegibilidadeTrial, setElegibilidadeTrial] = useState<{
    podeUsar: boolean;
    motivo: string | null;
  } | null>(null);

  const verificarElegibilidade = useCallback(
    async (cpf: string) => {
      if (!planoBase) return;
      // Só verifica elegibilidade se for TRIAL
      if (!planoBase.isTrial) return;

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
          setElegibilidadeTrial({
            podeUsar: data.pode_usar_trial,
            motivo: data.motivo_trial,
          });
        }
      } catch (err) {
        console.error('Erro ao verificar elegibilidade:', err);
      } finally {
        setVerificandoElegibilidade(false);
      }
    },
    [planoBase]
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      if (formData.cpf.replace(/\D/g, '').length === 11) {
        verificarElegibilidade(formData.cpf);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.cpf, verificarElegibilidade]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!planoBase) return;

    setLoading(true);
    setError('');

    // Validar senha
    if (formData.senha.length < 6) {
      setError('A senha deve ter no mínimo 6 caracteres.');
      setLoading(false);
      return;
    }
    if (formData.senha !== formData.confirmarSenha) {
      setError('As senhas não coincidem.');
      setLoading(false);
      return;
    }

    try {
      // Lógica de Trial
      if (planoBase.isTrial) {
        const response = await fetch(`${API_URL}/api/v1/pagamento/trial`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nome: formData.nome,
            email: formData.email,
            whatsapp: formData.whatsapp,
            cpf: formData.cpf,
            senha: formData.senha,
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

      // Lógica de Pagamento (Planos Pagos)
      const response = await fetch(`${API_URL}/api/v1/pagamento/criar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plano: planoId, // 'semanal' ou 'mensal'
          nome: formData.nome,
          email: formData.email,
          whatsapp: formData.whatsapp,
          cpf: formData.cpf,
          senha: formData.senha,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erro ao criar pagamento');
      }

      const data = await response.json();
      window.location.href = data.init_point; // Link do Mercado Pago
    } catch (err) {
      console.error('Erro:', err);
      setError(err instanceof Error ? err.message : 'Erro ao processar');
      setLoading(false);
    }
  };

  if (!planoBase) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <Card className="bg-slate-900 border-slate-800 p-8 text-center">
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

  const isTrial = !!planoBase.isTrial;
  const isTrialBloqueado = isTrial && elegibilidadeTrial?.podeUsar === false;

  return (
    <div className="min-h-screen bg-[#020617] selection:bg-purple-500/30">
      {/* Header Simplificado */}
      <header className="container mx-auto px-4 py-6 border-b border-white/5">
        <nav className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl">🤖</span>
            <span className="text-xl font-bold text-white">CrashBot</span>
          </Link>
          <Link href="/#planos">
            <Button variant="ghost" className="text-slate-400 hover:text-white">
              ← Cancelar
            </Button>
          </Link>
        </nav>
      </header>

      {/* Checkout Section */}
      <section className="container mx-auto px-4 py-12">
        <div className="max-w-5xl mx-auto">
          <h1 className="text-3xl md:text-4xl font-bold text-white text-center mb-2">
            {isTrial ? 'Ativar Licença de Teste' : 'Finalizar Assinatura'}
          </h1>
          <p className="text-slate-400 text-center mb-12">
            Preencha seus dados para receber a chave de acesso.
          </p>

          <div className="grid md:grid-cols-12 gap-8">
            {/* Coluna da Esquerda: Resumo (4 colunas) */}
            <div className="md:col-span-5 order-2 md:order-1">
              <Card className="bg-slate-900/50 border-slate-800 sticky top-4">
                <CardHeader className="border-b border-white/5 pb-6">
                  <div className="flex justify-between items-start mb-2">
                    <div className="text-sm text-slate-400 uppercase font-bold tracking-wider">
                      Item Selecionado
                    </div>
                    {planoBase.popular && (
                      <Badge className="bg-purple-600 border-0">
                        Recomendado
                      </Badge>
                    )}
                  </div>
                  <CardTitle className="text-2xl text-white">
                    {planoBase.nome}
                  </CardTitle>
                  <p className="text-slate-400 text-sm mt-2">
                    {planoBase.descricao}
                  </p>
                </CardHeader>
                <CardContent className="pt-6">
                  <div className="space-y-4 mb-6">
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-300">Duração</span>
                      <span className="text-white font-medium">
                        {planoBase.dias} dias
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-slate-300">Suporte</span>
                      <span className="text-white font-medium">
                        {isTrial ? 'Básico' : 'Prioritário'}
                      </span>
                    </div>
                    {planoBase.economize && (
                      <div className="flex justify-between text-sm bg-green-900/20 p-2 rounded border border-green-500/20">
                        <span className="text-green-400">Economia</span>
                        <span className="text-green-400 font-bold">
                          {planoBase.economize}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="border-t border-white/5 pt-4 mt-4">
                    <div className="flex justify-between items-center">
                      <span className="text-slate-300">Total a pagar</span>
                      <span className="text-3xl font-bold text-white">
                        {isTrial
                          ? 'Grátis'
                          : `R$ ${planoBase.preco.toFixed(2)}`}
                      </span>
                    </div>
                  </div>

                  <div className="mt-6 text-center">
                    <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
                      <span className="text-green-500">🔒</span> Ambiente Seguro
                      256-bit SSL
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Coluna da Direita: Formulário (7 colunas) */}
            <div className="md:col-span-7 order-1 md:order-2">
              <Card className="bg-[#0f172a] border-slate-700 shadow-xl">
                <CardHeader>
                  <CardTitle className="text-white">Dados da Licença</CardTitle>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleSubmit} className="space-y-5">
                    {error && (
                      <div className="bg-red-500/10 border border-red-500/50 text-red-200 p-4 rounded-lg text-sm flex items-center gap-2">
                        ⚠️ {error}
                      </div>
                    )}

                    {isTrial && isTrialBloqueado && (
                      <div className="bg-yellow-500/10 border border-yellow-500/50 text-yellow-200 p-4 rounded-lg text-sm">
                        🚫{' '}
                        {elegibilidadeTrial?.motivo ||
                          'Este CPF já utilizou o período de testes.'}{' '}
                        <br />
                        <Link
                          href="/checkout/mensal"
                          className="underline font-bold mt-2 inline-block"
                        >
                          Clique aqui para assinar a versão PRO.
                        </Link>
                      </div>
                    )}

                    <div className="grid md:grid-cols-2 gap-5">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">
                          Nome Completo
                        </label>
                        <Input
                          placeholder="Ex: João Silva"
                          required
                          value={formData.nome}
                          onChange={(e) =>
                            setFormData({ ...formData, nome: e.target.value })
                          }
                          className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">
                          CPF (Para a Licença)
                        </label>
                        <Input
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
                          className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                        />
                        {verificandoElegibilidade && (
                          <p className="text-xs text-purple-400">
                            Verificando disponibilidade...
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-slate-300">
                        E-mail Principal
                      </label>
                      <Input
                        type="email"
                        placeholder="seu@email.com"
                        required
                        value={formData.email}
                        onChange={(e) =>
                          setFormData({ ...formData, email: e.target.value })
                        }
                        className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                      />
                      <p className="text-xs text-slate-500">
                        A chave de acesso será enviada para este e-mail.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-slate-300">
                        WhatsApp (Com DDD)
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
                        className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                      />
                    </div>

                    <div className="grid md:grid-cols-2 gap-5">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">
                          Criar Senha
                        </label>
                        <Input
                          type="password"
                          placeholder="Mínimo 6 caracteres"
                          required
                          minLength={6}
                          value={formData.senha}
                          onChange={(e) =>
                            setFormData({ ...formData, senha: e.target.value })
                          }
                          className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-slate-300">
                          Confirmar Senha
                        </label>
                        <Input
                          type="password"
                          placeholder="Repita a senha"
                          required
                          minLength={6}
                          value={formData.confirmarSenha}
                          onChange={(e) =>
                            setFormData({ ...formData, confirmarSenha: e.target.value })
                          }
                          className="bg-slate-950 border-slate-700 text-white focus:border-purple-500 h-11"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-slate-500">
                      Esta senha será usada para acessar o painel do cliente.
                    </p>

                    <div className="pt-4 border-t border-white/5">
                      <div className="flex items-start gap-3">
                        <input
                          type="checkbox"
                          id="termos"
                          checked={aceitouTermos}
                          onChange={(e) => setAceitouTermos(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900 text-purple-600 focus:ring-purple-500"
                          required
                        />
                        <label
                          htmlFor="termos"
                          className="text-sm text-slate-400 leading-tight"
                        >
                          Concordo com os{' '}
                          <Link
                            href="/termos"
                            target="_blank"
                            className="text-purple-400 hover:underline"
                          >
                            Termos de Uso
                          </Link>{' '}
                          e Política de Privacidade.
                        </label>
                      </div>
                    </div>

                    <Button
                      type="submit"
                      disabled={
                        loading ||
                        !aceitouTermos ||
                        (isTrial && !!isTrialBloqueado)
                      }
                      className={`w-full h-14 text-lg font-bold shadow-lg mt-4 transition-all ${
                        isTrial
                          ? 'bg-slate-700 hover:bg-slate-600 text-white'
                          : 'bg-green-600 hover:bg-green-700 text-white hover:scale-[1.02]'
                      }`}
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
                          Processando...
                        </span>
                      ) : isTrial ? (
                        'Liberar Acesso Gratuito'
                      ) : (
                        'Ir para Pagamento Seguro'
                      )}
                    </Button>

                    {!isTrial && (
                      <p className="text-center text-xs text-slate-500 mt-4">
                        Você será redirecionado para o Mercado Pago para
                        concluir a compra via PIX ou Cartão.
                      </p>
                    )}
                  </form>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
