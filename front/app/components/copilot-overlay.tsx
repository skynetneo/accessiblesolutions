// components/landing/copilot-overlay.tsx
"use client";

import { useMemo } from "react";

import { useResources } from "@/lib/hooks/use-resources";
import { GeminiPopup } from "@/components/CopilotkitPopup";

function PopupLauncher() {
  const { hasMore } = useResources();

  const suggestions = useMemo(() => {
    const s = [
      { title: "Find Resources", message: "Find food banks and shelter resources near me." },
      { title: "Build Resume", message: "I need a resume for a warehouse job." },
    ];
    if (hasMore) {
      s.unshift({ title: "Show More Results", message: "Show the next batch of resources on the map." });
    }
    return s;
  }, [hasMore]);

  return (
    <GeminiPopup
      suggestions={suggestions.map((s) => ({
        icon: null,
        label: s.title,
        prompt: s.message,
      }))}
      placeholders={[
        "Find food banks near me",
        "I need wheelchair accessible housing",
        "Help me build a resume",
        "Legal aid for eviction help",
      ]}
    />
  );
}

export default function CopilotOverlay() {
  return <PopupLauncher />;
}
