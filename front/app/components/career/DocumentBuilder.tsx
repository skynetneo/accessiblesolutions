"use client";

import { useEffect, useRef, useState } from "react";
import { CopilotTextarea } from "@copilotkit/react-textarea";
import "@copilotkit/react-textarea/styles.css";
import { useResources } from "@/lib/hooks/use-resources";

export function DocumentBuilder() {
    const { resumeMarkdown } = useResources();
    const [text, setText] = useState("");
    const [docType, setDocType] = useState<"resume" | "cover_letter">("resume");
    const lastLoadedResumeRef = useRef("");

    useEffect(() => {
        if (!resumeMarkdown || resumeMarkdown === lastLoadedResumeRef.current) return;
        lastLoadedResumeRef.current = resumeMarkdown;
        setDocType("resume");
        setText(resumeMarkdown);
    }, [resumeMarkdown]);

    return (
        <div className="flex flex-col h-full bg-[var(--glass-surface)] rounded-xl border border-[rgba(255,255,255,0.06)] shadow-lg overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-[rgba(255,255,255,0.06)] bg-[var(--color-bg-card)]">
                <div>
                    <h2 className="text-xl font-bold font-[var(--font-display)] text-[var(--color-text)]">
                        Career Prep Workspace
                    </h2>
                    <p className="text-sm text-[var(--color-text-secondary)]">
                        AI-assisted document generation. Start typing or ask the AI to flesh out your points.
                    </p>
                </div>
                <div className="flex bg-[rgba(255,255,255,0.05)] rounded-lg p-1 border border-[rgba(255,255,255,0.1)]">
                    <button
                        onClick={() => setDocType("resume")}
                        className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${
                            docType === "resume" 
                                ? "bg-[var(--color-accent)] text-white shadow" 
                                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                        }`}
                    >
                        Resume
                    </button>
                    <button
                        onClick={() => setDocType("cover_letter")}
                        className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors ${
                            docType === "cover_letter" 
                                ? "bg-[var(--color-accent)] text-white shadow" 
                                : "text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
                        }`}
                    >
                        Cover Letter
                    </button>
                </div>
            </div>

            <div className="flex-1 p-6 flex flex-col relative w-full h-full min-h-[500px]">
                {/* CopilotTextarea handles the AI auto-completions magically via CopilotKit context */}
                <CopilotTextarea
                    className="w-full h-full p-4 bg-transparent outline-none resize-none 
                               text-[var(--color-text)] font-sans text-base leading-relaxed
                               placeholder-[var(--color-text-muted)]"
                    placeholder={`Start writing your ${
                        docType === "resume" ? "resume bullet points" : "cover letter"
                    } here...\n\n(Tip: Type a few words and pause to let the AI suggest completions, or use Cmd+K / Ctrl+K for inline AI instructions.)`}
                    value={text}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setText(e.target.value)}
                    autosuggestionsConfig={{
                        textareaPurpose: `You are helping the user write a professional ${
                            docType === "resume" ? "resume" : "cover letter"
                        }. Use active verbs and highlight quantifiable achievements. Keep the tone modern and professional.`,
                        chatApiConfigs: {
                            suggestionsApiConfig: {
                                maxTokens: 50,
                                stop: ["\n", ".", ","],
                            },
                        },
                    }}
                />
            </div>
            
            <div className="p-4 border-t border-[rgba(255,255,255,0.06)] bg-[var(--color-bg-card)] flex justify-between items-center text-xs text-[var(--color-text-muted)]">
                <span>Use <kbd className="font-mono bg-[rgba(255,255,255,0.1)] px-1.5 py-0.5 rounded text-[var(--color-text)]">Cmd+K</kbd> / <kbd className="font-mono bg-[rgba(255,255,255,0.1)] px-1.5 py-0.5 rounded text-[var(--color-text)]">Ctrl+K</kbd> to ask Copilot for specific edits or rewrites.</span>
                <span>{text.split(/\s+/).filter(w => w.length > 0).length} words</span>
            </div>
        </div>
    );
}
