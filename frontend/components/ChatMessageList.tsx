import { ReactNode, RefObject } from "react";
import CartSummary from "./CartSummary";
import Message from "./Message";
import { ChatMessage } from "./Chat.types";

interface Props {
  messages: ChatMessage[];
  bottomRef: RefObject<HTMLDivElement>;
  confirmation?: ReactNode;
}

export default function ChatMessageList({ messages, bottomRef, confirmation }: Props) {
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
      <div ref={bottomRef} />
    </div>
  );
}
