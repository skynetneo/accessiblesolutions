"use client";

/**
 * SessionSummary — post-session reward card.
 *
 * Shows what the learner accomplished:
 *   - Items completed + accuracy
 *   - XP earned
 *   - Streak status
 *   - Skills practiced
 *   - Ikigai convergence change
 *   - "What's next" preview
 *
 * This is the reward moment — the learner sees the tangible
 * output of their effort. Keep it warm, specific, and brief.
 */

interface SessionSummaryProps {
    itemsCompleted: number;
    accuracy: number;             // 0-1
    xpEarned: number;
    xpTotal: number;
    streak: number;
    streakMessage?: string;
    skillsPracticed: string[];
    convergenceBefore: number;    // 0-1
    convergenceAfter: number;     // 0-1
    sessionMinutes: number;
    nextRecommendation: string;
    onContinue: () => void;
    onDone: () => void;
}

export function SessionSummary({
    itemsCompleted,
    accuracy,
    xpEarned,
    xpTotal,
    streak,
    streakMessage,
    skillsPracticed,
    convergenceBefore,
    convergenceAfter,
    sessionMinutes,
    nextRecommendation,
    onContinue,
    onDone,
}: SessionSummaryProps) {
    const convergenceDelta = convergenceAfter - convergenceBefore;
    const accuracyPct = Math.round(accuracy * 100);

    return (
        <div className="ss-overlay">
            <div className="ss-card">
                {/* Header */}
                <div className="ss-header">
                    <h2 className="ss-title">Session Complete</h2>
                    <p className="ss-duration">{sessionMinutes.toFixed(0)} minutes</p>
                </div>

                {/* Stats grid */}
                <div className="ss-stats">
                    <div className="ss-stat" style={{ animationDelay: "0.1s" }}>
                        <span className="ss-stat-icon">📝</span>
                        <span className="ss-stat-value">{itemsCompleted}</span>
                        <span className="ss-stat-label">Items</span>
                    </div>
                    <div className="ss-stat" style={{ animationDelay: "0.2s" }}>
                        <span className="ss-stat-icon">🎯</span>
                        <span className="ss-stat-value">{accuracyPct}%</span>
                        <span className="ss-stat-label">Accuracy</span>
                    </div>
                    <div className="ss-stat" style={{ animationDelay: "0.3s" }}>
                        <span className="ss-stat-icon">⭐</span>
                        <span className="ss-stat-value">+{xpEarned}</span>
                        <span className="ss-stat-label">XP</span>
                    </div>
                    <div className="ss-stat" style={{ animationDelay: "0.4s" }}>
                        <span className="ss-stat-icon">🔥</span>
                        <span className="ss-stat-value">{streak}</span>
                        <span className="ss-stat-label">Streak</span>
                    </div>
                </div>

                {/* Streak message */}
                {streakMessage && (
                    <div className="ss-streak-msg">{streakMessage}</div>
                )}

                {/* Skills practiced */}
                {skillsPracticed.length > 0 && (
                    <div className="ss-skills">
                        <span className="ss-section-label">Skills practiced</span>
                        <div className="ss-skill-chips">
                            {skillsPracticed.map((skill, i) => (
                                <span key={i} className="ss-chip">{skill}</span>
                            ))}
                        </div>
                    </div>
                )}

                {/* Ikigai convergence change */}
                {convergenceDelta !== 0 && (
                    <div className={`ss-convergence ${convergenceDelta > 0 ? "ss-conv-up" : "ss-conv-down"}`}>
                        <span className="ss-conv-label">Ikigai Alignment</span>
                        <span className="ss-conv-delta">
                            {convergenceDelta > 0 ? "+" : ""}{(convergenceDelta * 100).toFixed(1)}%
                        </span>
                    </div>
                )}

                {/* Next recommendation */}
                <div className="ss-next">
                    <span className="ss-section-label">Up next</span>
                    <p className="ss-next-text">{nextRecommendation}</p>
                </div>

                {/* Actions */}
                <div className="ss-actions">
                    <button className="ss-btn-primary" onClick={onContinue}>
                        Keep Going
                    </button>
                    <button className="ss-btn-secondary" onClick={onDone}>
                        Done for now
                    </button>
                </div>
            </div>

            <style jsx>{`
                .ss-overlay {
                    position: fixed;
                    inset: 0;
                    z-index: 800;
                    background: rgba(44, 37, 32, 0.4);
                    backdrop-filter: blur(6px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    animation: fadeIn 0.3s ease-out;
                }

                .ss-card {
                    width: 90%;
                    max-width: 440px;
                    background: var(--color-bg);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-elevated);
                    padding: 28px;
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                    animation: modalPop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both;
                }

                .ss-header {
                    text-align: center;
                }

                .ss-title {
                    font-family: var(--font-display);
                    font-size: 28px;
                    font-weight: 800;
                    color: var(--color-text);
                }

                .ss-duration {
                    font-size: 14px;
                    color: var(--color-text-muted);
                    margin-top: 2px;
                }

                .ss-stats {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 8px;
                }

                .ss-stat {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 2px;
                    padding: 12px 8px;
                    background: var(--color-bg-sidebar);
                    border-radius: var(--radius-md);
                    animation: fadeInUp 0.3s ease-out both;
                }

                .ss-stat-icon { font-size: 20px; }

                .ss-stat-value {
                    font-family: var(--font-display);
                    font-size: 22px;
                    font-weight: 800;
                    color: var(--color-text);
                    line-height: 1;
                }

                .ss-stat-label {
                    font-size: 10px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--color-text-muted);
                    font-weight: 600;
                }

                .ss-streak-msg {
                    text-align: center;
                    font-size: 13px;
                    color: var(--color-success);
                    font-weight: 600;
                    padding: 8px 12px;
                    background: var(--color-success-soft);
                    border-radius: var(--radius-sm);
                    animation: fadeInUp 0.3s ease-out 0.5s both;
                }

                .ss-skills {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .ss-section-label {
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                    color: var(--color-text-muted);
                    font-weight: 600;
                }

                .ss-skill-chips {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 4px;
                }

                .ss-chip {
                    padding: 3px 10px;
                    background: var(--color-bg-sidebar);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-full);
                    font-size: 12px;
                    color: var(--color-text-secondary);
                }

                .ss-convergence {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px 14px;
                    border-radius: var(--radius-sm);
                    animation: fadeInUp 0.3s ease-out 0.6s both;
                }

                .ss-conv-up {
                    background: var(--color-success-soft);
                }

                .ss-conv-down {
                    background: var(--color-warn-soft);
                }

                .ss-conv-label {
                    font-size: 12px;
                    color: var(--color-text-secondary);
                    font-weight: 500;
                }

                .ss-conv-delta {
                    font-family: var(--font-display);
                    font-size: 18px;
                    font-weight: 800;
                    color: var(--color-success);
                }

                .ss-conv-down .ss-conv-delta {
                    color: var(--color-warn);
                }

                .ss-next {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }

                .ss-next-text {
                    font-size: 14px;
                    color: var(--color-text-secondary);
                    line-height: 1.4;
                }

                .ss-actions {
                    display: flex;
                    gap: 10px;
                    margin-top: 4px;
                }

                .ss-btn-primary {
                    flex: 1;
                    padding: 14px;
                    background: var(--color-accent);
                    color: white;
                    border: none;
                    border-radius: var(--radius-md);
                    font-family: var(--font-body);
                    font-size: 15px;
                    font-weight: 700;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .ss-btn-primary:hover {
                    filter: brightness(1.1);
                    transform: translateY(-1px);
                }

                .ss-btn-secondary {
                    flex: 1;
                    padding: 14px;
                    background: var(--color-bg-sidebar);
                    color: var(--color-text-secondary);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    font-family: var(--font-body);
                    font-size: 15px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                }

                .ss-btn-secondary:hover {
                    border-color: var(--color-text-muted);
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
            `}</style>
        </div>
    );
}
