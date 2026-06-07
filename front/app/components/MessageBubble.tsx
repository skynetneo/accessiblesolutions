"use client";

interface MessageBubbleProps {
    message: { type?: string; content?: string; id?: string };
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isHuman = message.type === "human";
    const content = typeof message.content === "string" ? message.content : "";

    if (!content.trim()) return null;

    return (
        <div className={`bubble-row ${isHuman ? "bubble-human" : "bubble-ai"}`}>
            {!isHuman && <div className="avatar">🎓</div>}
            <div className={`bubble ${isHuman ? "human" : "ai"}`}>
                <div className="bubble-content">{content}</div>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .bubble-row {
                    display: flex;
                    gap: 10px;
                    max-width: 85%;
                    animation: fadeInUp 0.3s ease-out both;
                }

                .bubble-human {
                    align-self: flex-end;
                    flex-direction: row-reverse;
                }

                .bubble-ai {
                    align-self: flex-start;
                }

                .avatar {
                    width: 32px;
                    height: 32px;
                    border-radius: var(--radius-full);
                    background: var(--color-accent-soft);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 16px;
                    flex-shrink: 0;
                    margin-top: 4px;
                }

                .bubble {
                    padding: 12px 16px;
                    border-radius: var(--radius-lg);
                    line-height: 1.55;
                    font-size: 15px;
                }

                .bubble.ai {
                    background: var(--glass-surface);
                    backdrop-filter: blur(var(--glass-blur));
                    -webkit-backdrop-filter: blur(var(--glass-blur));
                    border: var(--glass-border);
                    border-bottom-left-radius: var(--radius-sm);
                    box-shadow: var(--shadow-card);
                }

                .bubble.human {
                    background: var(--color-accent);
                    color: white;
                    border-bottom-right-radius: var(--radius-sm);
                }

                .bubble-content {
                    white-space: pre-wrap;
                    word-break: break-word;
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
