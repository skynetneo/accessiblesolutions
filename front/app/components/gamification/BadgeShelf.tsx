import type { ReactNode } from "react";

export function BadgeShelf({ badges }: { badges: ReactNode[] }) {
    return (
        <div className="badge-shelf">
            {badges.length === 0 ? (
                <div className="empty-shelf">
                    <span className="empty-icon">🏆</span>
                    <p>No badges yet</p>
                    <p className="empty-sub">Keep learning to earn some!</p>
                </div>
            ) : (
                <div className="badges-grid">
                    {badges.map((badge, i) => (
                        <div key={i} className="badge-item">
                            {badge}
                        </div>
                    ))}
                </div>
            )}
            <style dangerouslySetInnerHTML={{ __html: `
                .badge-shelf {
                    background: var(--color-bg-card, rgba(0, 0, 0, 0.05));
                    border-radius: var(--radius-md, 8px);
                    padding: 16px;
                    border: 1px solid var(--color-border, rgba(0, 0, 0, 0.1));
                }
                .empty-shelf {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    text-align: center;
                    padding: 16px 0;
                    color: var(--color-text-muted, #888);
                }
                .empty-icon {
                    font-size: 24px;
                    margin-bottom: 8px;
                    opacity: 0.5;
                }
                .empty-shelf p {
                    margin: 0;
                    font-size: 13px;
                }
                .empty-sub {
                    font-size: 11px !important;
                    margin-top: 4px !important;
                    opacity: 0.7;
                }
                .badges-grid {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                }
                .badge-item {
                    width: 40px;
                    height: 40px;
                    background: var(--color-accent, #007bff);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 18px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                }
            `}} />
        </div>
    );
}
