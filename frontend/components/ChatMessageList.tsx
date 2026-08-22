import { ReactNode, RefObject } from "react";
import CartSummary from "./CartSummary";
import Message from "./Message";
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
        <div className="flex items-center gap-2 text-sm text-gray-400 pl-2">
          <span className="animate-spin">⏳</span>
          <span>Graby está trabajando...</span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
