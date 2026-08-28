"use client";

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
  return (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className="relative">
        {/* Halo pulsante */}
        <span className="absolute inset-0 -m-2 animate-[graby-pulse-ring_1.6s_ease-out_infinite] rounded-full bg-indigo-500/30 blur-md" />
        <img
          src="/graby-avatar.png"
          alt="Graby"
          draggable={false}
          className={`relative ${SIZES[size]} animate-[graby-float_3.5s_ease-in-out_infinite] rounded-full object-cover shadow-lg shadow-indigo-500/30 ring-2 ring-white/70`}
        />
      </div>
      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
      <div className="progress-track w-40">
        <div className="progress-bar" />
      </div>
    </div>
  );
}