"use client";

import { useEffect, useState } from "react";

interface MasteryUnlockProps {
    skillName: string;
    skillIcon?: string;
    nextSkills?: string[];
    onDone: () => void;
}

export function MasteryUnlock({ skillName, skillIcon = "🔓", nextSkills = [], onDone }: MasteryUnlockProps) {
    const [phase, setPhase] = useState<"enter" | "show" | "exit">("enter");

    useEffect(() => {
        const t1 = setTimeout(() => setPhase("show"), 50);
        const t2 = setTimeout(() => setPhase("exit"), 3500);
        const t3 = setTimeout(onDone, 4000);
        return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }, [onDone]);

    return (
        <div className={`mu-overlay mu-${phase}`}>
            <div className="mu-card">
                {/* Star burst behind icon */}
                <div className="mu-burst">
                    {Array.from({ length: 12 }).map((_, i) => (
                        <span
                            key={i}
                            className="mu-ray"
                            style={{ "--angle": `${i * 30}deg` } as React.CSSProperties}
                        />
                    ))}
                </div>

                <div className="mu-icon">{skillIcon}</div>
                <div className="mu-label">SKILL MASTERED</div>
                <div className="mu-skill-name">{skillName}</div>

                {nextSkills.length > 0 && (
                    <div className="mu-next">
                        <span className="mu-next-label">Unlocked:</span>
                        {nextSkills.map((s, i) => (
                            <span key={i} className="mu-next-skill">{s}</span>
                        ))}
                    </div>
                )}
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .mu-overlay {
                    position: fixed; inset: 0; z-index: 1050;
                    display: flex; align-items: center; justify-content: center;
                    background: rgba(44, 37, 32, 0.6);
                    backdrop-filter: blur(4px);
                    pointer-events: none;
                    transition: opacity 400ms ease;
                }
                .mu-enter { opacity: 0; }
                .mu-show { opacity: 1; }
                .mu-exit { opacity: 0; }

                .mu-card {
                    position: relative;
                    text-align: center;
                    padding: 40px;
                    animation: mu-pop 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) 0.1s both;
                }

                .mu-burst {
                    position: absolute;
                    top: 30px; left: 50%;
                    transform: translateX(-50%);
                    width: 0; height: 0;
                }
                .mu-ray {
                    position: absolute;
                    width: 3px; height: 40px;
                    background: linear-gradient(to bottom, var(--color-mastery), transparent);
                    transform-origin: bottom center;
                    transform: rotate(var(--angle));
                    animation: mu-ray-expand 0.6s ease-out 0.3s both;
                    border-radius: 2px;
                }

                .mu-icon {
                    font-size: 64px;
                    position: relative;
                    z-index: 1;
                    animation: mu-icon-bounce 0.6s ease-out 0.2s both;
                }
                .mu-label {
                    font-size: 12px; font-weight: 700;
                    letter-spacing: 3px; text-transform: uppercase;
                    color: var(--color-success);
                    margin-top: 8px;
                }
                .mu-skill-name {
                    font-family: var(--font-display);
                    font-size: 32px; font-weight: 800;
                    color: white;
                    margin-top: 4px;
                    text-shadow: 0 2px 12px rgba(58, 138, 92, 0.4);
                }
                .mu-next {
                    display: flex; gap: 8px; align-items: center;
                    justify-content: center; flex-wrap: wrap;
                    margin-top: 16px;
                    animation: fadeInUp 0.4s ease-out 1s both;
                }
                .mu-next-label {
                    font-size: 13px; color: var(--color-text-muted);
                }
                .mu-next-skill {
                    padding: 4px 12px;
                    background: rgba(255,255,255,0.15);
                    border-radius: var(--radius-full);
                    font-size: 13px; font-weight: 600;
                    color: white;
                }

                @keyframes mu-pop {
                    0% { transform: scale(0); opacity: 0; }
                    60% { transform: scale(1.05); opacity: 1; }
                    100% { transform: scale(1); }
                }
                @keyframes mu-ray-expand {
                    0% { height: 0; opacity: 0; }
                    50% { height: 60px; opacity: 1; }
                    100% { height: 40px; opacity: 0.6; }
                }
                @keyframes mu-icon-bounce {
                    0% { transform: scale(0) rotate(-15deg); }
                    60% { transform: scale(1.2) rotate(5deg); }
                    100% { transform: scale(1) rotate(0); }
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
