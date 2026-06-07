"use client";

import { useState, useRef } from "react";

interface DragSortProps {
    instruction: string;
    items: { id: string; label: string }[];
    onSubmit: (orderedIds: string[]) => void;
    feedback?: { correct: boolean; correctOrder?: string[]; message?: string } | null;
    disabled?: boolean;
}

export function DragSort({
    instruction,
    items: initialItems,
    onSubmit,
    feedback = null,
    disabled = false,
}: DragSortProps) {
    const [items, setItems] = useState(initialItems);
    const dragItem = useRef<number | null>(null);
    const dragOver = useRef<number | null>(null);

    const handleDragStart = (idx: number) => {
        if (disabled || feedback) return;
        dragItem.current = idx;
    };

    const handleDragEnter = (idx: number) => {
        if (disabled || feedback) return;
        dragOver.current = idx;
    };

    const handleDragEnd = () => {
        if (dragItem.current === null || dragOver.current === null) return;
        const copy = [...items];
        const dragged = copy.splice(dragItem.current, 1)[0];
        copy.splice(dragOver.current, 0, dragged);
        setItems(copy);
        dragItem.current = null;
        dragOver.current = null;
    };

    const moveItem = (idx: number, dir: -1 | 1) => {
        if (disabled || feedback) return;
        const target = idx + dir;
        if (target < 0 || target >= items.length) return;
        const copy = [...items];
        [copy[idx], copy[target]] = [copy[target], copy[idx]];
        setItems(copy);
    };

    const getItemState = (id: string, idx: number) => {
        if (!feedback) return "idle";
        if (!feedback.correctOrder) return feedback.correct ? "correct" : "incorrect";
        return feedback.correctOrder[idx] === id ? "correct" : "incorrect";
    };

    return (
        <div className="ds-container">
            <p className="ds-instruction">{instruction}</p>

            <div className="ds-list">
                {items.map((item, i) => {
                    const state = getItemState(item.id, i);
                    return (
                        <div
                            key={item.id}
                            className={`ds-item ds-${state}`}
                            draggable={!disabled && !feedback}
                            onDragStart={() => handleDragStart(i)}
                            onDragEnter={() => handleDragEnter(i)}
                            onDragEnd={handleDragEnd}
                            onDragOver={(e) => e.preventDefault()}
                            style={{ animationDelay: `${i * 50}ms` }}
                        >
                            <span className="ds-grip">⠿</span>
                            <span className="ds-num">{i + 1}</span>
                            <span className="ds-label">{item.label}</span>
                            {!feedback && !disabled && (
                                <span className="ds-arrows">
                                    <button
                                        onClick={() => moveItem(i, -1)}
                                        disabled={i === 0}
                                        aria-label="Move up"
                                    >↑</button>
                                    <button
                                        onClick={() => moveItem(i, 1)}
                                        disabled={i === items.length - 1}
                                        aria-label="Move down"
                                    >↓</button>
                                </span>
                            )}
                            {state === "correct" && <span className="ds-icon">✓</span>}
                            {state === "incorrect" && <span className="ds-icon">✕</span>}
                        </div>
                    );
                })}
            </div>

            {!feedback && (
                <button
                    className="ds-submit"
                    onClick={() => onSubmit(items.map((it) => it.id))}
                    disabled={disabled}
                >
                    Check Order
                </button>
            )}

            {feedback && (
                <div className={`ds-feedback ds-fb-${feedback.correct ? "correct" : "incorrect"}`}>
                    <span>{feedback.correct ? "🌟" : "💡"}</span>
                    <span>{feedback.message || (feedback.correct ? "Perfect order!" : "Not quite — try thinking through the sequence again.")}</span>
                </div>
            )}

            <style dangerouslySetInnerHTML={{ __html: `
                .ds-container {
                    display: flex;
                    flex-direction: column;
                    gap: 14px;
                    padding: 20px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-card);
                    animation: fadeInUp 0.35s ease-out both;
                }
                .ds-instruction {
                    font-size: 16px;
                    line-height: 1.5;
                    color: var(--color-text);
                    font-weight: 500;
                }
                .ds-list { display: flex; flex-direction: column; gap: 6px; }
                .ds-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 12px 14px;
                    border: 2px solid var(--color-border);
                    border-radius: var(--radius-md);
                    background: var(--color-bg);
                    cursor: grab;
                    font-size: 15px;
                    transition: all var(--transition-fast);
                    animation: fadeInUp 0.3s ease-out both;
                    user-select: none;
                }
                .ds-item:active { cursor: grabbing; }
                .ds-item:hover:not(.ds-correct):not(.ds-incorrect) {
                    border-color: var(--color-accent);
                    transform: translateX(3px);
                }
                .ds-correct {
                    border-color: var(--color-success);
                    background: var(--color-success-soft);
                }
                .ds-incorrect {
                    border-color: #e74c3c;
                    background: #fde8e8;
                }
                .ds-grip {
                    color: var(--color-text-muted);
                    font-size: 14px;
                    letter-spacing: 1px;
                }
                .ds-num {
                    width: 24px;
                    height: 24px;
                    border-radius: var(--radius-full);
                    background: var(--color-border);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: 700;
                    color: var(--color-text-secondary);
                    flex-shrink: 0;
                }
                .ds-correct .ds-num { background: var(--color-success); color: white; }
                .ds-incorrect .ds-num { background: #e74c3c; color: white; }
                .ds-label { flex: 1; }
                .ds-icon { font-weight: 700; font-size: 16px; flex-shrink: 0; }
                .ds-correct .ds-icon { color: var(--color-success); }
                .ds-incorrect .ds-icon { color: #e74c3c; }
                .ds-arrows {
                    display: flex;
                    flex-direction: column;
                    gap: 2px;
                }
                .ds-arrows button {
                    width: 22px;
                    height: 18px;
                    border: 1px solid var(--color-border);
                    border-radius: 4px;
                    background: var(--color-bg-card);
                    cursor: pointer;
                    font-size: 10px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: var(--color-text-secondary);
                    transition: all var(--transition-fast);
                }
                .ds-arrows button:hover:not(:disabled) {
                    background: var(--color-accent-soft);
                    border-color: var(--color-accent);
                }
                .ds-arrows button:disabled { opacity: 0.3; cursor: default; }
                .ds-submit {
                    align-self: flex-start;
                    padding: 10px 24px;
                    background: var(--color-accent);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-family: var(--font-body);
                    font-size: 14px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }
                .ds-submit:hover:not(:disabled) {
                    filter: brightness(1.1);
                    transform: translateY(-1px);
                }
                .ds-submit:disabled { opacity: 0.4; cursor: not-allowed; }
                .ds-feedback {
                    display: flex; align-items: flex-start; gap: 8px;
                    padding: 12px 14px; border-radius: var(--radius-md);
                    font-size: 14px; animation: fadeInUp 0.3s ease-out both;
                }
                .ds-fb-correct { background: var(--color-success-soft); color: var(--color-success); }
                .ds-fb-incorrect { background: var(--color-warn-soft); color: var(--color-text); }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
