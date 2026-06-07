// components/home/HomeView.tsx
"use client";

/**
 * HomeView — the learner's landing screen.
 *
 * Design philosophy: reduce cognitive load to near zero.
 * The learner should be able to go from "app opened" to
 * "learning" in ONE TAP, within 2 seconds.
 *
 * Layout (mobile-first, top to bottom):
 *   1. Header: greeting + streak (compact)
 *   2. Primary action card (dominant, big tap target)
 *   3. Stat row (3 glanceable numbers)
 *   4. Quick actions list (secondary paths)
 *
 * Everything above the fold on a 667px (iPhone SE) screen.
 *
 * Color: warm copper palette. Typography: Fraunces display + DM Sans body.
 * Aesthetic: warm, encouraging, clean — NOT gamified or childish.
 */

// ── Types ────────────────────────────────────────────────────

interface LearnerState {
    name: string;
    streak: {
        current: number;
        longest: number;
        fireTier: number;
        shieldsAvailable: number;
        maxShields: number;
        shieldActive: boolean;
        status: "active" | "pending" | "shielded" | "recovery" | "broken";
        recoveryDeadline?: string | null;
        milestoneMessage?: string | null;
    };
    stats: {
        programProgress: number;    // 0-1
        programLabel: string;       // "GED Math", "Digital Literacy", etc.
        xpTotal: number;
        accuracy: number;           // 0-1
        skillsMastered: number;
        totalSkills: number;
    };
    nextAction: {
        title: string;              // Current recommended skill
        subtitle: string;           // "Lesson 3 of 8"
        programLabel: string;       // "GED Math"
        estimatedMinutes: number;
        progressInSkill: number;    // 0-1
        skillId: string;
    };
}

interface HomeViewProps {
    learner: LearnerState;
    onStartSession: (mode: "continue" | "quick" | "review") => void;
    onNavigate: (target: "career" | "path" | "ikigai") => void;
}

// ── Component ────────────────────────────────────────────────

export function HomeView({ learner, onStartSession, onNavigate }: HomeViewProps) {
    const { name, streak, stats, nextAction } = learner;
    const greeting = getGreeting();
    const progressPct = Math.round(stats.programProgress * 100);
    const accuracyPct = Math.round(stats.accuracy * 100);

    return (
        <div className="hv">
            {/* ── Header: greeting + streak ────────── */}
            <header className="hv-header">
                <div className="hv-greeting-area">
                    <h1 className="hv-greeting">{greeting}, {name || "there"}</h1>
                    <p className="hv-subtitle">
                        {streak.status === "active"
                            ? "You're on track today. Keep it up."
                            : streak.status === "shielded"
                            ? "Your streak shield has you covered."
                            : streak.status === "recovery"
                            ? "Jump back in to save your streak."
                            : "Ready to learn something new?"}
                    </p>
                </div>
                <div className="hv-streak-compact">
                    <span className="hv-streak-fire">
                        {streak.fireTier >= 2 ? "🔥" : "⚡"}
                    </span>
                    <span className="hv-streak-num">{streak.current}</span>
                    {streak.shieldsAvailable > 0 && (
                        <span className="hv-shield-badge">🛡️</span>
                    )}
                </div>
            </header>

            {/* ── Primary action card ──────────────── */}
            <button
                className="hv-primary-card"
                onClick={() => onStartSession("continue")}
            >
                <div className="hv-primary-top">
                    <span className="hv-program-tag">{nextAction.programLabel}</span>
                    <span className="hv-time-tag">
                        ⏱ {nextAction.estimatedMinutes} min
                    </span>
                </div>

                <h2 className="hv-primary-title">{nextAction.title}</h2>
                <p className="hv-primary-subtitle">{nextAction.subtitle}</p>

                {/* Skill progress mini-bar */}
                <div className="hv-skill-progress">
                    <div className="hv-skill-track">
                        <div
                            className="hv-skill-fill"
                            style={{ width: `${Math.round(nextAction.progressInSkill * 100)}%` }}
                        />
                    </div>
                    <span className="hv-skill-pct">
                        {Math.round(nextAction.progressInSkill * 100)}%
                    </span>
                </div>

                <div className="hv-primary-cta">
                    <span className="hv-cta-text">Continue Learning</span>
                    <span className="hv-cta-arrow">→</span>
                </div>
            </button>

            {/* ── Stat cards row ───────────────────── */}
            <div className="hv-stats">
                <div className="hv-stat" style={{ animationDelay: "0.1s" }}>
                    {/* Progress ring */}
                    <svg className="hv-ring" viewBox="0 0 40 40">
                        <circle cx="20" cy="20" r="16" fill="none"
                                stroke="var(--color-border)" strokeWidth="3" />
                        <circle cx="20" cy="20" r="16" fill="none"
                                stroke="var(--color-accent)" strokeWidth="3"
                                strokeDasharray={`${progressPct} ${100 - progressPct}`}
                                strokeDashoffset="25"
                                strokeLinecap="round"
                                style={{ transition: "stroke-dasharray 1s ease" }} />
                    </svg>
                    <div className="hv-stat-text">
                        <span className="hv-stat-value">{progressPct}%</span>
                        <span className="hv-stat-label">{stats.programLabel}</span>
                    </div>
                </div>

                <div className="hv-stat" style={{ animationDelay: "0.2s" }}>
                    <span className="hv-stat-icon">⭐</span>
                    <div className="hv-stat-text">
                        <span className="hv-stat-value">{stats.xpTotal.toLocaleString()}</span>
                        <span className="hv-stat-label">XP earned</span>
                    </div>
                </div>

                <div className="hv-stat" style={{ animationDelay: "0.3s" }}>
                    <span className="hv-stat-icon">🎯</span>
                    <div className="hv-stat-text">
                        <span className="hv-stat-value">{accuracyPct}%</span>
                        <span className="hv-stat-label">Accuracy</span>
                    </div>
                </div>
            </div>

            {/* ── Quick actions ────────────────────── */}
            <div className="hv-actions">
                <button className="hv-action" onClick={() => onStartSession("quick")}>
                    <span className="hv-action-icon">⚡</span>
                    <div className="hv-action-text">
                        <span className="hv-action-title">Quick Practice</span>
                        <span className="hv-action-sub">5 min · high-success items</span>
                    </div>
                    <span className="hv-action-arrow">›</span>
                </button>

                <button className="hv-action" onClick={() => onStartSession("review")}>
                    <span className="hv-action-icon">🔄</span>
                    <div className="hv-action-text">
                        <span className="hv-action-title">Review Mastered Skills</span>
                        <span className="hv-action-sub">
                            {stats.skillsMastered > 0
                                ? `${stats.skillsMastered} skills to maintain`
                                : "No reviews due yet"}
                        </span>
                    </div>
                    <span className="hv-action-arrow">›</span>
                </button>

                <button className="hv-action" onClick={() => onNavigate("career")}>
                    <span className="hv-action-icon">💼</span>
                    <div className="hv-action-text">
                        <span className="hv-action-title">Career Exploration</span>
                        <span className="hv-action-sub">Discover opportunities</span>
                    </div>
                    <span className="hv-action-arrow">›</span>
                </button>
            </div>

            <style jsx>{`
                .hv {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    padding: 20px 16px;
                    padding-top: max(20px, env(safe-area-inset-top, 20px));
                    max-width: 560px;
                    margin: 0 auto;
                    animation: fadeInUp 0.4s ease-out both;
                }

                /* ── Header ───────────────────────────── */

                .hv-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 12px;
                }

                .hv-greeting-area {
                    flex: 1;
                    min-width: 0;
                }

                .hv-greeting {
                    font-family: var(--font-display);
                    font-size: 24px;
                    font-weight: 800;
                    color: var(--color-text);
                    letter-spacing: -0.3px;
                    line-height: 1.2;
                }

                .hv-subtitle {
                    font-size: 14px;
                    color: var(--color-text-secondary);
                    margin-top: 3px;
                    line-height: 1.4;
                }

                .hv-streak-compact {
                    display: flex;
                    align-items: center;
                    gap: 3px;
                    padding: 6px 10px;
                    background: var(--color-bg-sidebar);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-full);
                    flex-shrink: 0;
                }

                .hv-streak-fire { font-size: 16px; }

                .hv-streak-num {
                    font-family: var(--font-display);
                    font-size: 18px;
                    font-weight: 800;
                    color: var(--color-streak);
                    line-height: 1;
                }

                .hv-shield-badge {
                    font-size: 12px;
                    margin-left: 1px;
                }

                /* ── Primary card ─────────────────────── */

                .hv-primary-card {
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                    padding: 22px 20px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-card);
                    cursor: pointer;
                    text-align: left;
                    font-family: var(--font-body);
                    transition: all var(--transition-fast);
                    -webkit-tap-highlight-color: transparent;
                    width: 100%;
                }

                .hv-primary-card:hover {
                    border-color: var(--color-accent);
                    box-shadow: var(--shadow-glow);
                    transform: translateY(-2px);
                }

                .hv-primary-card:active {
                    transform: translateY(0);
                }

                .hv-primary-top {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .hv-program-tag {
                    font-size: 11px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--color-accent);
                    padding: 2px 8px;
                    background: var(--color-accent-soft);
                    border-radius: var(--radius-full);
                }

                .hv-time-tag {
                    font-size: 12px;
                    color: var(--color-text-muted);
                    font-weight: 500;
                }

                .hv-primary-title {
                    font-family: var(--font-display);
                    font-size: 22px;
                    font-weight: 700;
                    color: var(--color-text);
                    line-height: 1.2;
                }

                .hv-primary-subtitle {
                    font-size: 14px;
                    color: var(--color-text-secondary);
                    line-height: 1.3;
                }

                .hv-skill-progress {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }

                .hv-skill-track {
                    flex: 1;
                    height: 4px;
                    background: var(--color-border);
                    border-radius: 2px;
                    overflow: hidden;
                }

                .hv-skill-fill {
                    height: 100%;
                    background: var(--color-accent);
                    border-radius: 2px;
                    transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
                }

                .hv-skill-pct {
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--color-text-muted);
                    font-variant-numeric: tabular-nums;
                    min-width: 32px;
                    text-align: right;
                }

                .hv-primary-cta {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    margin-top: 4px;
                    background: var(--color-accent);
                    color: white;
                    border-radius: var(--radius-md);
                    transition: filter var(--transition-fast);
                }

                .hv-primary-card:hover .hv-primary-cta {
                    filter: brightness(1.08);
                }

                .hv-cta-text {
                    font-size: 15px;
                    font-weight: 700;
                }

                .hv-cta-arrow {
                    font-size: 20px;
                    font-weight: 300;
                    transition: transform var(--transition-fast);
                }

                .hv-primary-card:hover .hv-cta-arrow {
                    transform: translateX(4px);
                }

                /* ── Stats ────────────────────────────── */

                .hv-stats {
                    display: flex;
                    gap: 10px;
                }

                .hv-stat {
                    flex: 1;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 12px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    animation: fadeInUp 0.35s ease-out both;
                }

                .hv-ring {
                    width: 36px;
                    height: 36px;
                    flex-shrink: 0;
                    transform: rotate(-90deg);
                }

                .hv-stat-icon {
                    font-size: 20px;
                    flex-shrink: 0;
                }

                .hv-stat-text {
                    display: flex;
                    flex-direction: column;
                    min-width: 0;
                }

                .hv-stat-value {
                    font-family: var(--font-display);
                    font-size: 18px;
                    font-weight: 800;
                    color: var(--color-text);
                    line-height: 1;
                }

                .hv-stat-label {
                    font-size: 10px;
                    color: var(--color-text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.3px;
                    font-weight: 600;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* ── Quick actions ─────────────────────── */

                .hv-actions {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .hv-action {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 14px 16px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    cursor: pointer;
                    font-family: var(--font-body);
                    text-align: left;
                    width: 100%;
                    transition: all var(--transition-fast);
                    -webkit-tap-highlight-color: transparent;
                }

                .hv-action:hover {
                    border-color: var(--color-accent);
                    transform: translateX(4px);
                }

                .hv-action:active {
                    transform: translateX(2px);
                }

                .hv-action-icon {
                    font-size: 20px;
                    flex-shrink: 0;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--color-bg-sidebar);
                    border-radius: var(--radius-sm);
                }

                .hv-action-text {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    gap: 1px;
                    min-width: 0;
                }

                .hv-action-title {
                    font-size: 14px;
                    font-weight: 600;
                    color: var(--color-text);
                }

                .hv-action-sub {
                    font-size: 12px;
                    color: var(--color-text-muted);
                }

                .hv-action-arrow {
                    font-size: 20px;
                    color: var(--color-text-muted);
                    flex-shrink: 0;
                    transition: transform var(--transition-fast);
                }

                .hv-action:hover .hv-action-arrow {
                    transform: translateX(3px);
                    color: var(--color-accent);
                }

                /* ── Responsive ────────────────────────── */

                @media (min-width: 768px) {
                    .hv {
                        padding: 32px 24px;
                        gap: 24px;
                    }

                    .hv-greeting {
                        font-size: 30px;
                    }

                    .hv-primary-title {
                        font-size: 26px;
                    }
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}

function getGreeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 17) return "Good afternoon";
    return "Good evening";
}
