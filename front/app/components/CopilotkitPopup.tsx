"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useCopilotChatInternal } from "@copilotkit/react-core";
import { AlertCircle, History, Loader2, Maximize2, Minimize2, Sparkles, X } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { ShootingStars } from "@/components/ui/shooting-stars";
import { StarsBackground } from "@/components/ui/stars-background";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";
import { COPILOT_ROLE, createCopilotTextMessage, toCopilotTextMessage } from "@/lib/copilot-messages";
import { useResources } from "@/lib/hooks/use-resources";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type GeminiSuggestion = {
  icon: React.ReactElement | null;
  label: string;
  prompt: string;
};

type GeminiPopupProps = {
  suggestions?: GeminiSuggestion[];
  placeholders?: string[];
};

const RESOURCE_KEYWORDS =
  /(near me|nearby|local|food|pantry|pantries|shelter|housing|eviction|legal|aid|resource|resources|clinic|medical|support|dv|domestic)/i;

const SOL_GREETING =
  "Great to meet you. I can help you find food, housing, health care, legal aid, job support, and other local resources. Tell me what you need, and I will help you get there.";

export function GeminiPopup({ suggestions = [], placeholders = [] }: GeminiPopupProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [draft, setDraft] = useState("");
  const [sendError, setSendError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const {
    messages: aguiMessages,
    visibleMessages: legacyVisibleMessages,
    sendMessage,
    isAvailable,
    isLoading,
  } = useCopilotChatInternal();
  const { requestLocation, userLocation } = useResources();

  const visibleMessages = Array.isArray(aguiMessages) && aguiMessages.length > 0
    ? aguiMessages
    : Array.isArray(legacyVisibleMessages)
      ? legacyVisibleMessages
      : [];
  const displayMessages = visibleMessages.map(toCopilotTextMessage).filter((msg) => msg !== null);
  const isChatEmpty = displayMessages.length === 0;
  const canInteract = !isLoading;

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const sendText = useCallback(
    async (text: string): Promise<boolean> => {
      const trimmed = text.trim();
      if (!trimmed) return false;
      if (!isAvailable) {
        setSendError("Assistant is not connected. Start the AccessFyndr agent and try again.");
        return false;
      }
      if (isLoading) {
        setSendError("Wait for the current assistant response to finish before sending another message.");
        return false;
      }

      setSendError(null);

      let content = trimmed;
      if (RESOURCE_KEYWORDS.test(trimmed) && !/lat=|lng=|longitude|latitude/i.test(trimmed)) {
        const location = userLocation ?? (await requestLocation());
        if (location) {
          const base = trimmed.endsWith(".") ? trimmed : `${trimmed}.`;
          content = `${base} My location coordinates: lat=${location.latitude}, lng=${location.longitude}.`;
        }
      }

      try {
        await sendMessage(createCopilotTextMessage(COPILOT_ROLE.user, content));
        return true;
      } catch (error) {
        if (mountedRef.current) {
          setSendError(error instanceof Error ? error.message : "Could not send your message.");
        }
        return false;
      }
    },
    [sendMessage, isAvailable, isLoading, requestLocation, userLocation]
  );

  const handleVanishSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const submitted = draft;
    void sendText(submitted).then((sent) => {
      if (sent && mountedRef.current) setDraft("");
    });
  };

  const sendQuickAction = (text: string) => {
    void sendText(text);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full border border-white/15 bg-[#1e1f20] text-white shadow-2xl shadow-black/30 transition-all hover:bg-[#2e2f30]"
        aria-label="Open assistant"
      >
        <Sparkles className="w-6 h-6 text-[#c48df6]" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        "fixed text-gray-200 flex flex-col overflow-hidden font-sans transition-all duration-300 ease-in-out z-50",
        isExpanded
          ? "inset-0 w-full h-full rounded-none border-none"
          : "bottom-5 right-5 h-[min(38rem,calc(100dvh-6rem))] w-[min(26rem,calc(100vw-2.5rem))] rounded-[1.75rem] border border-white/10"
      )}
      style={{
        background: "rgba(8, 6, 14, 0.60)",
        boxShadow: "0 30px 90px rgba(0,0,0,0.55)",
        backdropFilter: "blur(14px)",
      }}
    >
      <div className="pointer-events-none absolute inset-0">
        <StarsBackground
          className="absolute inset-0 opacity-90"
          density={0.0001}
          minStars={1}
          maxStars={6}
          colors={[[255, 255, 255]]}
          meteorRate={0.6}
          drift={0.01}
          twinkle={0.08}
          interactive={false}
          staggerAppearMs={70}
          appearFadeMs={550}
        />
        <ShootingStars
          className="opacity-80"
          minSpeed={2}
          maxSpeed={6}
          minDelay={7500}
          maxDelay={18000}
          starColor="#ffffff"
          trailColor="#c48df6"
          starWidth={30}
          starHeight={1.5}
        />
      </div>

      <div className="flex items-center justify-between px-6 py-4 bg-transparent z-10 shrink-0">
        <div className="flex items-center gap-2 text-[#e3e3e3] font-medium text-lg">
          Sol
        </div>
        <div className="flex items-center gap-4 text-gray-400">
          <button className="hover:text-white transition" aria-label="History">
            <History className="w-5 h-5" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="hover:text-white transition"
            aria-label={isExpanded ? "Minimize" : "Maximize"}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="hover:text-white transition"
            aria-label="Close"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      <div className={cn("flex-1 flex flex-col overflow-hidden", isExpanded && "max-w-5xl w-full mx-auto")}>
        <div className="flex-1 overflow-y-auto p-4 scrollbar-hide relative w-full">
          {isChatEmpty ? (
            <div className="h-full flex flex-col items-start justify-start px-4 pt-6 animate-in fade-in zoom-in duration-300">
              <div className="w-full rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-xl shadow-black/15">
                <Sparkles className="mb-3 h-5 w-5 text-[#c48df6]" />
                <h1 className="mb-2 text-2xl font-semibold text-white">Hi, I&apos;m Sol.</h1>
                <p className="text-sm leading-relaxed text-gray-200">{SOL_GREETING}</p>
              </div>
              <div className="flex flex-wrap justify-start gap-2 w-full pb-2 mt-5">
                {suggestions.map((s) => (
                  <SuggestionChip
                    key={s.label}
                    icon={s.icon}
                    label={s.label}
                    onClick={() => sendQuickAction(s.prompt)}
                    disabled={!canInteract}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-6 pb-4">
              {displayMessages.map((msg, idx) => {
                const isUser = msg.role === COPILOT_ROLE.user;
                return (
                  <div key={msg.id ?? idx} className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
                    <div
                      className={cn(
                        "p-4 rounded-2xl max-w-[85%] text-sm leading-relaxed",
                        isUser
                          ? "bg-white/10 text-white border border-white/10"
                          : "max-w-[92%] bg-white/[0.04] text-gray-100 border border-white/10 shadow-xl shadow-black/15"
                      )}
                    >
                      {!isUser && <Sparkles className="w-5 h-5 text-[#c48df6] mb-2" />}
                      <MessageContent content={msg.content} isUser={isUser} />
                    </div>
                  </div>
                );
              })}
              {isLoading && (
                <div className="inline-flex items-center gap-2 text-gray-400 text-sm pl-1">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Thinking...
                </div>
              )}
            </div>
          )}
        </div>

        <div className="p-4 bg-transparent w-full mt-auto">
          <PlaceholdersAndVanishInput
            className="bg-white/5 border border-white/15 focus-within:border-[#c48df6]/40 focus-within:bg-white/10"
            inputClassName="text-white"
            buttonClassName="bg-white/90 disabled:bg-white/10"
            placeholderClassName="text-white/40"
            placeholders={
              placeholders.length
                ? placeholders
                : [
                    "Where can I get help with housing?",
                    "Help me create a resume",
                    "Who helps people leave DV situations?",
                    "Where are the clothing closets near me?",
                  ]
            }
            onChange={(e) => setDraft(e.target.value)}
            onSubmit={handleVanishSubmit}
            disabled={!canInteract}
          />
          {sendError ? (
            <p className="mx-auto mt-2 flex max-w-xl items-center gap-2 text-xs text-red-200" role="alert">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" />
              {sendError}
            </p>
          ) : !isAvailable ? (
            <p className="mx-auto mt-2 max-w-xl text-xs text-white/45">
              Connecting to AccessAI...
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function SuggestionChip({
  icon,
  label,
  onClick,
  disabled = false,
}: {
  icon: React.ReactElement | null;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  const hasIcon = Boolean(icon);
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn(
        "inline-flex w-auto items-center justify-center bg-transparent hover:bg-white/5 text-[#c48df6] px-4 py-2 rounded-full whitespace-nowrap transition-colors border border-white/15 hover:border-white/25",
        hasIcon ? "gap-2" : "gap-0",
        disabled && "cursor-not-allowed opacity-50 hover:bg-transparent hover:border-white/15"
      )}
    >
      {icon ? <div className="w-5 h-5 text-gray-400">{icon}</div> : null}
      <span className="text-gray-200 text-sm font-medium leading-none">{label}</span>
    </button>
  );
}

function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  if (isUser) {
    return <p className="whitespace-pre-wrap">{cleanUserContent(content)}</p>;
  }

  return <AssistantMarkdown content={content} />;
}

function AssistantMarkdown({ content }: { content: string }) {
  const lines = normalizeAssistantContent(content)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (!lines.length) return null;

  const blocks: React.ReactNode[] = [];

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];

    if (line === "---") {
      blocks.push(<div key={`hr-${i}`} className="h-px bg-white/10" />);
      continue;
    }

    const h2Match = line.match(/^##\s+(.+)$/);
    if (h2Match) {
      blocks.push(
        <h2 key={`h2-${i}`} className="pt-1 text-base font-semibold text-white">
          {renderInline(h2Match[1])}
        </h2>
      );
      continue;
    }

    const h3Match = line.match(/^#{3,4}\s+(.+)$/);
    if (h3Match) {
      const detailLines: string[] = [];
      let cursor = i + 1;
      while (cursor < lines.length && !/^(#{1,4}\s+|---$)/.test(lines[cursor])) {
        detailLines.push(lines[cursor]);
        cursor += 1;
      }
      blocks.push(
        <ResourceCard key={`card-${i}`} title={h3Match[1]} lines={detailLines} />
      );
      i = cursor - 1;
      continue;
    }

    const h1Match = line.match(/^#\s+(.+)$/);
    if (h1Match) {
      blocks.push(
        <h1 key={`h1-${i}`} className="text-lg font-semibold text-white">
          {renderInline(h1Match[1])}
        </h1>
      );
      continue;
    }

    if (line.startsWith(">")) {
      blocks.push(
        <div key={`quote-${i}`} className="rounded-xl border border-amber-300/20 bg-amber-300/10 p-3 text-sm text-amber-50">
          {renderInline(line.replace(/^>\s*/, ""))}
        </div>
      );
      continue;
    }

    const orderedMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (orderedMatch) {
      blocks.push(
        <div key={`ordered-${i}`} className="flex gap-2 text-gray-200">
          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#c48df6]/20 text-xs font-semibold text-[#d8b6ff]">
            {orderedMatch[1]}
          </span>
          <p>{renderInline(orderedMatch[2])}</p>
        </div>
      );
      continue;
    }

    if (line.startsWith("- ")) {
      blocks.push(
        <div key={`bullet-${i}`} className="flex gap-2 text-gray-200">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#c48df6]" />
          <p>{renderInline(line.slice(2))}</p>
        </div>
      );
      continue;
    }

    blocks.push(
      <p key={`p-${i}`} className="text-gray-200">
        {renderInline(line)}
      </p>
    );
  }

  return <div className="space-y-3">{blocks}</div>;
}

function ResourceCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.05] p-3">
      <h3 className="mb-2 font-semibold text-white">{renderInline(title)}</h3>
      {lines.length ? (
        <div className="space-y-2 text-gray-200">
          {lines.map((line, index) => {
            const cleanedLine = line.replace(/^[-*]\s+/, "");
            return (
              <div key={`${title}-${index}`} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#4f86f7]" />
                <p>{renderInline(cleanedLine)}</p>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

function renderInline(text: string) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((segment, index) => {
    if (segment.startsWith("**") && segment.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-white">
          {segment.slice(2, -2)}
        </strong>
      );
    }
    return segment.replace(/\*([^*]+)\*/g, "$1");
  });
}

function normalizeAssistantContent(content: string) {
  return content
    .replace(/\s*App Context:\s*\[[\s\S]*$/i, "")
    .replace(/^\s*NAVIGATE_TO:.*$/gim, "")
    .replace(/RESUME_DRAFT_START\s*/gi, "")
    .replace(/\s*RESUME_DRAFT_END/gi, "")
    .replace(/\s+---\s+/g, "\n---\n")
    .replace(/\s+(#{1,4}\s+)/g, "\n$1")
    .replace(/\s+(-\s+\*\*[^*]+:\*\*)/g, "\n$1")
    .replace(/\s+(-\s+[A-Z][^:]{2,35}:)/g, "\n$1")
    .replace(/\s+(\d+\.\s+)/g, "\n$1")
    .replace(/\s+(>\s+)/g, "\n$1")
    .trim();
}

function cleanUserContent(content: string) {
  return content
    .replace(/\s*My location coordinates:\s*lat=-?\d+(?:\.\d+)?,\s*lng=-?\d+(?:\.\d+)?\.?\s*$/i, "")
    .trim();
}
