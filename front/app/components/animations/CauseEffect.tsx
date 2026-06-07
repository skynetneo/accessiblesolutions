"use client";

import { COLORS, scaledMs } from "./svg-utils";
import type { AnimationTemplateProps } from "./types";

interface CauseEffectProps {
    causes: string[];
    effects: string[];
    connections: Array<[number, number]>;  // [causeIdx, effectIdx]
}

const W = 480, H = 360;
const COL_W = 170, BOX_H = 36, GAP = 14;

export function CauseEffect({
    props, activeStep, speed,
}: AnimationTemplateProps<CauseEffectProps>) {
    const { causes, effects, connections } = props;
    const dur = scaledMs(400, speed);

    const show = activeStep !== "idle";
    const showCauses = show;
    const showEffects = activeStep !== "show_causes" && show;
    const showArrows = activeStep === "connect" || activeStep === "complete";

    const leftX = 20;
    const rightX = W - COL_W - 20;
    const causeStartY = 60;
    const effectStartY = 60;
    const causeStep = BOX_H + GAP;
    const effectStep = BOX_H + GAP;

    // Center each column vertically
    const causeOffY = causeStartY + ((Math.max(causes.length, effects.length) - causes.length) * causeStep) / 2;
    const effectOffY = effectStartY + ((Math.max(causes.length, effects.length) - effects.length) * effectStep) / 2;

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="anim-svg" role="img"
             aria-label="Cause and effect diagram">
            <defs>
                <filter id="ce-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feFlood floodColor="var(--color-accent)" floodOpacity="0.3" result="c" />
                    <feComposite in="c" in2="blur" operator="in" result="g" />
                    <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
                <marker id="ce-arrow" markerWidth="8" markerHeight="6"
                        refX="8" refY="3" orient="auto">
                    <path d="M0,0 L8,3 L0,6" fill={COLORS.accent} />
                </marker>
            </defs>

            {/* Column headers */}
            <text x={leftX + COL_W / 2} y={30} textAnchor="middle"
                  fill={COLORS.textMuted} fontSize="11" fontWeight="600" letterSpacing="1"
                  style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }}>
                CAUSE
            </text>
            <text x={rightX + COL_W / 2} y={30} textAnchor="middle"
                  fill={COLORS.textMuted} fontSize="11" fontWeight="600" letterSpacing="1"
                  style={{ opacity: showEffects ? 1 : 0, transition: `opacity ${dur}` }}>
                EFFECT
            </text>

            {/* Connection arrows */}
            {showArrows && connections.map(([ci, ei], i) => {
                const cy = causeOffY + ci * causeStep + BOX_H / 2;
                const ey = effectOffY + ei * effectStep + BOX_H / 2;
                const delay = `${(i * 200) / speed}ms`;
                return (
                    <line key={`conn-${i}`}
                          x1={leftX + COL_W} y1={cy}
                          x2={rightX - 4} y2={ey}
                          stroke={COLORS.accent} strokeWidth={2}
                          markerEnd="url(#ce-arrow)"
                          filter="url(#ce-glow)"
                          style={{
                              opacity: 0.8,
                              transition: `opacity ${dur}`,
                              transitionDelay: delay,
                          }} />
                );
            })}

            {/* Cause boxes */}
            {causes.map((text, i) => {
                const y = causeOffY + i * causeStep;
                const delay = `${(i * 120) / speed}ms`;
                return (
                    <g key={`cause-${i}`} style={{
                        opacity: showCauses ? 1 : 0,
                        transition: `opacity ${dur}`,
                        transitionDelay: delay,
                    }}>
                        <rect x={leftX} y={y} width={COL_W} height={BOX_H} rx={8}
                              fill={COLORS.surface} stroke={COLORS.border} strokeWidth={1} />
                        <text x={leftX + 12} y={y + BOX_H / 2 + 4}
                              fill={COLORS.text} fontSize="12">
                            {truncate(text, 22)}
                        </text>
                    </g>
                );
            })}

            {/* Effect boxes */}
            {effects.map((text, i) => {
                const y = effectOffY + i * effectStep;
                const delay = `${(i * 120) / speed}ms`;
                return (
                    <g key={`effect-${i}`} style={{
                        opacity: showEffects ? 1 : 0,
                        transition: `opacity ${dur}`,
                        transitionDelay: delay,
                    }}>
                        <rect x={rightX} y={y} width={COL_W} height={BOX_H} rx={8}
                              fill={COLORS.accentSoft} stroke={COLORS.accent} strokeWidth={1} />
                        <text x={rightX + 12} y={y + BOX_H / 2 + 4}
                              fill={COLORS.text} fontSize="12">
                            {truncate(text, 22)}
                        </text>
                    </g>
                );
            })}
        </svg>
    );
}

function truncate(s: string, max: number): string {
    return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}
