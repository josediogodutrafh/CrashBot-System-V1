import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Image from 'next/image';
import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <div className="text-2xl font-bold text-white">🤖 CrashBot</div>
          <div className="flex gap-4">
            <Link href="#plataforma">
              <Button
                variant="ghost"
                className="text-white hover:text-purple-300"
              >
                Plataforma
              </Button>
            </Link>
            <Link href="#planos">
              <Button
                variant="ghost"
                className="text-white hover:text-purple-300"
              >
                Planos
              </Button>
            </Link>
            <Link href="#como-funciona">
              <Button
                variant="ghost"
                className="text-white hover:text-purple-300"
              >
                Como Funciona
              </Button>
            </Link>
            <Link href="/manual">
              <Button
                variant="ghost"
                className="text-white hover:text-purple-300"
              >
                📚 Manual
              </Button>
            </Link>
            <Link href="/login">
              <Button
                variant="outline"
                className="border-purple-500 text-purple-300 hover:bg-purple-500 hover:text-white"
              >
                Entrar
              </Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-20 text-center">
        <Badge className="mb-6 bg-purple-500/20 text-purple-300 border-purple-500/50">
          🚀 Bot com IA Avançada
        </Badge>

        <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
          Automatize Suas Apostas
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
            Com Inteligência Artificial
          </span>
        </h1>

        <p className="text-xl text-slate-300 mb-10 max-w-2xl mx-auto">
          Bot profissional com Machine Learning que analisa padrões em tempo
          real. Taxa de acerto comprovada. Resultados reais.
        </p>

        <div className="flex gap-4 justify-center">
          <Link href="#planos">
            <Button
              size="lg"
              className="bg-purple-600 hover:bg-purple-700 text-white px-8 py-6 text-lg"
            >
              Ver Planos
            </Button>
          </Link>
          <Link href="/manual">
            <Button
              size="lg"
              className="bg-white text-purple-700 hover:bg-purple-100 px-8 py-6 text-lg font-semibold"
            >
              📚 Ver Manual
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-8 mt-20 max-w-3xl mx-auto">
          <div className="text-center">
            <div className="text-4xl font-bold text-purple-400">GESTÃO</div>
            <div className="text-slate-400">Automática</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-purple-400">INSTALAÇÃO</div>
            <div className="text-slate-400">Prática</div>
          </div>
          <div className="text-center">
            <div className="text-4xl font-bold text-purple-400">24/7</div>
            <div className="text-slate-400">Suporte</div>
          </div>
        </div>
      </section>

      {/* Plataforma Parceira - BRABET */}
      <section id="plataforma" className="container mx-auto px-4 py-20">
        <h2 className="text-4xl font-bold text-white text-center mb-4">
          Plataforma Compatível
        </h2>
        <p className="text-slate-400 text-center mb-12">
          Nosso bot funciona exclusivamente com a Brabet - Cadastre-se agora!
        </p>

        <Card className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 border-purple-500 max-w-4xl mx-auto">
          <CardContent className="p-8">
            <div className="grid md:grid-cols-2 gap-8 items-center">
              {/* Lado Esquerdo - Informações */}
              <div className="text-center md:text-left">
                <div className="text-4xl font-bold text-white mb-2">
                  🎰 BRABET
                </div>
                <p className="text-purple-300 text-lg mb-6">
                  A melhor plataforma de apostas do Brasil
                </p>

                <ul className="space-y-3 text-slate-300 mb-8">
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Saque rápido via PIX
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Bônus de boas-vindas
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    100% compatível com o CrashBot
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="text-green-400">✓</span>
                    Suporte 24 horas
                  </li>
                </ul>

                <a
                  href="https://www.brabet.com/?agentid=135486005"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <Button
                    size="lg"
                    className="bg-green-600 hover:bg-green-700 text-white px-8 py-6 text-lg w-full md:w-auto"
                  >
                    🚀 Criar Conta na Brabet
                  </Button>
                </a>

                <p className="text-xs text-slate-500 mt-4">
                  * Use nosso link para garantir compatibilidade com o bot
                </p>
              </div>

              {/* Lado Direito - QR Code */}
              <div className="text-center">
                <div className="bg-white p-4 rounded-xl inline-block mb-4">
                  <Image
                    src="/qrcode-brabet.png"
                    alt="QR Code Brabet"
                    width={192}
                    height={192}
                    className="object-contain"
                  />
                </div>
                <p className="text-slate-400 text-sm">
                  📱 Escaneie o QR Code para cadastrar
                </p>
                <p className="text-purple-400 text-xs mt-2">
                  ou acesse: brabet.com
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center mt-8">
          <Badge className="bg-yellow-500/20 text-yellow-300 border-yellow-500/50 text-sm px-4 py-2">
            ⚠️ IMPORTANTE: O bot só funciona com contas criadas através do nosso
            link
          </Badge>
        </div>
      </section>

      {/* Como Funciona */}
      <section id="como-funciona" className="container mx-auto px-4 py-20">
        <h2 className="text-4xl font-bold text-white text-center mb-16">
          Como Funciona
        </h2>

        <div className="grid md:grid-cols-3 gap-8">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center text-2xl mb-4">
                1️⃣
              </div>
              <CardTitle className="text-white">Cadastre na Brabet</CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Crie sua conta na Brabet usando nosso link exclusivo. É rápido,
              seguro e você ganha bônus de boas-vindas!
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center text-2xl mb-4">
                2️⃣
              </div>
              <CardTitle className="text-white">Compre a Licença</CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Escolha o plano ideal para você. Pagamento seguro via Mercado
              Pago. Licença enviada instantaneamente.
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center text-2xl mb-4">
                3️⃣
              </div>
              <CardTitle className="text-white">Lucre no Automático</CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Instale o bot, configure seu saldo e deixe a IA trabalhar.
              Acompanhe seus resultados em tempo real.
            </CardContent>
          </Card>
        </div>

        {/* Link para Manual */}
        <div className="text-center mt-12">
          <Link href="/manual">
            <Button
              size="lg"
              variant="outline"
              className="border-purple-500 text-purple-300 hover:bg-purple-500 hover:text-white"
            >
              📚 Ver Manual Completo
            </Button>
          </Link>
        </div>
      </section>

      {/* Planos */}
      <section id="planos" className="container mx-auto px-4 py-20">
        <h2 className="text-4xl font-bold text-white text-center mb-4">
          Escolha seu Plano
        </h2>
        <p className="text-slate-400 text-center mb-16">
          Comece agora e veja resultados reais
        </p>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {/* Plano Experimental */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Experimental</CardTitle>
              <div className="text-slate-400">Para testar</div>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <span className="text-4xl font-bold text-white">R$ 29,90</span>
                <span className="text-slate-400">/3 dias</span>
              </div>
              <ul className="space-y-3 text-slate-300 mb-8">
                <li>✅ Acesso completo ao bot</li>
                <li>✅ Suporte via WhatsApp</li>
                <li>✅ Atualizações inclusas</li>
                <li>❌ Dashboard avançado</li>
              </ul>
              <Link href="/checkout/experimental">
                <Button className="w-full bg-slate-700 hover:bg-slate-600">
                  Começar Agora
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Plano Semanal - Destaque */}
          <Card className="bg-gradient-to-b from-purple-900/50 to-slate-800/50 border-purple-500 relative">
            <div className="absolute -top-3 left-1/2 -translate-x-1/2">
              <Badge className="bg-purple-600 text-white">Mais Popular</Badge>
            </div>
            <CardHeader>
              <CardTitle className="text-white">Semanal</CardTitle>
              <div className="text-slate-400">Melhor custo-benefício</div>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <span className="text-slate-400 line-through text-lg">
                  R$ 299
                </span>
                <br />
                <span className="text-4xl font-bold text-white">R$ 149,90</span>
                <span className="text-slate-400">/7 dias</span>
              </div>
              <ul className="space-y-3 text-slate-300 mb-8">
                <li>✅ Acesso completo ao bot</li>
                <li>✅ Suporte prioritário</li>
                <li>✅ Atualizações inclusas</li>
                <li>✅ Dashboard avançado</li>
              </ul>
              <Link href="/checkout/semanal">
                <Button className="w-full bg-purple-600 hover:bg-purple-700">
                  Escolher Plano
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Plano Mensal */}
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white">Mensal</CardTitle>
              <div className="text-slate-400">Para profissionais</div>
            </CardHeader>
            <CardContent>
              <div className="mb-6">
                <span className="text-slate-400 line-through text-lg">
                  R$ 659
                </span>
                <br />
                <span className="text-4xl font-bold text-white">R$ 499,90</span>
                <span className="text-slate-400">/30 dias</span>
              </div>
              <ul className="space-y-3 text-slate-300 mb-8">
                <li>✅ Acesso completo ao bot</li>
                <li>✅ Suporte VIP 24/7</li>
                <li>✅ Atualizações inclusas</li>
                <li>✅ Dashboard avançado</li>
                <li>✅ Consultoria inicial</li>
              </ul>
              <Link href="/checkout/mensal">
                <Button className="w-full bg-slate-700 hover:bg-slate-600">
                  Escolher Plano
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* FAQ */}
      <section className="container mx-auto px-4 py-20">
        <h2 className="text-4xl font-bold text-white text-center mb-16">
          Perguntas Frequentes
        </h2>

        <div className="max-w-3xl mx-auto space-y-6">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                O bot é seguro?
              </CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Sim! O bot roda localmente no seu computador e não tem acesso às
              suas senhas. Apenas controla a interface do jogo de forma
              automática.
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                Por que preciso cadastrar na Brabet pelo link?
              </CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              O bot foi desenvolvido especificamente para a Brabet. Contas
              criadas pelo nosso link garantem total compatibilidade e suporte
              técnico.
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                Posso usar em qualquer computador?
              </CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Cada licença é vinculada a um computador. Se precisar trocar de
              máquina, entre em contato com nosso suporte.
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardHeader>
              <CardTitle className="text-white text-lg">
                Qual a taxa de acerto?
              </CardTitle>
            </CardHeader>
            <CardContent className="text-slate-300">
              Nossa IA alcança uma taxa média de 68% de acerto. Porém,
              resultados podem variar e ganhos passados não garantem ganhos
              futuros.
            </CardContent>
          </Card>
        </div>

        {/* Link para FAQ completo */}
        <div className="text-center mt-10">
          <Link href="/manual#faq">
            <Button
              variant="link"
              className="text-purple-400 hover:text-purple-300"
            >
              Ver todas as perguntas no Manual →
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-10">
        <div className="container mx-auto px-4 text-center text-slate-400">
          <p>© 2025 CrashBot. Todos os direitos reservados.</p>
          <p className="mt-2 text-sm">
            Jogue com responsabilidade. Este produto é destinado apenas para
            maiores de 18 anos.
          </p>
          <div className="mt-4 flex justify-center gap-6 text-sm">
            <Link
              href="/manual"
              className="hover:text-purple-400 transition-colors"
            >
              📚 Manual
            </Link>
            <Link
              href="/privacidade"
              className="hover:text-purple-400 transition-colors"
            >
              Política de Privacidade
            </Link>
            <Link
              href="/termos"
              className="hover:text-purple-400 transition-colors"
            >
              Termos de Uso
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
