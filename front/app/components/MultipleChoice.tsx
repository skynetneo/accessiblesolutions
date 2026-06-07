"use client";

import { useState } from "react";

interface MultipleChoiceProps {
    question: string;
    choices: string[];
    onAnswer: (choice: string) => void;
    disabled?: boolean;
    feedback?: { correct: boolean; correctAnswer?: string; message?: string } | null;
}

export function MultipleChoice({
    question,
    choices,
    onAnswer,
    disabled = false,
    feedback = null,
}: MultipleChoiceProps) {
    const [selected, setSelected] = useState<string | null>(null);

    const handleSelect = (choice: string) => {
        if (disabled || feedback) return;
        setSelected(choice);
        onAnswer(choice);
    };

    const getChoiceState = (choice: string) => {
        if (!feedback) return selected === choice ? "selected" : "idle";
        if (choice === feedback.correctAnswer) return "correct";
        if (choice === selected && !feedback.correct) return "incorrect";
        return "dimmed";
    };

    return (
        <div className="mc-container">
            <p className="mc-question">{question}</p>

            <div className="mc-choices">
                {choices.map((choice, i) => {
                    const state = getChoiceState(choice);
                    return (
                        <button
                            key={i}
                            className={`mc-choice mc-${state}`}
                            onClick={() => handleSelect(choice)}
                            disabled={disabled || !!feedback}
                            style={{ animationDelay: `${i * 60}ms` }}
                        >
                            <span className="mc-letter">
                                {String.fromCharCode(65 + i)}
                            </span>
                            <span className="mc-text">{choice}</span>
                            {state === "correct" && <span className="mc-icon">✓</span>}
                            {state === "incorrect" && <span className="mc-icon">✕</span>}
                        </button>
                    );
                })}
            </div>

            {feedback && (
                <div className={`mc-feedback mc-feedback-${feedback.correct ? "correct" : "incorrect"}`}>
                    <span className="mc-feedback-icon">
                        {feedback.correct ? "🌟" : "💡"}
                    </span>
                    <span className="mc-feedback-text">
                        {feedback.message || (feedback.correct ? "That's right!" : "Not quite — let's look at this together.")}
                    </span>
                </div>
            )}

            <style dangerouslySetInnerHTML={{ __html: `
                .mc-container {
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

                .mc-question {
                    font-size: 16px;
                    line-height: 1.5;
                    color: var(--color-text);
                    font-weight: 500;
                }

                .mc-choices {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .mc-choice {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 14px 16px;
                    border: 2px solid var(--color-border);
                    border-radius: var(--radius-md);
                    background: var(--color-bg);
                    cursor: pointer;
                    font-family: var(--font-body);
                    font-size: 15px;
                    text-align: left;
                    transition: all var(--transition-fast);
                    animation: fadeInUp 0.3s ease-out both;
                }

                .mc-choice:hover:not(:disabled) {
                    border-color: var(--color-accent);
                    background: var(--color-accent-soft);
                    transform: translateX(4px);
                }

                .mc-idle {}

                .mc-selected {
                    border-color: var(--color-accent);
                    background: var(--color-accent-soft);
                }

                .mc-correct {
                    border-color: var(--color-success);
                    background: var(--color-success-soft);
                    animation: choice-correct 0.4s ease-out both;
                }

                .mc-incorrect {
                    border-color: #e74c3c;
                    background: #fde8e8;
                    animation: choice-shake 0.4s ease-out both;
                }

                .mc-dimmed {
                    opacity: 0.45;
                }

                .mc-letter {
                    width: 28px;
                    height: 28px;
                    border-radius: var(--radius-full);
                    background: var(--color-border);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    font-size: 13px;
                    color: var(--color-text-secondary);
                    flex-shrink: 0;
                    transition: all var(--transition-fast);
                }

                .mc-correct .mc-letter {
                    background: var(--color-success);
                    color: white;
                }

                .mc-incorrect .mc-letter {
                    background: #e74c3c;
                    color: white;
                }

                .mc-text {
                    flex: 1;
                }

                .mc-icon {
                    font-weight: 700;
                    font-size: 18px;
                    flex-shrink: 0;
                }

                .mc-correct .mc-icon { color: var(--color-success); }
                .mc-incorrect .mc-icon { color: #e74c3c; }

                .mc-feedback {
                    display: flex;
                    align-items: flex-start;
                    gap: 10px;
                    padding: 14px 16px;
                    border-radius: var(--radius-md);
                    font-size: 14px;
                    line-height: 1.5;
                    animation: fadeInUp 0.3s ease-out both;
                }

                .mc-feedback-correct {
                    background: var(--color-success-soft);
                    color: var(--color-success);
                }

                .mc-feedback-incorrect {
                    background: var(--color-warn-soft);
                    color: var(--color-text);
                }

                .mc-feedback-icon { font-size: 18px; flex-shrink: 0; }
                .mc-feedback-text { flex: 1; }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                @keyframes choice-correct {
                    0% { transform: scale(1); }
                    40% { transform: scale(1.03); }
                    100% { transform: scale(1); }
                }

                @keyframes choice-shake {
                    0%, 100% { transform: translateX(0); }
                    20% { transform: translateX(-6px); }
                    40% { transform: translateX(6px); }
                    60% { transform: translateX(-4px); }
                    80% { transform: translateX(4px); }
                }
            `}} />
        </div>
    );
}
