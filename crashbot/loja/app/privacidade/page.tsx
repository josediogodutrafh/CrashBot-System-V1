import Link from 'next/link';

export default function PoliticaPrivacidade() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#1a1a2e] text-white">
      <div className="container mx-auto px-4 py-16 max-w-4xl">
        <h1 className="text-4xl font-bold mb-8 text-center bg-gradient-to-r from-purple-400 to-pink-500 bg-clip-text text-transparent">
          Política de Privacidade
        </h1>

        <div className="bg-slate-800/50 rounded-2xl p-8 space-y-6 text-gray-300">
          <p className="text-sm text-gray-400">
            Última atualização: {new Date().toLocaleDateString('pt-BR')}
          </p>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              1. Introdução
            </h2>
            <p>
              {/* CORREÇÃO 1: Uso de &quot; para aspas duplas */}A CrashBot
              (&quot;nós&quot;, &quot;nosso&quot; ou &quot;empresa&quot;) está
              comprometida em proteger sua privacidade. Esta Política de
              Privacidade explica como coletamos, usamos, divulgamos e
              protegemos suas informações pessoais quando você utiliza nosso
              software e serviços.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              2. Dados que Coletamos
            </h2>
            <p>Coletamos os seguintes tipos de informações:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>
                <strong>Dados de cadastro:</strong> Nome, e-mail, CPF, WhatsApp
              </li>
              <li>
                <strong>Dados de pagamento:</strong> Processados pelo
                MercadoPago (não armazenamos dados de cartão)
              </li>
              <li>
                <strong>Dados de uso:</strong> Logs de atividade, telemetria do
                bot, HWID do dispositivo
              </li>
              <li>
                <strong>Dados técnicos:</strong> Endereço IP, tipo de navegador,
                sistema operacional
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              3. Como Usamos seus Dados
            </h2>
            <p>Utilizamos suas informações para:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Fornecer e gerenciar sua licença de software</li>
              <li>Processar pagamentos e emitir notas fiscais</li>
              <li>Enviar comunicações sobre sua conta e atualizações</li>
              <li>Melhorar nossos produtos e serviços</li>
              <li>Prevenir fraudes e garantir a segurança</li>
              <li>Cumprir obrigações legais</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              4. Compartilhamento de Dados
            </h2>
            <p>Podemos compartilhar seus dados com:</p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>
                <strong>Processadores de pagamento:</strong> MercadoPago para
                processar transações
              </li>
              <li>
                <strong>Provedores de infraestrutura:</strong> Serviços de
                hospedagem e banco de dados
              </li>
              <li>
                <strong>Autoridades legais:</strong> Quando exigido por lei
              </li>
            </ul>
            <p className="mt-2">
              Não vendemos seus dados pessoais a terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              5. Seus Direitos (LGPD)
            </h2>
            <p>
              Conforme a Lei Geral de Proteção de Dados (Lei 13.709/2018), você
              tem direito a:
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>Confirmar a existência de tratamento de dados</li>
              <li>Acessar seus dados pessoais</li>
              <li>Corrigir dados incompletos ou desatualizados</li>
              <li>Solicitar anonimização, bloqueio ou eliminação de dados</li>
              <li>Solicitar portabilidade dos dados</li>
              <li>Revogar consentimento a qualquer momento</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              6. Segurança dos Dados
            </h2>
            <p>
              Implementamos medidas técnicas e organizacionais para proteger
              seus dados, incluindo: criptografia de dados em trânsito (HTTPS),
              hash de senhas (bcrypt), controle de acesso restrito e
              monitoramento de segurança.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              7. Retenção de Dados
            </h2>
            <p>
              Mantemos seus dados pelo tempo necessário para fornecer nossos
              serviços e cumprir obrigações legais. Após o término da relação,
              os dados serão eliminados ou anonimizados, exceto quando a
              retenção for exigida por lei.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              8. Cookies
            </h2>
            <p>
              Utilizamos cookies essenciais para funcionamento do site e
              autenticação. Você pode configurar seu navegador para recusar
              cookies, mas isso pode afetar a funcionalidade do serviço.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              9. Contato
            </h2>
            <p>
              Para exercer seus direitos ou esclarecer dúvidas sobre esta
              política, entre em contato:
            </p>
            <ul className="list-disc list-inside mt-2 space-y-1 ml-4">
              <li>
                <strong>E-mail:</strong> privacidade@crashbot.com
              </li>
              <li>
                <strong>WhatsApp:</strong> (XX) XXXXX-XXXX
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">
              10. Alterações
            </h2>
            <p>
              Esta política pode ser atualizada periodicamente. Notificaremos
              sobre mudanças significativas por e-mail ou através do nosso site.
            </p>
          </section>
        </div>

        <div className="mt-8 text-center">
          {/* CORREÇÃO 2: Substituindo <a> por <Link> do Next.js */}
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
