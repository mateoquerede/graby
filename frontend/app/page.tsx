"use client";
import { useState } from "react";
import Chat from "@/components/Chat";
import InfoModal from "@/components/InfoModal";
import BotAvatar from "@/components/BotAvatar";
import ThemeToggle from "@/components/ThemeToggle";

export default function Home() {
  const [infoOpen, setInfoOpen] = useState(false);

  return (
    <main className="flex h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-2xl flex flex-col h-full max-h-[92vh]">
        <header className="flex items-center gap-3 rounded-2xl bg-white/80 p-3 shadow-sm backdrop-blur-md border border-white/60 dark:border-white/10 dark:bg-white/5">
          <BotAvatar size="md" />
          <div className="leading-tight">
            <h1 className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-indigo-600 via-violet-600 to-fuchsia-600 bg-clip-text text-transparent dark:from-indigo-400 dark:via-violet-400 dark:to-fuchsia-400">
              Graby
            </h1>
            <p className="text-[10px] text-gray-500 dark:text-gray-400">tu copiloto de compras</p>
          </div>
          <span className="ml-1 rounded-full bg-gradient-to-r from-indigo-100 to-fuchsia-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-700 ring-1 ring-indigo-200 dark:from-indigo-500/20 dark:to-fuchsia-500/20 dark:text-indigo-300 dark:ring-indigo-400/30">
            {process.env.NEXT_PUBLIC_APP_VERSION}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            <button
              type="button"
              aria-label="Cómo funciona Graby"
              title="Cómo funciona Graby"
              onClick={() => setInfoOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 bg-white text-sm font-semibold text-gray-500 shadow-sm transition-colors hover:border-indigo-400 hover:bg-indigo-50 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-gray-400 dark:hover:border-indigo-400 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-300"
            >
              <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M18 10A8 8 0 1 1 2 10a8 8 0 0 1 16 0ZM9 8.5a1 1 0 1 1 2 0v5a1 1 0 1 1-2 0v-5ZM10 5a1 1 0 1 1 0 2 1 1 0 0 1 0-2Z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </header>
        <div className="pt-3 h-full min-h-0">
          <Chat />
        </div>
      </div>
      <InfoModal open={infoOpen} onClose={() => setInfoOpen(false)} />
      <footer className="mt-2 text-center text-[10px] text-gray-400 dark:text-gray-500">
        Graby v{process.env.NEXT_PUBLIC_APP_VERSION} · alpha
      </footer>
    </main>
  );
}
