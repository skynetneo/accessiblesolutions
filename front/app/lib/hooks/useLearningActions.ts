// hooks/useLearningActions.ts
"use client";

import { useEffect, useRef } from "react";
import { useCopilotChat } from "@copilotkit/react-core";

/**
 * Watches the CopilotKit message stream for tool call results from
 * the backend agent and fires the appropriate frontend callbacks.
 *
 * The backend coaching agent calls tools like `award_progress`.
 * These arrive in the message stream as
 * assistant messages with function_call / tool_call content.
 * We scan for them and trigger overlays, toasts, and theme changes.
 *
 * This approach works regardless of CopilotKit version — it doesn't
 * depend on useCopilotAction or useDefaultTool being available.
 */
export function useLearningActions(
    onCelebration: (data: { xp: number; badge?: string }) => void,
    onReinforcement: (xp: number) => void,
) {
    const { visibleMessages } = useCopilotChat();

    // Track which messages we've already processed so we don't
    // fire callbacks twice on re-render
    const processedIds = useRef(new Set<string>());

    useEffect(() => {
        if (!visibleMessages || visibleMessages.length === 0) return;

        for (const msg of visibleMessages) {
            // Skip if we already processed this message
            const msgId = getMessageKey(msg);
            if (processedIds.current.has(msgId)) continue;

            // Look for tool calls in the message content
            const calls = extractToolCalls(msg);
            if (calls.length === 0) continue;

            // Mark as processed
            processedIds.current.add(msgId);

            for (const call of calls) {
                switch (call.name) {
                    case "award_progress": {
                        const xp = toNumber(call.args.xp, 10);
                        const badge = asString(call.args.badge) || undefined;
                        if (badge) {
                            onCelebration({ xp, badge });
                        } else {
                            onReinforcement(xp);
                        }
                        break;
                    }
                    // present_content — no callback needed, CopilotChat
                    // renders the tool result inline. Interactive exercise
                    // components can be wired in here later.
                }
            }
        }
    }, [visibleMessages, onCelebration, onReinforcement]);
}


// ── Helpers ──────────────────────────────────────────────────

interface ToolCall {
    name: string;
    args: Record<string, unknown>;
}

function safeParseJson(value: string, context: string): unknown {
    try {
        return JSON.parse(value);
    } catch (error) {
        console.debug("useLearningActions: failed to parse JSON", { context, error });
        return null;
    }
}

function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === "object" && value !== null;
}

function asString(value: unknown): string {
    return typeof value === "string" ? value : "";
}

function stableSignature(value: unknown): string {
    if (value === undefined) return "";
    if (typeof value === "string") return value;
    try {
        return JSON.stringify(value);
    } catch {
        return String(value);
    }
}

function getMessageKey(msg: unknown): string {
    if (!isRecord(msg)) return "";

    const id = asString(msg.id);
    if (id) return `id:${id}`;

    const role = asString(msg.role);
    const name = asString(msg.name);
    const content = stableSignature(msg.content);
    const functionCall = stableSignature(msg.function_call);
    const toolCalls = stableSignature(msg.tool_calls);

    return [role, name, content, functionCall, toolCalls].join("|");
}

/**
 * Extract tool calls from a CopilotKit message.
 * Messages can have various shapes depending on the SDK version:
 *   - msg.function_call?.name + msg.function_call?.arguments
 *   - msg.tool_calls[]  (array of { name, args })
 *   - msg.content as JSON with tool_calls
 *   - msg.role === "function" with msg.name
 */
function extractToolCalls(msg: unknown): ToolCall[] {
    const calls: ToolCall[] = [];
    if (!isRecord(msg)) return calls;

    // Shape 1: OpenAI-style function_call
    const functionCall = isRecord(msg.function_call) ? msg.function_call : null;
    if (functionCall && asString(functionCall.name)) {
        const rawArguments = functionCall.arguments;
        const parsed = typeof rawArguments === "string"
            ? safeParseJson(rawArguments, "function_call.arguments")
            : rawArguments;
        const args = isRecord(parsed) ? parsed : {};
        calls.push({ name: asString(functionCall.name), args });
    }

    // Shape 2: tool_calls array (newer OpenAI / LangChain format)
    if (Array.isArray(msg.tool_calls)) {
        for (const tc of msg.tool_calls) {
            if (!isRecord(tc)) continue;
            const tcFunction = isRecord(tc.function) ? tc.function : null;
            const name = asString(tc.name) || asString(tcFunction?.name);
            const raw = tc.args ?? tcFunction?.arguments;
            const parsed = typeof raw === "string"
                ? safeParseJson(raw, `tool_calls.${name || "unknown"}.arguments`)
                : raw;
            const args = isRecord(parsed) ? parsed : {};
            if (name) calls.push({ name, args });
        }
    }

    // Shape 3: CopilotKit actionResult in content
    if (typeof msg.content === "string" && msg.content.includes('"actionName"')) {
        const parsed = safeParseJson(msg.content, "message.content.actionName");
        if (isRecord(parsed) && asString(parsed.actionName)) {
            const args = isRecord(parsed.args)
                ? parsed.args
                : isRecord(parsed.parameters)
                    ? parsed.parameters
                    : {};
            calls.push({ name: asString(parsed.actionName), args });
        }
    }

    return calls;
}

function toNumber(val: unknown, fallback: number): number {
    const n = Number(val);
    return isNaN(n) ? fallback : n;
}
