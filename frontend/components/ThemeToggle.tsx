"use client";

import { useTheme, Theme } from "./ThemeProvider";

const ICONS: Record<Theme, React.ReactNode> = {
  light: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
      <path
        d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4m11.4-11.4 1.4-1.4"
        strokeLinecap="round"
      />
    </svg>
  ),
  dark: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2">
      <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  ),
  system: (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2">
      <rect x="2" y="4" width="20" height="14" rx="2" />
      <path d="M8 21h8" strokeLinecap="round" />
    </svg>
  ),
};

const LABELS: Record<Theme, string> = {
  light: "Tema claro",
  dark: "Tema oscuro",
  system: "Tema del sistema",
};

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  function cycle() {
    const order: Theme[] = ["system", "light", "dark"];
    const idx = order.indexOf(theme);
    setTheme(order[(idx + 1) % order.length]);
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`Cambiar tema. Actual: ${LABELS[theme]}`}
        title={LABELS[theme]}
        onClick={cycle}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-500 shadow-sm transition-colors hover:border-indigo-400 hover:text-indigo-600 dark:border-white/10 dark:bg-white/5 dark:text-gray-400 dark:hover:border-indigo-400 dark:hover:text-indigo-300"
      >
        {ICONS[theme]}
      </button>
    </div>
  );
}