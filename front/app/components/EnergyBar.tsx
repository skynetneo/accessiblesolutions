"use client";

/**
 * EnergyBar — cognitive energy indicator.
 *
 * Shows a depleting energy bar that changes color based on level:
 *   100-60: green (fresh)
 *   60-30:  amber (working)
 *   30-10:  orange (tiring)
 *   10-0:   red (depleted)
 *
 * Suggests breaks based on energy level, not time.
 * Never blocks the learner — just suggests.
 */

interface EnergyBarProps {
    energy: number;          // 0-100
    shouldSuggestBreak: boolean;
    shouldInsistBreak: boolean;
    itemsCompleted: number;
    elapsedMinutes: number;
    onTakeBreak?: () => void;
}

export function EnergyBar({
    energy,
    shouldSuggestBreak,
    shouldInsistBreak,
    itemsCompleted,
    elapsedMinutes,
    onTakeBreak,
}: EnergyBarProps) {
    const pct = Math.max(0, Math.min(100, energy));
    const color =
        pct > 60 ? "var(--color-success)" :
        pct > 30 ? "var(--color-warn)" :
        pct > 10 ? "var(--color-accent)" :
        "#e74c3c";

    const bgColor =
        pct > 60 ? "var(--color-success-soft)" :
        pct > 30 ? "var(--color-warn-soft)" :
        pct > 10 ? "var(--color-accent-soft)" :
        "#fde8e8";

    return (
        <div className="eb-container">
            <div className="eb-header">
                <span className="eb-label">
                    {pct > 60 ? "⚡" : pct > 30 ? "🔋" : "🪫"} Energy
                </span>
                <span className="eb-stats">
                    {itemsCompleted} items · {elapsedMinutes.toFixed(0)}m
                </span>
            </div>

            <div className="eb-track">
                <div
                    className="eb-fill"
                    style={{
                        width: `${pct}%`,
                        background: color,
                    }}
                />
            </div>

            {/* Break suggestion */}
            {shouldSuggestBreak && !shouldInsistBreak && (
                <div className="eb-suggest">
                    <span>Nice work so far! A quick break might help you stay sharp.</span>
                    {onTakeBreak && (
                        <button className="eb-break-btn" onClick={onTakeBreak}>
                            Take a breather
                        </button>
                    )}
                </div>
            )}

            {shouldInsistBreak && (
                <div className="eb-insist">
                    <span>You&apos;ve been going hard. Even a 30-second pause helps your brain absorb what you&apos;ve learned.</span>
                    {onTakeBreak && (
                        <button className="eb-break-btn eb-break-primary" onClick={onTakeBreak}>
                            Recharge
                        </button>
                    )}
                </div>
            )}

            <style jsx>{`
                .eb-container {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }

                .eb-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: baseline;
                }

                .eb-label {
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--color-text-secondary);
                }

                .eb-stats {
                    font-size: 11px;
                    color: var(--color-text-muted);
                    font-variant-numeric: tabular-nums;
                }

                .eb-track {
                    height: 6px;
                    background: var(--color-border);
                    border-radius: 3px;
                    overflow: hidden;
                }

                .eb-fill {
                    height: 100%;
                    border-radius: 3px;
                    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1),
                                background 0.6s ease;
                    min-width: 2px;
                }

                .eb-suggest,
                .eb-insist {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    padding: 10px 12px;
                    border-radius: var(--radius-sm);
                    font-size: 12px;
                    line-height: 1.4;
                    animation: fadeInUp 0.3s ease-out both;
                }

                .eb-suggest {
                    background: var(--color-info-soft);
                    color: var(--color-info);
                }

                .eb-insist {
                    background: var(--color-warn-soft);
                    color: var(--color-text);
                }

                .eb-break-btn {
                    align-self: flex-start;
                    padding: 6px 14px;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-full);
                    background: var(--color-bg-card);
                    font-family: var(--font-body);
                    font-size: 12px;
                    font-weight: 600;
                    cursor: pointer;
                    color: var(--color-text-secondary);
                    transition: all var(--transition-fast);
                }

                .eb-break-btn:hover {
                    border-color: var(--color-accent);
                    color: var(--color-accent);
                }

                .eb-break-primary {
                    background: var(--color-accent);
                    color: white;
                    border-color: var(--color-accent);
                }

                .eb-break-primary:hover {
                    filter: brightness(1.1);
                    color: white;
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(6px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        </div>
    );
}
