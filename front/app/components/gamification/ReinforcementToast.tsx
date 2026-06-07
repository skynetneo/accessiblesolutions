"use client";

import { useEffect, useState } from "react";

interface ReinforcementToastProps {
    xp: number;
    message?: string;
    position?: "top" | "bottom";
    onDone: () => void;
}

const ENCOURAGEMENTS = [
    "Nice work!",
    "You got this!",
    "Keep it going!",
    "Solid!",
    "Right on!",
    "That's the way!",
    "Nailed it!",
    "Look at you go!",
];

export function ReinforcementToast({
    xp,
    message,
    position = "bottom",
    onDone,
}: ReinforcementToastProps) {
    const [visible, setVisible] = useState(false);
    const displayMsg = message || ENCOURAGEMENTS[Math.abs(xp) % ENCOURAGEMENTS.length];

    useEffect(() => {
        const t1 = setTimeout(() => setVisible(true), 50);
        const t2 = setTimeout(() => setVisible(false), 2200);
        const t3 = setTimeout(onDone, 2600);
        return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }, [onDone]);

    return (
        <div
            className={`rt-toast rt-${position} ${visible ? "rt-visible" : "rt-hidden"}`}
        >
            <span className="rt-xp">+{xp} XP</span>
            <span className="rt-divider" />
            <span className="rt-msg">{displayMsg}</span>

            <style dangerouslySetInnerHTML={{ __html: `
                .rt-toast {
                    position: fixed;
                    left: 50%; transform: translateX(-50%);
                    z-index: 800;
                    display: flex; align-items: center; gap: 10px;
                    padding: 10px 20px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-accent);
                    border-radius: var(--radius-full);
                    box-shadow: var(--shadow-elevated), var(--shadow-glow);
                    font-size: 14px;
                    pointer-events: none;
                    transition: all 350ms cubic-bezier(0.34, 1.56, 0.64, 1);
                }
                .rt-top { top: 24px; }
                .rt-bottom { bottom: 100px; }

                .rt-hidden {
                    opacity: 0;
                    transform: translateX(-50%) translateY(12px) scale(0.9);
                }
                .rt-visible {
                    opacity: 1;
                    transform: translateX(-50%) translateY(0) scale(1);
                }
                .rt-top.rt-hidden { transform: translateX(-50%) translateY(-12px) scale(0.9); }

                .rt-xp {
                    font-family: var(--font-display);
                    font-weight: 800;
                    color: var(--color-accent);
                    font-size: 16px;
                }
                .rt-divider {
                    width: 1px; height: 16px;
                    background: var(--color-border);
                }
                .rt-msg {
                    font-weight: 600;
                    color: var(--color-text);
                }
            `}} />
        </div>
    );
}
