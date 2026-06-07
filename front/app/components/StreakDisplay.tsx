"use client";

/**
 * StreakDisplay — shows the learner's streak with shields and fire tiers.
 *
 * Replaces the simple StreakCounter with a richer display that
 * communicates shield status, recovery state, and milestones.
 *
 * Fire tiers:
 *   0 = no fire (< 7 days)
 *   1 = small flame (7+)
 *   2 = medium flame (14+)
 *   3 = large flame (30+)
 *   4 = roaring flame (60+)
 *   5 = legendary (100+)
 *
 * Messaging is ALWAYS forward-looking, never guilt-based.
 */

import { useEffect, useState } from "react";

interface StreakDisplayProps {
    streak: number;
    longestStreak: number;
    fireTier: number;
    shieldsAvailable: number;
    maxShields: number;
    shieldActive: boolean;
    status: "active" | "pending" | "shielded" | "recovery" | "broken";
    recoveryDeadline?: string | null;
    milestoneMessage?: string | null;
    onDismissMilestone?: () => void;
}

const FIRE_EMOJIS = ["⚡", "🔥", "🔥", "🔥", "🔥", "💎"];
const STATUS_MESSAGES: Record<string, string> = {
    active: "You're on track today!",
    pending: "Start a session to keep your streak alive.",
    shielded: "Your Streak Shield protected you yesterday.",
    recovery: "Complete a session to recover your streak!",
    broken: "Fresh start. Every streak begins with day one.",
};

export function StreakDisplay({
    streak,
    longestStreak,
    fireTier,
    shieldsAvailable,
    maxShields,
    shieldActive,
    status,
    recoveryDeadline,
    milestoneMessage,
    onDismissMilestone,
}: StreakDisplayProps) {
    const [showDetails, setShowDetails] = useState(false);
    const [nowMs, setNowMs] = useState<number | null>(null);
    const emoji = FIRE_EMOJIS[Math.min(fireTier, 5)];
    const isUrgent = status === "recovery";
    const isBroken = status === "broken";

    useEffect(() => {
        const updateNow = () => setNowMs(Date.now());
        updateNow();
        const intervalId = setInterval(updateNow, 60_000);
        return () => clearInterval(intervalId);
    }, []);

    // Recovery countdown
    let recoveryHours = 0;
    if (recoveryDeadline && nowMs !== null) {
        const deadline = new Date(recoveryDeadline);
        recoveryHours = Math.max(0, Math.round((deadline.getTime() - nowMs) / 3600000));
    }

    return (
        <div className={`sd-container ${isUrgent ? "sd-urgent" : ""} ${isBroken ? "sd-broken" : ""}`}>
            {/* Milestone toast */}
            {milestoneMessage && (
                <div className="sd-milestone" onClick={onDismissMilestone}>
                    <span className="sd-milestone-icon">🎉</span>
                    <span className="sd-milestone-text">{milestoneMessage}</span>
                </div>
            )}

            {/* Main streak display */}
            <div className="sd-main" onClick={() => setShowDetails(!showDetails)}>
                <span className={`sd-emoji ${fireTier >= 2 ? "sd-fire-anim" : ""}`}>
                    {emoji}
                </span>
                <div className="sd-info">
                    <span className="sd-count">{streak}</span>
                    <span className="sd-label">
                        {streak === 1 ? "day" : "days"}
                    </span>
                </div>

                {/* Shield indicators */}
                <div className="sd-shields">
                    {Array.from({ length: maxShields }, (_, i) => (
                        <span
                            key={i}
                            className={`sd-shield ${i < shieldsAvailable ? "sd-shield-full" : "sd-shield-empty"} ${shieldActive && i === 0 ? "sd-shield-active" : ""}`}
                            title={i < shieldsAvailable ? "Shield ready" : "Shield slot empty"}
                        >
                            🛡️
                        </span>
                    ))}
                </div>
            </div>

            {/* Status message */}
            <p className={`sd-status ${isUrgent ? "sd-status-urgent" : ""}`}>
                {STATUS_MESSAGES[status]}
                {isUrgent && recoveryHours > 0 && (
                    <span className="sd-countdown"> ({recoveryHours}h remaining)</span>
                )}
            </p>

            {/* Details panel */}
            {showDetails && (
                <div className="sd-details">
                    <div className="sd-detail-row">
                        <span className="sd-detail-label">Longest streak</span>
                        <span className="sd-detail-value">{longestStreak} days</span>
                    </div>
                    <div className="sd-detail-row">
                        <span className="sd-detail-label">Shields</span>
                        <span className="sd-detail-value">{shieldsAvailable}/{maxShields}</span>
                    </div>
                    <p className="sd-detail-hint">
                        {shieldsAvailable === 0
                            ? `Complete ${3} extra sessions to earn a shield.`
                            : shieldActive
                            ? "A shield is protecting your streak right now."
                            : "Shields auto-activate when you miss a day."}
                    </p>
                </div>
            )}

            <style jsx>{`
                .sd-container {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    padding: 12px 14px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    transition: all var(--transition-fast);
                }

                .sd-urgent {
                    border-color: var(--color-warn);
                    background: var(--color-warn-soft);
                }

                .sd-broken {
                    opacity: 0.7;
                }

                .sd-main {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    cursor: pointer;
                }

                .sd-emoji {
                    font-size: 24px;
                    flex-shrink: 0;
                }

                .sd-fire-anim {
                    animation: streak-pulse 2s ease-in-out infinite;
                }

                .sd-info {
                    display: flex;
                    align-items: baseline;
                    gap: 4px;
                    flex: 1;
                }

                .sd-count {
                    font-family: var(--font-display);
                    font-size: 26px;
                    font-weight: 800;
                    color: var(--color-streak);
                    line-height: 1;
                }

                .sd-label {
                    font-size: 13px;
                    color: var(--color-text-muted);
                    font-weight: 500;
                }

                .sd-shields {
                    display: flex;
                    gap: 2px;
                }

                .sd-shield {
                    font-size: 14px;
                    transition: all var(--transition-fast);
                }

                .sd-shield-empty {
                    opacity: 0.2;
                    filter: grayscale(1);
                }

                .sd-shield-full {
                    opacity: 0.8;
                }

                .sd-shield-active {
                    opacity: 1;
                    animation: shield-glow 2s ease-in-out infinite;
                }

                .sd-status {
                    font-size: 12px;
                    color: var(--color-text-secondary);
                    line-height: 1.4;
                }

                .sd-status-urgent {
                    color: var(--color-warn);
                    font-weight: 600;
                }

                .sd-countdown {
                    font-weight: 700;
                }

                .sd-details {
                    padding-top: 8px;
                    border-top: 1px solid var(--color-border);
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    animation: fadeInUp 0.2s ease-out both;
                }

                .sd-detail-row {
                    display: flex;
                    justify-content: space-between;
                    font-size: 12px;
                }

                .sd-detail-label {
                    color: var(--color-text-muted);
                }

                .sd-detail-value {
                    font-weight: 600;
                    color: var(--color-text-secondary);
                }

                .sd-detail-hint {
                    font-size: 11px;
                    color: var(--color-text-muted);
                    font-style: italic;
                    line-height: 1.4;
                }

                .sd-milestone {
                    display: flex;
                    gap: 8px;
                    padding: 8px 12px;
                    background: var(--color-success-soft);
                    border-radius: var(--radius-sm);
                    cursor: pointer;
                    animation: fadeInUp 0.3s ease-out both;
                }

                .sd-milestone-icon {
                    font-size: 16px;
                    flex-shrink: 0;
                }

                .sd-milestone-text {
                    font-size: 12px;
                    color: var(--color-success);
                    font-weight: 600;
                    line-height: 1.4;
                }

                @keyframes streak-pulse {
                    0%, 100% { transform: scale(1); filter: brightness(1); }
                    50% { transform: scale(1.1); filter: brightness(1.15); }
                }

                @keyframes shield-glow {
                    0%, 100% { filter: brightness(1) drop-shadow(0 0 0 transparent); }
                    50% { filter: brightness(1.2) drop-shadow(0 0 4px rgba(201, 149, 46, 0.4)); }
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(6px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
