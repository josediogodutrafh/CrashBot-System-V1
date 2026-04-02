'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import Link from 'next/link';

export default function PagamentoPendentePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
      <Card className="bg-slate-800/50 border-slate-700 max-w-lg w-full">
        <CardContent className="pt-10 pb-10 text-center">
          {/* Ícone de Pendente */}
          <div className="w-20 h-20 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              className="w-10 h-10 text-yellow-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>

          {/* Título */}
          <h1 className="text-3xl font-bold text-white mb-4">
            Pagamento Pendente ⏳
          </h1>

          {/* Mensagem */}
          <p className="text-slate-300 mb-6">
            Seu pagamento está sendo processado e aguarda confirmação.
          </p>

          {/* Info Box */}
          <div className="bg-slate-900/50 rounded-lg p-6 mb-8 text-left">
            <h3 className="text-yellow-400 font-semibold mb-4">
              📋 Próximos passos:
            </h3>
            <ul className="text-slate-300 text-sm space-y-2">
              <li className="flex items-center gap-2">
                <span className="text-yellow-400">1.</span>
                Se escolheu boleto, efetue o pagamento
              </li>
              <li className="flex items-center gap-2">
                <span className="text-yellow-400">2.</span>
                Aguarde a confirmação (pode levar até 3 dias úteis)
              </li>
              <li className="flex items-center gap-2">
                <span className="text-yellow-400">3.</span>
                Você receberá um e-mail quando for aprovado
              </li>
            </ul>
          </div>

          {/* Aviso */}
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 mb-8">
            <p className="text-purple-300 text-sm">
              💡 Assim que o pagamento for confirmado, enviaremos sua licença
              por e-mail automaticamente.
            </p>
          </div>

          {/* Botões */}
          <div className="space-y-3">
            <Link href="/" className="block">
              <Button className="w-full bg-purple-600 hover:bg-purple-700 text-white py-6">
                Voltar para Home
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
