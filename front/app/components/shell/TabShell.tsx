"use client";

/**
 * TabShell — the app's main navigation shell.
 *
 * Bottom tab bar (mobile) / side rail (desktop).
 * Tabs: Home, Learn, Path, Ikigai, Profile.
 *
 * Design decisions:
 *   - Tabs mount/unmount on switch (no hidden rendering of inactive views)
 *     EXCEPT Learn, which stays mounted during active sessions to preserve state
 *   - Active tab has a warm accent indicator, not a fill (subtler, more refined)
 *   - Tab labels are hidden on small screens, visible on wider
 *   - The shell renders children via a render prop pattern — parent controls content
 *   - Safe area insets for iOS PWA (notch, home indicator)
 */

import { useState, useCallback } from "react";

export type TabId = "home" | "learn" | "path" | "ikigai" | "profile";

interface TabShellProps {
    activeTab: TabId;
    onTabChange: (tab: TabId) => void;
    sessionActive?: boolean;       // when true, Learn tab pulses
    hasNotification?: Partial<Record<TabId, boolean>>;
    children: React.ReactNode;
}

const TABS: Array<{ id: TabId; label: string; icon: string; activeIcon: string }> = [
    { id: "home",    label: "Home",    icon: "○",  activeIcon: "●" },
    { id: "learn",   label: "Learn",   icon: "📚", activeIcon: "📖" },
    { id: "path",    label: "Path",    icon: "🗺",  activeIcon: "🗺" },
    { id: "ikigai",  label: "Ikigai",  icon: "◎",  activeIcon: "◉" },
    { id: "profile", label: "Profile", icon: "👤", activeIcon: "👤" },
];

export function TabShell({
    activeTab,
    onTabChange,
    sessionActive = false,
    hasNotification = {},
    children,
}: TabShellProps) {
    return (
        <div className="shell">
            {/* Main content area */}
            <main className="shell-content">
                {children}
            </main>

            {/* Tab bar */}
            <nav className="tab-bar" role="tablist">
                {TABS.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const hasNote = hasNotification[tab.id];
                    const isPulsing = tab.id === "learn" && sessionActive && !isActive;

                    return (
                        <button
                            key={tab.id}
                            role="tab"
                            aria-selected={isActive}
                            aria-label={tab.label}
                            className={`tab ${isActive ? "tab-active" : ""} ${isPulsing ? "tab-pulse" : ""}`}
                            onClick={() => onTabChange(tab.id)}
                        >
                            <span className="tab-icon">
                                {isActive ? tab.activeIcon : tab.icon}
                            </span>
                            <span className="tab-label">{tab.label}</span>
                            {hasNote && !isActive && <span className="tab-dot" />}
                            {isActive && <span className="tab-indicator" />}
                        </button>
                    );
                })}
            </nav>

            <style jsx>{`
                .shell {
                    display: flex;
                    flex-direction: column;
                    height: 100vh;
                    height: 100dvh;
                    overflow: hidden;
                    background: var(--color-bg);
                }

                .shell-content {
                    flex: 1;
                    overflow-y: auto;
                    overflow-x: hidden;
                    -webkit-overflow-scrolling: touch;
                }

                /* ── Tab Bar ──────────────────────────── */

                .tab-bar {
                    display: flex;
                    align-items: stretch;
                    background: var(--color-bg-card);
                    border-top: 1px solid var(--color-border);
                    padding-bottom: env(safe-area-inset-bottom, 0);
                    flex-shrink: 0;
                }

                .tab {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 2px;
                    padding: 8px 0 6px;
                    background: none;
                    border: none;
                    cursor: pointer;
                    position: relative;
                    -webkit-tap-highlight-color: transparent;
                    transition: color var(--transition-fast);
                    color: var(--color-text-muted);
                    font-family: var(--font-body);
                }

                .tab:active {
                    transform: scale(0.95);
                }

                .tab-active {
                    color: var(--color-accent);
                }

                .tab-icon {
                    font-size: 20px;
                    line-height: 1;
                    transition: transform var(--transition-fast);
                }

                .tab-active .tab-icon {
                    transform: scale(1.1);
                }

                .tab-label {
                    font-size: 10px;
                    font-weight: 600;
                    letter-spacing: 0.2px;
                }

                .tab-indicator {
                    position: absolute;
                    top: 0;
                    left: 50%;
                    transform: translateX(-50%);
                    width: 20px;
                    height: 2px;
                    background: var(--color-accent);
                    border-radius: 0 0 2px 2px;
                }

                .tab-dot {
                    position: absolute;
                    top: 6px;
                    right: calc(50% - 14px);
                    width: 6px;
                    height: 6px;
                    background: var(--color-accent);
                    border-radius: 50%;
                }

                .tab-pulse .tab-icon {
                    animation: tab-breathe 2s ease-in-out infinite;
                }

                @keyframes tab-breathe {
                    0%, 100% { opacity: 0.5; }
                    50% { opacity: 1; }
                }

                /* ── Desktop: side rail instead of bottom bar ── */

                @media (min-width: 768px) {
                    .shell {
                        flex-direction: row;
                    }

                    .tab-bar {
                        flex-direction: column;
                        width: 72px;
                        border-top: none;
                        border-right: 1px solid var(--color-border);
                        padding: 16px 0;
                        padding-bottom: 0;
                        gap: 4px;
                    }

                    .tab {
                        padding: 12px 0;
                    }

                    .tab-indicator {
                        top: 50%;
                        left: 0;
                        right: auto;
                        transform: translateY(-50%);
                        width: 2px;
                        height: 20px;
                        border-radius: 0 2px 2px 0;
                    }

                    .tab-label {
                        font-size: 9px;
                    }

                    .tab-dot {
                        top: 8px;
                        right: 16px;
                    }
                }
            `}</style>
        </div>
    );
}
