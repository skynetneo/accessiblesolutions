interface SubagentSummary {
    name?: string | null;
    status?: string | null;
}

export function SubagentCard({ subagent }: { subagent?: SubagentSummary | null }) {
    return (
        <div className="subagent-card">
            <div className="subagent-icon">🤖</div>
            <div className="subagent-info">
                <span className="subagent-name">{subagent?.name || "Agent"}</span>
                <span className="subagent-status">{subagent?.status || "Active"}</span>
            </div>
            <style dangerouslySetInnerHTML={{ __html: `
                .subagent-card {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    background: var(--color-bg-card, #f8f9fa);
                    border: 1px solid var(--color-border, #eee);
                    padding: 8px 16px;
                    border-radius: var(--radius-md, 8px);
                    box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                    transition: all 0.2s ease;
                }
                .subagent-card:hover {
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                    transform: translateY(-1px);
                }
                .subagent-icon {
                    font-size: 20px;
                }
                .subagent-info {
                    display: flex;
                    flex-direction: column;
                }
                .subagent-name {
                    font-size: 13px;
                    font-weight: 700;
                    color: var(--color-text, #333);
                }
                .subagent-status {
                    font-size: 11px;
                    color: var(--color-success, #28a745);
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                .subagent-status::before {
                    content: "";
                    display: inline-block;
                    width: 6px;
                    height: 6px;
                    background: var(--color-success, #28a745);
                    border-radius: 50%;
                }
            `}} />
        </div>
    );
}
