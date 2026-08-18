"use client";

import { useState } from "react";

interface Props {
  onSubmit: (email: string, password: string) => void;
}

export default function CredentialsForm({ onSubmit }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (email.trim() && password) onSubmit(email.trim(), password);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-gray-500">
        Ingresá tus credenciales para que Graby pueda hacer las compras. No las guardamos.
      </p>
      <input
        type="text"
        placeholder="Documento, email o usuario"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
        className="rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <input
        type="password"
        placeholder="Contraseña"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
        className="rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <button
        type="submit"
        className="rounded-xl bg-indigo-600 py-3 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        Continuar
      </button>
    </form>
  );
}
