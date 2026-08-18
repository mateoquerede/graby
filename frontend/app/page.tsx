"use client";
import Chat from "@/components/Chat";

export default function Home() {
  return (
    <main className="flex h-screen flex-col items-center justify-center bg-gray-50 p-4">
      <div className="w-full max-w-2xl flex flex-col h-full max-h-[90vh]">
        <header className="flex items-center gap-2 pb-4 border-b border-gray-200">
          <span className="text-2xl font-bold tracking-tight">Graby</span>
          <span className="text-sm text-gray-400 ml-1">tu copiloto de compras</span>
        </header>
        <Chat />
      </div>
    </main>
  );
}
