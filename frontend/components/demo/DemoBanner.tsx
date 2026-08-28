interface Props {
  onExit: () => void;
}

export default function DemoBanner({ onExit }: Props) {
  return (
    <button
      type="button"
      onClick={onExit}
      title="Salir del modo demo"
      className="msg-enter flex w-full cursor-pointer items-center justify-center gap-2 rounded-xl border border-amber-300/60 bg-amber-50/90 px-3 py-2 text-xs font-semibold text-amber-700 shadow-sm backdrop-blur-md transition-colors hover:bg-amber-100 dark:border-amber-400/30 dark:bg-amber-500/10 dark:text-amber-300 dark:hover:bg-amber-500/20"
    >
      <span>🧪</span>
      <span>Estás usando Graby Demo</span>
      <span className="font-normal text-amber-600/80 dark:text-amber-300/70">
        · Modo demo · No se realizan compras
      </span>
      <span className="ml-1 rounded-md bg-amber-200/70 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-amber-800 dark:bg-amber-400/20 dark:text-amber-200">
        Salir
      </span>
    </button>
  );
}
