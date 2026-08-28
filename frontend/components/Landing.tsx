"use client";

import { useState } from "react";

interface Props {
  onExample: (text: string) => void;
}

const EXAMPLES = [
  {
    icon: "🛒",
    text: "Comprá 2 paquetes de fideos, leche descremada y algo dulce para el sábado.",
  },
  {
    icon: "🥩",
    text: "Necesito para el asado del domingo: 1kg de vacío, chorizos y provoleta.",
  },
  {
    icon: "🧼",
    text: "Un pedido de limpieza: lavandina, detergente y esponjas, lo más barato.",
  },
];

const STEPS = [
  {
    icon: "💬",
    title: "1. Contale qué necesitás",
    text: "Escribí tu pedido con productos, cantidades y preferencias, como se lo dirías a alguien.",
  },
  {
    icon: "🔎",
    title: "2. Graby busca y compara",
    text: "Busca cada producto, compara opciones y arma la lista. Te la muestra para que la confirmes.",
  },
  {
    icon: "🛒",
    title: "3. Revisá y pagá en la tienda",
    text: "Deja el carrito listo en tu supermercado. Vos revisás el total y completás el pago ahí.",
  },
];

export default function Landing({ onExample }: Props) {
  const [selected, setSelected] = useState<string | null>(null);

  function handleSelect(text: string) {
    const next = selected === text ? null : text;
    setSelected(next);
    onExample(next ?? "");
  }

  return (
    <div className="msg-enter flex flex-col gap-4">
      <div className="rounded-2xl border border-white/70 bg-white/90 p-5 shadow-lg shadow-indigo-500/5 backdrop-blur-md dark:border-white/10 dark:bg-white/5">
        <p className="text-center text-lg font-semibold leading-snug text-gray-800 dark:text-gray-100">
          Decile qué necesitás.{" "}
          <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent dark:from-indigo-400 dark:via-violet-400 dark:to-fuchsia-400">
            Graby busca, compara y arma tu compra.
          </span>
        </p>
        <p className="mt-2 text-center text-sm text-gray-500 dark:text-gray-400">
          Tu copiloto de compras: escribí tu pedido y Graby lo deja listo en tu supermercado.
        </p>
      </div>

      <div className="rounded-2xl border border-white/70 bg-white/90 p-4 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-white/5">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
          Cómo funciona
        </p>
        <div className="flex flex-col gap-3">
          {STEPS.map((step) => (
            <div key={step.title} className="flex items-start gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 text-sm font-bold text-white">
                {step.icon}
              </span>
              <div>
                <p className="text-sm font-semibold text-gray-800 dark:text-gray-100">{step.title}</p>
                <p className="text-sm leading-5 text-gray-500 dark:text-gray-400">{step.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-2xl border border-white/70 bg-white/90 p-4 shadow-sm backdrop-blur-md dark:border-white/10 dark:bg-white/5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400 dark:text-gray-500">
          Probá con un ejemplo
        </p>
        <div className="flex flex-col gap-2">
          {EXAMPLES.map((ex) => {
            const isSelected = selected === ex.text;
            return (
              <button
                key={ex.text}
                type="button"
                aria-pressed={isSelected}
                onClick={() => handleSelect(ex.text)}
                className={`flex items-start gap-2 rounded-xl border px-3 py-2.5 text-left text-sm transition-colors ${
                  isSelected
                    ? "border-indigo-400 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-300 dark:border-indigo-500/50 dark:bg-indigo-500/10 dark:text-indigo-300 dark:ring-indigo-400/30"
                    : "border-gray-100 bg-gray-50/60 text-gray-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 dark:border-white/10 dark:bg-white/5 dark:text-gray-300 dark:hover:border-indigo-500/40 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-300"
                }`}
              >
                <span className="text-base leading-5">{ex.icon}</span>
                <span className="leading-5">{ex.text}</span>
                {isSelected && (
                  <span className="ml-auto text-indigo-500 dark:text-indigo-300">✓</span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}