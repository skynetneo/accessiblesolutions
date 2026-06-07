export function CelebrationOverlay({ xp, badge, onDone }: { xp: number; badge?: string; onDone: () => void }) {
    return (
        <div className="celebration-overlay" onClick={onDone}>
            <div className="celebration-card" onClick={e => e.stopPropagation()}>
                <div className="celebration-icon">🎉</div>
                <h2 className="celebration-title">Great Job!</h2>

                <div className="celebration-rewards">
                    <div className="reward-item">
                        <span className="reward-value">+{xp}</span>
                        <span className="reward-label">XP</span>
                    </div>
                    {badge && (
                        <div className="reward-item badge-reward">
                            <span className="reward-icon">🏆</span>
                            <span className="reward-label">{badge}</span>
                        </div>
                    )}
                </div>

                <button className="celebration-btn" onClick={onDone}>
                    Continue Learning
                </button>
            </div>

            <style dangerouslySetInnerHTML={{ __html: `
                .celebration-overlay {
                    position: fixed;
                    inset: 0;
                    background: rgba(0, 0, 0, 0.6);
                    backdrop-filter: blur(4px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                    animation: fadeIn 0.3s ease;
                }
                .celebration-card {
                    background: var(--color-bg, #fff);
                    border-radius: var(--radius-lg, 16px);
                    padding: 32px;
                    text-align: center;
                    max-width: 320px;
                    width: 90%;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                    animation: popIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
                }
                .celebration-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                    animation: bounce 1s ease infinite;
                }
                .celebration-title {
                    margin: 0 0 24px;
                    font-size: 24px;
                    color: var(--color-text, #222);
                    font-weight: 800;
                }
                .celebration-rewards {
                    display: flex;
                    justify-content: center;
                    gap: 16px;
                    margin-bottom: 32px;
                }
                .reward-item {
                    background: rgba(var(--color-accent-rgb, 0, 123, 255), 0.1);
                    border: 1px solid rgba(var(--color-accent-rgb, 0, 123, 255), 0.2);
                    padding: 12px 20px;
                    border-radius: var(--radius-md, 8px);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }
                .badge-reward {
                    background: rgba(255, 193, 7, 0.1);
                    border-color: rgba(255, 193, 7, 0.3);
                }
                .reward-value {
                    font-size: 24px;
                    font-weight: 800;
                    color: var(--color-accent, #007bff);
                }
                .reward-icon {
                    font-size: 24px;
                    margin-bottom: 4px;
                }
                .reward-label {
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-weight: 600;
                    color: var(--color-text-muted, #666);
                    margin-top: 4px;
                }
                .celebration-btn {
                    background: var(--color-accent, #007bff);
                    color: white;
                    border: none;
                    padding: 14px 24px;
                    font-size: 16px;
                    font-weight: 600;
                    border-radius: var(--radius-full, 99px);
                    cursor: pointer;
                    width: 100%;
                    transition: transform 0.2s;
                }
                .celebration-btn:hover {
                    transform: scale(1.05);
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes popIn {
                    from { transform: scale(0.8); opacity: 0; }
                    to { transform: scale(1); opacity: 1; }
                }
                @keyframes bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }
            `}} />
        </div>
    );
}
