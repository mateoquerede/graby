"use client";
import { useState } from "react";
import Chat from "@/components/Chat";
import InfoModal from "@/components/InfoModal";

export default function Home() {
  const [infoOpen, setInfoOpen] = useState(false);

  return (
    <main className="flex h-screen flex-col items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-2xl flex flex-col h-full max-h-[90vh]">
        <header className="flex items-center gap-2 border-b border-gray-200 pb-4">
          <span className="text-2xl font-bold tracking-tight">Graby</span>
          <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-700">
            beta
          </span>
          <span className="ml-1 text-sm text-gray-400">tu copiloto de compras</span>
          <button
            type="button"
            aria-label="Cómo funciona Graby"
            title="Cómo funciona Graby"
            onClick={() => setInfoOpen(true)}
            className="ml-auto flex h-7 w-7 items-center justify-center rounded-full border border-gray-300 text-sm font-semibold text-gray-500 transition-colors hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600"
          >
            <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M18 10A8 8 0 1 1 2 10a8 8 0 0 1 16 0ZM9 8.5a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0v-5ZM10 5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </header>
        <Chat />
      </div>
      <InfoModal open={infoOpen} onClose={() => setInfoOpen(false)} />
    </main>
  );
}
