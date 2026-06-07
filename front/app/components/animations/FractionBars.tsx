"use client";

import type { AnimationTemplateProps } from "./types";

export function FractionBars({
    className,
}: AnimationTemplateProps<Record<string, unknown>>) {
    return (
        <svg viewBox="0 0 480 320" className={className ?? "anim-svg"} role="img" aria-label="Fraction bars">
            <text x="240" y="160" textAnchor="middle" fill="currentColor">
                Fraction Bars Template
            </text>
        </svg>
    );
}
