export function StreakCounter({ streak }: { streak: number }) {
    const isActive = streak > 0;

    return (
        <div className={`streak-container ${isActive ? 'active' : ''}`}>
            <span className="streak-icon">{isActive ? '🔥' : '⏸️'}</span>
            <div className="streak-info">
                <span className="streak-count">{streak} Day Streak</span>
                <span className="streak-sub">{isActive ? 'Keep it up!' : 'Start your learning habit'}</span>
            </div>
            <style dangerouslySetInnerHTML={{
                __html: `
                .streak-container {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 12px;
                    background: var(--color-bg-card, rgba(0, 0, 0, 0.03));
                    border-radius: var(--radius-md, 8px);
                    border: 1px solid var(--color-border, rgba(0,0,0,0.1));
                    transition: all 0.2s ease;
                }
                .streak-container.active {
                    border-color: rgba(255, 152, 0, 0.3);
                    background: rgba(255, 152, 0, 0.05);
                }
                .streak-icon {
                    font-size: 24px;
                    filter: grayscale(1);
                    opacity: 0.5;
                    transition: all 0.3s ease;
                }
                .streak-container.active .streak-icon {
                    filter: grayscale(0);
                    opacity: 1;
                    animation: pulse 2s infinite;
                }
                .streak-info {
                    display: flex;
                    flex-direction: column;
                }
                .streak-count {
                    font-size: 14px;
                    font-weight: 700;
                    color: var(--color-text, #333);
                }
                .streak-sub {
                    font-size: 11px;
                    color: var(--color-text-muted, #888);
                }
                @keyframes pulse {
                    0% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                    100% { transform: scale(1); }
                }
            `}} />
        </div>
    );
}
