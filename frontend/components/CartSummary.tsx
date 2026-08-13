import { CartItem } from "./Chat";

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
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <span>🤖</span>
        <span>Listo. Preparé tu carrito.</span>
      </div>

      {items.length > 0 && (
        <ul className="flex flex-col gap-2">
          {items.map((item, i) => (
            <li key={i} className="flex flex-col gap-0.5 rounded-xl bg-gray-50 px-3 py-2">
              <div className="flex items-center gap-2 text-sm font-medium">
                <span>{getEmoji(item.name)}</span>
                <span>
                  {item.quantity}x {item.name}
                </span>
                {item.price && (
                  <span className="ml-auto text-gray-500 font-normal">
                    {formatPrice(item.price * item.quantity)}
                  </span>
                )}
              </div>
              {item.reason && (
                <p className="text-xs text-gray-400 pl-6">{item.reason}</p>
              )}
            </li>
          ))}
        </ul>
      )}

      {total > 0 && (
        <div className="flex justify-between text-sm font-semibold border-t border-gray-100 pt-2">
          <span>Total estimado</span>
          <span>{formatPrice(total)}</span>
        </div>
      )}

      <a
        href={checkoutUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1 flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
      >
        Continuar con la compra →
      </a>

      <p className="text-xs text-center text-gray-400">
        Revisá los productos y completá el pago directamente en el sitio.
      </p>
    </div>
  );
}
