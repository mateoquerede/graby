"use client";

import { useEffect, useRef, useState } from "react";
import CredentialsForm from "./CredentialsForm";
import Message from "./Message";
import CartSummary from "./CartSummary";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

type Msg =
  | { role: "assistant" | "user"; text: string }
  | { role: "status"; text: string; icon?: string }
  | { role: "summary"; items: CartItem[]; total: number; checkoutUrl: string };

export interface CartItem {
  requested: string;
  name: string;
  quantity: number;
  price?: number;
  reason: string;
}

type Phase = "credentials" | "prompt" | "working" | "done";

export default function Chat() {
  const [phase, setPhase] = useState<Phase>("credentials");
  const [credentials, setCredentials] = useState<{ email: string; password: string } | null>(null);
  const [messages, setMessages] = useState<Msg[]>([
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

  function pushMsg(msg: Msg) {
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

    // Create job
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
    } catch {
      pushMsg({ role: "assistant", text: "❌ No pude conectarme al servidor. Intentá de nuevo." });
      setBusy(false);
      return;
    }

    setPhase("working");

    // Subscribe to SSE
    const sse = new EventSource(`${API_URL}/api/purchases/${jobId}/events`);

    sse.addEventListener("worker_status", (e) => {
      try {
        const event = JSON.parse(e.data);
        const { status, message, items, total, checkout_url } = event;

        if (status === "COMPLETED") {
          sse.close();
          setBusy(false);
          setPhase("done");
          pushMsg({
            role: "summary",
            items: items ?? [],
            total: total ?? 0,
            checkoutUrl: checkout_url ?? "https://www.cotodigital.com.ar/sitios/cdigi/carrito",
          });
          return;
        }

        if (status === "FAILED") {
          sse.close();
          setBusy(false);
          setPhase("prompt");
          pushMsg({ role: "assistant", text: `❌ ${message}` });
          return;
        }

        // Show meaningful status messages in the chat
        const label = STATUS_LABELS[status];
        const display = label !== undefined ? (label || message) : message;

        if (display) {
          pushMsg({ role: "status", text: display });
        }
      } catch {
        // ignore parse errors
      }
    });

    sse.onerror = () => {
      sse.close();
      setBusy(false);
      setPhase("prompt");
      pushMsg({ role: "assistant", text: "❌ Se interrumpió la conexión con el servidor." });
    };
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden pt-4 gap-4">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
        {messages.map((msg, i) => {
          if (msg.role === "summary") {
            return (
              <CartSummary
                key={i}
                items={msg.items}
                total={msg.total}
                checkoutUrl={msg.checkoutUrl}
              />
            );
          }
          return <Message key={i} msg={msg} />;
        })}
        {busy && (
          <div className="flex items-center gap-2 text-sm text-gray-400 pl-2">
            <span className="animate-spin">⏳</span>
            <span>Graby está trabajando...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
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
