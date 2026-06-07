"use client";

import { useEffect, useState } from "react";

interface LevelUpOverlayProps {
    newLevel: number;
    onDone: () => void;
}

export function LevelUpOverlay({ newLevel, onDone }: LevelUpOverlayProps) {
    const [phase, setPhase] = useState<"enter" | "show" | "exit">("enter");

    useEffect(() => {
        const t1 = setTimeout(() => setPhase("show"), 50);
        const t2 = setTimeout(() => setPhase("exit"), 3200);
        const t3 = setTimeout(onDone, 3800);
        return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }, [onDone]);

    return (
        <div className={`lu-overlay lu-${phase}`}>
            {/* Particle ring */}
            <div className="lu-ring">
                {Array.from({ length: 16 }).map((_, i) => (
                    <span
                        key={i}
                        className="lu-particle"
                        style={{
                            "--i": i,
                            "--total": 16,
                            "--hue": `${(i / 16) * 360}`,
                        } as React.CSSProperties}
                    />
                ))}
            </div>

            <div className="lu-content">
                <div className="lu-label">LEVEL UP</div>
                <div className="lu-number">{newLevel}</div>
                <div className="lu-tagline">
                    {newLevel <= 3 ? "Keep going!" :
                     newLevel <= 6 ? "You're building something real." :
                     newLevel <= 9 ? "Seriously impressive." :
                     "Unstoppable."}
                </div>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .lu-overlay {
                    position: fixed; inset: 0; z-index: 1100;
                    display: flex; align-items: center; justify-content: center;
                    background: rgba(44, 37, 32, 0.75);
                    backdrop-filter: blur(6px);
                    pointer-events: none;
                    transition: opacity 500ms ease;
                }
                .lu-enter { opacity: 0; }
                .lu-show { opacity: 1; }
                .lu-exit { opacity: 0; }

                .lu-ring {
                    position: absolute;
                    width: 280px; height: 280px;
                }
                .lu-particle {
                    position: absolute;
                    width: 6px; height: 6px;
                    border-radius: 50%;
                    background: hsl(var(--hue), 70%, 60%);
                    top: 50%; left: 50%;
                    animation: lu-orbit 2.5s ease-out both;
                    animation-delay: calc(var(--i) * 0.06s);
                }

                .lu-content {
                    text-align: center;
                    animation: lu-pop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1) 0.2s both;
                }
                .lu-label {
                    font-family: var(--font-body);
                    font-size: 14px;
                    font-weight: 700;
                    letter-spacing: 4px;
                    text-transform: uppercase;
                    color: var(--color-accent-soft);
                    margin-bottom: 4px;
                }
                .lu-number {
                    font-family: var(--font-display);
                    font-size: 96px;
                    font-weight: 900;
                    color: white;
                    line-height: 1;
                    text-shadow: 0 0 40px rgba(212, 98, 43, 0.5);
                }
                .lu-tagline {
                    font-size: 16px;
                    color: var(--color-accent-soft);
                    margin-top: 8px;
                    animation: fadeInUp 0.4s ease-out 0.6s both;
                }

                @keyframes lu-orbit {
                    0% {
                        transform: rotate(calc(var(--i) * (360deg / var(--total))))
                                   translateX(0) scale(0);
                        opacity: 1;
                    }
                    40% {
                        transform: rotate(calc(var(--i) * (360deg / var(--total)) + 90deg))
                                   translateX(140px) scale(1.5);
                        opacity: 1;
                    }
                    100% {
                        transform: rotate(calc(var(--i) * (360deg / var(--total)) + 200deg))
                                   translateX(180px) scale(0);
                        opacity: 0;
                    }
                }
                @keyframes lu-pop {
                    0% { transform: scale(0); opacity: 0; }
                    60% { transform: scale(1.1); opacity: 1; }
                    100% { transform: scale(1); opacity: 1; }
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
