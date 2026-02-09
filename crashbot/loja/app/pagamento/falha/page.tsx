'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import Link from 'next/link';

export default function PagamentoFalhaPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <Card className="bg-slate-800/50 border-slate-700 max-w-lg w-full">
        <CardContent className="pt-10 pb-10 text-center">
          {/* Ícone de Erro */}
          <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              className="w-10 h-10 text-red-500"
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
          </div>

          {/* Título */}
          <h1 className="text-3xl font-bold text-white mb-4">
            Pagamento não aprovado 😕
          </h1>

          {/* Mensagem */}
          <p className="text-slate-300 mb-6">
            Infelizmente seu pagamento não foi aprovado. Isso pode acontecer por
            diversos motivos.
          </p>

          {/* Dicas */}
          <div className="bg-slate-900/50 rounded-lg p-6 mb-8 text-left">
            <h3 className="text-purple-400 font-semibold mb-4">
              💡 O que você pode fazer:
            </h3>
            <ul className="text-slate-300 text-sm space-y-2">
              <li className="flex items-center gap-2">
                <span className="text-purple-400">•</span>
                Verificar os dados do cartão
              </li>
              <li className="flex items-center gap-2">
                <span className="text-purple-400">•</span>
                Tentar outro método de pagamento
              </li>
              <li className="flex items-center gap-2">
                <span className="text-purple-400">•</span>
                Entrar em contato com seu banco
              </li>
            </ul>
          </div>

          {/* Botões */}
          <div className="space-y-3">
            <Link href="/#planos" className="block">
              <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white py-6">
                Tentar Novamente
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
        </CardContent>
      </Card>
    </div>
  );
}
