export function XPBar({ xp, level, progress }: { xp: number; level: number; progress: number }) {
    return (
        <div className="xp-container">
            <div className="xp-header">
                <span className="xp-level">Lvl {level}</span>
                <span className="xp-amount">{xp} XP</span>
            </div>
            <div className="xp-track">
                <div className="xp-fill" style={{ width: `${progress}%` }} />
            </div>
            <style dangerouslySetInnerHTML={{ __html: `
                .xp-container {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                .xp-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-end;
                    font-size: 12px;
                    font-weight: 600;
                    color: var(--color-text, #333);
                }
                .xp-amount {
                    color: var(--color-accent, #007bff);
                }
                .xp-track {
                    height: 8px;
                    background: var(--color-border, #eee);
                    border-radius: 4px;
                    overflow: hidden;
                }
                .xp-fill {
                    height: 100%;
                    background: var(--color-accent, #007bff);
                    border-radius: 4px;
                    transition: width 0.3s ease;
                }
            `}} />
        </div>
    );
}
