"use client";

import { useMemo, useState, useEffect } from "react";

interface DomainData {
    score: number;
    top_items: string[];
}

interface NexusVisualizerProps {
    passion: DomainData;
    talent: DomainData;
    mission: DomainData;
    vocation: DomainData;
    convergence: number;
    onDomainClick?: (domain: string) => void;
    onDomainHover?: (domain: string | null) => void;
    className?: string;
}

const DOMAINS = {
    passion: { label: "Passion", color: "#d4622b", orbitalOffset: 0 },
    talent: { label: "Talent", color: "#3a8a5c", orbitalOffset: Math.PI / 2 },
    mission: { label: "Mission", color: "#4a7fa5", orbitalOffset: Math.PI },
    vocation: { label: "Vocation", color: "#c9952e", orbitalOffset: (3 * Math.PI) / 2 },
} as const;

type DomainKey = keyof typeof DOMAINS;

export function NexusVisualizer({
    passion,
    talent,
    mission,
    vocation,
    convergence,
    onDomainClick,
    onDomainHover,
    className = "",
}: NexusVisualizerProps) {
    const [activeDomain, setActiveDomain] = useState<DomainKey | null>(null);
    const [hoveredDomain, setHoveredDomain] = useState<DomainKey | null>(null);
    const [time, setTime] = useState(0);

    const data: Record<DomainKey, DomainData> = { passion, talent, mission, vocation };
    const focusedDomain = activeDomain ?? hoveredDomain;

    useEffect(() => {
        let animationFrame: number;
        const startTime = Date.now();
        const animate = () => {
            setTime((Date.now() - startTime) / 1000);
            animationFrame = requestAnimationFrame(animate);
        };
        animationFrame = requestAnimationFrame(animate);
        return () => cancelAnimationFrame(animationFrame);
    }, []);

    const CX = 240, CY = 240;
    const baseRadius = 140;

    const positions = useMemo(() => {
        const result: Record<DomainKey, { cx: number; cy: number }> = {} as Record<DomainKey, { cx: number; cy: number }>;
        (Object.keys(DOMAINS) as DomainKey[]).forEach((key) => {
            const domain = DOMAINS[key];
            const score = data[key].score;

            // Instead of sticking to one orbit, change lengths dynamically based on score and time
            const distanceFactor = 1.3 - (score * 0.6); // Higher score -> closer to center
            const breathing = Math.sin(time * 0.8 + domain.orbitalOffset) * 15;
            const orbitalRadius = (baseRadius * distanceFactor) * (1 - convergence * 0.3) + breathing + 20;

            // Orbit speed changes based on score, but overall slowly drifting
            const speed = 0.15 + score * 0.2;
            // The angle evolves over time
            const angle = domain.orbitalOffset + time * speed;

            const cx = CX + Math.cos(angle) * orbitalRadius;
            const cy = CY + Math.sin(angle) * orbitalRadius;

            result[key] = { cx, cy };
        });
        return result;
    }, [data, convergence, time]);

    return (
        <div className={`nexus-wrap ${className}`}>
            <svg viewBox="0 0 480 480" className="nexus-svg">
                <defs>
                    <radialGradient id="nexus-core-glow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#ffffff" stopOpacity={0.8 + convergence * 0.2} />
                        <stop offset="20%" stopColor="#4090ff" stopOpacity={0.3 + convergence * 0.5} />
                        <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                    </radialGradient>

                    {(Object.keys(DOMAINS) as DomainKey[]).map((key) => (
                        <radialGradient key={`glow-${key}`} id={`glow-${key}`} cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor={DOMAINS[key].color} stopOpacity="0.8" />
                            <stop offset="50%" stopColor={DOMAINS[key].color} stopOpacity="0.2" />
                            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
                        </radialGradient>
                    ))}
                    <filter id="blur-glow">
                        <feGaussianBlur stdDeviation="4" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>

                {/* Core connection lines */}
                {(Object.keys(DOMAINS) as DomainKey[]).map((key) => {
                    const pos = positions[key];
                    const isFocused = focusedDomain === key;
                    const lineOpacity = 0.1 + (data[key].score * convergence * 0.6);
                    return (
                        <line
                            key={`line-${key}`}
                            x1={CX}
                            y1={CY}
                            x2={pos.cx}
                            y2={pos.cy}
                            stroke={DOMAINS[key].color}
                            strokeWidth={isFocused ? 3 : 1.5}
                            strokeOpacity={isFocused ? lineOpacity + 0.3 : lineOpacity}
                            style={{ transition: "stroke-opacity 0.3s ease, stroke-width 0.3s ease" }}
                        />
                    );
                })}

                {/* Ambient rings */}
                <circle cx={CX} cy={CY} r={baseRadius} fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" strokeDasharray="4 8" className="nexus-ambient-ring" />
                <circle cx={CX} cy={CY} r={baseRadius * 0.6} fill="none" stroke="rgba(255, 255, 255, 0.05)" strokeWidth="1" className="nexus-ambient-ring" style={{ animationDirection: "reverse" }} />

                {/* Central core */}
                <circle cx={CX} cy={CY} r={20 + convergence * 10} fill="url(#nexus-core-glow)" className="nexus-core-pulse" />
                <circle cx={CX} cy={CY} r={4} fill="#fff" />

                {/* Orbital nodes */}
                {(Object.keys(DOMAINS) as DomainKey[]).map((key) => {
                    const pos = positions[key];
                    const domain = DOMAINS[key];
                    const score = data[key].score;
                    const isActive = activeDomain === key;
                    const isFocused = focusedDomain === key;

                    const nodeRadius = 8 + score * 8 + (isFocused ? 4 : 0);

                    return (
                        <g
                            key={key}
                            className={`nexus-node ${isFocused ? "nexus-node-focus" : ""}`}
                            onClick={() => {
                                setActiveDomain(activeDomain === key ? null : key);
                                onDomainClick?.(key);
                            }}
                            onMouseEnter={() => {
                                setHoveredDomain(key);
                                onDomainHover?.(key);
                            }}
                            onMouseLeave={() => {
                                setHoveredDomain(null);
                                onDomainHover?.(null);
                            }}
                            style={{ cursor: "pointer", transition: "all 0.3s ease" }}
                        >
                            {/* Glow aura */}
                            <circle cx={pos.cx} cy={pos.cy} r={nodeRadius * 2.5} fill={`url(#glow-${key})`} opacity={isFocused || score > 0.7 ? 1 : 0.4} />

                            {/* Inner Node */}
                            <circle cx={pos.cx} cy={pos.cy} r={nodeRadius} fill={domain.color} filter="url(#blur-glow)" stroke="#fff" strokeWidth={isFocused ? 2 : 0} />

                            {/* Data Orbitals (small dots orbiting the node to show data density) */}
                            {data[key].top_items.slice(0, 3).map((_, i) => {
                                const dotAngle = time * (1 + i * 0.5) + (i * Math.PI * 2) / 3;
                                const dotRadius = nodeRadius + 10;
                                return (
                                    <circle
                                        key={`dot-${i}`}
                                        cx={pos.cx + Math.cos(dotAngle) * dotRadius}
                                        cy={pos.cy + Math.sin(dotAngle) * dotRadius}
                                        r={2}
                                        fill="#fff"
                                        opacity={0.6 + score * 0.4}
                                    />
                                );
                            })}

                            {/* Labels */}
                            <text
                                x={pos.cx}
                                y={pos.cy - nodeRadius - 16}
                                textAnchor="middle"
                                fill="#fff"
                                fontSize="12"
                                fontWeight="700"
                                fontFamily="var(--font-display)"
                                opacity={isFocused || hoveredDomain === key ? 1 : 0}
                                style={{ transition: "opacity 0.3s ease", pointerEvents: "none" }}
                            >
                                {domain.label}
                            </text>

                            <text
                                x={pos.cx}
                                y={pos.cy + nodeRadius + 20}
                                textAnchor="middle"
                                fill={domain.color}
                                fontSize="14"
                                fontWeight="800"
                                fontFamily="var(--font-display)"
                                opacity={isFocused || hoveredDomain === key ? 1 : 0}
                                style={{ transition: "opacity 0.3s ease", pointerEvents: "none" }}
                            >
                                {Math.round(score * 100)}%
                            </text>
                        </g>
                    );
                })}
            </svg>

            {/* Floating details panel */}
            {activeDomain && (
                <div className="nexus-detail glass animate-fade-in-up" onClick={() => setActiveDomain(null)}>
                    <div className="nexus-detail-header" style={{ color: DOMAINS[activeDomain].color }}>
                        {DOMAINS[activeDomain].label}
                    </div>
                    <div className="nexus-detail-score">
                        {Math.round(data[activeDomain].score * 100)}%
                    </div>
                    <div className="nexus-detail-items">
                        {data[activeDomain].top_items.length > 0
                            ? data[activeDomain].top_items.map((item, i) => (
                                <span key={i} className="nexus-chip">{item}</span>
                            ))
                            : <span className="nexus-empty">Awaiting synthesis</span>
                        }
                    </div>
                </div>
            )}

            <style jsx>{`
                .nexus-wrap {
                    position: relative;
                    width: 100%;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    perspective: 1000px;
                }
                .nexus-svg {
                    width: 100%;
                    max-width: 500px;
                    aspect-ratio: 1;
                    filter: drop-shadow(0 0 30px rgba(0, 0, 0, 0.4));
                }
                .nexus-ambient-ring {
                    animation: spin 30s linear infinite;
                    transform-origin: center;
                }
                .nexus-core-pulse {
                    animation: pulse 4s ease-in-out infinite alternate;
                }
                .nexus-node {
                    transform-origin: center;
                }
                .nexus-node:hover circle {
                    filter: brightness(1.3);
                }
                
                .nexus-detail {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    padding: 24px;
                    border-radius: var(--radius-lg);
                    min-width: 220px;
                    text-align: center;
                    cursor: pointer;
                    z-index: 20;
                    box-shadow: var(--shadow-elevated);
                    border: 1px solid rgba(255,255,255,0.15);
                }
                .nexus-detail-header {
                    font-family: var(--font-display);
                    font-size: 14px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    margin-bottom: 8px;
                }
                .nexus-detail-score {
                    font-size: 48px;
                    font-weight: 900;
                    font-family: var(--font-display);
                    margin-bottom: 16px;
                    background: linear-gradient(135deg, #fff, rgba(255,255,255,0.5));
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .nexus-detail-items {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                .nexus-chip {
                    font-size: 12px;
                    padding: 6px 12px;
                    background: rgba(255,255,255,0.08);
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: var(--radius-sm);
                    color: var(--color-text);
                    transition: all var(--transition-fast);
                }
                .nexus-chip:hover {
                    background: rgba(255,255,255,0.15);
                    transform: translateY(-2px);
                }
                .nexus-empty {
                    font-size: 12px;
                    color: var(--color-text-muted);
                    font-style: italic;
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                @keyframes pulse {
                    0% { transform: scale(0.95); opacity: 0.8; }
                    100% { transform: scale(1.05); opacity: 1; }
                }
            `}</style>
        </div>
    );
}
