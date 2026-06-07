"use client";

import { COLORS, scaledMs } from "./svg-utils";
import type { AnimationTemplateProps } from "./types";

interface CoordinatePlaneProps {
    points: Array<{ x: number; y: number; label?: string }>;
    lines?: Array<{ x1: number; y1: number; x2: number; y2: number }>;
    x_range: [number, number];
    y_range: [number, number];
}

const W = 480, H = 400, PAD = 50;

export function CoordinatePlane({
    props, activeStep, speed, scaffoldLevel,
}: AnimationTemplateProps<CoordinatePlaneProps>) {
    const { points, lines, x_range, y_range } = props;
    const [xMin, xMax] = x_range;
    const [yMin, yMax] = y_range;
    const dur = scaledMs(400, speed);

    const cW = W - PAD * 2;
    const cH = H - PAD * 2;
    const toSX = (v: number) => PAD + ((v - xMin) / (xMax - xMin)) * cW;
    const toSY = (v: number) => PAD + cH - ((v - yMin) / (yMax - yMin)) * cH;

    const show = activeStep !== "idle";
    const showPts = show && activeStep !== "show_axes";
    const showLines = activeStep === "show_line" || activeStep === "complete";
    const showLabels = activeStep === "label_points" || activeStep === "complete";

    // Grid lines
    const xStep = niceGridStep(xMax - xMin);
    const yStep = niceGridStep(yMax - yMin);
    const xTicks: number[] = [];
    const yTicks: number[] = [];
    for (let v = Math.ceil(xMin / xStep) * xStep; v <= xMax; v += xStep) xTicks.push(v);
    for (let v = Math.ceil(yMin / yStep) * yStep; v <= yMax; v += yStep) yTicks.push(v);

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="anim-svg" role="img"
             aria-label="Coordinate plane">
            <defs>
                <filter id="cp-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feFlood floodColor="var(--color-accent)" floodOpacity="0.3" result="c" />
                    <feComposite in="c" in2="blur" operator="in" result="g" />
                    <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Grid */}
            {xTicks.map((v) => (
                <g key={`x${v}`} style={{ opacity: show ? 0.25 : 0, transition: `opacity ${dur}` }}>
                    <line x1={toSX(v)} y1={PAD} x2={toSX(v)} y2={PAD + cH}
                          stroke={COLORS.textMuted} strokeWidth={v === 0 ? 1.5 : 0.5} />
                    <text x={toSX(v)} y={PAD + cH + 18} textAnchor="middle"
                          fill={COLORS.textSecondary} fontSize="11">{v}</text>
                </g>
            ))}
            {yTicks.map((v) => (
                <g key={`y${v}`} style={{ opacity: show ? 0.25 : 0, transition: `opacity ${dur}` }}>
                    <line x1={PAD} y1={toSY(v)} x2={PAD + cW} y2={toSY(v)}
                          stroke={COLORS.textMuted} strokeWidth={v === 0 ? 1.5 : 0.5} />
                    <text x={PAD - 8} y={toSY(v) + 4} textAnchor="end"
                          fill={COLORS.textSecondary} fontSize="11">{v}</text>
                </g>
            ))}

            {/* Axes (stronger) */}
            {xMin <= 0 && xMax >= 0 && (
                <line x1={toSX(0)} y1={PAD} x2={toSX(0)} y2={PAD + cH}
                      stroke={COLORS.textSecondary} strokeWidth={1.5}
                      style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }} />
            )}
            {yMin <= 0 && yMax >= 0 && (
                <line x1={PAD} y1={toSY(0)} x2={PAD + cW} y2={toSY(0)}
                      stroke={COLORS.textSecondary} strokeWidth={1.5}
                      style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }} />
            )}

            {/* Lines */}
            {showLines && lines?.map((l, i) => {
                const len = Math.hypot(toSX(l.x2) - toSX(l.x1), toSY(l.y2) - toSY(l.y1));
                return (
                    <line key={i}
                          x1={toSX(l.x1)} y1={toSY(l.y1)}
                          x2={toSX(l.x2)} y2={toSY(l.y2)}
                          stroke={COLORS.accent} strokeWidth={2.5}
                          strokeDasharray={len}
                          strokeDashoffset={0}
                          filter="url(#cp-glow)"
                          style={{
                              transition: `stroke-dashoffset ${scaledMs(800, speed)} ease-out`,
                          }} />
                );
            })}

            {/* Points */}
            {points.map((pt, i) => {
                const sx = toSX(pt.x);
                const sy = toSY(pt.y);
                const delay = `${(i * 200) / speed}ms`;
                return (
                    <g key={i} style={{
                        opacity: showPts ? 1 : 0,
                        transition: `opacity ${dur}`,
                        transitionDelay: delay,
                    }}>
                        <circle cx={sx} cy={sy} r={6}
                                fill={COLORS.accent} filter="url(#cp-glow)" />
                        {(showLabels || scaffoldLevel <= 2) && (
                            <text x={sx + 10} y={sy - 10}
                                  fill={COLORS.text} fontSize="13" fontWeight="600">
                                {pt.label || `(${pt.x}, ${pt.y})`}
                            </text>
                        )}
                    </g>
                );
            })}
        </svg>
    );
}

function niceGridStep(range: number): number {
    const r = range / 5;
    const m = Math.pow(10, Math.floor(Math.log10(r)));
    const n = r / m;
    if (n <= 1.5) return m;
    if (n <= 3.5) return 2 * m;
    return 5 * m;
}