"use client";

import { useState } from "react";

interface Pair {
    id: string;
    left: string;
    right: string;
}

interface MatchPairsProps {
    instruction: string;
    pairs: Pair[];
    onSubmit: (matches: Record<string, string>) => void;
    feedback?: { correct: boolean; corrections?: Record<string, string>; message?: string } | null;
    disabled?: boolean;
}

function stableHash(text: string): number {
    let hash = 0;
    for (let i = 0; i < text.length; i += 1) {
        hash = (hash * 31 + text.charCodeAt(i)) | 0;
    }
    return Math.abs(hash);
}

export function MatchPairs({
    instruction,
    pairs,
    onSubmit,
    feedback = null,
    disabled = false,
}: MatchPairsProps) {
    // Keep a deterministic order across server/client renders.
    const [rightItems] = useState(() =>
        [...pairs]
            .sort((a, b) => {
                const ah = stableHash(`${a.id}:${a.right}`);
                const bh = stableHash(`${b.id}:${b.right}`);
                return ah - bh || a.id.localeCompare(b.id);
            })
            .map((p) => ({ id: p.id, label: p.right }))
    );
    const leftItems = pairs.map((p) => ({ id: p.id, label: p.left }));

    const [selectedLeft, setSelectedLeft] = useState<string | null>(null);
    const [matches, setMatches] = useState<Record<string, string>>({});

    const handleLeftClick = (id: string) => {
        if (disabled || feedback) return;
        setSelectedLeft(id === selectedLeft ? null : id);
    };

    const handleRightClick = (id: string) => {
        if (disabled || feedback || !selectedLeft) return;
        setMatches((prev) => ({ ...prev, [selectedLeft]: id }));
        setSelectedLeft(null);
    };

    const removeMatch = (leftId: string) => {
        if (disabled || feedback) return;
        setMatches((prev) => {
            const copy = { ...prev };
            delete copy[leftId];
            return copy;
        });
    };

    const getMatchedRight = (leftId: string) => matches[leftId];
    const isRightTaken = (rightId: string) => Object.values(matches).includes(rightId);

    const getPairState = (leftId: string): "idle" | "matched" | "correct" | "incorrect" => {
        if (!feedback) return matches[leftId] ? "matched" : "idle";
        if (!matches[leftId]) return "idle";
        if (feedback.corrections && feedback.corrections[leftId]) return "incorrect";
        return "correct";
    };

    const allMatched = Object.keys(matches).length === pairs.length;

    return (
        <div className="mp-container">
            <p className="mp-instruction">{instruction}</p>

            <div className="mp-columns">
                <div className="mp-col">
                    {leftItems.map((item) => {
                        const state = getPairState(item.id);
                        const matched = getMatchedRight(item.id);
                        const matchedLabel = matched
                            ? rightItems.find((r) => r.id === matched)?.label
                            : null;

                        return (
                            <button
                                key={item.id}
                                className={`mp-item mp-left mp-${state} ${selectedLeft === item.id ? "mp-active" : ""}`}
                                onClick={() => matched ? removeMatch(item.id) : handleLeftClick(item.id)}
                                disabled={disabled || !!feedback}
                            >
                                <span className="mp-label">{item.label}</span>
                                {matchedLabel && (
                                    <span className="mp-link">
                                        → {matchedLabel}
                                        {state === "correct" && " ✓"}
                                        {state === "incorrect" && " ✕"}
                                    </span>
                                )}
                            </button>
                        );
                    })}
                </div>

                <div className="mp-col">
                    {rightItems.map((item) => {
                        const taken = isRightTaken(item.id);
                        return (
                            <button
                                key={item.id}
                                className={`mp-item mp-right ${taken ? "mp-taken" : ""} ${selectedLeft && !taken ? "mp-available" : ""}`}
                                onClick={() => handleRightClick(item.id)}
                                disabled={disabled || !!feedback || taken || !selectedLeft}
                            >
                                <span className="mp-label">{item.label}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {!feedback && (
                <button
                    className="mp-submit"
                    onClick={() => onSubmit(matches)}
                    disabled={disabled || !allMatched}
                >
                    Check Matches
                </button>
            )}

            {feedback && (
                <div className={`mp-feedback mp-fb-${feedback.correct ? "correct" : "incorrect"}`}>
                    <span>{feedback.correct ? "🌟" : "💡"}</span>
                    <span>{feedback.message || (feedback.correct ? "All matched!" : "Some pairs need another look.")}</span>
                </div>
            )}

            <style dangerouslySetInnerHTML={{ __html: `
                .mp-container {
                    display: flex; flex-direction: column; gap: 16px;
                    padding: 20px; background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-card);
                    animation: fadeInUp 0.35s ease-out both;
                }
                .mp-instruction { font-size: 16px; line-height: 1.5; font-weight: 500; }
                .mp-columns { display: flex; gap: 16px; }
                .mp-col { flex: 1; display: flex; flex-direction: column; gap: 6px; }
                .mp-item {
                    display: flex; flex-direction: column; gap: 4px;
                    padding: 12px 14px; border: 2px solid var(--color-border);
                    border-radius: var(--radius-md); background: var(--color-bg);
                    font-family: var(--font-body); font-size: 14px;
                    text-align: left; cursor: pointer;
                    transition: all var(--transition-fast);
                }
                .mp-item:hover:not(:disabled):not(.mp-taken) {
                    border-color: var(--color-accent);
                }
                .mp-active { border-color: var(--color-accent) !important; background: var(--color-accent-soft); }
                .mp-available {
                    border-color: var(--color-info);
                    animation: pulse-glow 1.5s ease-in-out infinite;
                }
                .mp-matched { border-color: var(--color-text-muted); background: var(--color-bg-sidebar); }
                .mp-correct { border-color: var(--color-success); background: var(--color-success-soft); }
                .mp-incorrect { border-color: #e74c3c; background: #fde8e8; }
                .mp-taken { opacity: 0.4; cursor: default; }
                .mp-label { font-weight: 500; }
                .mp-link {
                    font-size: 12px; color: var(--color-text-muted); font-weight: 600;
                }
                .mp-correct .mp-link { color: var(--color-success); }
                .mp-incorrect .mp-link { color: #e74c3c; }
                .mp-submit {
                    align-self: flex-start; padding: 10px 24px;
                    background: var(--color-accent); color: white; border: none;
                    border-radius: var(--radius-md); font-family: var(--font-body);
                    font-size: 14px; font-weight: 600; cursor: pointer;
                    transition: all var(--transition-fast);
                }
                .mp-submit:hover:not(:disabled) { filter: brightness(1.1); transform: translateY(-1px); }
                .mp-submit:disabled { opacity: 0.4; cursor: not-allowed; }
                .mp-feedback {
                    display: flex; align-items: flex-start; gap: 8px;
                    padding: 12px 14px; border-radius: var(--radius-md);
                    font-size: 14px; animation: fadeInUp 0.3s ease-out both;
                }
                .mp-fb-correct { background: var(--color-success-soft); color: var(--color-success); }
                .mp-fb-incorrect { background: var(--color-warn-soft); color: var(--color-text); }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes pulse-glow {
                    0%, 100% { box-shadow: 0 0 0 0 rgba(74, 127, 165, 0.25); }
                    50% { box-shadow: 0 0 0 6px rgba(74, 127, 165, 0); }
                }
            `}} />
        </div>
    );
}
