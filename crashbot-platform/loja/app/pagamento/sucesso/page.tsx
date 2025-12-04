'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';

function SucessoContent() {
  const searchParams = useSearchParams();
  const paymentId = searchParams.get('collection_id');
  const status = searchParams.get('collection_status');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <Card className="bg-slate-800/50 border-slate-700 max-w-lg w-full">
        <CardContent className="pt-10 pb-10 text-center">
          {/* Ícone de Sucesso */}
          <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              className="w-10 h-10 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>

          {/* Título */}
          <h1 className="text-3xl font-bold text-white mb-4">
            Pagamento Aprovado! 🎉
          </h1>

          {/* Mensagem */}
          <p className="text-slate-300 mb-6">
            Sua compra foi realizada com sucesso!
          </p>

          {/* Info Box */}
          <div className="bg-slate-900/50 rounded-lg p-6 mb-8 text-left">
            <h3 className="text-purple-400 font-semibold mb-4 flex items-center gap-2">
              <span>📧</span> Verifique seu e-mail
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Enviamos para o seu e-mail:
            </p>
            <ul className="text-slate-300 text-sm space-y-2">
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Sua chave de licença
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Dados de acesso ao painel
              </li>
              <li className="flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Instruções de instalação
              </li>
            </ul>
          </div>

          {/* Aviso */}
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4 mb-8">
            <p className="text-yellow-400 text-sm">
              ⚠️ Não encontrou o e-mail? Verifique a pasta de spam ou lixo
              eletrônico.
            </p>
          </div>

          {/* Botões */}
          <div className="space-y-3">
            <Link href="/login" className="block">
              <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white py-6">
                Acessar Meu Painel
              </Button>
            </Link>
            <Link href="/" className="block">
              <Button
                variant="ghost"
                className="w-full text-slate-400 hover:text-white"
              >
                Voltar para Home
              </Button>
            </Link>
          </div>

          {/* ID do Pagamento */}
          {paymentId && (
            <p className="text-slate-500 text-xs mt-6">
              ID do pagamento: {paymentId}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function PagamentoSucessoPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
          <div className="text-white">Carregando...</div>
        </div>
      }
    >
      <SucessoContent />
    </Suspense>
  );
}
