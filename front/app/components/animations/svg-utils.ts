export function parseFraction(s: string): [number, number] {
    const parts = s.split("/").map(Number);
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1]) && parts[1] !== 0) {
        return [parts[0], parts[1]];
    }
    return [0, 1];
}

export function lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
}

export function easeOut(t: number): number {
    return 1 - Math.pow(1 - t, 3);
}


export function scaledMs(ms: number, speed: number): string {
    return `${ms / speed}ms`;
}

export const COLORS = {
    accent: "var(--color-accent)",
    accentSoft: "var(--color-accent-soft)",
    accentDim: "var(--color-accent-dim)",
    text: "var(--color-text)",
    textSecondary: "var(--color-text-secondary)",
    textMuted: "var(--color-text-muted)",
    border: "var(--color-border)",
    surface: "var(--color-surface)",
    background: "var(--color-background)",
};



