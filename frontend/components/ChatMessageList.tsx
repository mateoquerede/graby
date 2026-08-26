import { ReactNode, RefObject } from "react";
import CartSummary from "./CartSummary";
import Message from "./Message";
import BotAvatar from "./BotAvatar";
import { ChatMessage } from "./Chat.types";

interface Props {
  messages: ChatMessage[];
  busy: boolean;
  bottomRef: RefObject<HTMLDivElement>;
  confirmation?: ReactNode;
}

export default function ChatMessageList({ messages, busy, bottomRef, confirmation }: Props) {
  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
      {messages.map((msg, i) => {
        if (msg.role === "summary") {
          return (
            <CartSummary
              key={i}
              items={msg.items}
              total={msg.total}
              checkoutUrl={msg.checkoutUrl}
            />
          );
        }
        return <Message key={i} msg={msg} />;
      })}
      {confirmation}
      {busy && (
        <div className="msg-enter flex items-center gap-2.5 pl-0.5">
          <BotAvatar size="sm" animate={false} />
          <div className="flex items-center gap-1.5 rounded-full border border-white/70 bg-white px-4 py-3 shadow-sm dark:border-white/10 dark:bg-white/5">
            <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400 dark:bg-indigo-300" />
            <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400 dark:bg-indigo-300" />
            <span className="typing-dot h-2 w-2 rounded-full bg-indigo-400 dark:bg-indigo-300" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
