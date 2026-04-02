'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import Link from 'next/link';
import { useState } from 'react';

export default function ManualPage() {
  const [activeSection, setActiveSection] = useState('introducao');

  const sections = [
    { id: 'introducao', title: '1. Introdução', icon: '📖' },
    { id: 'requisitos', title: '2. Requisitos', icon: '💻' },
    { id: 'instalacao', title: '3. Instalação', icon: '📥' },
    { id: 'calibracao', title: '4. Calibração', icon: '🎯' },
    { id: 'modos', title: '5. Modos de Risco', icon: '⚡' },
    { id: 'interface', title: '6. Interface', icon: '🖥️' },
    { id: 'estrategias', title: '7. Estratégias', icon: '📈' },
    { id: 'alertas', title: '8. Alertas', icon: '🔔' },
    { id: 'dicas', title: '9. Dicas', icon: '💡' },
    { id: 'faq', title: '10. FAQ', icon: '❓' },
    { id: 'suporte', title: '11. Suporte', icon: '📞' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold text-white">
            🤖 CrashBot
          </Link>
          <div className="flex gap-4">
            <Link href="/#planos">
              <Button
                variant="ghost"
                className="text-white hover:text-purple-300"
              >
                Planos
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

      {/* Hero */}
      <section className="container mx-auto px-4 py-10 text-center">
        <Badge className="mb-4 bg-purple-500/20 text-purple-300 border-purple-500/50">
          📚 Documentação Completa
        </Badge>
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
          Manual do Usuário
        </h1>
        <p className="text-xl text-slate-300 mb-6">
          Tudo que você precisa saber para usar o CrashBot Pro
        </p>
        <div className="flex gap-4 justify-center">
          <a href="/CrashBot_Manual_Usuario.pdf" download>
            <Button className="bg-purple-600 hover:bg-purple-700">
              📄 Baixar PDF
            </Button>
          </a>
        </div>
      </section>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-10">
        <div className="grid lg:grid-cols-4 gap-8">
          {/* Sidebar Navigation */}
          <aside className="lg:col-span-1">
            <Card className="bg-slate-800/50 border-slate-700 sticky top-6">
              <CardHeader>
                <CardTitle className="text-white text-lg">📑 Sumário</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <nav className="space-y-1">
                  {sections.map((section) => (
                    <a
                      key={section.id}
                      href={`#${section.id}`}
                      onClick={() => setActiveSection(section.id)}
                      className={`block px-4 py-2 text-sm transition-colors ${
                        activeSection === section.id
                          ? 'bg-purple-600 text-white'
                          : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                      }`}
                    >
                      {section.icon} {section.title}
                    </a>
                  ))}
                </nav>
              </CardContent>
            </Card>
          </aside>

          {/* Content */}
          <main className="lg:col-span-3 space-y-8">
            {/* Introdução */}
            <Card
              id="introducao"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  📖 1. Introdução
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <p>
                  O <strong className="text-white">CrashBot Pro</strong> é uma
                  ferramenta automatizada para auxiliar em jogos do tipo Crash.
                  Utilizando tecnologia de{' '}
                  <strong className="text-purple-400">
                    visão computacional
                  </strong>{' '}
                  e{' '}
                  <strong className="text-purple-400">machine learning</strong>,
                  o bot analisa padrões históricos e executa apostas de forma
                  automática.
                </p>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    ✨ Principais Funcionalidades
                  </h4>
                  <ul className="space-y-2">
                    <li>✅ Detecção automática de multiplicadores via OCR</li>
                    <li>
                      ✅ Sistema de Martingale inteligente com 3 modos de risco
                    </li>
                    <li>✅ Machine Learning para análise de padrões</li>
                    <li>✅ Alertas via Telegram em tempo real</li>
                    <li>✅ Dashboard visual com estatísticas completas</li>
                    <li>
                      ✅ Meta de lucro automática com suspensão programada
                    </li>
                  </ul>
                </div>

                <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4">
                  <p className="text-red-300">
                    <strong>⚠️ Aviso Importante:</strong> O CrashBot Pro é uma
                    ferramenta de auxílio e NÃO garante lucros. Jogos de azar
                    envolvem risco financeiro. Use com responsabilidade e nunca
                    aposte mais do que pode perder.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Requisitos */}
            <Card
              id="requisitos"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  💻 2. Requisitos do Sistema
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      🖥️ Hardware Mínimo
                    </h4>
                    <ul className="space-y-2">
                      <li>• Processador: Intel Core i3 ou equivalente</li>
                      <li>• Memória RAM: 4GB (recomendado 8GB)</li>
                      <li>• Resolução: 1920x1080 (Full HD)</li>
                      <li>• Internet estável</li>
                    </ul>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      💿 Software
                    </h4>
                    <ul className="space-y-2">
                      <li>
                        •{' '}
                        <strong className="text-white">Windows 10 ou 11</strong>{' '}
                        (64 bits)
                      </li>
                      <li>• Chrome, Firefox ou Edge atualizado</li>
                    </ul>
                  </div>
                </div>

                <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4">
                  <p className="text-yellow-300">
                    <strong>🚫 Importante:</strong> O CrashBot Pro funciona{' '}
                    <strong>EXCLUSIVAMENTE em computadores Windows</strong>. Não
                    há versão para Mac, Linux, celular ou tablet.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Instalação */}
            <Card
              id="instalacao"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  📥 3. Instalação e Primeiro Acesso
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    📦 Download e Instalação
                  </h4>
                  <ol className="space-y-2 list-decimal list-inside">
                    <li>
                      Acesse{' '}
                      <strong className="text-purple-400">
                        tucunarebot.com.br
                      </strong>{' '}
                      e faça login
                    </li>
                    <li>
                      Vá em &quot;Minhas Licenças&quot; e copie sua chave de
                      ativação
                    </li>
                    <li>
                      Baixe o arquivo{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        CrashBot_Pro.exe
                      </code>
                    </li>
                    <li>
                      Extraia o arquivo ZIP em uma pasta de sua preferência
                    </li>
                    <li>
                      Execute o arquivo{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        CrashBot_Pro.exe
                      </code>
                    </li>
                  </ol>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🔑 Primeiro Acesso
                  </h4>
                  <ol className="space-y-2 list-decimal list-inside">
                    <li>Cole a chave de licença que você copiou do site</li>
                    <li>
                      Aguarde a validação (necessário conexão com internet)
                    </li>
                    <li>Após validação, a chave será salva automaticamente</li>
                  </ol>
                </div>

                <div className="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4">
                  <h4 className="text-blue-300 font-semibold mb-2">
                    🔗 Vinculação de Dispositivo (HWID)
                  </h4>
                  <p className="text-blue-200">
                    Sua licença é vinculada ao seu computador através do HWID
                    (Hardware ID). Para trocar de PC, entre em contato com o
                    suporte.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Calibração */}
            <Card
              id="calibracao"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  🎯 4. Calibração da Tela
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <p>
                  A calibração é{' '}
                  <strong className="text-white">essencial</strong> para o bot
                  funcionar corretamente. Você precisa mapear as áreas da tela
                  do jogo.
                </p>

                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-slate-600">
                        <th className="py-3 px-4 text-white">Área</th>
                        <th className="py-3 px-4 text-white">Descrição</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Multiplicador
                        </td>
                        <td className="py-3 px-4">
                          Onde os números voam/explodem no centro
                        </td>
                      </tr>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Saldo
                        </td>
                        <td className="py-3 px-4">
                          Onde aparece seu saldo em R$ no topo
                        </td>
                      </tr>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Status da Aposta
                        </td>
                        <td className="py-3 px-4">
                          Onde aparece &quot;Apostar&quot; ou contagem
                          regressiva
                        </td>
                      </tr>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Campo de Valor
                        </td>
                        <td className="py-3 px-4">
                          Onde digita o valor da aposta
                        </td>
                      </tr>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Campo Auto-Retirar
                        </td>
                        <td className="py-3 px-4">
                          Onde digita o multiplicador alvo (ex: 1.85)
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 px-4 font-semibold text-purple-400">
                          Botão Apostar
                        </td>
                        <td className="py-3 px-4">
                          O botão verde grande de apostar
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🎯 Como Calibrar
                  </h4>
                  <ol className="space-y-2 list-decimal list-inside">
                    <li>
                      Execute o bot e selecione{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">0</code>{' '}
                      para criar novo perfil
                    </li>
                    <li>
                      Digite um nome para o perfil (ex: &quot;MeuMonitor&quot;)
                    </li>
                    <li>
                      Para cada área, posicione o mouse no{' '}
                      <strong className="text-green-400">
                        CANTO SUPERIOR ESQUERDO
                      </strong>{' '}
                      e pressione Enter
                    </li>
                    <li>
                      Depois posicione no{' '}
                      <strong className="text-green-400">
                        CANTO INFERIOR DIREITO
                      </strong>{' '}
                      e pressione Enter
                    </li>
                    <li>Repita para todas as 6 áreas obrigatórias</li>
                  </ol>
                </div>

                <div className="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4">
                  <h4 className="text-blue-300 font-semibold mb-2">
                    💡 Dicas de Calibração
                  </h4>
                  <ul className="space-y-1 text-blue-200">
                    <li>
                      • Mantenha o jogo em tela cheia durante a calibração
                    </li>
                    <li>
                      • Não redimensione a janela do navegador após calibrar
                    </li>
                    <li>• Se trocar de monitor, será necessário recalibrar</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Modos de Risco */}
            <Card
              id="modos"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  ⚡ 5. Modos de Risco
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <p>
                  O CrashBot Pro oferece{' '}
                  <strong className="text-white">3 modos de operação</strong>,
                  cada um com características próprias de risco e retorno.
                </p>

                <div className="grid md:grid-cols-3 gap-4">
                  {/* Conservador */}
                  <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4 text-center">
                    <div className="text-3xl mb-2">🟢</div>
                    <h4 className="text-green-400 font-bold text-lg">
                      CONSERVADOR
                    </h4>
                    <div className="text-4xl font-bold text-white my-3">
                      33%
                    </div>
                    <p className="text-sm text-green-300">da banca</p>
                    <div className="mt-3 text-sm">
                      <p>
                        <strong>Gatilho:</strong> 8 velas
                      </p>
                      <p>
                        <strong>Meta:</strong> 25% a 40%
                      </p>
                    </div>
                  </div>

                  {/* Moderado */}
                  <div className="bg-yellow-900/30 border border-yellow-500/50 rounded-lg p-4 text-center">
                    <div className="text-3xl mb-2">🟡</div>
                    <h4 className="text-yellow-400 font-bold text-lg">
                      MODERADO
                    </h4>
                    <div className="text-4xl font-bold text-white my-3">
                      50%
                    </div>
                    <p className="text-sm text-yellow-300">da banca</p>
                    <div className="mt-3 text-sm">
                      <p>
                        <strong>Gatilho:</strong> 7 ou 8 velas
                      </p>
                      <p>
                        <strong>Meta:</strong> 30% a 45%
                      </p>
                    </div>
                  </div>

                  {/* Agressivo */}
                  <div className="bg-red-900/30 border border-red-500/50 rounded-lg p-4 text-center">
                    <div className="text-3xl mb-2">🔴</div>
                    <h4 className="text-red-400 font-bold text-lg">
                      AGRESSIVO
                    </h4>
                    <div className="text-4xl font-bold text-white my-3">
                      100%
                    </div>
                    <p className="text-sm text-red-300">da banca</p>
                    <div className="mt-3 text-sm">
                      <p>
                        <strong>Gatilho:</strong> 6 ou 7 velas
                      </p>
                      <p>
                        <strong>Meta:</strong> 35% a 55%
                      </p>
                    </div>
                  </div>
                </div>

                <div className="bg-purple-900/30 border border-purple-500/50 rounded-lg p-4">
                  <h4 className="text-purple-300 font-semibold mb-2">
                    ⏸️ Suspensão Automática
                  </h4>
                  <p className="text-purple-200">
                    Quando o bot atinge a meta de lucro, ele entra em{' '}
                    <strong>suspensão automática por 4 horas</strong>. Isso
                    protege seus ganhos e evita operações em momentos de alta
                    volatilidade.
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* Interface */}
            <Card
              id="interface"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  🖥️ 6. Interface do Bot
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      💰 Painel de Banca
                    </h4>
                    <ul className="space-y-1">
                      <li>• Saldo atual em R$</li>
                      <li>• Lucro/Prejuízo (valor e %)</li>
                      <li>• Tempo de execução</li>
                      <li>• Rodadas processadas</li>
                    </ul>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      📊 Painel de Histórico
                    </h4>
                    <ul className="space-y-1">
                      <li>• Últimos 15 multiplicadores</li>
                      <li>• Média, volatilidade, CV</li>
                      <li>• Contagem de zeros (1.00x)</li>
                      <li>• Maior sequência de baixos</li>
                    </ul>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      🎯 Painel de Estratégia
                    </h4>
                    <ul className="space-y-1">
                      <li>• Modo de risco atual</li>
                      <li>• Status do Martingale</li>
                      <li>• Dobra atual (1 a 4)</li>
                      <li>• Confiança do ML</li>
                    </ul>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">🎨 Cores</h4>
                    <ul className="space-y-1">
                      <li>
                        <span className="text-green-400">● Verde:</span>{' '}
                        multiplicador &gt;= 2.00x
                      </li>
                      <li>
                        <span className="text-red-400">● Vermelho:</span>{' '}
                        multiplicador &lt; 2.00x
                      </li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Estratégias */}
            <Card
              id="estrategias"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  📈 7. Sistema de Estratégias
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🎲 Martingale Comercial
                  </h4>
                  <ol className="space-y-2 list-decimal list-inside">
                    <li>
                      O bot aguarda X velas baixas consecutivas (&lt; 2.00x)
                    </li>
                    <li>
                      Quando atinge o gatilho, inicia a sequência de apostas
                    </li>
                    <li>Se perder, dobra a aposta (até 4 dobras)</li>
                    <li>Se ganhar entre 1.81x e 1.99x, volta para dobra 2</li>
                    <li>Se ganhar &gt;= 2.00x, encerra o ciclo com sucesso</li>
                  </ol>
                  <p className="mt-3 text-sm text-slate-400">
                    💡 <strong>Targets Randomizados:</strong> O bot sorteia o
                    target entre 1.81x e 1.95x a cada aposta para evitar
                    detecção por padrões.
                  </p>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🎯 ML High Confidence (Sniper)
                  </h4>
                  <p className="mb-2">
                    Estratégia secundária que roda em paralelo:
                  </p>
                  <ul className="space-y-1">
                    <li>• Usa Machine Learning para detectar padrões</li>
                    <li>• Só aposta quando confiança &gt;= 80%</li>
                    <li>• Apostas pequenas (1% da banca)</li>
                    <li>• Target fixo em 2.00x</li>
                  </ul>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🛡️ Sistema de Segurança
                  </h4>
                  <ul className="space-y-1">
                    <li>• Detecta &quot;Fase Arrecadatória&quot;</li>
                    <li>• Analisa volatilidade das últimas 20 rodadas</li>
                    <li>• Alerta quando detecta 6 velas baixas</li>
                    <li>• Stop-loss automático (50% da banca)</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Alertas */}
            <Card
              id="alertas"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  🔔 8. Alertas e Notificações
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    🔊 Alertas Sonoros
                  </h4>
                  <ul className="space-y-1">
                    <li>
                      •{' '}
                      <strong className="text-green-400">
                        Som agudo (beep curto):
                      </strong>{' '}
                      Aposta GANHOU
                    </li>
                    <li>
                      •{' '}
                      <strong className="text-red-400">
                        Som grave (beep longo):
                      </strong>{' '}
                      Aposta PERDEU
                    </li>
                    <li>
                      •{' '}
                      <strong className="text-yellow-400">
                        Som repetido (3x):
                      </strong>{' '}
                      Stop-Loss
                    </li>
                  </ul>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    📱 Configurar Telegram
                  </h4>
                  <ol className="space-y-2 list-decimal list-inside">
                    <li>
                      Crie um bot no Telegram com{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        @BotFather
                      </code>
                    </li>
                    <li>Copie o token do bot</li>
                    <li>
                      Descubra seu Chat ID com{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        @userinfobot
                      </code>
                    </li>
                    <li>
                      Edite o arquivo{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        config.json
                      </code>
                    </li>
                    <li>
                      Preencha{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        telegram_bot_token
                      </code>{' '}
                      e{' '}
                      <code className="bg-slate-700 px-2 py-1 rounded">
                        telegram_chat_id
                      </code>
                    </li>
                  </ol>
                </div>

                <div className="bg-blue-900/30 border border-blue-500/50 rounded-lg p-4">
                  <h4 className="text-blue-300 font-semibold mb-2">
                    📬 Tipos de Notificações
                  </h4>
                  <ul className="space-y-1 text-blue-200">
                    <li>
                      • <strong>HIT/MISS:</strong> Resultado de cada aposta
                    </li>
                    <li>
                      • <strong>Meta Atingida:</strong> Quando bate a meta de
                      lucro
                    </li>
                    <li>
                      • <strong>Stop-Loss:</strong> Quando perde 50% da banca
                    </li>
                    <li>
                      • <strong>Relatório Periódico:</strong> A cada 30 minutos
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* Dicas */}
            <Card
              id="dicas"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  💡 9. Dicas de Uso
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      ✅ Antes de Começar
                    </h4>
                    <ol className="space-y-1 list-decimal list-inside">
                      <li>Teste com valores baixos primeiro</li>
                      <li>Certifique-se que a calibração está correta</li>
                      <li>Verifique se o jogo está em tela cheia</li>
                      <li>Não minimize a janela do jogo</li>
                      <li>Desative protetor de tela</li>
                    </ol>
                  </div>
                  <div className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-white font-semibold mb-3">
                      ⚙️ Durante a Operação
                    </h4>
                    <ul className="space-y-1">
                      <li>• Não mova o mouse sobre as áreas calibradas</li>
                      <li>• Não clique na tela do jogo manualmente</li>
                      <li>• Mantenha a conexão de internet estável</li>
                      <li>
                        • Use{' '}
                        <code className="bg-slate-700 px-1 rounded">
                          Ctrl+C
                        </code>{' '}
                        para parar
                      </li>
                    </ul>
                  </div>
                </div>

                <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4">
                  <h4 className="text-green-300 font-semibold mb-2">
                    💵 Gestão de Banca
                  </h4>
                  <ul className="space-y-1 text-green-200">
                    <li>
                      • Comece com o modo <strong>Conservador</strong>
                    </li>
                    <li>• Nunca aposte dinheiro que não pode perder</li>
                    <li>• Defina um valor máximo diário</li>
                    <li>• Respeite as pausas de suspensão automática</li>
                    <li>
                      • Não tente &quot;recuperar&quot; perdas aumentando o
                      risco
                    </li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            {/* FAQ */}
            <Card
              id="faq"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  ❓ 10. Perguntas Frequentes
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  {
                    q: 'O bot funciona em celular?',
                    a: 'Não. O CrashBot Pro funciona EXCLUSIVAMENTE em computadores Windows.',
                  },
                  {
                    q: 'Posso usar em mais de um computador?',
                    a: 'Não. A licença é vinculada ao HWID do computador onde foi ativada. Para trocar de PC, entre em contato com o suporte.',
                  },
                  {
                    q: 'O que é HWID?',
                    a: 'Hardware ID é um identificador único do seu computador baseado nos componentes de hardware.',
                  },
                  {
                    q: 'Preciso deixar o bot rodando 24h?',
                    a: 'Não é recomendado. O bot tem meta de lucro e entra em suspensão automática. Use por algumas horas e respeite as pausas.',
                  },
                  {
                    q: 'O bot garante lucro?',
                    a: 'NÃO. Nenhuma ferramenta pode garantir lucro em jogos de azar. O bot é uma ferramenta de auxílio que utiliza estatística e matemática para aumentar suas chances, mas perdas fazem parte do processo.',
                  },
                  {
                    q: 'Como atualizo o bot?',
                    a: 'O bot verifica atualizações automaticamente ao iniciar. Se houver nova versão, você será notificado.',
                  },
                ].map((item, index) => (
                  <div key={index} className="bg-slate-900/50 rounded-lg p-4">
                    <h4 className="text-purple-400 font-semibold mb-2">
                      {item.q}
                    </h4>
                    <p className="text-slate-300">{item.a}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Suporte */}
            <Card
              id="suporte"
              className="bg-slate-800/50 border-slate-700 scroll-mt-6"
            >
              <CardHeader>
                <CardTitle className="text-white text-2xl">
                  📞 11. Suporte
                </CardTitle>
              </CardHeader>
              <CardContent className="text-slate-300 space-y-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-slate-600">
                        <th className="py-3 px-4 text-white">Canal</th>
                        <th className="py-3 px-4 text-white">Contato</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold">🌐 Site</td>
                        <td className="py-3 px-4 text-purple-400">
                          tucunarebot.com.br
                        </td>
                      </tr>
                      <tr className="border-b border-slate-700">
                        <td className="py-3 px-4 font-semibold">📧 E-mail</td>
                        <td className="py-3 px-4">
                          suporte@tucunarebot.com.br
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 px-4 font-semibold">💬 WhatsApp</td>
                        <td className="py-3 px-4">
                          (disponível na área do cliente)
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="bg-slate-900/50 rounded-lg p-4">
                  <h4 className="text-white font-semibold mb-3">
                    📋 Ao Entrar em Contato
                  </h4>
                  <p className="mb-2">
                    Para agilizar o atendimento, tenha em mãos:
                  </p>
                  <ul className="space-y-1">
                    <li>• Seu e-mail de cadastro</li>
                    <li>• Chave de licença</li>
                    <li>• Versão do bot</li>
                    <li>• Descrição detalhada do problema</li>
                    <li>• Screenshot da tela se possível</li>
                  </ul>
                </div>

                <div className="bg-green-900/30 border border-green-500/50 rounded-lg p-4 text-center">
                  <p className="text-green-300 text-lg">
                    <strong>Obrigado por escolher o CrashBot Pro!</strong>
                  </p>
                  <p className="text-green-200">Bons trades! 🚀</p>
                </div>
              </CardContent>
            </Card>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-slate-800 py-10 mt-10">
        <div className="container mx-auto px-4 text-center text-slate-400">
          <p>© 2025 CrashBot. Todos os direitos reservados.</p>
          <p className="mt-2 text-sm">
            Jogue com responsabilidade. Este produto é destinado apenas para
            maiores de 18 anos.
          </p>
          <div className="mt-4 flex justify-center gap-6 text-sm">
            <Link href="/" className="hover:text-purple-400 transition-colors">
              Início
            </Link>
            <Link
              href="/privacidade"
              className="hover:text-purple-400 transition-colors"
            >
              Privacidade
            </Link>
            <Link
              href="/termos"
              className="hover:text-purple-400 transition-colors"
            >
              Termos
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
