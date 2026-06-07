"use client";

import { useState, useRef, useEffect } from "react";

interface Blank {
    id: string;
    correctAnswer: string;
    hint?: string;
}

interface FillInBlankProps {
    /** Template with {blank_id} placeholders, e.g. "The area of a {shape} is {formula}" */
    template: string;
    blanks: Blank[];
    onSubmit: (answers: Record<string, string>) => void;
    feedback?: { correct: boolean; corrections?: Record<string, string>; message?: string } | null;
    disabled?: boolean;
}

export function FillInBlank({
    template,
    blanks,
    onSubmit,
    feedback = null,
    disabled = false,
}: FillInBlankProps) {
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

    // Focus first blank on mount
    useEffect(() => {
        const firstId = blanks[0]?.id;
        if (firstId && inputRefs.current[firstId]) {
            inputRefs.current[firstId]?.focus();
        }
    }, [blanks]);

    const handleChange = (id: string, value: string) => {
        setAnswers((prev) => ({ ...prev, [id]: value }));
    };

    const handleKeyDown = (e: React.KeyboardEvent, currentIdx: number) => {
        if (e.key === "Enter" || e.key === "Tab") {
            e.preventDefault();
            const nextIdx = currentIdx + 1;
            if (nextIdx < blanks.length) {
                const nextId = blanks[nextIdx].id;
                inputRefs.current[nextId]?.focus();
            } else {
                handleSubmit();
            }
        }
    };

    const handleSubmit = () => {
        if (disabled || feedback) return;
        onSubmit(answers);
    };

    // Parse template into segments
    const segments = parseTemplate(template, blanks);

    const getBlankState = (id: string): "idle" | "correct" | "incorrect" => {
        if (!feedback) return "idle";
        const correction = feedback.corrections?.[id];
        if (correction === undefined) return "correct"; // no correction = correct
        return answers[id]?.toLowerCase().trim() === correction?.toLowerCase().trim()
            ? "correct" : "incorrect";
    };

    return (
        <div className="fib-container">
            <div className="fib-sentence">
                {segments.map((seg, i) => {
                    if (seg.type === "text") {
                        return <span key={i} className="fib-text">{seg.value}</span>;
                    }

                    const blank = blanks.find((b) => b.id === seg.value)!;
                    const state = getBlankState(blank.id);

                    return (
                        <span key={i} className="fib-blank-wrap">
                            <input
                                ref={(el) => { inputRefs.current[blank.id] = el; }}
                                className={`fib-input fib-input-${state}`}
                                type="text"
                                value={answers[blank.id] || ""}
                                onChange={(e) => handleChange(blank.id, e.target.value)}
                                onKeyDown={(e) => handleKeyDown(e, blanks.indexOf(blank))}
                                placeholder={blank.hint || "…"}
                                disabled={disabled || !!feedback}
                                autoComplete="off"
                                spellCheck={false}
                                style={{
                                    width: `${Math.max(blank.correctAnswer.length + 2, 6)}ch`,
                                }}
                            />
                            {state === "incorrect" && feedback?.corrections?.[blank.id] && (
                                <span className="fib-correction">
                                    {feedback.corrections[blank.id]}
                                </span>
                            )}
                        </span>
                    );
                })}
            </div>

            {!feedback && (
                <button
                    className="fib-submit"
                    onClick={handleSubmit}
                    disabled={disabled || Object.keys(answers).length < blanks.length}
                >
                    Check
                </button>
            )}

            {feedback && (
                <div className={`fib-feedback fib-feedback-${feedback.correct ? "correct" : "incorrect"}`}>
                    <span>{feedback.correct ? "🌟" : "💡"}</span>
                    <span>{feedback.message || (feedback.correct ? "Perfect!" : "Let's take another look.")}</span>
                </div>
            )}

            <style dangerouslySetInnerHTML={{ __html: `
                .fib-container {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    padding: 20px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-card);
                    animation: fadeInUp 0.35s ease-out both;
                }

                .fib-sentence {
                    font-size: 17px;
                    line-height: 2.2;
                    color: var(--color-text);
                    display: flex;
                    flex-wrap: wrap;
                    align-items: baseline;
                    gap: 2px;
                }

                .fib-text {
                    white-space: pre-wrap;
                }

                .fib-blank-wrap {
                    display: inline-flex;
                    flex-direction: column;
                    align-items: center;
                    position: relative;
                }

                .fib-input {
                    border: none;
                    border-bottom: 2px solid var(--color-border);
                    background: transparent;
                    font-family: var(--font-body);
                    font-size: 17px;
                    font-weight: 600;
                    color: var(--color-accent);
                    text-align: center;
                    padding: 2px 6px;
                    outline: none;
                    transition: all var(--transition-fast);
                }

                .fib-input::placeholder {
                    color: var(--color-text-muted);
                    font-weight: 400;
                }

                .fib-input:focus {
                    border-bottom-color: var(--color-accent);
                }

                .fib-input-correct {
                    border-bottom-color: var(--color-success);
                    color: var(--color-success);
                }

                .fib-input-incorrect {
                    border-bottom-color: #e74c3c;
                    color: #e74c3c;
                    text-decoration: line-through;
                    animation: choice-shake 0.4s ease-out both;
                }

                .fib-correction {
                    position: absolute;
                    top: 100%;
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--color-success);
                    white-space: nowrap;
                    animation: fadeInUp 0.3s ease-out 0.4s both;
                }

                .fib-submit {
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

                .fib-submit:hover:not(:disabled) {
                    filter: brightness(1.1);
                    transform: translateY(-1px);
                }

                .fib-submit:disabled {
                    opacity: 0.4;
                    cursor: not-allowed;
                }

                .fib-feedback {
                    display: flex;
                    align-items: flex-start;
                    gap: 8px;
                    padding: 12px 14px;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    animation: fadeInUp 0.3s ease-out both;
                }

                .fib-feedback-correct {
                    background: var(--color-success-soft);
                    color: var(--color-success);
                }

                .fib-feedback-incorrect {
                    background: var(--color-warn-soft);
                    color: var(--color-text);
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                @keyframes choice-shake {
                    0%, 100% { transform: translateX(0); }
                    20% { transform: translateX(-4px); }
                    40% { transform: translateX(4px); }
                    60% { transform: translateX(-3px); }
                    80% { transform: translateX(3px); }
                }
            `}} />
        </div>
    );
}

// Parse "The {x} is {y}" into [{type:"text",value:"The "},{type:"blank",value:"x"}, ...]
function parseTemplate(template: string, blanks: Blank[]) {
    const segments: { type: "text" | "blank"; value: string }[] = [];
    const regex = /\{(\w+)\}/g;
    let last = 0;
    let match;

    while ((match = regex.exec(template)) !== null) {
        if (match.index > last) {
            segments.push({ type: "text", value: template.slice(last, match.index) });
        }
        const blankId = match[1];
        if (blanks.some((b) => b.id === blankId)) {
            segments.push({ type: "blank", value: blankId });
        } else {
            segments.push({ type: "text", value: match[0] });
        }
        last = regex.lastIndex;
    }

    if (last < template.length) {
        segments.push({ type: "text", value: template.slice(last) });
    }

    return segments;
}
