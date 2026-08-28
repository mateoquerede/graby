"use client";

import { useEffect } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function InfoModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 dark:bg-black/70"
      onClick={onClose}
      role="presentation"
    >
      <section
        aria-labelledby="info-modal-title"
        aria-modal="true"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl dark:bg-slate-900 dark:ring-1 dark:ring-white/10"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5 dark:border-white/10">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">Guía rápida</p>
            <h2 id="info-modal-title" className="mt-1 text-xl font-semibold text-gray-900 dark:text-gray-100">
              Cómo funciona Graby
            </h2>
          </div>
          <button
            type="button"
            aria-label="Cerrar información"
            onClick={onClose}
            className="rounded-lg p-2 text-xl leading-none text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 dark:text-gray-500 dark:hover:bg-white/10 dark:hover:text-gray-200"
          >
            ×
          </button>
        </div>

        <div className="space-y-5 px-6 py-5 text-sm leading-6 text-gray-600 dark:text-gray-300">
          <div className="rounded-xl bg-gradient-to-r from-indigo-50 to-fuchsia-50 px-4 py-3 text-center dark:from-indigo-500/10 dark:to-fuchsia-500/10">
            <p className="text-base font-semibold text-gray-800 dark:text-gray-100">
              Decile qué necesitás.{" "}
              <span className="bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent dark:from-indigo-400 dark:via-violet-400 dark:to-fuchsia-400">
                Graby busca, compara y arma tu compra.
              </span>
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">1. Contale qué necesitás</h3>
            <p>
              Escribí un pedido con tus productos, cantidades y preferencias. Por ejemplo:
              <span className="mt-2 block rounded-lg bg-gray-50 px-3 py-2 text-gray-700 dark:bg-white/5 dark:text-gray-200">
                “Comprá 2 paquetes de fideos, leche descremada y algo dulce para el sábado.”
              </span>
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">2. Graby busca y compara</h3>
            <p>
              Busca cada producto, compara opciones y arma la lista. Te la muestra para que la
              confirmes o la corrijas antes de seguir.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">3. Revisá y pagá en la tienda</h3>
            <p>
              Graby deja el carrito listo en tu supermercado. Al finalizar vas a poder revisar el
              carrito y completar el pago directamente en la tienda.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Para obtener mejores resultados</h3>
            <p>
              Indicá marca, tamaño, presupuesto o reemplazos aceptables. Si algo no queda claro,
              podés enviar otro pedido para ajustar tu compra.
            </p>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900 dark:border-amber-400/30 dark:bg-amber-400/10 dark:text-amber-200">
            <h3 className="font-semibold">Importante</h3>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              <li>Graby usa modelos de IA no determinísticos: puede interpretar mal o equivocarse.</li>
              <li>Verificá productos, cantidades, precios y el total antes de pagar.</li>
              <li>No ingreses datos de tarjetas ni información sensible en el chat.</li>
              <li>Tus credenciales se usan para esta sesión y no se guardan en una base de datos ni en logs.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
