export interface CartItem {
  requested: string;
  name: string;
  quantity: number;
  price?: number;
  reason: string;
}

export type NonSummaryMessage =
  | { role: "assistant" | "user"; text: string }
  | { role: "status"; text: string; icon?: string };

export type ChatMessage =
  | NonSummaryMessage
  | { role: "summary"; items: CartItem[]; total: number; checkoutUrl: string };

export type Phase = "credentials" | "prompt" | "working" | "done";
