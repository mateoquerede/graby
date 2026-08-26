interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
  animate?: boolean;
}

const SIZES = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-14 w-14",
};

export default function BotAvatar({ size = "md", className = "", animate = true }: Props) {
  return (
    <div
      className={`relative flex ${SIZES[size]} shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500 shadow-lg shadow-indigo-500/30 ring-2 ring-white/70 ${className}`}
    >
      {/* Ojos que parpadean */}
      <span
        className={`absolute h-[6px] w-[6px] rounded-full bg-white ${size === "sm" ? "text-[4px]" : ""}`}
        style={{ top: size === "sm" ? "32%" : "34%", left: "34%" }}
      />
      <span
        className="absolute h-[6px] w-[6px] rounded-full bg-white"
        style={{ top: size === "sm" ? "32%" : "34%", right: "34%" }}
      />
      {/* Sonrisa */}
      <svg viewBox="0 0 40 20" className="absolute h-[28%] w-[60%] text-white" style={{ top: "52%" }} fill="none">
        <path
          d="M6 4 Q 20 18 34 4"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          fill="none"
          className={animate ? "animate-[graby-smile_3s_ease-in-out_infinite]" : ""}
        />
      </svg>
      {/* Cabello / antena */}
      <svg viewBox="0 0 24 24" className="absolute -top-2 h-4 w-4 text-indigo-300" fill="currentColor">
        <path d="M12 0 a2 2 0 1 1-2 2 a1 1 0 0 0 .5-.9 A2 2 0 0 1 12 0Z" />
      </svg>
    </div>
  );
}