"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

interface ThemePreset {
    id: string;
    name: string;
    swatch: { bg: string; accent: string; text: string };
}

const PRESETS: ThemePreset[] = [
    { id: "obsidian", name: "Obsidian", swatch: { bg: "#0a0a0c", accent: "#e07a3a", text: "#e8e4df" } },
    { id: "ember", name: "Ember", swatch: { bg: "#0c0908", accent: "#e85530", text: "#f0e8e0" } },
    { id: "abyss", name: "Abyss", swatch: { bg: "#06080e", accent: "#4090ff", text: "#dce4f0" } },
    { id: "void", name: "Void", swatch: { bg: "#08060c", accent: "#b050e8", text: "#e4ddf0" } },
    { id: "carbon", name: "Carbon", swatch: { bg: "#101012", accent: "#20c0a0", text: "#e0e0e4" } },
    { id: "aurora", name: "Aurora", swatch: { bg: "#060a0c", accent: "#30e8a0", text: "#d8f0e8" } },
    { id: "rosegold", name: "Rosé", swatch: { bg: "#181418", accent: "#e08878", text: "#f0e4e8" } },
    { id: "snow", name: "Snow", swatch: { bg: "#f8f9fb", accent: "#3060d0", text: "#1a1d24" } },
];

const STORAGE_KEY = "praxis-theme";
const CUSTOM_KEY = "praxis-theme-custom";
const LEGACY_STORAGE_KEY = "upskill-theme";
const LEGACY_CUSTOM_KEY = "upskill-theme-custom";

interface CustomOverrides {
    accent?: string;
    bg?: string;
    text?: string;
}

function safeSetSessionStorage(key: string, value: string): void {
    try {
        sessionStorage.setItem(key, value);
    } catch (error) {
        console.debug("ThemePicker: failed to write sessionStorage", { key, error });
    }
}

function safeRemoveSessionStorage(key: string): void {
    try {
        sessionStorage.removeItem(key);
    } catch (error) {
        console.debug("ThemePicker: failed to remove sessionStorage", { key, error });
    }
}

export function ThemePicker() {
    const initial = useMemo(() => getInitialThemeState(), []);
    const [open, setOpen] = useState(false);
    const [activeTheme, setActiveTheme] = useState(initial.theme);
    const [customMode, setCustomMode] = useState(initial.customMode);
    const [overrides, setOverrides] = useState<CustomOverrides>(initial.overrides);

    useEffect(() => {
        document.documentElement.setAttribute("data-theme", activeTheme);
        if (customMode) {
            applyCustomOverrides(overrides);
        } else {
            clearCustomOverrides();
        }
    }, [activeTheme, customMode, overrides]);

    const selectPreset = useCallback((id: string) => {
        setActiveTheme(id);
        setCustomMode(false);
        setOverrides({});
        safeSetSessionStorage(STORAGE_KEY, id);
        safeRemoveSessionStorage(CUSTOM_KEY);
    }, []);

    const updateCustomColor = useCallback((key: keyof CustomOverrides, value: string) => {
        setCustomMode(true);
        setOverrides((prev) => {
            const next = { ...prev, [key]: value };
            safeSetSessionStorage(CUSTOM_KEY, JSON.stringify(next));
            return next;
        });
    }, []);

    const resetCustom = useCallback(() => {
        setCustomMode(false);
        setOverrides({});
        safeRemoveSessionStorage(CUSTOM_KEY);
    }, []);

    return (
        <div className="tp-wrapper">
            <button
                className="tp-trigger"
                onClick={() => setOpen(!open)}
                title="Change theme"
                aria-label="Open theme picker"
            >
                <span className="tp-trigger-swatch" />
                <span className="tp-trigger-label">Theme</span>
            </button>

            {open && (
                <div className="tp-dropdown">
                    <div className="tp-section">
                        <span className="tp-section-label">Presets</span>
                        <div className="tp-presets">
                            {PRESETS.map((preset) => (
                                <button
                                    key={preset.id}
                                    className={`tp-preset ${activeTheme === preset.id && !customMode ? "tp-preset-active" : ""}`}
                                    onClick={() => selectPreset(preset.id)}
                                    title={preset.name}
                                >
                                    <span
                                        className="tp-swatch"
                                        style={{ background: preset.swatch.bg }}
                                    >
                                        <span
                                            className="tp-swatch-dot"
                                            style={{ background: preset.swatch.accent }}
                                        />
                                    </span>
                                    <span className="tp-preset-name">{preset.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="tp-divider" />

                    <div className="tp-section">
                        <span className="tp-section-label">
                            Customize
                            {customMode && (
                                <button className="tp-reset" onClick={resetCustom}>Reset</button>
                            )}
                        </span>
                        <div className="tp-custom-grid">
                            <label className="tp-color-field">
                                <span className="tp-color-label">Accent</span>
                                <input
                                    type="color"
                                    value={overrides.accent || getCurrentVar("--color-accent")}
                                    onChange={(e) => updateCustomColor("accent", e.target.value)}
                                />
                            </label>
                            <label className="tp-color-field">
                                <span className="tp-color-label">Background</span>
                                <input
                                    type="color"
                                    value={overrides.bg || getCurrentVar("--color-bg")}
                                    onChange={(e) => updateCustomColor("bg", e.target.value)}
                                />
                            </label>
                            <label className="tp-color-field">
                                <span className="tp-color-label">Text</span>
                                <input
                                    type="color"
                                    value={overrides.text || getCurrentVar("--color-text")}
                                    onChange={(e) => updateCustomColor("text", e.target.value)}
                                />
                            </label>
                        </div>
                    </div>
                </div>
            )}

            <style dangerouslySetInnerHTML={{ __html: `
                .tp-wrapper {
                    position: relative;
                }
                .tp-trigger {
                    display: flex; align-items: center; gap: 8px;
                    padding: 8px 14px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-md);
                    cursor: pointer;
                    font-family: var(--font-body);
                    font-size: 13px;
                    color: var(--color-text-secondary);
                    transition: all var(--transition-fast);
                }
                .tp-trigger:hover {
                    border-color: var(--color-border-active);
                }
                .tp-trigger-swatch {
                    width: 16px; height: 16px;
                    border-radius: var(--radius-full);
                    background: var(--color-accent);
                    border: 2px solid var(--color-bg);
                    box-shadow: 0 0 0 1px var(--color-border);
                }
                .tp-trigger-label { font-weight: 600; }

                .tp-dropdown {
                    position: absolute;
                    bottom: calc(100% + 8px);
                    left: 0;
                    width: 260px;
                    background: var(--color-bg-card);
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-lg);
                    box-shadow: var(--shadow-elevated);
                    padding: 16px;
                    z-index: 500;
                    animation: fadeInUp 0.2s ease-out both;
                }
                .tp-section {
                    display: flex; flex-direction: column; gap: 10px;
                }
                .tp-section-label {
                    font-size: 11px; text-transform: uppercase;
                    letter-spacing: 1px; font-weight: 700;
                    color: var(--color-text-muted);
                    display: flex; align-items: center; justify-content: space-between;
                }
                .tp-reset {
                    font-size: 11px; color: var(--color-accent);
                    background: none; border: none; cursor: pointer;
                    font-weight: 600; text-transform: none; letter-spacing: 0;
                }
                .tp-reset:hover { text-decoration: underline; }
                .tp-divider {
                    height: 1px; background: var(--color-border);
                    margin: 12px 0;
                }

                .tp-presets {
                    display: grid; grid-template-columns: 1fr 1fr;
                    gap: 6px;
                }
                .tp-preset {
                    display: flex; align-items: center; gap: 8px;
                    padding: 8px 10px;
                    border: 2px solid transparent;
                    border-radius: var(--radius-md);
                    background: var(--color-bg);
                    cursor: pointer;
                    font-family: var(--font-body);
                    font-size: 12px;
                    transition: all var(--transition-fast);
                }
                .tp-preset:hover {
                    border-color: var(--color-border);
                }
                .tp-preset-active {
                    border-color: var(--color-accent) !important;
                }
                .tp-swatch {
                    width: 24px; height: 24px;
                    border-radius: var(--radius-full);
                    border: 1px solid rgba(0,0,0,0.1);
                    display: flex; align-items: center; justify-content: center;
                    flex-shrink: 0;
                }
                .tp-swatch-dot {
                    width: 10px; height: 10px;
                    border-radius: var(--radius-full);
                }
                .tp-preset-name {
                    font-weight: 600;
                    color: var(--color-text);
                }

                .tp-custom-grid {
                    display: flex; gap: 12px;
                }
                .tp-color-field {
                    display: flex; flex-direction: column;
                    align-items: center; gap: 4px;
                    flex: 1;
                }
                .tp-color-label {
                    font-size: 11px; font-weight: 600;
                    color: var(--color-text-secondary);
                }
                .tp-color-field input[type="color"] {
                    width: 100%; height: 32px;
                    border: 1px solid var(--color-border);
                    border-radius: var(--radius-sm);
                    padding: 2px;
                    cursor: pointer;
                    background: var(--color-bg);
                }

                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(8px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}} />
        </div>
    );
}

// ── Helpers ──────────────────────────────────────────────────

function applyCustomOverrides(overrides: CustomOverrides) {
    const root = document.documentElement;
    if (overrides.accent) {
        root.style.setProperty("--color-accent", overrides.accent);
        root.style.setProperty("--color-border-active", overrides.accent);
        root.style.setProperty("--color-xp", overrides.accent);
        // Generate a soft version (crude but effective)
        root.style.setProperty("--color-accent-soft", overrides.accent + "22");
        root.style.setProperty("--shadow-glow", `0 0 20px ${overrides.accent}26`);
    }
    if (overrides.bg) {
        root.style.setProperty("--color-bg", overrides.bg);
    }
    if (overrides.text) {
        root.style.setProperty("--color-text", overrides.text);
    }
}

function clearCustomOverrides() {
    const root = document.documentElement;
    [
        "--color-accent", "--color-border-active", "--color-xp",
        "--color-accent-soft", "--shadow-glow",
        "--color-bg", "--color-text",
    ].forEach((prop) => root.style.removeProperty(prop));
}

function getCurrentVar(name: string): string {
    if (typeof window === "undefined") return "#888888";
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888888";
}

function getInitialThemeState(): {
    theme: string;
    customMode: boolean;
    overrides: CustomOverrides;
} {
    if (typeof window === "undefined") {
        return { theme: "obsidian", customMode: false, overrides: {} };
    }

    let theme = "obsidian";
    let overrides: CustomOverrides = {};

    try {
        const saved = sessionStorage.getItem(STORAGE_KEY) ?? sessionStorage.getItem(LEGACY_STORAGE_KEY);
        const custom = sessionStorage.getItem(CUSTOM_KEY) ?? sessionStorage.getItem(LEGACY_CUSTOM_KEY);

        // One-time migration: preserve existing user theme settings under new Praxis keys.
        if (!sessionStorage.getItem(STORAGE_KEY) && saved) {
            sessionStorage.setItem(STORAGE_KEY, saved);
        }
        if (!sessionStorage.getItem(CUSTOM_KEY) && custom) {
            sessionStorage.setItem(CUSTOM_KEY, custom);
        }
        if (sessionStorage.getItem(LEGACY_STORAGE_KEY)) {
            sessionStorage.removeItem(LEGACY_STORAGE_KEY);
        }
        if (sessionStorage.getItem(LEGACY_CUSTOM_KEY)) {
            sessionStorage.removeItem(LEGACY_CUSTOM_KEY);
        }

        if (saved) theme = saved;
        if (custom) {
            const parsed = JSON.parse(custom) as CustomOverrides;
            if (parsed && typeof parsed === "object") {
                overrides = parsed;
            }
        }
    } catch {
        // ignore storage parse failures and use defaults
    }

    return {
        theme,
        customMode: Object.keys(overrides).length > 0,
        overrides,
    };
}
