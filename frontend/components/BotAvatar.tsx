interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
  animate?: boolean;
}

const SIZES = {
  sm: "h-9 w-9",
  md: "h-12 w-12",
  lg: "h-16 w-16",
};

const MARGIN = {
  sm: "m-1.5",
  md: "m-1",
  lg: "m-1",
};

export default function BotAvatar({ size = "md", className = "", animate = true }: Props) {
  return (
    <div
      className={`relative flex ${SIZES[size]} shrink-0 items-center justify-center rounded-full shadow-lg shadow-indigo-500/30 ring-2 ring-white/70 ${MARGIN[size]} ${className}`}
    >
      <img
        src="/graby-avatar.png"
        alt="Graby"
        draggable={false}
        className="h-full w-full object-contain"
      />
    </div>
  );
}