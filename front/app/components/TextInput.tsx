"use client";

import { useState } from "react";

interface TextInputProps {
    prompt: string;
    onSubmit: (answer: string) => void;
    disabled?: boolean;
}

export function TextInput({
    prompt,
    onSubmit,
    disabled = false,
}: TextInputProps) {
    const [value, setValue] = useState("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (value.trim() && !disabled) {
            onSubmit(value.trim());
        }
    };

    return (
        <div className="ti-container">
            <p className="ti-prompt">{prompt}</p>

            <form onSubmit={handleSubmit} className="ti-form">
                <input
                    type="text"
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    disabled={disabled}
                    className="ti-input"
                    placeholder="Type your answer here..."
                />
                <button
                    type="submit"
                    disabled={disabled || !value.trim()}
                    className="ti-submit"
                >
                    Submit
                </button>
            </form>

            <style dangerouslySetInnerHTML={{
                __html: `
                .ti-container {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    padding: 20px;
                    background: var(--color-bg-card, #ffffff);
                    border: 1px solid var(--color-border, #e5e7eb);
                    border-radius: var(--radius-lg, 12px);
                    box-shadow: var(--shadow-card, 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06));
                    animation: fadeInUp 0.35s ease-out both;
                }

                .ti-prompt {
                    font-size: 16px;
                    line-height: 1.5;
                    color: var(--color-text, #111827);
                    font-weight: 500;
                    margin: 0;
                }

                .ti-form {
                    display: flex;
                    gap: 12px;
                }

                .ti-input {
                    flex: 1;
                    padding: 12px 16px;
                    border: 2px solid var(--color-border, #e5e7eb);
                    border-radius: var(--radius-md, 8px);
                    font-family: var(--font-body, inherit);
                    font-size: 15px;
                    outline: none;
                    transition: all 0.2s ease;
                }

                .ti-input:focus:not(:disabled) {
                    border-color: var(--color-accent, #3b82f6);
                }

                .ti-input:disabled {
                    background: #f3f4f6;
                    cursor: not-allowed;
                    opacity: 0.7;
                }

                .ti-submit {
                    padding: 12px 24px;
                    background: var(--color-accent, #3b82f6);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md, 8px);
                    font-family: var(--font-body, inherit);
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .ti-submit:hover:not(:disabled) {
                    background: var(--color-accent-hover, #2563eb);
                    transform: translateY(-1px);
                }

                .ti-submit:disabled {
                    background: var(--color-border, #e5e7eb);
                    color: #9ca3af;
                    cursor: not-allowed;
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
