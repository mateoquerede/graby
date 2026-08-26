"use client";

import { useEffect, useRef, useState } from "react";
import CredentialsForm from "./CredentialsForm";
import ChatMessageList from "./ChatMessageList";
import { ChatMessage, Phase, ProposedItem } from "./Chat.types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || API_URL.replace(/^http/, "ws");

// Stable presentation for progress events. Product-specific messages come from the worker.
const STATUS_PRESENTATION: Record<string, { label?: string; icon: string }> = {
  STARTING: { label: "Procesando tu pedido...", icon: "⏳" },
  AUTHENTICATING: { label: "Iniciando sesión...", icon: "🔐" },
  AUTHENTICATED: { label: "Sesión iniciada ✓", icon: "🔐" },
  INTERPRETING_REQUEST: { label: "Entendiendo tu pedido...", icon: "🧠" },
  INTERPRETED: { icon: "🧠" },
  SEARCHING_PRODUCTS: { icon: "🔎" },
  COMPARING_OPTIONS: { icon: "⚖️" },
  PRODUCT_ADDED: { icon: "🎯" },
  PRODUCT_NOT_FOUND: { icon: "⚠️" },
  PRODUCT_ERROR: { icon: "⚠️" },
  REVIEWING_CART: { icon: "🧾" },
  CALCULATING_TOTAL: { icon: "💰" },
  PREPARING_CART: { icon: "🛒" },
  AWAITING_CONFIRMATION: { icon: "🧠" },
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
  const inputRef = useRef<HTMLInputElement>(null);
  const confirmationShownRef = useRef(false);
  const confirmationAcceptedRef = useRef(false);
  const [pendingConfirmation, setPendingConfirmation] = useState<{
    jobId: string;
    items: ProposedItem[];
  } | null>(null);
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
    confirmationShownRef.current = false;
    confirmationAcceptedRef.current = false;
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
          setPendingConfirmation(null);
          pushMsg({
            role: "summary",
            items,
            total,
            checkoutUrl,
          });
          return;
        }

        if (status === "AWAITING_CONFIRMATION") {
          if (confirmationAcceptedRef.current || confirmationShownRef.current) {
            return;
          }
          const proposedItems = items.filter(
            (item): item is ProposedItem =>
              typeof item === "object" &&
              item !== null &&
              typeof (item as Record<string, unknown>).query === "string" &&
              typeof (item as Record<string, unknown>).quantity === "number",
          );
          setBusy(false);
          confirmationShownRef.current = true;
          setPendingConfirmation({ jobId, items: proposedItems });
        }

        if (status === "FAILED") {
          closedByTerminal = true;
          ws.close();
          setBusy(false);
          setPhase("prompt");
          setPendingConfirmation(null);
          pushMsg({ role: "assistant", text: `❌ ${message}` });
          return;
        }

        if (status === "DEBUG_LLM_USAGE" && event.debug === true) {
          pushMsg({ role: "status", text: message, icon: "🧠" });
          return;
        }

        const presentation = STATUS_PRESENTATION[status];
        const display = presentation?.label ?? message;
        if (display) {
          pushMsg({
            role: "status",
            text: display,
            icon: presentation?.icon,
          });
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

  async function confirmList(confirmed: boolean, message?: string) {
    if (!pendingConfirmation || busy) return;
    if (confirmed) {
      confirmationAcceptedRef.current = true;
    } else {
      confirmationShownRef.current = false;
    }
    setPendingConfirmation(null);
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/purchases/${pendingConfirmation.jobId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          confirmed
            ? { confirmed: true, items: pendingConfirmation.items }
            : { confirmed: false, message },
        ),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail ?? "No pude actualizar la lista.");
      }
      if (!confirmed && message) {
        pushMsg({ role: "user", text: message });
      }
      setPendingConfirmation(null);
    } catch (error) {
      setBusy(false);
      setPhase("prompt");
      pushMsg({
        role: "assistant",
        text: `❌ ${error instanceof Error ? error.message : "No pude actualizar la lista."}`,
      });
    }
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden pt-4 gap-4">
      <ChatMessageList
        messages={messages}
        busy={busy}
        bottomRef={bottomRef}
        confirmation={
          pendingConfirmation && (
            <div className="msg-enter rounded-2xl border border-indigo-100 bg-white/90 p-4 text-sm shadow-sm backdrop-blur-sm dark:border-indigo-500/20 dark:bg-white/5">
              <div className="flex items-center gap-2">
                <span className="text-lg">🧠</span>
                <p className="font-semibold text-gray-800 dark:text-gray-100">Esta es la lista que voy a buscar:</p>
              </div>
              <ul className="mt-2 grid gap-1.5 text-gray-600 dark:text-gray-300">
                {pendingConfirmation.items.map((item, index) => (
                  <li
                    key={`${item.query}-${index}`}
                    className="flex items-center gap-2 rounded-lg bg-indigo-50/70 px-3 py-2 dark:bg-indigo-500/10"
                  >
                    <span className="h-2 w-2 shrink-0 rounded-full bg-indigo-500 dark:bg-indigo-300" />
                    <span className="font-medium">{item.query}</span>
                    <span className="ml-auto text-xs text-indigo-500 dark:text-indigo-300">x {item.quantity}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-gray-700 dark:text-gray-200">¿Está correcta?</p>
              <div className="mt-3 flex gap-2">
                <button
                  type="button"
                  onClick={() => confirmList(true)}
                  disabled={busy}
                  className="rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.02] hover:from-indigo-700 hover:to-violet-700 disabled:opacity-40 disabled:hover:scale-100"
                >
                  Sí, buscar productos ✓
                </button>
              </div>
              <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
                ¿Algo mal? Escribí la corrección abajo para ajustar la lista.
              </p>
            </div>
          )
        }
      />

      {phase === "credentials" && (
        <CredentialsForm onSubmit={handleCredentials} />
      )}

      {(phase === "prompt" || phase === "done" || pendingConfirmation) && (
        <form
          className="flex items-center gap-2 rounded-2xl border border-white/60 bg-white/90 p-2 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-white/5"
          onSubmit={(e) => {
            e.preventDefault();
            if (pendingConfirmation) {
              const correction = input.trim();
              if (correction) {
                setInput("");
                confirmList(false, correction);
              } else {
                confirmList(true);
              }
            } else {
              handleSend();
            }
          }}
        >
          <input
            ref={inputRef}
            className="flex-1 bg-transparent px-3 py-2.5 text-sm focus:outline-none"
            placeholder={pendingConfirmation ? "¿Qué querés corregir?" : "¿Qué querés comprar?"}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={busy}
            autoFocus
          />
          <button
            type="submit"
            disabled={busy || !input.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 text-white shadow-sm transition-colors hover:from-indigo-700 hover:to-violet-700 disabled:opacity-40"
            aria-label="Enviar mensaje"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" className="h-4 w-4">
              <path d="M3.4 20.4 22 12 3.4 3.6 3.39 10l13 2-13 2z" />
            </svg>
          </button>
        </form>
      )}

    </div>
  );
}
