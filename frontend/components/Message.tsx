interface Props {
  msg: { role: "assistant" | "user" | "status"; text: string; icon?: string };
}

export default function Message({ msg }: Props) {
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-3 text-sm text-white shadow-sm">
          {msg.text}
        </div>
      </div>
    );
  }

  if (msg.role === "status") {
    return (
      <div className="flex items-start gap-2 text-sm text-gray-400 pl-2">
        <span>{msg.icon ?? "🔄"}</span>
        <span>{msg.text}</span>
      </div>
    );
  }

  // assistant
  return (
    <div className="flex items-start gap-2">
      <span className="mt-1 text-lg">🤖</span>
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm bg-white px-4 py-3 text-sm shadow-sm border border-gray-100">
        {msg.text}
      </div>
    </div>
  );
}
