"use client";

import { useEffect, useRef, useState } from "react";
import CredentialsForm from "./CredentialsForm";
import ChatMessageList from "./ChatMessageList";
import MonitorModal from "./MonitorModal";
import { ChatMessage, Phase } from "./Chat.types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || API_URL.replace(/^http/, "ws");
const MONITOR_URL =
  process.env.NEXT_PUBLIC_MONITOR_URL ||
  "http://localhost:6080/vnc_lite.html?autoconnect=true&scale=true&view_only=true";

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
  LIVE_MONITOR_READY: "Monitor en vivo conectado ✅",
  COMPLETED: "",
  FAILED: "",
};

function formatBrowserAction(event: Record<string, unknown>) {
  const action = typeof event.action === "string" ? event.action : "";
  const query = typeof event.query === "string" ? event.query : "";
  const target = typeof event.target === "string" ? event.target : "";
  const product = typeof event.product === "string" ? event.product : "";
  const quantity = typeof event.quantity === "number" ? event.quantity : null;
  const url = typeof event.url === "string" ? event.url : "";

  switch (action) {
    case "search":
      return query ? `Buscando "${query}"...` : "Buscando producto...";
    case "click":
      return target ? `Click en "${target}".` : "Click en página.";
    case "product_added":
      return product
        ? `Producto agregado: ${product}${quantity ? ` x${quantity}` : ""}.`
        : "Producto agregado al carrito.";
    case "navigate":
      return url ? `Navegando: ${url}` : "Abriendo página...";
    case "login":
      return "Acción: inicio de sesión en tienda.";
    case "clear_cart":
      return "Acción: limpiando carrito.";
    case "open_cart":
      return "Abriendo carrito final.";
    default:
      return "Acción en navegador.";
  }
}

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
  const [monitorEnabled, setMonitorEnabled] = useState(false);
  const [monitorOpen, setMonitorOpen] = useState(false);
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
    const monitorRequested = monitorEnabled;

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
          monitor_playwright: monitorRequested,
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
      if (monitorRequested) {
        setMonitorOpen(true);
      }

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

        if (event.type === "browser_action") {
          pushMsg({ role: "action", text: formatBrowserAction(event), icon: "•" });
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

      {phase !== "credentials" && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => {
              if (!monitorEnabled) {
                setMonitorEnabled(true);
                setMonitorOpen(true);
              } else {
                setMonitorOpen((prev) => !prev);
              }
            }}
            className={`rounded-xl px-4 py-2 text-xs font-medium transition-colors ${
              monitorEnabled
                ? "bg-indigo-100 text-indigo-700 hover:bg-indigo-200"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {!monitorEnabled ? "Monitorear" : monitorOpen ? "Monitorear: activado" : "Monitorear: minimizado"}
          </button>
        </div>
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

      <MonitorModal
        open={monitorOpen}
        monitorEnabled={monitorEnabled}
        monitorUrl={MONITOR_URL}
        onClose={() => setMonitorOpen(false)}
      />
    </div>
  );
}
