"use client";

interface Props {
  open: boolean;
  monitorEnabled: boolean;
  monitorUrl: string;
  onClose: () => void;
}

function handleIframeLoad(e: React.SyntheticEvent<HTMLIFrameElement>) {
  try {
    const doc = (e.target as HTMLIFrameElement).contentDocument;
    if (!doc) return;
    const style = doc.createElement("style");
    style.textContent = `
      #top_bar { display: none !important; }
      #sendCtrlAltDelButton { display: none !important; }
      body { margin: 0; background: #000; }
    `;
    doc.head.appendChild(style);
  } catch {
    // cross-origin — noop
  }
}

export default function MonitorModal({ open, monitorEnabled, monitorUrl, onClose }: Props) {
  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex h-[95vh] w-[35vw] max-w-7xl flex-col rounded-2xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
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

        <div className="min-h-0 flex-1 p-4">
          {!monitorEnabled && (
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              El monitoreo está desactivado. Activalo antes de enviar el próximo pedido.
            </div>
          )}

          <div className="relative h-full">
            <iframe
              src={monitorUrl}
              title="Monitoreo del worker"
              className="h-full w-full rounded-lg border border-gray-200 bg-black"
              allow="fullscreen"
              onLoad={handleIframeLoad}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
