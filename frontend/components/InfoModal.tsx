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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="presentation"
    >
      <section
        aria-labelledby="info-modal-title"
        aria-modal="true"
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="flex items-start justify-between border-b border-gray-100 px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-600">Guía rápida</p>
            <h2 id="info-modal-title" className="mt-1 text-xl font-semibold text-gray-900">
              Cómo funciona Graby
            </h2>
          </div>
          <button
            type="button"
            aria-label="Cerrar información"
            onClick={onClose}
            className="rounded-lg p-2 text-xl leading-none text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            ×
          </button>
        </div>

        <div className="space-y-5 px-6 py-5 text-sm leading-6 text-gray-600">
          <div>
            <h3 className="font-semibold text-gray-900">1. Contale qué necesitás</h3>
            <p>
              Escribí un pedido con tus productos, cantidades y preferencias. Por ejemplo:
              <span className="mt-2 block rounded-lg bg-gray-50 px-3 py-2 text-gray-700">
                “Comprá 2 paquetes de fideos, leche descremada y algo dulce para el sábado.”
              </span>
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900">2. Revisá el resultado</h3>
            <p>
              Graby busca los productos y arma el carrito en la tienda. Al finalizar vas a poder
              revisar el carrito y completar el pago directamente en la tienda.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-gray-900">Para obtener mejores resultados</h3>
            <p>
              Indicá marca, tamaño, presupuesto o reemplazos aceptables. Si algo no queda claro,
              podés enviar otro pedido para ajustar tu compra.
            </p>
          </div>

          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-900">
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
