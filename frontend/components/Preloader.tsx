"use client";

import { useEffect, useRef } from "react";

interface Props {
  label?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

const SIZES = {
  sm: "h-16 w-16",
  md: "h-24 w-24",
  lg: "h-40 w-40",
  xl: "h-56 w-56",
};

export default function Preloader({ label = "Cargando…", size = "md" }: Props) {
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const el = imgRef.current;
    if (!el) return;

    let raf = 0;
    let last = performance.now();

    // Estado actual y objetivo (en px / grados / escala)
    const state = { x: 0, y: 0, r: 0, s: 1 };
    const target = { x: 0, y: 0, r: 0, s: 1 };

    const pickTarget = () => {
      target.x = (Math.random() * 2 - 1) * 14;
      target.y = (Math.random() * 2 - 1) * 20;
      target.r = (Math.random() * 2 - 1) * 6;
      target.s = 0.92 + Math.random() * 0.16;
    };

    pickTarget();

    const tick = (now: number) => {
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;

      // Interpolación suave hacia el objetivo (velocidad variable = "alma")
      // Base baja = movimiento lento y uniforme, decelera al acercarse
      const ease = 1 - Math.pow(0.05, dt);
      state.x += (target.x - state.x) * ease;
      state.y += (target.y - state.y) * ease;
      state.r += (target.r - state.r) * ease;
      state.s += (target.s - state.s) * ease;

      // Cuando está cerca del objetivo, elegir uno nuevo
      const dist = Math.hypot(target.x - state.x, target.y - state.y);
      if (dist < 1.5) pickTarget();

      el.style.transform = `translate(${state.x.toFixed(2)}px, ${state.y.toFixed(2)}px) rotate(${state.r.toFixed(2)}deg) scale(${state.s.toFixed(3)})`;

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className="relative">
        {/* Halo pulsante */}
        <span className="absolute inset-0 -m-2 animate-[graby-pulse-ring_1.6s_ease-out_infinite] rounded-full bg-indigo-500/30 blur-md" />
        {/* Brillo espacial que respira */}
        <span className="absolute inset-0 -m-4 animate-[graby-glow_3.5s_ease-in-out_infinite] rounded-full bg-indigo-400/20 blur-2xl" />
        <img
          ref={imgRef}
          src="/graby-avatar.png"
          alt="Graby"
          draggable={false}
          className={`relative ${SIZES[size]} rounded-full object-cover shadow-lg shadow-indigo-500/30 ring-2 ring-white/70`}
        />
      </div>
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <div className="progress-track w-40">
        <div className="progress-bar" />
      </div>
    </div>
  );
}