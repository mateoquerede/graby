import { CartItem } from "./Chat.types";

interface Props {
  items: CartItem[];
  total: number;
  checkoutUrl: string;
}

const PRODUCT_EMOJI: Record<string, string> = {
  leche: "🥛",
  huevo: "🥚",
  pan: "🍞",
  carne: "🥩",
  pollo: "🍗",
  arroz: "🍚",
  pasta: "🍝",
  aceite: "🫙",
  cafe: "☕",
  azucar: "🧂",
  harina: "🌾",
};

function getEmoji(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, emoji] of Object.entries(PRODUCT_EMOJI)) {
    if (lower.includes(key)) return emoji;
  }
  return "🛒";
}

function formatPrice(n?: number): string {
  if (!n) return "";
  return `$${n.toLocaleString("es-AR")}`;
}

export default function CartSummary({ items, total, checkoutUrl }: Props) {
  return (
    <div className="msg-enter overflow-hidden rounded-2xl border border-white/70 bg-white shadow-lg shadow-indigo-500/10 dark:border-white/10 dark:bg-white/5">
      {/* Header con gradiente */}
      <div className="flex items-center gap-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-white">
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/25 text-lg">🛒</span>
        <div>
          <p className="text-sm font-bold">¡Listo! Preparé tu carrito</p>
          <p className="text-xs text-white/85">Revisá los productos y completá el pago en la tienda</p>
        </div>
      </div>

      {items.length > 0 && (
        <ul className="flex flex-col gap-2 p-4">
          {items.map((item, i) => (
            <li key={i} className="flex flex-col gap-0.5 rounded-xl border border-gray-100 bg-gray-50/60 px-3 py-2.5 transition-colors hover:bg-gray-50 dark:border-white/5 dark:bg-white/[0.03] dark:hover:bg-white/[0.06]">
              <div className="flex items-center gap-2 text-sm font-medium text-gray-800 dark:text-gray-100">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-base shadow-sm dark:bg-white/10">
                  {getEmoji(item.name)}
                </span>
                <span className="flex items-center gap-1.5">
                  <span>
                    {item.quantity}x {item.name}
                  </span>
                </span>
                {item.price && (
                  <span className="ml-auto font-semibold text-gray-700 dark:text-gray-200">
                    {formatPrice(item.price * item.quantity)}
                  </span>
                )}
              </div>
              {item.reason && (
                <p className="pl-10 text-xs text-gray-400 dark:text-gray-500">{item.reason}</p>
              )}
            </li>
          ))}
        </ul>
      )}

      {total > 0 && (
        <div className="mx-4 flex justify-between rounded-xl bg-gradient-to-r from-indigo-50 to-fuchsia-50 px-4 py-3 text-sm font-bold text-gray-900 ring-1 ring-indigo-100 dark:from-indigo-500/10 dark:to-fuchsia-500/10 dark:text-gray-100 dark:ring-indigo-400/20">
          <span>Total estimado</span>
          <span className="text-indigo-700 dark:text-indigo-300">{formatPrice(total)}</span>
        </div>
      )}

      <div className="p-4 pt-2">
        <a
          href={checkoutUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 py-3 text-sm font-semibold text-white shadow-sm transition-transform hover:scale-[1.01] hover:from-indigo-700 hover:to-violet-700"
        >
          Continuar con la compra
          <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
        <p className="mt-2 text-center text-xs text-gray-400 dark:text-gray-500">
          Revisá los productos y completá el pago directamente en el sitio.
        </p>
      </div>
    </div>
  );
}
