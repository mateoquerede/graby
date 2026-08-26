import { NonSummaryMessage } from "./Chat.types";
import BotAvatar from "./BotAvatar";

interface Props {
  msg: NonSummaryMessage;
}

export default function Message({ msg }: Props) {
  if (msg.role === "user") {
    return (
      <div className="msg-enter flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-gradient-to-br from-indigo-500 to-violet-600 px-4 py-3 text-sm text-white shadow-md shadow-indigo-500/20">
          {msg.text}
        </div>
      </div>
    );
  }

  if (msg.role === "status") {
    return (
      <div className="msg-enter ml-2 flex items-start gap-2 text-sm text-gray-500 dark:text-gray-400">
        <span className="mt-px flex h-5 w-5 items-center justify-center rounded-full bg-indigo-50 text-[11px] dark:bg-indigo-500/15">
          {msg.icon ?? "🔄"}
        </span>
        <span>{msg.text}</span>
      </div>
    );
  }

  // assistant
  return (
    <div className="msg-enter flex items-start gap-2.5">
      <BotAvatar size="sm" />
      <div className="max-w-[80%] rounded-2xl rounded-bl-sm border border-white/70 bg-white px-4 py-3 text-sm text-gray-700 shadow-sm dark:border-white/10 dark:bg-white/5 dark:text-gray-200">
        {msg.text}
      </div>
    </div>
  );
}
