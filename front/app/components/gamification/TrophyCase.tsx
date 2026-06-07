"use client";

import { useState } from "react";

interface Trophy {
    id: string;
    name: string;
    description: string;
    category: "streak" | "mastery" | "xp" | "career" | "milestone";
    earned: boolean;
    earnedAt?: string;
    rarity: "common" | "rare" | "epic" | "legendary";
}

interface TrophyCaseProps {
    trophies: Trophy[];
    onClose: () => void;
}

const CATEGORY_META: Record<string, { label: string; icon: string }> = {
    streak: { label: "Streaks", icon: "🔥" },
    mastery: { label: "Mastery", icon: "🎓" },
    xp: { label: "Experience", icon: "⭐" },
    career: { label: "Career", icon: "💼" },
    milestone: { label: "Milestones", icon: "🏆" },
};

const RARITY_COLORS: Record<string, { border: string; glow: string; bg: string }> = {
    common: { border: "#a89888", glow: "none", bg: "var(--color-bg-card)" },
    rare: { border: "#4a7fa5", glow: "0 0 12px rgba(74,127,165,0.2)", bg: "#f0f6fb" },
    epic: { border: "#8b5cf6", glow: "0 0 16px rgba(139,92,246,0.25)", bg: "#f5f0ff" },
    legendary: { border: "#d4622b", glow: "0 0 20px rgba(212,98,43,0.3)", bg: "#fef3ec" },
};

const TROPHY_ICONS: Record<string, string> = {
    first_correct: "🎯", streak_3: "🎩", streak_7: "🔥", streak_15: "💎",
    first_mastery: "🔓", mastery_5: "📈", mastery_20: "🏛️",
    sessions_5: "📚", sessions_20: "🎓",
    xp_100: "💯", xp_500: "⭐", xp_1000: "🏆",
    employment_intake: "💼", first_resume: "📄",
};

export function TrophyCase({ trophies, onClose }: TrophyCaseProps) {
    const [activeCategory, setActiveCategory] = useState<string | null>(null);
    const categories = Object.keys(CATEGORY_META);

    const filtered = activeCategory
        ? trophies.filter((t) => t.category === activeCategory)
        : trophies;

    const earnedCount = trophies.filter((t) => t.earned).length;

    return (
        <div className="tc-overlay" onClick={onClose}>
            <div className="tc-modal" onClick={(e) => e.stopPropagation()}>
                <div className="tc-header">
                    <div>
                        <h2 className="tc-title">Trophy Case</h2>
                        <p className="tc-count">{earnedCount} of {trophies.length} earned</p>
                    </div>
                    <button className="tc-close" onClick={onClose}>✕</button>
                </div>

                <div className="tc-progress-bar">
                    <div
                        className="tc-progress-fill"
                        style={{ width: `${(earnedCount / Math.max(trophies.length, 1)) * 100}%` }}
                    />
                </div>

                <div className="tc-tabs">
                    <button
                        className={`tc-tab ${!activeCategory ? "tc-tab-active" : ""}`}
                        onClick={() => setActiveCategory(null)}
                    >
                        All
                    </button>
                    {categories.map((cat) => (
                        <button
                            key={cat}
                            className={`tc-tab ${activeCategory === cat ? "tc-tab-active" : ""}`}
                            onClick={() => setActiveCategory(cat)}
                        >
                            {CATEGORY_META[cat].icon} {CATEGORY_META[cat].label}
                        </button>
                    ))}
                </div>

                <div className="tc-grid">
                    {filtered.map((trophy, i) => {
                        const rarity = RARITY_COLORS[trophy.rarity] || RARITY_COLORS.common;
                        return (
                            <div
                                key={trophy.id}
                                className={`tc-trophy ${trophy.earned ? "tc-earned" : "tc-locked"}`}
                                style={{
                                    borderColor: trophy.earned ? rarity.border : "var(--color-border)",
                                    boxShadow: trophy.earned ? rarity.glow : "none",
                                    background: trophy.earned ? rarity.bg : "var(--color-bg)",
                                    animationDelay: `${i * 40}ms`,
                                }}
                            >
                                <div className="tc-icon-wrap">
                                    <span className="tc-icon">
                                        {trophy.earned
                                            ? TROPHY_ICONS[trophy.id] || "🏅"
                                            : "🔒"}
                                    </span>
                                    {trophy.earned && (
                                        <span className="tc-rarity-dot"
                                            style={{ background: rarity.border }}
                                        />
                                    )}
                                </div>
                                <div className="tc-info">
                                    <span className="tc-name">{trophy.name}</span>
                                    <span className="tc-desc">{trophy.description}</span>
                                    {trophy.earned && trophy.earnedAt && (
                                        <span className="tc-date">
                                            {new Date(trophy.earnedAt).toLocaleDateString()}
                                        </span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .tc-overlay {
                    position: fixed; inset: 0; z-index: 900;
                    background: rgba(44, 37, 32, 0.5);
                    backdrop-filter: blur(4px);
                    display: flex; align-items: center; justify-content: center;
                    animation: fadeIn 0.2s ease-out;
                }
                .tc-modal {
                    width: 90%; max-width: 640px; max-height: 80vh;
                    background: var(--color-bg);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-elevated);
                    display: flex; flex-direction: column;
                    overflow: hidden;
                    animation: modalPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
                }
                .tc-header {
                    display: flex; justify-content: space-between; align-items: flex-start;
                    padding: 24px 24px 0;
                }
                .tc-title {
                    font-family: var(--font-display); font-size: 26px;
                    font-weight: 800; color: var(--color-text);
                }
                .tc-count {
                    font-size: 13px; color: var(--color-text-muted); margin-top: 2px;
                }
                .tc-close {
                    width: 32px; height: 32px; border: none;
                    background: var(--color-bg-sidebar); border-radius: var(--radius-full);
                    cursor: pointer; font-size: 16px; color: var(--color-text-muted);
                    display: flex; align-items: center; justify-content: center;
                    transition: all var(--transition-fast);
                }
                .tc-close:hover { background: var(--color-border); }
                .tc-progress-bar {
                    height: 4px; background: var(--color-border);
                    margin: 16px 24px 0; border-radius: 2px; overflow: hidden;
                }
                .tc-progress-fill {
                    height: 100%; background: var(--color-accent);
                    border-radius: 2px;
                    transition: width 600ms cubic-bezier(0.34, 1.56, 0.64, 1);
                }
                .tc-tabs {
                    display: flex; gap: 4px; padding: 16px 24px 0;
                    overflow-x: auto;
                }
                .tc-tab {
                    padding: 6px 14px; border: 1px solid var(--color-border);
                    border-radius: var(--radius-full); background: var(--color-bg-card);
                    font-family: var(--font-body); font-size: 13px;
                    cursor: pointer; white-space: nowrap;
                    transition: all var(--transition-fast);
                }
                .tc-tab:hover { border-color: var(--color-accent); }
                .tc-tab-active {
                    background: var(--color-accent); color: white;
                    border-color: var(--color-accent);
                }
                .tc-grid {
                    display: grid; grid-template-columns: 1fr 1fr;
                    gap: 10px; padding: 16px 24px 24px;
                    overflow-y: auto; flex: 1;
                }
                .tc-trophy {
                    display: flex; gap: 12px; padding: 14px;
                    border: 2px solid; border-radius: var(--radius-md);
                    transition: all var(--transition-fast);
                    animation: fadeInUp 0.3s ease-out both;
                }
                .tc-earned:hover { transform: translateY(-2px); }
                .tc-locked { opacity: 0.5; }
                .tc-icon-wrap {
                    position: relative; flex-shrink: 0;
                }
                .tc-icon { font-size: 28px; }
                .tc-rarity-dot {
                    position: absolute; bottom: -2px; right: -2px;
                    width: 8px; height: 8px; border-radius: 50%;
                    border: 2px solid white;
                }
                .tc-info {
                    display: flex; flex-direction: column; gap: 2px; min-width: 0;
                }
                .tc-name {
                    font-weight: 700; font-size: 14px; color: var(--color-text);
                }
                .tc-desc {
                    font-size: 12px; color: var(--color-text-secondary);
                    line-height: 1.4;
                }
                .tc-date {
                    font-size: 11px; color: var(--color-text-muted); margin-top: 2px;
                }
                @keyframes fadeIn {
                    from { opacity: 0; } to { opacity: 1; }
                }
                @keyframes modalPop {
                    from { opacity: 0; transform: scale(0.95) translateY(10px); }
                    to { opacity: 1; transform: scale(1) translateY(0); }
                }
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}
