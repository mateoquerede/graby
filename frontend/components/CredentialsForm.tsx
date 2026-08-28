"use client";

import { useEffect, useState } from "react";

export interface Provider {
  id: string;
  label: string;
}

interface Props {
  providers: Provider[];
  onSubmit: (email: string, password: string, provider: string) => void;
}

export default function CredentialsForm({ providers, onSubmit }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [provider, setProvider] = useState<string>("coto");

  // Default to the first provider once the list loads.
  useEffect(() => {
    if (providers.length > 0 && !providers.some((p) => p.id === provider)) {
      setProvider(providers[0].id);
    }
  }, [providers, provider]);

  const singleProvider = providers.length === 1 ? providers[0] : null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (email.trim() && password) onSubmit(email.trim(), password, provider);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="msg-enter flex flex-col gap-3 overflow-hidden rounded-2xl border border-white/70 bg-white/90 p-4 shadow-lg shadow-indigo-500/5 backdrop-blur-md dark:border-white/10 dark:bg-white/5"
    >
      <div className="flex items-start gap-2">
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Ingresá tus credenciales para que <b className="text-indigo-600 dark:text-indigo-400">Graby</b> pueda hacer las
          compras. <span className="text-gray-400 dark:text-gray-500">No las guardamos.</span>
        </p>
      </div>
      <fieldset className="flex flex-col gap-1.5">
        {!singleProvider && (
          <>
            <legend className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
              Supermercado
            </legend>
            <div className="flex gap-2">
              {providers.map((p) => (
                <label
                  key={p.id}
                  className={`flex flex-1 cursor-pointer items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors ${
                    provider === p.id
                      ? "border-indigo-400 bg-indigo-50 text-indigo-700 dark:border-indigo-500/50 dark:bg-indigo-500/10 dark:text-indigo-300"
                      : "border-gray-200 bg-gray-50/60 text-gray-600 hover:border-gray-300 dark:border-white/10 dark:bg-white/5 dark:text-gray-300"
                  }`}
                >
                  <input
                    type="radio"
                    name="provider"
                    value={p.id}
                    checked={provider === p.id}
                    onChange={() => setProvider(p.id)}
                    className="h-4 w-4 accent-indigo-600"
                  />
                  {p.label}
                </label>
              ))}
            </div>
          </>
        )}
      </fieldset>
      <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50/60 px-3 focus-within:ring-2 focus-within:ring-indigo-400 dark:border-white/10 dark:bg-white/5">
        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 shrink-0 text-gray-400" stroke="currentColor" strokeWidth="2">
          <path d="M3 8l7.9 5.3a2 2 0 0 0 2.2 0L21 8M5 19h14a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2Z" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <input
          type="text"
          placeholder="Documento, email o usuario"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full bg-transparent px-2 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder-gray-500"
        />
      </div>
      <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-gray-50/60 px-3 focus-within:ring-2 focus-within:ring-indigo-400 dark:border-white/10 dark:bg-white/5">
        <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 shrink-0 text-gray-400" stroke="currentColor" strokeWidth="2">
          <path d="M12 15v2m-7 4h14a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2Zm5-10V7a5 5 0 0 1 10 0v4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <input
          type="password"
          placeholder="Contraseña"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full bg-transparent px-2 py-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none dark:text-gray-100 dark:placeholder-gray-500"
        />
      </div>
      <button
        type="submit"
        className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 py-3 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.01] hover:from-indigo-700 hover:to-violet-700"
      >
        Continuar
      </button>
    </form>
  );
}
