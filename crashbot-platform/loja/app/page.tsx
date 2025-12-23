'use client';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  Check,
  Cpu,
  Eye,
  Lock,
  Monitor,
  Smartphone,
  Terminal,
  Video,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';

// --- ESTILOS INJETADOS (ANIMAÇÕES) ---
const customStyles = `
  @keyframes blob {
    0% { transform: translate(0px, 0px) scale(1); }
    33% { transform: translate(30px, -50px) scale(1.1); }
    66% { transform: translate(-20px, 20px) scale(0.9); }
    100% { transform: translate(0px, 0px) scale(1); }
  }
  .animate-blob { animation: blob 7s infinite; }
  .animation-delay-2000 { animation-delay: 2s; }
  .animation-delay-4000 { animation-delay: 4s; }
  .glass-panel { background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.05); }
`;

// --- 1. TICKER DE DADOS ---
function MarketTicker() {
  return (
    <div className="bg-[#020617] border-b border-purple-500/20 overflow-hidden h-9 flex items-center relative z-50">
      <div className="absolute left-0 top-0 bottom-0 w-10 bg-gradient-to-r from-[#020617] to-transparent z-10"></div>
      <div className="absolute right-0 top-0 bottom-0 w-10 bg-gradient-to-l from-[#020617] to-transparent z-10"></div>

      <div className="flex items-center px-3 bg-purple-900/20 border-r border-purple-500/30 h-full z-20 shrink-0">
        <Activity className="w-3 h-3 text-green-400 mr-2 animate-pulse" />
        <span className="text-[10px] font-bold text-green-400 tracking-widest uppercase hidden md:inline">
          SYSTEM ONLINE
        </span>
      </div>

      <div className="animate-marquee whitespace-nowrap flex gap-12 text-[10px] md:text-xs font-mono font-medium items-center text-slate-400">
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>{' '}
          BOT #402: HIT 2.00x
        </span>
        <span className="flex items-center gap-2 text-yellow-400">
          <AlertTriangle className="w-3 h-3" /> IA PROTEÇÃO: FASE DE ARRECADAÇÃO
          DETECTADA
        </span>
        <span className="flex items-center gap-2">
          <Cpu className="w-3 h-3 text-blue-400" /> LATÊNCIA OCR: 12ms
        </span>
        <span className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>{' '}
          BOT #889: META BATIDA 🚀
        </span>
        <span className="flex items-center gap-2 text-purple-400">
          <Eye className="w-3 h-3" /> VISÃO COMPUTACIONAL: ATIVA
        </span>
      </div>
    </div>
  );
}

// --- 2. TERMINAL INTELIGENTE ---
function LivingTerminal() {
  const [lines, setLines] = useState<string[]>([
    '> SYSTEM_INIT: CrashBot Core v3.2',
  ]);

  useEffect(() => {
    const sequence = [
      { text: '> CONNECT: Optical Engine (OCR)... OK', delay: 500 },
      { text: '> SCANNING: Analisando últimos 50 candles...', delay: 1500 },
      {
        text: '> PATTERN: Tendência de Recuperação (94%)',
        delay: 2500,
        color: 'text-blue-300',
      },
      {
        text: '> WAITING: Aguardando ponto de entrada...',
        delay: 3500,
        color: 'text-yellow-400 animate-pulse',
      },
      {
        text: '>> EXECUTION: ENTRADA EM 2.00x',
        delay: 4500,
        color: 'text-green-400 font-bold bg-green-900/20 px-1',
      },
      { text: '> SUCCESS: Target Atingido. R$ +150,00', delay: 6000 },
      {
        text: '> SYSTEM: Protegendo lucro...',
        delay: 7000,
        color: 'text-slate-500',
      },
    ];
    const timeouts: NodeJS.Timeout[] = [];
    sequence.forEach(({ text, delay, color }) => {
      timeouts.push(
        setTimeout(() => {
          setLines((p) => {
            const newLines = [
              ...p,
              color ? `<span class="${color}">${text}</span>` : text,
            ];
            return newLines.slice(-8);
          });
        }, delay)
      );
    });
    return () => timeouts.forEach(clearTimeout);
  }, []);

  return (
    <div className="w-full h-full bg-[#09090b] font-mono text-xs text-slate-400 p-4 relative overflow-hidden flex flex-col">
      <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-green-500/50 to-transparent opacity-50"></div>
      <div className="space-y-2 relative z-10">
        {lines.map((l, i) => (
          <div
            key={i}
            dangerouslySetInnerHTML={{ __html: l }}
            className="animate-in fade-in slide-in-from-left-2 duration-300"
          />
        ))}
        <span className="w-2 h-4 bg-green-500 animate-pulse inline-block align-middle ml-1"></span>
      </div>
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-green-500/5 to-transparent h-[10px] w-full animate-scan pointer-events-none"></div>
    </div>
  );
}

// --- 3. GALERIA DE VÍDEO ---
// --- CONFIGURAÇÃO DA LIVE (KICK) ---
const LIVE_CONFIG = {
  status: 'ONLINE',
  kickChannel: 'CrashBot_tucunare', // Seu usuário exato
  titulo: '🔴 AO VIVO: Operação TucunaréBot Sem Cortes',
};

// --- CONFIGURAÇÃO DOS TUTORIAIS (ARQUIVOS LOCAIS) ---
const TUTORIAL_VIDEOS = [
  {
    path: '/videos/tuto_01.mp4', // Caminho do arquivo na pasta public
    titulo: '1. Instalação e Login',
    desc: 'Passo a passo para baixar, instalar e ativar sua licença no Windows.',
  },
  {
    path: '/videos/tuto_02.mp4',
    titulo: '2. Configuração Estratégica',
    desc: 'Como ajustar o MartinGale, Stop Loss e Metas diárias.',
  },
  {
    path: '/videos/tuto_03.mp4',
    titulo: '3. Funcionalidades Avançadas',
    desc: 'Domine a leitura de sinais, análise de gráficos e recursos extras.',
  },
];

function VideoShowcase() {
  return (
    <div className="mt-12 max-w-5xl mx-auto">
      <Card className="bg-slate-900 border-slate-800 overflow-hidden relative shadow-2xl">
        {/* HEADER DO MONITOR */}
        <div className="bg-[#0f172a] px-4 py-3 flex items-center justify-between border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-slate-600"></div>
              <div className="w-3 h-3 rounded-full bg-slate-600"></div>
            </div>
            <span className="text-xs font-mono text-slate-400 font-bold uppercase tracking-widest">
              TRANSMISSÃO CRIPTOGRAFADA // CANAL 01
            </span>
          </div>
          <Badge className="bg-red-600 text-white border-0 animate-pulse flex gap-2">
            <div className="w-2 h-2 bg-white rounded-full"></div> AO VIVO
          </Badge>
        </div>

        {/* ÁREA DO PLAYER KICK (SEM CÓDIGO ANTIGO) */}
        <div className="aspect-video bg-black relative flex items-center justify-center overflow-hidden">
          <iframe
            src={`https://player.kick.com/${LIVE_CONFIG.kickChannel}?autoplay=true&muted=true`}
            height="100%"
            width="100%"
            frameBorder="0"
            scrolling="no"
            allowFullScreen={true}
            className="relative z-10 w-full h-full"
          />
          <div className="absolute top-4 left-4 z-20 flex items-center gap-2">
            <span className="bg-black/80 text-[#53FC18] text-xs font-bold px-2 py-1 rounded border border-[#53FC18]/30">
              SINAL KICK 🟢
            </span>
          </div>
        </div>

        {/* RODAPÉ SIMPLES */}
        <div className="bg-[#0b1121] p-4 border-t border-slate-800 text-xs font-mono text-center text-slate-500">
          BOT VERSION v8.3 STABLE // {LIVE_CONFIG.titulo}
        </div>
      </Card>
    </div>
  );
}

// --- 4. GALERIA DE TUTORIAIS (PLAYER NATIVO) ---
function TutorialGallery() {
  return (
    <div className="mt-20 max-w-6xl mx-auto">
      <div className="text-center mb-10">
        <Badge className="bg-blue-500/20 text-blue-300 border-blue-500/30 px-3 py-1 mb-4">
          ACADEMIA CRASHBOT
        </Badge>
        <h3 className="text-2xl md:text-3xl font-bold text-white">
          Domine a Ferramenta
        </h3>
        <p className="text-slate-400 mt-2">
          Tutoriais rápidos para você começar a operar em menos de 10 minutos.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {TUTORIAL_VIDEOS.map((video, index) => (
          <Card
            key={index}
            className="bg-slate-900/50 border-slate-800 overflow-hidden hover:border-purple-500/50 transition-all group flex flex-col"
          >
            {/* Player de Vídeo Nativo */}
            <div className="aspect-video bg-black relative">
              <video
                controls
                preload="metadata"
                className="w-full h-full object-cover"
                poster="/logo.png" // Opcional: mostra seu logo antes do play
              >
                <source src={video.path} type="video/mp4" />
                Seu navegador não suporta a tag de vídeo.
              </video>
            </div>

            {/* Conteúdo do Card */}
            <CardContent className="p-5 flex-1">
              <h4 className="text-lg font-bold text-white mb-2 group-hover:text-purple-400 transition-colors">
                {video.titulo}
              </h4>
              <p className="text-sm text-slate-400 leading-relaxed">
                {video.desc}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <>
      <style jsx global>
        {customStyles}
      </style>

      <div className="min-h-screen bg-[#020617] text-white overflow-x-hidden font-sans selection:bg-purple-500/30">
        {/* BACKGROUND AURORA */}
        <div className="fixed inset-0 z-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-2000"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-blob animation-delay-4000"></div>
          <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
        </div>

        <div className="relative z-10">
          <MarketTicker />

          {/* HEADER */}
          <header className="container mx-auto px-6 h-20 flex items-center justify-between border-b border-white/5 backdrop-blur-md sticky top-0 z-40 bg-[#020617]/80">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-indigo-600 rounded flex items-center justify-center shadow-lg shadow-purple-500/30">
                <Terminal className="w-4 h-4 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight">
                CrashBot<span className="text-purple-400">.AI</span>
              </span>
            </div>

            <nav className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
              <Link
                href="#demonstracao"
                className="hover:text-white transition-colors"
              >
                Demonstração
              </Link>
              <Link
                href="#plataforma"
                className="hover:text-white transition-colors"
              >
                Plataforma
              </Link>
              <Link
                href="#planos"
                className="hover:text-white transition-colors"
              >
                Licenciamento
              </Link>
              <Link
                href="/agendar"
                className="hover:text-white transition-colors flex items-center gap-1"
              >
                <CalendarDays className="w-4 h-4" />
                Agendar Treinamento
              </Link>
            </nav>

            <div className="flex gap-3">
              <Link href="/login">
                <Button
                  variant="ghost"
                  className="text-slate-300 hover:text-white hover:bg-white/5"
                >
                  Login
                </Button>
              </Link>
              <Link href="#planos">
                <Button className="bg-white text-slate-900 font-bold hover:bg-slate-200 transition-all shadow-[0_0_20px_-5px_rgba(255,255,255,0.4)]">
                  Começar Agora
                </Button>
              </Link>
            </div>
          </header>

          {/* HERO SECTION */}
          <section className="pt-20 pb-20 container mx-auto px-6">
            <div className="grid lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-8 relative">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-purple-500/30 bg-purple-500/10 text-purple-300 text-[10px] font-bold uppercase tracking-widest">
                  <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse"></span>
                  Nova Versão v8.3 Disponível
                </div>
                <h1 className="text-5xl md:text-7xl font-bold leading-tight tracking-tight">
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-pink-400 to-blue-400 animate-gradient-x">
                    Crash Bot
                  </span>
                  <br />
                  Automatize suas apostas com Inteligência.
                </h1>
                <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
                  Este sistema utiliza <strong>Visão Computacional</strong> para
                  ler os multiplicadores externamente, permitindo encontrar
                  padrões Lucrativos.
                </p>
                <div className="flex flex-col sm:flex-row gap-4">
                  <Link href="/checkout/trial" className="w-full sm:w-auto">
                    <Button
                      size="lg"
                      className="w-full h-14 bg-purple-600 hover:bg-purple-700 text-white font-bold text-lg shadow-[0_0_40px_-10px_rgba(147,51,234,0.5)] animate-pulse hover:animate-none"
                    >
                      ⚡ Baixar Trial (7 Dias)
                    </Button>
                  </Link>
                  <Link href="#planos" className="w-full sm:w-auto">
                    <Button
                      size="lg"
                      variant="outline"
                      className="w-full h-14 border-slate-700 hover:bg-slate-800 text-slate-300 font-medium"
                    >
                      Saiba Mais
                    </Button>
                  </Link>
                </div>
              </div>
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-purple-600 to-blue-600 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-1000"></div>
                <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-[#09090b] shadow-2xl h-80">
                  <div className="bg-[#1e293b] px-4 py-2 flex items-center gap-2 border-b border-slate-700">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-500/50"></div>
                      <div className="w-3 h-3 rounded-full bg-yellow-500/50"></div>
                      <div className="w-3 h-3 rounded-full bg-green-500/50"></div>
                    </div>
                    <div className="ml-auto text-[10px] text-slate-500 font-mono">
                      crashbot_engine.exe — running
                    </div>
                  </div>
                  <LivingTerminal />
                </div>
              </div>
            </div>

            {/* VÍDEOS */}
            <div
              id="demonstracao"
              className="mt-24 pt-12 border-t border-white/5"
            >
              <div className="text-center mb-8">
                <h2 className="text-3xl font-bold">Sala de Controle</h2>
                <p className="text-slate-400">
                  Veja a tecnologia operando em tempo real.
                </p>
              </div>
              <VideoShowcase />
              <TutorialGallery />
            </div>
          </section>

          {/* --- NOVA SEÇÃO DESTAQUE: PLATAFORMA BRABET --- */}
          <section
            id="plataforma"
            className="py-24 bg-gradient-to-r from-[#0B0F19] via-[#101624] to-[#0B0F19] border-y border-white/5 relative overflow-hidden"
          >
            {/* Efeitos de Fundo */}
            <div className="absolute top-0 right-0 p-64 bg-purple-500/5 blur-[100px] rounded-full pointer-events-none"></div>

            <div className="container mx-auto px-6 relative z-10">
              <div className="grid lg:grid-cols-2 gap-16 items-center">
                {/* Texto e Botão */}
                <div className="space-y-8">
                  <Badge className="bg-purple-500/20 text-purple-300 border-purple-500/30 px-3 py-1">
                    PARCERIA OFICIAL
                  </Badge>
                  <h2 className="text-4xl md:text-5xl font-bold text-white leading-tight">
                    Otimizado para <br />
                    <span className="text-purple-400">BRABET</span>
                  </h2>
                  <p className="text-lg text-slate-300 leading-relaxed">
                    Atualmente, nosso sistema disponibilizado opera
                    exclusivamente para a interface do site de apostas da
                    Brabet.
                  </p>

                  <div className="bg-yellow-500/10 border border-yellow-500/20 p-4 rounded-lg flex gap-4 items-start">
                    <AlertTriangle className="w-6 h-6 text-yellow-500 shrink-0 mt-1" />
                    <div className="text-sm text-yellow-200">
                      <strong>Atenção:</strong> Acesse com um clique na caixa
                      verde abaixo ou aponte sua câmera para o QR Code ao lado!!
                    </div>
                  </div>

                  <a
                    href="https://www.brabet.com/?agentid=135486005"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Button
                      size="lg"
                      className="w-full sm:w-auto h-16 px-8 bg-green-600 hover:bg-green-700 text-white font-bold text-lg shadow-[0_0_30px_-5px_rgba(34,197,94,0.4)]"
                    >
                      CRIAR CONTA NA BRABET
                    </Button>
                  </a>
                </div>

                {/* QR Code Gigante em Destaque */}
                <div className="flex justify-center lg:justify-end">
                  <div className="bg-white p-6 rounded-3xl shadow-2xl rotate-2 hover:rotate-0 transition-transform duration-500 relative group max-w-sm">
                    <div className="absolute -inset-4 bg-gradient-to-br from-purple-500 to-blue-500 rounded-[2rem] blur opacity-30 group-hover:opacity-50 transition duration-500 -z-10"></div>

                    <div className="text-center mb-4">
                      <p className="text-slate-900 font-bold text-xl mb-1">
                        Escaneie para Jogar
                      </p>
                      <p className="text-slate-500 text-sm">
                        Acesso direto ao Cadastro
                      </p>
                    </div>

                    <Image
                      src="/qrcode-brabet.png"
                      alt="QR Code Brabet"
                      width={250}
                      height={250}
                      className="object-contain mx-auto"
                    />

                    <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-center gap-2 text-slate-400 text-sm">
                      <Lock className="w-4 h-4" /> Link Seguro SSL
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* PLANOS */}
          <section id="planos" className="py-24 relative">
            <div className="container mx-auto px-6">
              <div className="text-center mb-16">
                <h2 className="text-4xl font-bold text-white mb-4">
                  Licenciamento de Software
                </h2>
                <p className="text-slate-400">
                  Escolha o nível de acesso adequado à sua banca.
                </p>
              </div>

              <div className="grid lg:grid-cols-3 gap-6 max-w-6xl mx-auto items-end">
                {/* TRIAL */}
                <Card className="bg-slate-900/40 border-slate-800 h-[420px] flex flex-col hover:border-slate-600 transition-all">
                  <CardHeader>
                    <CardTitle className="text-white">Trial Gratuito</CardTitle>
                    <p className="text-sm text-slate-400">Para testar</p>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <div className="text-3xl font-bold text-white mb-6">
                      R$ 0,00
                    </div>
                    <ul className="space-y-4 text-sm text-slate-300 flex-1">
                      <li className="flex gap-2">
                        <Check className="w-4 h-4 text-slate-500" /> 7 Dias de
                        Acesso
                      </li>
                      <li className="flex gap-2">
                        <Check className="w-4 h-4 text-slate-500" /> 100%
                        Funcional
                      </li>
                    </ul>
                    <Link href="/checkout/trial" className="mt-auto">
                      <Button
                        variant="outline"
                        className="w-full border-slate-700 text-slate-300 hover:bg-slate-800"
                      >
                        Baixar Trial
                      </Button>
                    </Link>
                  </CardContent>
                </Card>

                {/* MENSAL PRO */}
                <div className="relative transform lg:-translate-y-4 z-10">
                  <div className="absolute -inset-[2px] bg-gradient-to-b from-purple-500 to-pink-500 rounded-xl blur-sm opacity-50"></div>
                  <Card className="bg-[#0f172a] border-0 h-[500px] flex flex-col relative">
                    <div className="absolute top-0 right-4 top-4">
                      <Badge className="bg-purple-600">POPULAR</Badge>
                    </div>
                    <CardHeader>
                      <CardTitle className="text-white text-2xl">
                        Mensal <span className="text-purple-400">PRO</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="flex-1 flex flex-col">
                      <div className="mb-2">
                        <span className="text-5xl font-bold text-white">
                          R$ 497
                        </span>
                        <span className="text-slate-500">/mês</span>
                      </div>
                      <ul className="space-y-4 text-sm text-white flex-1 mt-8">
                        <li className="flex gap-3">
                          <Check className="text-green-400" />{' '}
                          <strong>
                            Setup Flexível estruturado em longo prazo
                          </strong>
                        </li>
                        <li className="flex gap-3">
                          <Check className="text-green-400" />{' '}
                          <strong>Melhor diluição de risco</strong>
                        </li>
                        <li className="flex gap-3">
                          <Check className="text-green-400" /> Suporte de
                          instalação via WhatsApp/Telegram
                        </li>
                        <li className="flex gap-3">
                          <Check className="text-green-400" /> Receba telemetria
                          pelo Telegram
                        </li>
                        <li className="flex gap-3">
                          <Check className="text-green-400" /> Acesso a análises
                          estratégicas semanais
                        </li>
                      </ul>
                      <Link href="/checkout/mensal" className="mt-8">
                        <Button
                          size="lg"
                          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 font-bold h-14 shadow-lg hover:scale-[1.02] transition-transform"
                        >
                          GARANTIR ACESSO VIP
                        </Button>
                      </Link>
                    </CardContent>
                  </Card>
                </div>

                {/* SEMANAL */}
                <Card className="bg-slate-900/40 border-slate-800 h-[420px] flex flex-col hover:border-slate-600 transition-all">
                  <CardHeader>
                    <CardTitle className="text-white">Semanal</CardTitle>
                    <p className="text-sm text-slate-400">Curto Prazo</p>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <div className="text-3xl font-bold text-white mb-6">
                      R$ 147{' '}
                      <span className="text-sm text-slate-500">/sem</span>
                    </div>
                    <ul className="space-y-4 text-sm text-slate-300 flex-1">
                      <li className="flex gap-2">
                        <Check className="w-4 h-4 text-purple-400" /> Setup
                        Flexível estruturado em curto prazo
                      </li>
                      <li className="flex gap-2">
                        <Check className="w-4 h-4 text-purple-400" /> Controle
                        risco/retorno
                      </li>
                      <li className="flex gap-2">
                        <Check className="w-4 h-4 text-purple-400" /> Suporte de
                        instalação via WhatsApp/Telegram
                      </li>
                    </ul>
                    <Link href="/checkout/semanal" className="mt-auto">
                      <Button
                        variant="secondary"
                        className="w-full bg-slate-800 text-white border border-slate-700"
                      >
                        Comprar Semanal
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              </div>
            </div>
          </section>

          {/* --- NOVA SEÇÃO: AGENDAR TREINAMENTO --- */}
          <section className="py-20 bg-gradient-to-r from-purple-900/20 via-[#0B0F19] to-purple-900/20 border-y border-purple-500/10">
            <div className="container mx-auto px-6">
              <div className="max-w-4xl mx-auto">
                <Card className="bg-gradient-to-br from-purple-900/40 to-slate-900/60 border-purple-500/30 overflow-hidden relative">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-purple-500/10 blur-[80px] rounded-full pointer-events-none"></div>

                  <CardContent className="p-8 md:p-12">
                    <div className="grid md:grid-cols-2 gap-8 items-center">
                      {/* Texto */}
                      <div className="space-y-6">
                        <Badge className="bg-green-500/20 text-green-300 border-green-500/30 px-3 py-1">
                          GRATUITO
                        </Badge>
                        <h2 className="text-3xl md:text-4xl font-bold text-white leading-tight">
                          Agende seu{' '}
                          <span className="text-purple-400">Treinamento</span>
                        </h2>
                        <p className="text-slate-300 leading-relaxed">
                          Marque uma sessão de <strong>30 minutos</strong> com
                          nossa equipe para aprender a configurar e operar o
                          CrashBot da melhor forma.
                        </p>
                        <ul className="space-y-3 text-sm text-slate-300">
                          <li className="flex items-center gap-3">
                            <Video className="w-5 h-5 text-purple-400" />
                            Reunião via Google Meet
                          </li>
                          <li className="flex items-center gap-3">
                            <CalendarDays className="w-5 h-5 text-purple-400" />
                            Seg a Sex, 10h às 18h
                          </li>
                          <li className="flex items-center gap-3">
                            <Check className="w-5 h-5 text-green-400" />
                            Configuração inicial incluída
                          </li>
                        </ul>
                      </div>

                      {/* Botão */}
                      <div className="flex flex-col items-center justify-center space-y-4">
                        <div className="w-24 h-24 bg-purple-500/20 rounded-full flex items-center justify-center border border-purple-500/30">
                          <CalendarDays className="w-12 h-12 text-purple-400" />
                        </div>
                        <Link href="/agendar" className="w-full">
                          <Button
                            size="lg"
                            className="w-full h-14 bg-gradient-to-r from-purple-600 to-pink-600 font-bold text-lg shadow-[0_0_30px_-5px_rgba(147,51,234,0.5)] hover:scale-[1.02] transition-transform"
                          >
                            <CalendarDays className="w-5 h-5 mr-2" />
                            Agendar Agora
                          </Button>
                        </Link>
                        <p className="text-xs text-slate-500 text-center">
                          Escolha o melhor horário para você
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </section>

          {/* --- NOVA SEÇÃO: REQUISITOS TÉCNICOS (RODAPÉ) --- */}
          <section className="py-16 border-t border-white/5 bg-[#05080f]">
            <div className="container mx-auto px-6">
              <div className="flex flex-col md:flex-row items-center justify-between gap-8 mb-8">
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                  <Terminal className="text-slate-500" /> Requisitos de
                  Instalação
                </h3>
                <p className="text-sm text-slate-500">
                  Verifique se seu equipamento é compatível antes de adquirir.
                </p>
              </div>

              <div className="grid md:grid-cols-4 gap-6">
                <Card className="bg-slate-900/30 border-slate-800 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Monitor className="text-blue-400 w-5 h-5" />
                    <span className="font-bold text-white text-sm">
                      Sistema
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Windows 10 ou 11 (64 bits)
                  </p>
                </Card>

                <Card className="bg-slate-900/30 border-slate-800 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Cpu className="text-purple-400 w-5 h-5" />
                    <span className="font-bold text-white text-sm">
                      Processador
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Intel i3 ou superior (min 2.0Ghz)
                  </p>
                </Card>

                <Card className="bg-slate-900/30 border-slate-800 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Activity className="text-green-400 w-5 h-5" />
                    <span className="font-bold text-white text-sm">
                      Resolução
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    1366x768 ou superior (Recomendado Full HD)
                  </p>
                </Card>

                <Card className="bg-slate-900/30 border-slate-800 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Activity className="text-green-400 w-5 h-5" />
                    <span className="font-bold text-white text-sm">
                      Devolução do Investimento
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Devolvemos seu investimento em até 7 dias, caso se arrependa
                    ou na hipótese de incompatibilidade do software com a sua
                    máquina.
                  </p>
                </Card>

                <Card className="bg-red-900/10 border-red-900/30 p-4">
                  <div className="flex items-center gap-3 mb-2">
                    <Smartphone className="text-red-400 w-5 h-5" />
                    <span className="font-bold text-red-200 text-sm">
                      Incompatível
                    </span>
                  </div>
                  <p className="text-xs text-red-300">
                    Não funciona em Celular, Tablet, Mac ou Linux.
                  </p>
                </Card>
              </div>
            </div>
          </section>

          {/* FOOTER */}
          <footer className="py-12 text-center text-slate-600 text-sm bg-[#010409]">
            <div className="mb-4 text-2xl">🤖</div>
            <p className="mb-4">
              © 2025 CrashBot AI. Todos os direitos reservados.
            </p>
            <div className="flex justify-center gap-6 text-xs">
              <Link href="/manual" className="hover:text-purple-400">
                Manual
              </Link>
              <Link href="/termos" className="hover:text-purple-400">
                Termos
              </Link>
              <Link href="/privacidade" className="hover:text-purple-400">
                Privacidade
              </Link>
              <Link href="/agendar" className="hover:text-purple-400">
                Agendar Treinamento
              </Link>
            </div>
          </footer>
        </div>
      </div>
    </>
  );
}
