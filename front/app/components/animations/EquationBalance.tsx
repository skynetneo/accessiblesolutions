"use client";

import { COLORS, scaledMs } from "./svg-utils";
import type { AnimationTemplateProps } from "./types";

interface EquationBalanceProps {
    left: string;                     // e.g. "2x + 3"
    right: string;                    // e.g. "11"
    variable: string;                 // e.g. "x"
    steps: Array<{
        description: string;          // "Subtract 3 from both sides"
        left: string;                 // "2x"
        right: string;               // "8"
    }>;
}

const W = 480, H = 340;
const BEAM_Y = 120, BEAM_W = 300, PIVOT_X = W / 2;
const PAN_W = 120, PAN_H = 50, PAN_R = 8;

export function EquationBalance({
    props, activeStep, speed, scaffoldLevel,
}: AnimationTemplateProps<EquationBalanceProps>) {
    const { left, right, variable, steps } = props;
    const dur = scaledMs(500, speed);

    const show = activeStep !== "idle";
    const stepMatch = activeStep.match(/^step_(\d+)$/);
    const currentStep = stepMatch ? parseInt(stepMatch[1], 10) : -1;
    const showSolution = activeStep === "solution";

    // Determine what to display on each pan
    let leftText = left;
    let rightText = right;
    let description = "";
    if (currentStep >= 0 && currentStep < steps.length) {
        leftText = steps[currentStep].left;
        rightText = steps[currentStep].right;
        description = steps[currentStep].description;
    } else if (showSolution && steps.length > 0) {
        const last = steps[steps.length - 1];
        leftText = last.left;
        rightText = last.right;
    }

    // Beam tilt: 0 when balanced. We keep it at 0 (balanced) since equations hold.
    const tilt = 0;

    const leftPanX = PIVOT_X - BEAM_W / 2 + 20;
    const rightPanX = PIVOT_X + BEAM_W / 2 - PAN_W - 20;
    const panY = BEAM_Y + 25;

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="anim-svg" role="img"
             aria-label={`Balance equation: ${left} = ${right}`}>
            <defs>
                <filter id="eb-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feFlood floodColor="var(--color-accent)" floodOpacity="0.3" result="c" />
                    <feComposite in="c" in2="blur" operator="in" result="g" />
                    <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Pivot / fulcrum */}
            <g style={{ opacity: show ? 1 : 0, transition: `opacity ${dur}` }}>
                <polygon points={`${PIVOT_X},${BEAM_Y + 10} ${PIVOT_X - 16},${BEAM_Y + 40} ${PIVOT_X + 16},${BEAM_Y + 40}`}
                         fill={COLORS.surface} stroke={COLORS.border} strokeWidth={1} />
                <line x1={PIVOT_X - 20} y1={BEAM_Y + 40}
                      x2={PIVOT_X + 20} y2={BEAM_Y + 40}
                      stroke={COLORS.border} strokeWidth={2} />
            </g>

            {/* Beam */}
            <g style={{
                opacity: show ? 1 : 0,
                transition: `all ${dur}`,
                transformOrigin: `${PIVOT_X}px ${BEAM_Y}px`,
                transform: `rotate(${tilt}deg)`,
            }}>
                <rect x={PIVOT_X - BEAM_W / 2} y={BEAM_Y - 4}
                      width={BEAM_W} height={8} rx={4}
                      fill={COLORS.textMuted} />

                {/* Left pan */}
                <rect x={leftPanX} y={panY} width={PAN_W} height={PAN_H} rx={PAN_R}
                      fill={COLORS.surface} stroke={COLORS.border} strokeWidth={1} />
                <line x1={leftPanX + PAN_W / 2} y1={BEAM_Y + 4}
                      x2={leftPanX + PAN_W / 2} y2={panY}
                      stroke={COLORS.textMuted} strokeWidth={1.5} />
                <text x={leftPanX + PAN_W / 2} y={panY + PAN_H / 2 + 6}
                      textAnchor="middle"
                      fill={showSolution ? COLORS.accent : COLORS.text}
                      fontSize="18" fontWeight="700"
                      filter={showSolution ? "url(#eb-glow)" : "none"}
                      style={{ transition: `all ${dur}` }}>
                    {leftText}
                </text>

                {/* Right pan */}
                <rect x={rightPanX} y={panY} width={PAN_W} height={PAN_H} rx={PAN_R}
                      fill={COLORS.surface} stroke={COLORS.border} strokeWidth={1} />
                <line x1={rightPanX + PAN_W / 2} y1={BEAM_Y + 4}
                      x2={rightPanX + PAN_W / 2} y2={panY}
                      stroke={COLORS.textMuted} strokeWidth={1.5} />
                <text x={rightPanX + PAN_W / 2} y={panY + PAN_H / 2 + 6}
                      textAnchor="middle"
                      fill={showSolution ? COLORS.accent : COLORS.text}
                      fontSize="18" fontWeight="700"
                      filter={showSolution ? "url(#eb-glow)" : "none"}
                      style={{ transition: `all ${dur}` }}>
                    {rightText}
                </text>

                {/* Equals sign */}
                <text x={PIVOT_X} y={panY + PAN_H / 2 + 6} textAnchor="middle"
                      fill={COLORS.textMuted} fontSize="22" fontWeight="300">
                    =
                </text>
            </g>

            {/* Step description */}
            {description && (
                <g style={{ opacity: 1, transition: `opacity ${dur}` }}>
                    <rect x={W / 2 - 160} y={panY + PAN_H + 20}
                          width={320} height={30} rx={6}
                          fill={COLORS.accentSoft} stroke={COLORS.accent} strokeWidth={1}
                          opacity={0.5} />
                    <text x={W / 2} y={panY + PAN_H + 40}
                          textAnchor="middle"
                          fill={COLORS.accent} fontSize="13" fontWeight="600">
                        {description}
                    </text>
                </g>
            )}

            {/* Solution highlight */}
            {showSolution && (
                <text x={W / 2} y={H - 30} textAnchor="middle"
                      fill={COLORS.accent} fontSize="24" fontWeight="700"
                      filter="url(#eb-glow)">
                    {variable} = {rightText}
                </text>
            )}

            {/* Step indicators */}
            {scaffoldLevel <= 3 && steps.length > 0 && show && (
                <g>
                    {steps.map((_, i) => {
                        const dotX = W / 2 - ((steps.length - 1) * 14) / 2 + i * 14;
                        const isCurrent = i === currentStep;
                        const isPast = i < currentStep || showSolution;
                        return (
                            <circle key={i} cx={dotX} cy={H - 10} r={3}
                                    fill={isCurrent ? COLORS.accent : isPast ? COLORS.accent : COLORS.textMuted}
                                    opacity={isCurrent ? 1 : isPast ? 0.5 : 0.3} />
                        );
                    })}
                </g>
            )}
        </svg>
    );
}