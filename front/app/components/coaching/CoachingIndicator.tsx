export function CoachingIndicator({ mode }: { mode: string }) {
    const isCoaching = mode === 'teaching' || mode === 'coaching';

    if (!isCoaching) return null;

    return (
        <div className="coaching-indicator">
            <span className="coaching-dot"></span>
            <span className="coaching-text">Teaching Mode Active</span>
            <style dangerouslySetInnerHTML={{ __html: `
                .coaching-indicator {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    padding: 8px 16px;
                    background: rgba(var(--color-accent-rgb, 0, 123, 255), 0.1);
                    border: 1px solid rgba(var(--color-accent-rgb, 0, 123, 255), 0.2);
                    border-radius: var(--radius-full, 99px);
                    align-self: flex-start;
                    margin: 16px 24px 0;
                    font-size: 13px;
                    font-weight: 600;
                    color: var(--color-accent, #007bff);
                    animation: slideIn 0.3s ease;
                }
                .coaching-dot {
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: var(--color-accent, #007bff);
                    box-shadow: 0 0 8px rgba(var(--color-accent-rgb, 0, 123, 255), 0.6);
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(var(--color-accent-rgb, 0, 123, 255), 0.7); }
                    70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(var(--color-accent-rgb, 0, 123, 255), 0); }
                    100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(var(--color-accent-rgb, 0, 123, 255), 0); }
                }
                @keyframes slideIn {
                    from { transform: translateY(-10px); opacity: 0; }
                    to { transform: translateY(0); opacity: 1; }
                }
            `}} />
        </div>
    );
}
