"use client";

export const COPILOT_ROLE = {
  assistant: "assistant",
  user: "user",
} as const;

type CopilotRole = (typeof COPILOT_ROLE)[keyof typeof COPILOT_ROLE];

type CopilotTextMessage = {
  id: string;
  role: CopilotRole;
  content: string;
};

export type CopilotDisplayMessage = {
  id?: string;
  role: string;
  content: string;
};

export function createCopilotTextMessage(role: CopilotRole, content: string): CopilotTextMessage {
  return {
    id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`,
    role,
    content,
  };
}

export function toCopilotTextMessage(message: unknown): CopilotDisplayMessage | null {
  if (!message || typeof message !== "object") return null;

  const candidate = message as {
    id?: unknown;
    role?: unknown;
    content?: unknown;
    text?: unknown;
    isTextMessage?: unknown;
  };

  if (
    typeof candidate.isTextMessage === "function"
    && !candidate.isTextMessage.call(candidate)
  ) {
    return null;
  }

  const role = typeof candidate.role === "string" ? candidate.role.toLowerCase() : "";
  const content = getTextContent(candidate.content ?? candidate.text);

  if (!role || !content) return null;

  return {
    id: typeof candidate.id === "string" ? candidate.id : undefined,
    role,
    content,
  };
}

function getTextContent(content: unknown): string {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";

  return content
    .map((part) => {
      if (typeof part === "string") return part;
      if (part && typeof part === "object" && "text" in part) {
        const text = (part as { text?: unknown }).text;
        return typeof text === "string" ? text : "";
      }
      return "";
    })
    .join("");
}
