"use client";

import { useCallback, useRef, useState } from "react";
import { ChatMessage, ProposedItem } from "../Chat.types";
import { DEMO_CART, DEMO_ITEMS, DEMO_MESSAGE, DEMO_TOTAL } from "./demoData";

export interface DemoConfirmation {
  jobId: string;
  items: ProposedItem[];
}

interface UseDemoOptions {
  pushMsg: (msg: ChatMessage) => void;
  clearMessages: () => void;
  setPhase: (phase: "credentials" | "prompt" | "working" | "done") => void;
  setBusy: (busy: boolean) => void;
  setPendingConfirmation: (conf: DemoConfirmation | null) => void;
}

export function useDemo({ pushMsg, clearMessages, setPhase, setBusy, setPendingConfirmation }: UseDemoOptions) {
  const [demo, setDemo] = useState(false);
  const timersRef = useRef<number[]>([]);

  const schedule = useCallback((fn: () => void, delay: number) => {
    const id = window.setTimeout(fn, delay);
    timersRef.current.push(id);
    return id;
  }, []);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach((id) => window.clearTimeout(id));
    timersRef.current = [];
  }, []);

  const startDemo = useCallback(() => {
    clearTimers();
    setDemo(true);
    setPhase("prompt");
    clearMessages();
    pushMsg({
      role: "assistant",
      text: "¡Bienvenido a la demo! 👋 Estás usando Graby Demo: no se hace ninguna compra real. Probá con el pedido de ejemplo.",
    });
  }, [pushMsg, clearMessages, setPhase, clearTimers]);

  const runDemoFlow = useCallback(() => {
    setPhase("working");
    const steps: Array<[number, ChatMessage]> = [
      [400, { role: "status", text: "Procesando tu pedido...", icon: "⏳" }],
      [1200, { role: "status", text: "Entendiendo tu pedido...", icon: "🧠" }],
      [2200, { role: "status", text: "Buscando productos en Coto...", icon: "🔎" }],
      [3200, { role: "status", text: "Comparando opciones...", icon: "⚖️" }],
      [4200, { role: "status", text: "Armando la lista...", icon: "🧾" }],
    ];
    steps.forEach(([delay, msg]) => schedule(() => pushMsg(msg), delay));
    schedule(() => {
      setBusy(false);
      setPendingConfirmation({ jobId: "demo", items: DEMO_ITEMS });
    }, 5000);
  }, [pushMsg, setPhase, setBusy, setPendingConfirmation, schedule]);

  const confirmDemo = useCallback(() => {
    setPendingConfirmation(null);
    setBusy(true);
    schedule(() => pushMsg({ role: "status", text: "Agregando productos al carrito...", icon: "🛒" }), 400);
    schedule(() => pushMsg({ role: "status", text: "Calculando el total...", icon: "💰" }), 1400);
    schedule(() => {
      setBusy(false);
      setPhase("done");
      pushMsg({ role: "summary", items: DEMO_CART, total: DEMO_TOTAL, checkoutUrl: "#" });
    }, 2400);
  }, [pushMsg, setPhase, setBusy, setPendingConfirmation, schedule]);

  const exitDemo = useCallback(() => {
    clearTimers();
    setDemo(false);
    setPhase("credentials");
    setPendingConfirmation(null);
    setBusy(false);
    clearMessages();
  }, [setPhase, setPendingConfirmation, clearMessages, clearTimers]);

  return { demo, startDemo, runDemoFlow, confirmDemo, exitDemo, demoMessage: DEMO_MESSAGE };
}
