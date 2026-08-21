"use client";

import { useEffect, useRef, useState } from "react";
import CredentialsForm from "./CredentialsForm";
import ChatMessageList from "./ChatMessageList";
import { ChatMessage, Phase } from "./Chat.types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || API_URL.replace(/^http/, "ws");

// Human-readable labels for worker states
const STATUS_LABELS: Record<string, string> = {
  STARTING: "Iniciando el asistente...",
  AUTHENTICATING: "Iniciando sesión...",
  AUTHENTICATED: "Sesión iniciada ✅",
  INTERPRETING_REQUEST: "Interpretando tu pedido...",
  INTERPRETED: "",
  SEARCHING_PRODUCTS: "",
  PRODUCT_ADDED: "",
  PRODUCT_NOT_FOUND: "",
  PRODUCT_ERROR: "",
  CART_READY: "Carrito listo ✅",
  COMPLETED: "",
  FAILED: "",
};

export default function Chat() {
  const [phase, setPhase] = useState<Phase>("credentials");
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Hola 👋 Para comenzar necesito acceder a tu cuenta para hacer las compras.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function pushMsg(msg: ChatMessage) {
    setMessages((prev) => [...prev, msg]);
  }

  function handleCredentials(email: string, password: string) {
    setCredentials({ email, password });
    setPhase("prompt");
    pushMsg({ role: "assistant", text: "Perfecto. ¿Qué querés comprar hoy?" });
  }

  async function handleSend() {
    const text = input.trim();
    if (!text || busy || !credentials) return;
    setInput("");
    setBusy(true);
    pushMsg({ role: "user", text });

    let jobId: string;
    try {
      const res = await fetch(`${API_URL}/api/purchases`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          email: credentials.email,
          password: credentials.password,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        pushMsg({ role: "assistant", text: `❌ Error al iniciar la compra: ${err?.detail ?? res.statusText}` });
        setBusy(false);
        return;
      }

      const data = await res.json();
      jobId = data.job_id;
      if (data.status === "PENDING") {
        pushMsg({
          role: "status",
          text: "Hay pedidos en cola. Cuando el worker se desocupe, sigo con el tuyo.",
          icon: "⏳",
        });
      }
    } catch {
      pushMsg({ role: "assistant", text: "❌ No pude conectarme al servidor. Intentá de nuevo." });
      setBusy(false);
      return;
    }

    setPhase("working");

    const ws = new WebSocket(`${WS_BASE_URL}/api/purchases/${jobId}/ws`);
    let closedByTerminal = false;

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data) as Record<string, unknown>;
        if (event.type === "ping") {
          return;
        }

        const status = typeof event.status === "string" ? event.status : "";
        const message = typeof event.message === "string" ? event.message : "";
        const items = Array.isArray(event.items) ? event.items : [];
        const total = typeof event.total === "number" ? event.total : 0;
        const checkoutUrl =
          typeof event.checkout_url === "string"
            ? event.checkout_url
            : "https://www.cotodigital.com.ar/sitios/cdigi/carrito";

        if (status === "COMPLETED") {
          closedByTerminal = true;
          ws.close();
          setBusy(false);
          setPhase("done");
          pushMsg({
            role: "summary",
            items,
            total,
            checkoutUrl,
          });
          return;
        }

        if (status === "FAILED") {
          closedByTerminal = true;
          ws.close();
          setBusy(false);
          setPhase("prompt");
          pushMsg({ role: "assistant", text: `❌ ${message}` });
          return;
        }

        if (status === "DEBUG_LLM_USAGE" && event.debug === true) {
          pushMsg({ role: "status", text: message, icon: "🧠" });
          return;
        }

        const label = STATUS_LABELS[status];
        const display = label !== undefined ? (label || message) : message;
        if (display) {
          pushMsg({ role: "status", text: display });
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onclose = () => {
      if (closedByTerminal) {
        return;
      }
      setBusy(false);
      setPhase("prompt");
      pushMsg({ role: "assistant", text: "❌ Se interrumpió la conexión con el servidor." });
    };
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden pt-4 gap-4">
      <ChatMessageList messages={messages} busy={busy} bottomRef={bottomRef} />

      {phase === "credentials" && (
        <CredentialsForm onSubmit={handleCredentials} />
      )}

      {(phase === "prompt" || phase === "done") && (
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
            className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            placeholder="¿Qué querés comprar?"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            autoFocus
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="rounded-xl bg-indigo-600 px-5 py-3 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 disabled:opacity-40 transition-colors"
          >
            Enviar
          </button>
        </form>
      )}

    </div>
  );
}
