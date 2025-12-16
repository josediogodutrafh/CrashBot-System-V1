"use client";

import { useState, useEffect } from "react";
import { Calendar, Clock, User, Mail, Phone, MessageSquare, Video, CheckCircle, ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";

interface Slot {
  inicio: string;
  fim: string;
  disponivel: boolean;
}

interface AgendamentoResponse {
  success: boolean;
  mensagem: string;
  evento_id?: string;
  meet_link?: string;
  data_hora?: string;
}

export default function AgendarPage() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);
  const [agendamento, setAgendamento] = useState<AgendamentoResponse | null>(null);
  const [error, setError] = useState("");
  
  const [formData, setFormData] = useState({
    nome: "",
    email: "",
    whatsapp: "",
    observacoes: "",
  });

  // Gerar próximos 14 dias úteis
  const getProximosDias = () => {
    const dias = [];
    const hoje = new Date();
    let count = 0;
    
    while (dias.length < 14) {
      const data = new Date(hoje);
      data.setDate(hoje.getDate() + count);
      
      // Pular fins de semana
      if (data.getDay() !== 0 && data.getDay() !== 6) {
        dias.push({
          date: data.toISOString().split("T")[0],
          label: data.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" }),
          weekday: data.toLocaleDateString("pt-BR", { weekday: "long" }),
        });
      }
      count++;
    }
    
    return dias;
  };

  const dias = getProximosDias();

  // Buscar horários disponíveis quando selecionar data
  useEffect(() => {
    if (selectedDate) {
      fetchSlots(selectedDate);
    }
  }, [selectedDate]);

  const fetchSlots = async (date: string) => {
    setLoadingSlots(true);
    setError("");
    
    try {
      const response = await fetch(
        \https://crash-api-jose.onrender.com/api/v1/calendar/horarios-disponiveis?data=\\
      );
      
      if (!response.ok) {
        throw new Error("Erro ao buscar horários");
      }
      
      const data = await response.json();
      setSlots(data.slots || []);
    } catch (err) {
      setError("Não foi possível carregar os horários. Tente novamente.");
      setSlots([]);
    } finally {
      setLoadingSlots(false);
    }
  };

  const handleSubmit = async () => {
    if (!selectedSlot || !formData.nome || !formData.email || !formData.whatsapp) {
      setError("Preencha todos os campos obrigatórios");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(
        "https://crash-api-jose.onrender.com/api/v1/calendar/agendar",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            nome: formData.nome,
            email: formData.email,
            whatsapp: formData.whatsapp,
            data_hora: selectedSlot.inicio,
            observacoes: formData.observacoes,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Erro ao agendar");
      }

      setAgendamento(data);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Erro ao agendar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  };

  const formatDateTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleDateString("pt-BR", {
      weekday: "long",
      day: "2-digit",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-white hover:text-purple-400 transition">
            <ArrowLeft size={20} />
            <span>Voltar</span>
          </Link>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center">
              <span className="text-white font-bold text-sm">C</span>
            </div>
            <span className="text-white font-semibold">CrashBot</span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Título */}
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">
            Agende seu Treinamento
          </h1>
          <p className="text-gray-400">
            Escolha o melhor horário para sua sessão de integração com o CrashBot
          </p>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-8">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className={\w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all \\}
              >
                {step > s ? <CheckCircle size={20} /> : s}
              </div>
              {s < 3 && (
                <div
                  className={\w-12 h-1 rounded \\}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Labels */}
        <div className="flex justify-center gap-8 mb-8 text-sm">
          <span className={step >= 1 ? "text-purple-400" : "text-gray-500"}>Data e Hora</span>
          <span className={step >= 2 ? "text-purple-400" : "text-gray-500"}>Seus Dados</span>
          <span className={step >= 3 ? "text-purple-400" : "text-gray-500"}>Confirmação</span>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-300 px-4 py-3 rounded-lg mb-6 text-center">
            {error}
          </div>
        )}

        {/* Step 1: Escolher Data e Hora */}
        {step === 1 && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
              <Calendar className="text-purple-400" />
              Escolha a Data
            </h2>

            {/* Seletor de Data */}
            <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2 mb-6">
              {dias.map((dia) => (
                <button
                  key={dia.date}
                  onClick={() => {
                    setSelectedDate(dia.date);
                    setSelectedSlot(null);
                  }}
                  className={\p-3 rounded-lg text-center transition-all \\}
                >
                  <div className="text-xs opacity-70">{dia.label.split(",")[0]}</div>
                  <div className="font-semibold">{dia.label.split(",")[1] || dia.label.split(" ")[1]}</div>
                </button>
              ))}
            </div>

            {/* Horários */}
            {selectedDate && (
              <>
                <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                  <Clock className="text-purple-400" />
                  Escolha o Horário
                </h2>

                {loadingSlots ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="animate-spin text-purple-400" size={32} />
                  </div>
                ) : slots.length === 0 ? (
                  <p className="text-gray-400 text-center py-8">
                    Nenhum horário disponível nesta data. Escolha outra data.
                  </p>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                    {slots.map((slot) => (
                      <button
                        key={slot.inicio}
                        onClick={() => setSelectedSlot(slot)}
                        className={\p-3 rounded-lg text-center transition-all \\}
                      >
                        {formatTime(slot.inicio)}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Botão Próximo */}
            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setStep(2)}
                disabled={!selectedSlot}
                className={\lex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all \\}
              >
                Próximo
                <ArrowRight size={20} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Dados do Cliente */}
        {step === 2 && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-white/10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <User className="text-purple-400" />
              Seus Dados
            </h2>

            {/* Resumo da seleção */}
            <div className="bg-purple-500/20 border border-purple-500/30 rounded-lg p-4 mb-6">
              <p className="text-purple-300 text-sm">Horário selecionado:</p>
              <p className="text-white font-semibold">
                {selectedSlot && formatDateTime(selectedSlot.inicio)}
              </p>
            </div>

            <div className="space-y-4">
              {/* Nome */}
              <div>
                <label className="block text-gray-300 mb-2 flex items-center gap-2">
                  <User size={16} />
                  Nome completo *
                </label>
                <input
                  type="text"
                  value={formData.nome}
                  onChange={(e) => setFormData({ ...formData, nome: e.target.value })}
                  className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                  placeholder="Seu nome"
                />
              </div>

              {/* Email */}
              <div>
                <label className="block text-gray-300 mb-2 flex items-center gap-2">
                  <Mail size={16} />
                  E-mail *
                </label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                  placeholder="seu@email.com"
                />
              </div>

              {/* WhatsApp */}
              <div>
                <label className="block text-gray-300 mb-2 flex items-center gap-2">
                  <Phone size={16} />
                  WhatsApp *
                </label>
                <input
                  type="tel"
                  value={formData.whatsapp}
                  onChange={(e) => setFormData({ ...formData, whatsapp: e.target.value })}
                  className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                  placeholder="(00) 00000-0000"
                />
              </div>

              {/* Observações */}
              <div>
                <label className="block text-gray-300 mb-2 flex items-center gap-2">
                  <MessageSquare size={16} />
                  Observações (opcional)
                </label>
                <textarea
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  className="w-full bg-gray-700/50 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 h-24 resize-none"
                  placeholder="Alguma dúvida específica ou observação..."
                />
              </div>
            </div>

            {/* Botões */}
            <div className="mt-6 flex justify-between">
              <button
                onClick={() => setStep(1)}
                className="flex items-center gap-2 px-6 py-3 rounded-lg font-semibold bg-gray-700 text-white hover:bg-gray-600 transition-all"
              >
                <ArrowLeft size={20} />
                Voltar
              </button>
              <button
                onClick={handleSubmit}
                disabled={loading || !formData.nome || !formData.email || !formData.whatsapp}
                className={\lex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition-all \\}
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    Agendando...
                  </>
                ) : (
                  <>
                    <CheckCircle size={20} />
                    Confirmar Agendamento
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Confirmação */}
        {step === 3 && agendamento && (
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-8 border border-white/10 text-center">
            <div className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="text-white" size={40} />
            </div>

            <h2 className="text-2xl font-bold text-white mb-2">
              Agendamento Confirmado!
            </h2>
            <p className="text-gray-400 mb-6">
              Você receberá um e-mail de confirmação com os detalhes.
            </p>

            <div className="bg-gray-700/50 rounded-lg p-6 mb-6 text-left max-w-md mx-auto">
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Calendar className="text-purple-400" size={20} />
                  <span className="text-white">
                    {agendamento.data_hora && formatDateTime(agendamento.data_hora)}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <Clock className="text-purple-400" size={20} />
                  <span className="text-white">Duração: 30 minutos</span>
                </div>
                {agendamento.meet_link && (
                  <div className="flex items-center gap-3">
                    <Video className="text-purple-400" size={20} />
                    
                      href={agendamento.meet_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-purple-400 hover:text-purple-300 underline"
                    >
                      Acessar Google Meet
                    </a>
                  </div>
                )}
              </div>
            </div>

            <div className="space-y-3">
              {agendamento.meet_link && (
                
                  href={agendamento.meet_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold bg-gradient-to-r from-purple-500 to-pink-500 text-white hover:opacity-90 transition-all"
                >
                  <Video size={20} />
                  Acessar Reunião
                </a>
              )}
              <div>
                <Link
                  href="/"
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-semibold bg-gray-700 text-white hover:bg-gray-600 transition-all"
                >
                  Voltar ao Início
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Info Box */}
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <h3 className="text-blue-400 font-semibold mb-2">ℹ Sobre o Treinamento</h3>
          <ul className="text-gray-300 text-sm space-y-1">
            <li> Duração de 30 minutos via Google Meet</li>
            <li> Apresentação completa do CrashBot</li>
            <li> Configuração inicial e dúvidas</li>
            <li> Horário de Brasília (UTC-3)</li>
          </ul>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-12 py-6 text-center text-gray-500 text-sm">
        <p>© 2025 CrashBot - Todos os direitos reservados</p>
      </footer>
    </div>
  );
}
