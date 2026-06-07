"use client";

import { COLORS, scaledMs } from "./svg-utils";
import type { AnimationTemplateProps } from "./types";

interface AreaModelProps {
    rows: number;
    cols: number;
    shaded: number;
    label_rows?: string;
    label_cols?: string;
}

const W = 480, H = 320, PAD = 60;

export function AreaModel({
    props, activeStep, speed, scaffoldLevel,
}: AnimationTemplateProps<AreaModelProps>) {
    const { rows, cols, shaded, label_rows, label_cols } = props;
    const r = Math.max(1, Math.min(rows, 12));
    const c = Math.max(1, Math.min(cols, 12));
    const total = r * c;
    const filled = Math.min(shaded, total);

    const gridW = W - PAD * 2;
    const gridH = H - PAD * 2;
    const cellW = gridW / c;
    const cellH = gridH / r;
    const dur = scaledMs(350, speed);

    const show = activeStep !== "idle";
    const showGrid = show;
    const showShaded = activeStep !== "show_grid" && show;
    const showLabels = activeStep === "label" || activeStep === "result";
    const showResult = activeStep === "result";

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="anim-svg" role="img"
             aria-label={`Area model: ${r} rows × ${c} columns, ${filled} shaded`}>
            <defs>
                <filter id="am-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feFlood floodColor="var(--color-accent)" floodOpacity="0.25" result="c" />
                    <feComposite in="c" in2="blur" operator="in" result="g" />
                    <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Grid cells */}
            {Array.from({ length: total }, (_, i) => {
                const row = Math.floor(i / c);
                const col = i % c;
                const x = PAD + col * cellW;
                const y = PAD + row * cellH;
                const isFilled = i < filled;
                const stagger = `${(i * 40) / speed}ms`;

                return (
                    <rect key={i} x={x + 1} y={y + 1}
                          width={cellW - 2} height={cellH - 2} rx={3}
                          fill={isFilled && showShaded ? COLORS.accent : "transparent"}
                          stroke={COLORS.border} strokeWidth={1}
                          style={{
                              opacity: showGrid ? (isFilled && showShaded ? 0.85 : 0.3) : 0,
                              transition: `all ${dur} ease-out`,
                              transitionDelay: showShaded ? stagger : "0ms",
                              filter: isFilled && showShaded ? "url(#am-glow)" : "none",
                          }} />
                );
            })}

            {/* Row label */}
            {(showLabels || scaffoldLevel <= 2) && label_rows && (
                <text x={PAD / 2} y={PAD + gridH / 2 + 5} textAnchor="middle"
                      fill={COLORS.text} fontSize="15" fontWeight="600"
                      transform={`rotate(-90 ${PAD / 2} ${PAD + gridH / 2})`}
                      style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }}>
                    {label_rows}
                </text>
            )}

            {/* Col label */}
            {(showLabels || scaffoldLevel <= 2) && label_cols && (
                <text x={PAD + gridW / 2} y={PAD - 12} textAnchor="middle"
                      fill={COLORS.text} fontSize="15" fontWeight="600"
                      style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }}>
                    {label_cols}
                </text>
            )}

            {/* Result */}
            {showResult && (
                <text x={W / 2} y={H - 10} textAnchor="middle"
                      fill={COLORS.accent} fontSize="20" fontWeight="700"
                      filter="url(#am-glow)">
                    {filled} / {total}
                    {filled === total ? " = 1 whole" : ` = ${(filled / total).toFixed(2)}`}
                </text>
            )}
        </svg>
    );
}