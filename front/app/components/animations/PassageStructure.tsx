"use client";

import { COLORS, scaledMs } from "./svg-utils";
import type { AnimationTemplateProps } from "./types";

interface PassageStructureProps {
    paragraphs: string[];           // paragraph summaries
    main_idea: string;
    supporting_details: string[];
    highlight_paragraph?: number;   // index to emphasize
}

const W = 480, H = 380;

export function PassageStructure({
    props, activeStep, speed, scaffoldLevel,
}: AnimationTemplateProps<PassageStructureProps>) {
    const { paragraphs, main_idea, supporting_details, highlight_paragraph } = props;
    const dur = scaledMs(400, speed);

    const show = activeStep !== "idle";
    const showParas = show;
    const showMainIdea = activeStep !== "show_paragraphs" && show;
    const showDetails = activeStep === "show_details" || activeStep === "connect";
    const showConnections = activeStep === "connect";
    const hlPara = highlight_paragraph ?? -1;

    // Layout: main idea at top center, paragraphs down the left, details right
    const mainX = W / 2, mainY = 45;
    const paraX = 30, paraStartY = 100, paraSpacing = 60;
    const detailX = W - 160, detailStartY = 110, detailSpacing = 50;

    return (
        <svg viewBox={`0 0 ${W} ${H}`} className="anim-svg" role="img"
             aria-label="Passage structure diagram">
            <defs>
                <filter id="ps-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="blur" />
                    <feFlood floodColor="var(--color-accent)" floodOpacity="0.3" result="c" />
                    <feComposite in="c" in2="blur" operator="in" result="g" />
                    <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
                </filter>
            </defs>

            {/* Main idea box */}
            <g style={{ opacity: showMainIdea ? 1 : 0, transition: `opacity ${dur}` }}>
                <rect x={mainX - 140} y={mainY - 20} width={280} height={36} rx={8}
                      fill={COLORS.accent} opacity={0.15}
                      stroke={COLORS.accent} strokeWidth={1.5} />
                <text x={mainX} y={mainY + 2} textAnchor="middle"
                      fill={COLORS.accent} fontSize="14" fontWeight="700">
                    {truncate(main_idea, 40)}
                </text>
                <text x={mainX} y={mainY - 28} textAnchor="middle"
                      fill={COLORS.textMuted} fontSize="10" fontWeight="600"
                      letterSpacing="1">
                    MAIN IDEA
                </text>
            </g>

            {/* Paragraph nodes */}
            {paragraphs.map((para, i) => {
                const y = paraStartY + i * paraSpacing;
                const isHl = i === hlPara;
                const delay = `${(i * 150) / speed}ms`;
                return (
                    <g key={i} style={{
                        opacity: showParas ? 1 : 0,
                        transition: `opacity ${dur}`,
                        transitionDelay: delay,
                    }}>
                        {/* Connection line to main idea */}
                        {showConnections && (
                            <line x1={paraX + 120} y1={y}
                                  x2={mainX - 140} y2={mainY + 16}
                                  stroke={COLORS.textMuted} strokeWidth={1}
                                  strokeDasharray="4 4"
                                  style={{ opacity: 0.4 }} />
                        )}
                        <rect x={paraX} y={y - 16} width={240} height={32} rx={6}
                              fill={isHl ? COLORS.accentSoft : COLORS.surface}
                              stroke={isHl ? COLORS.accent : COLORS.border}
                              strokeWidth={isHl ? 1.5 : 1}
                              filter={isHl ? "url(#ps-glow)" : "none"} />
                        <text x={paraX + 12} y={y + 4}
                              fill={isHl ? COLORS.accent : COLORS.text}
                              fontSize="12" fontWeight={isHl ? "600" : "400"}>
                            <tspan fill={COLORS.textMuted} fontSize="10">P{i + 1}</tspan>
                            {"  "}{truncate(para, 28)}
                        </text>
                    </g>
                );
            })}

            {/* Supporting details */}
            {supporting_details.map((detail, i) => {
                const y = detailStartY + i * detailSpacing;
                const delay = `${(i * 180) / speed}ms`;
                return (
                    <g key={i} style={{
                        opacity: showDetails ? 1 : 0,
                        transition: `opacity ${dur}`,
                        transitionDelay: delay,
                    }}>
                        {showConnections && (
                            <line x1={detailX} y1={y}
                                  x2={mainX + 140} y2={mainY + 16}
                                  stroke={COLORS.accent} strokeWidth={1}
                                  strokeDasharray="3 3" opacity={0.5} />
                        )}
                        <circle cx={detailX} cy={y} r={4}
                                fill={COLORS.accent} filter="url(#ps-glow)" />
                        <text x={detailX + 12} y={y + 4}
                              fill={COLORS.text} fontSize="12">
                            {truncate(detail, 22)}
                        </text>
                    </g>
                );
            })}

            {/* Legend at bottom for scaffold 1-2 */}
            {scaffoldLevel <= 2 && show && (
                <g style={{ opacity: 0.6 }}>
                    <rect x={20} y={H - 30} width={10} height={10} rx={2}
                          fill={COLORS.accent} opacity={0.3} stroke={COLORS.accent} strokeWidth={1} />
                    <text x={36} y={H - 21} fill={COLORS.textMuted} fontSize="10">Main Idea</text>
                    <rect x={120} y={H - 30} width={10} height={10} rx={2}
                          fill={COLORS.surface} stroke={COLORS.border} strokeWidth={1} />
                    <text x={136} y={H - 21} fill={COLORS.textMuted} fontSize="10">Paragraphs</text>
                    <circle cx={235} cy={H - 25} r={3} fill={COLORS.accent} />
                    <text x={244} y={H - 21} fill={COLORS.textMuted} fontSize="10">Details</text>
                </g>
            )}
        </svg>
    );
}

function truncate(s: string, max: number): string {
    return s.length > max ? s.slice(0, max - 1) + "\u2026" : s;
}