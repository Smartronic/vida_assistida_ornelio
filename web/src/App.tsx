import { useState, useEffect, useRef } from "react";
import "./App.css";
import { ConfirmDialog } from "./components/ConfirmDialog";

// ATENÇÃO DE SEGURANÇA: Esta senha é compilada no client-side para o build do React/Vite.
// Ela funciona apenas como uma barreira simples para a demonstração local via ngrok.
// Não deve ser utilizada para autenticação segura em ambiente de produção definitiva.
const DEMO_PASSWORD = import.meta.env.VITE_DEMO_ACCESS_PASSWORD;

const API_URL = import.meta.env.VITE_API_URL ?? "";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

const SUGGESTED_QUESTIONS = [
  "Qual é a proposta geral do livro Vida Assistida?",
  "Como lidar com a culpa ao levar um familiar idoso para uma ILPI?",
  "O que observar de importante ao escolher uma ILPI?",
  "Como conversar com o idoso sobre a possibilidade de vida assistida?",
];

function resetViewportScroll() {
  const reset = () => {
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;

    const messagesArea = document.querySelector(".messages-area");
    if (messagesArea) {
      messagesArea.scrollTop = 0;
    }
  };

  requestAnimationFrame(reset);
  setTimeout(reset, 50);
  setTimeout(reset, 250);
}

function App() {
  const [demoUnlocked, setDemoUnlocked] = useState<boolean>(() => {
    // Se a senha de demonstração não estiver configurada, mantemos o acesso bloqueado
    const configuredPassword = String(DEMO_PASSWORD || "").trim();
    if (!configuredPassword) return false;
    return localStorage.getItem("vida_assistida_demo_access") === "granted";
  });

  const [passwordInput, setPasswordInput] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const [sessionId, setSessionId] = useState<string>(() => {
    const saved = localStorage.getItem("vida_assistida_session_id");
    if (saved) return saved;
    const newId = crypto.randomUUID();
    localStorage.setItem("vida_assistida_session_id", newId);
    return newId;
  });

  const [messages, setMessages] = useState<Message[]>(() => {
    const saved = localStorage.getItem("vida_assistida_chat_history");
    return saved ? JSON.parse(saved) : [];
  });

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Ao liberar acesso, força o topo correto no iPhone/Safari/WhatsApp WebView.
  useEffect(() => {
    if (demoUnlocked) {
      resetViewportScroll();
    }
  }, [demoUnlocked]);

  // Persiste o histórico a cada alteração
  useEffect(() => {
    localStorage.setItem("vida_assistida_chat_history", JSON.stringify(messages));
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      const messagesArea = document.querySelector(".messages-area");
      if (messagesArea) {
        messagesArea.scrollTo({
          top: messagesArea.scrollHeight,
          behavior: "smooth",
        });
        return;
      }

      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    });
  };

  // Ajusta altura do textarea dinamicamente
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      const newHeight = textarea.scrollHeight;
      textarea.style.height = `${newHeight}px`;

      // Se a altura real calculada ultrapassar a altura máxima da caixa (160px),
      // ativa o scroll vertical, caso contrário mantém oculto.
      if (newHeight > 160) {
        textarea.style.overflowY = "auto";
      } else {
        textarea.style.overflowY = "hidden";
      }
    }
  }, [input]);

  function startNewConversation() {
    setConfirmOpen(true);
  }

  function handleConfirmNewConversation() {
    setConfirmOpen(false);
    const newId = crypto.randomUUID();
    localStorage.setItem("vida_assistida_session_id", newId);
    localStorage.removeItem("vida_assistida_chat_history");
    setSessionId(newId);
    setMessages([]);
    setInput("");

    resetViewportScroll();

    setTimeout(() => textareaRef.current?.focus(), 80);
  }

  function handleCancelNewConversation() {
    setConfirmOpen(false);
    setTimeout(() => textareaRef.current?.focus(), 50);
  }

  function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();

    const configuredPassword = String(DEMO_PASSWORD || "").trim();
    const typedPassword = passwordInput.trim();

    console.debug("[DemoAccessGate] senha configurada?", Boolean(configuredPassword));

    if (!configuredPassword) {
      setErrorMsg("Senha de demonstração não configurada.");
      return;
    }

    if (typedPassword === configuredPassword) {
      const activeElement = document.activeElement as HTMLElement | null;
      activeElement?.blur();

      localStorage.setItem("vida_assistida_demo_access", "granted");
      setPasswordInput("");
      setErrorMsg("");
      setDemoUnlocked(true);

      resetViewportScroll();
    } else {
      setErrorMsg("Senha incorreta. Tente novamente.");
      setPasswordInput("");
    }
  }

  function handleLockDemo() {
    const activeElement = document.activeElement as HTMLElement | null;
    activeElement?.blur();

    localStorage.removeItem("vida_assistida_demo_access");
    setDemoUnlocked(false);
    setPasswordInput("");
    setErrorMsg("");

    resetViewportScroll();
  }

  // Enviar mensagem para a API com suporte a streaming progressivo e cancelamento
  async function handleSend(textToSend = input) {
    const cleanText = textToSend.trim();
    if (!cleanText || loading) return;

    // 1. Adicionar mensagem do usuário
    const userMessage: Message = { role: "user", content: cleanText };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // 2. Adicionar mensagem temporária vazia para o assistente
    const assistantMessage: Message = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMessage]);

    // Criar o AbortController e guardar na Ref
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch(`${API_URL}/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: sessionId,
          message: cleanText,
          debug: false,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error("Erro na requisição da API de streaming.");
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Mantém a linha incompleta no buffer

          for (const line of lines) {
            if (line.trim()) {
              try {
                const data = JSON.parse(line);
                if (data.token) {
                  // Acumula os tokens progressivamente na última mensagem do assistente sem mutação direta
                  setMessages((prev) => {
                    const updated = [...prev];
                    const lastIdx = updated.length - 1;
                    if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
                      updated[lastIdx] = {
                        ...updated[lastIdx],
                        content: updated[lastIdx].content + data.token,
                      };
                    }
                    return updated;
                  });
                }
              } catch (e) {
                console.error("Erro ao fazer parse de linha do stream:", e);
              }
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") {
        // Trata o abort de forma amigável sem apagar nada e adicionando sinalização
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === "assistant") {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: updated[lastIdx].content + "\n\n*(Resposta interrompida)*",
            };
          }
          return updated;
        });
      } else {
        console.error(error);
        // Remove a mensagem vazia e adiciona aviso de erro se falhar
        setMessages((prev) => {
          const updated = prev.slice(0, -1);
          const errorMessage: Message = {
            role: "system",
            content:
              "Desculpe, ocorreu uma instabilidade de conexão com o Vida Assistida. Certifique-se de que o backend esteja ativo e tente novamente.",
          };
          return [...updated, errorMessage];
        });
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }

  function handleSendOrStop() {
    if (loading) {
      abortControllerRef.current?.abort();
    } else {
      handleSend();
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!loading) {
        handleSend();
      }
    }
  }

  function renderContent(text: string) {
    const lines = text.split("\n");
    const rendered: React.ReactNode[] = [];
    let inList = false;
    let listItems: React.ReactNode[] = [];

    const parseBold = (str: string): string => {
      let safeStr = str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
      return safeStr.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    };

    lines.forEach((line, index) => {
      const trimmed = line.trim();
      const isListItem =
        trimmed.startsWith("- ") ||
        trimmed.startsWith("* ") ||
        trimmed.startsWith("### ");

      if (isListItem) {
        if (!inList && listItems.length > 0) {
          rendered.push(<ul key={`list-${index}`}>{listItems}</ul>);
          listItems = [];
        }
        inList = true;
        const cleanItem = trimmed.replace(/^(\-\s*|\*\s*|###\s*)/, "");
        listItems.push(
          <li
            key={`li-${index}`}
            dangerouslySetInnerHTML={{ __html: parseBold(cleanItem) }}
          />
        );
      } else {
        if (inList) {
          rendered.push(<ul key={`list-${index}`}>{listItems}</ul>);
          listItems = [];
          inList = false;
        }
        if (trimmed === "") {
          rendered.push(<div key={`empty-${index}`} style={{ height: "8px" }} />);
        } else {
          rendered.push(
            <p
              key={`p-${index}`}
              dangerouslySetInnerHTML={{ __html: parseBold(line) }}
            />
          );
        }
      }
    });

    if (inList && listItems.length > 0) {
      rendered.push(<ul key={`list-end`}>{listItems}</ul>);
    }

    return rendered;
  }

  if (!demoUnlocked) {
    return (
      <div className="demo-gate-container">
        <div className="demo-gate-card animate-scale-in">
          <div className="demo-gate-logo">
            <svg
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="leaf-icon"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 1.2 4 .8 9.8A7 7 0 0 1 11 20z" />
              <path d="M19 2L11 10" />
            </svg>
          </div>
          <h1 className="demo-gate-title">Vida Assistida</h1>
          <p className="demo-gate-subtitle">Acesso de demonstração</p>
          <p className="demo-gate-description">
            Digite a senha fornecida para acessar o oráculo Vida Assistida.
          </p>

          {!String(DEMO_PASSWORD || "").trim() ? (
            <div className="demo-gate-config-error">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="warning-icon"
              >
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span>Senha de demonstração não configurada.</span>
            </div>
          ) : (
            <form onSubmit={handlePasswordSubmit} className="demo-gate-form">
              <div className="demo-gate-input-wrapper">
                <input
                  type="password"
                  className="demo-gate-input"
                  placeholder="Digite a senha..."
                  value={passwordInput}
                  onChange={(e) => {
                    setPasswordInput(e.target.value);
                    setErrorMsg("");
                  }}
                  autoFocus
                  aria-label="Senha de acesso"
                />
              </div>
              {errorMsg && <p className="demo-gate-error-text">{errorMsg}</p>}
              <button type="submit" className="demo-gate-btn">
                Entrar
              </button>
            </form>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {/* Cabeçalho */}
      <header className="chat-header">
        <div className="brand">
          <div className="brand-logo">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="leaf-icon"
            >
              <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 1.2 4 .8 9.8A7 7 0 0 1 11 20z" />
              <path d="M19 2L11 10" />
            </svg>
          </div>
          <div className="brand-text">
            <h1 className="brand-title">Vida Assistida</h1>
            <p className="brand-subtitle">
              O cuidado do idoso, da família e das ILPIs em uma conversa inteligente.
            </p>
          </div>
        </div>

        <div className="header-actions">
          <button
            id="btn-new-conversation"
            onClick={startNewConversation}
            disabled={loading}
            title="Iniciar nova conversa"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            Nova conversa
          </button>

          <button
            id="btn-lock-demo"
            className="btn-secondary"
            onClick={handleLockDemo}
            title="Bloquear acesso à demonstração"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.0"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <span>Bloquear</span>
          </button>
        </div>
      </header>

      {/* Histórico / Área das Mensagens */}
      <main className="messages-area">
        {messages.length === 0 ? (
          <div className="welcome-screen">
            <div className="welcome-badge">🌿 Espaço de Acolhimento e Cuidado</div>
            <h2 className="welcome-title">Como podemos apoiar você hoje?</h2>
            <p className="subtitle">
              Esta é uma inteligência prática e humanizada projetada para acolher
              familiares, apoiar cuidadores e orientar gestores de ILPIs. Suas dúvidas
              esclarecidas com respeito e dignidade.
            </p>

            <div className="suggestions-section">
              <span className="suggestions-label">Perguntas sugeridas:</span>
              <div className="suggestions-chips">
                {SUGGESTED_QUESTIONS.map((question, idx) => (
                  <button
                    key={idx}
                    id={`btn-suggestion-${idx}`}
                    className="suggestion-chip"
                    onClick={() => handleSend(question)}
                    disabled={loading}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, index) => {
              // Se o assistente estiver gerando a resposta e ela ainda estiver vazia,
              // podemos exibir um microindicador de digitação
              const isEmptyAssistant = msg.role === "assistant" && msg.content === "";

              return (
                <div key={index} className={`message-row ${msg.role}`}>
                  <div className="message-wrapper">
                    {msg.role === "assistant" && (
                      <div className="message-avatar">
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M12 2a10 10 0 0 0-10 10c0 5.523 4.477 10 10 10s10-4.477 10-10A10 10 0 0 0 12 2z" />
                          <path d="M12 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
                          <path d="M12 18h.01" />
                        </svg>
                      </div>
                    )}
                    <div className="message-bubble">
                      {msg.role === "system" ? (
                        <p className="system-text">{msg.content}</p>
                      ) : isEmptyAssistant ? (
                        <div className="typing-indicator" aria-label="Oráculo digitando">
                          <span></span>
                          <span></span>
                          <span></span>
                        </div>
                      ) : (
                        renderContent(msg.content)
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      {/* Caixa de Entrada de Mensagens */}
      <footer className="chat-input-area">
        <div className="input-container-wrapper">
          <div className="input-container">
            <textarea
              ref={textareaRef}
              id="chat-textarea"
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Digite sua pergunta..."
              disabled={loading}
              aria-label="Mensagem para o assistente"
            />
            <button
              id="btn-send"
              className={loading ? "btn-stop" : ""}
              onClick={handleSendOrStop}
              disabled={!loading && !input.trim()}
              title={loading ? "Parar resposta" : "Enviar mensagem"}
              aria-label={loading ? "Parar resposta" : "Enviar"}
            >
              {loading ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              )}
            </button>
          </div>
        </div>
        <p className="input-note">
          As informações contidas nesta conversa têm caráter informativo e de acolhimento,
          não substituindo pareceres médicos, clínicos ou jurídicos especializados.
        </p>
      </footer>

      <ConfirmDialog
        open={confirmOpen}
        title="Iniciar nova conversa?"
        description="O histórico atual será limpo para começarmos um novo atendimento."
        confirmLabel="Iniciar nova conversa"
        cancelLabel="Continuar conversa"
        onConfirm={handleConfirmNewConversation}
        onCancel={handleCancelNewConversation}
        variant="default"
      />
    </div>
  );
}

export default App;