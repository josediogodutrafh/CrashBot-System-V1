import Link from 'next/link';

export default function TermosDeUso() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#1a1a2e] text-white">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8 text-center bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
          Termos de Uso
        </h1>

        <div className="bg-slate-800/50 rounded-2xl p-8 space-y-6 text-gray-300">
          <p className="text-sm text-gray-400">
            Última atualização: {new Date().toLocaleDateString('pt-BR')}
          </p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              1. Aceitação dos Termos
            </h2>
            <p>
              Ao acessar ou usar o CrashBot, você concorda em cumprir estes
              Termos de Uso. Se você não concordar com qualquer parte destes
              termos, não deve usar nosso serviço.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              2. Descrição do Serviço
            </h2>
            <p>
              {/* CORREÇÃO: Aspas escapadas */}O CrashBot é um software de
              automação e análise para jogos do tipo &quot;Crash&quot;. O
              software é fornecido apenas para fins de entretenimento e análise
              estatística.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              3. Aviso de Risco
            </h2>
            <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4 mt-2">
              <p className="text-red-300 font-semibold">
                ⚠️ ATENÇÃO: RISCO FINANCEIRO
              </p>
              <ul className="list-disc list-inside mt-2 space-y-1 text-red-200">
                <li>
                  Jogos de azar envolvem risco significativo de perda financeira
                </li>
                <li>O CrashBot NÃO garante lucros ou resultados positivos</li>
                <li>Resultados passados não garantem resultados futuros</li>
                <li>Nunca aposte mais do que você pode perder</li>
                <li>
                  Se você tem problemas com jogos de azar, procure ajuda
                  profissional
                </li>
              </ul>
            </div>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              4. Licença de Uso
            </h2>
            <p>Ao adquirir uma licença, você recebe:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Direito de uso pessoal e intransferível do software</li>
              <li>Acesso às atualizações durante o período da licença</li>
              <li>Suporte técnico via WhatsApp</li>
            </ul>
            <p className="mt-2">
              A licença é vinculada a um único dispositivo (HWID) e não pode ser
              compartilhada.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              5. Restrições de Uso
            </h2>
            <p>Você NÃO pode:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Revender, sublicenciar ou transferir sua licença</li>
              <li>
                Fazer engenharia reversa, descompilar ou modificar o software
              </li>
              <li>Usar o software para atividades ilegais</li>
              <li>Compartilhar sua chave de licença com terceiros</li>
              <li>Burlar o sistema de proteção HWID</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              6. Pagamento e Reembolso
            </h2>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Os pagamentos são processados pelo MercadoPago</li>
              <li>Após a ativação da licença, NÃO há reembolso</li>
              <li>
                Você pode testar o software no período experimental antes de
                comprar
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              7. Limitação de Responsabilidade
            </h2>
            <p>
              {/* CORREÇÃO: Aspas escapadas */}O CrashBot é fornecido &quot;como
              está&quot;, sem garantias de qualquer tipo. Não nos
              responsabilizamos por:
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Perdas financeiras decorrentes do uso do software</li>
              <li>Bloqueios ou banimentos em plataformas de terceiros</li>
              <li>Indisponibilidade temporária do serviço</li>
              <li>Erros ou falhas no software</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              8. Suspensão e Cancelamento
            </h2>
            <p>
              Reservamo-nos o direito de suspender ou cancelar sua licença, sem
              reembolso, em caso de violação destes termos.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              9. Propriedade Intelectual
            </h2>
            <p>
              Todo o conteúdo, código, design e marcas do CrashBot são de
              propriedade exclusiva da empresa e protegidos por leis de
              propriedade intelectual.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              10. Alterações nos Termos
            </h2>
            <p>
              Podemos modificar estes termos a qualquer momento. O uso
              continuado do serviço após alterações constitui aceitação dos
              novos termos.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              11. Lei Aplicável
            </h2>
            <p>
              Estes termos são regidos pelas leis da República Federativa do
              Brasil. Qualquer disputa será resolvida no foro da comarca de [sua
              cidade/estado].
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              12. Contato
            </h2>
            <p>Dúvidas sobre estes termos podem ser enviadas para:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>
                <strong>E-mail:</strong> contato@crashbot.com
              </li>
              <li>
                <strong>WhatsApp:</strong> (XX) XXXXX-XXXX
              </li>
            </ul>
          </section>
        </div>

        <div className="mt-8 text-center">
          {/* CORREÇÃO: Uso de Link do Next.js */}
          <Link
            href="/"
            className="text-purple-400 hover:text-purple-300 transition-colors"
          >
            ← Voltar para o início
          </Link>
        </div>
      </div>
    </div>
  );
}
