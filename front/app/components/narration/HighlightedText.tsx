"use client";

import { useMemo } from "react";
import { useNarration, type WordTiming } from "./NarrationPlayer";

// ── Types ────────────────────────────────────────────────────

interface HighlightedTextProps {
    chunks: Array<{
        text: string;
        word_timings: WordTiming[];
        highlight?: string;
    }>;
    variant?: "glow" | "underline" | "fill" | "minimal";
    showAll?: boolean;
    className?: string;
}

// ── Component ────────────────────────────────────────────────

export function HighlightedText({
    chunks,
    variant = "glow",
    showAll = true,
    className = "",
}: HighlightedTextProps) {
    const { currentChunk, currentWord, state } = useNarration();
    const isActive = state === "playing" || state === "paused";

    return (
        <div className={`ht-container ${className}`}>
            {chunks.map((chunk, chunkIdx) => {
                const isCurrentChunk = chunkIdx === currentChunk;
                const isPast = chunkIdx < currentChunk;
                const isFuture = chunkIdx > currentChunk;

                if (!showAll && !isCurrentChunk) return null;

                return (
                    <span
                        key={chunkIdx}
                        className={`ht-chunk${isPast ? " ht-past" : ""}${isFuture ? " ht-future" : ""}`}
                    >
                        <ChunkWords
                            words={chunk.word_timings}
                            keyTerm={chunk.highlight}
                            isCurrentChunk={isCurrentChunk && isActive}
                            currentWord={isCurrentChunk ? currentWord : -1}
                            variant={variant}
                        />
                        {chunkIdx < chunks.length - 1 && " "}
                    </span>
                );
            })}
        </div>
    );
}

// ── Word-level rendering ─────────────────────────────────────

interface ChunkWordsProps {
    words: WordTiming[];
    keyTerm?: string;
    isCurrentChunk: boolean;
    currentWord: number;
    variant: "glow" | "underline" | "fill" | "minimal";
}

function ChunkWords({
    words,
    keyTerm,
    isCurrentChunk,
    currentWord,
    variant,
}: ChunkWordsProps) {
    const keyTermIndices = useMemo(() => {
        if (!keyTerm) return new Set<number>();
        const lower = keyTerm.toLowerCase();
        const indices = new Set<number>();
        const wordTexts = words.map((w) =>
            w.word.toLowerCase().replace(/[^a-z0-9]/g, ""),
        );

        const keyWords = lower.split(/\s+/);
        for (let i = 0; i <= wordTexts.length - keyWords.length; i++) {
            let match = true;
            for (let j = 0; j < keyWords.length; j++) {
                if (!wordTexts[i + j].includes(keyWords[j])) {
                    match = false;
                    break;
                }
            }
            if (match) {
                for (let j = 0; j < keyWords.length; j++) indices.add(i + j);
            }
        }
        return indices;
    }, [words, keyTerm]);

    return (
        <>
            {words.map((timing, wordIdx) => {
                const isCurrent = isCurrentChunk && wordIdx === currentWord;
                const isSpoken = isCurrentChunk && wordIdx <= currentWord;
                const isKeyTerm = keyTermIndices.has(wordIdx);

                const cls = [
                    "ht-word",
                    `ht-${variant}`,
                    isCurrent ? "ht-active" : "",
                    isSpoken ? "ht-spoken" : "",
                    isKeyTerm ? "ht-key" : "",
                ]
                    .filter(Boolean)
                    .join(" ");

                return (
                    <span key={wordIdx} className={cls}>
                        {timing.word}
                        {wordIdx < words.length - 1 ? " " : ""}
                    </span>
                );
            })}
        </>
    );
}
