interface Props {
  open: boolean;
  monitorEnabled: boolean;
  monitorUrl: string;
  onClose: () => void;
}

export default function MonitorModal({ open, monitorEnabled, monitorUrl, onClose }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-4xl rounded-2xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div className="text-sm font-semibold text-gray-800">Monitoreo del worker</div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
          >
            Cerrar
          </button>
        </div>

        <div className="p-4">
          {!monitorEnabled && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              El monitoreo está desactivado. Activalo antes de enviar el próximo pedido.
            </div>
          )}

          <div className="space-y-3">
            <iframe
              src={monitorUrl}
              title="Monitoreo Playwright en vivo"
              className="h-[65vh] w-full rounded-lg border border-gray-200 bg-black"
              allow="fullscreen"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
