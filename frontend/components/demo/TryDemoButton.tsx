interface Props {
  onClick: () => void;
}

export default function TryDemoButton({ onClick }: Props) {
  return (
    <div className="msg-enter flex items-center gap-3 rounded-2xl border-2 border-dashed border-indigo-300/70 bg-gradient-to-r from-indigo-50/80 to-fuchsia-50/80 p-3 shadow-sm backdrop-blur-md dark:border-indigo-500/40 dark:from-indigo-500/10 dark:to-fuchsia-500/10">
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-xl text-white shadow-md shadow-indigo-500/20">
        🚀
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-gray-800 dark:text-gray-100">¿Sin cuenta? Probá la demo</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Experiencia real con datos de ejemplo, sin compras ni registro.
        </p>
      </div>
      <button
        type="button"
        onClick={onClick}
        className="shrink-0 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.03] hover:from-indigo-700 hover:to-violet-700"
      >
        Probar la demo
      </button>
    </div>
  );
}
