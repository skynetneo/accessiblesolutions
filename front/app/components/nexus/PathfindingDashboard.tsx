// This is a placeholder for the PathfindingDashboard
"use client";

import { useMemo } from "react";
import { NexusVisualizer } from "./NexusVisualizer";
import { SparklesCore } from "@/components/ui/sparkles";
import { BackgroundGradient } from "@/components/ui/background-gradient";

interface NexusData {
    convergence: number;
    passion: { score: number; top_items: string[] };
    talent: { score: number; top_items: string[] };
    mission: { score: number; top_items: string[] };
    vocation: { score: number; top_items: string[] };
}

interface QuickStat {
    label: string;
    value: string;
    color?: string;
}

interface PathfindingDashboardProps {
    nexusData: NexusData;
    learnerName: string;
    stats: QuickStat[];
    nextAction: {
        title: string;
        subtitle: string;
        programLabel?: string;
    };
    onStartSession: () => void;
    onDomainClick?: (domain: string) => void;
}

const DOMAIN_META = {
    passion: { label: "Passion", tone: "Pursuing what drives you", color: "#d4622b" },
    talent: { label: "Talent", tone: "Honing your edge", color: "#3a8a5c" },
    mission: { label: "Mission", tone: "Creating impact", color: "#4a7fa5" },
    vocation: { label: "Vocation", tone: "Building a career", color: "#c9952e" },
} as const;

type DomainKey = keyof typeof DOMAIN_META;

export function PathfindingDashboard({
    nexusData,
    learnerName,
    stats,
    nextAction,
    onStartSession,
    onDomainClick,
}: PathfindingDashboardProps) {
    const convergencePercent = Math.round(nexusData.convergence * 100);

    const dominantDomain = useMemo(() => {
        let max = -1;
        let dom: DomainKey = "passion";
        (Object.keys(DOMAIN_META) as DomainKey[]).forEach((d) => {
            if (nexusData[d].score > max) {
                max = nexusData[d].score;
                dom = d;
            }
        });
        return dom;
    }, [nexusData]);

    const spotlightMeta = DOMAIN_META[dominantDomain];
    const spotlightItems = nexusData[dominantDomain].top_items.slice(0, 3);

    let greeting = "Welcome back";
    const hour = new Date().getHours();
    if (hour < 12) greeting = "Good morning";
    else if (hour < 18) greeting = "Good afternoon";
    else greeting = "Good evening";

    return (
        <div className="dashboard-grid glass">
            {/* Area 1: Hero */}
            <div className="dashboard-hero">
                <div className="hero-kicker">Alignment Protocol</div>
                <h1 className="hero-title">{greeting}, {learnerName}</h1>
                <p className="hero-subtitle">
                    Your skills and aspirations are converging into a unified path.
                </p>
            </div>

            {/* Area 2: The Visualizer */}
            <div className="dashboard-visualizer relative rounded-xl overflow-hidden border border-[rgba(255,255,255,0.05)] bg-[rgba(0,0,0,0.2)]">
                <div className="absolute inset-0 w-full h-full pointer-events-none -z-0">
                    <SparklesCore
                        background="transparent"
                        minSize={0.4}
                        maxSize={1.5}
                        particleDensity={100}
                        className="w-full h-full"
                        particleColor="#FFFFFF"
                        speed={1}
                    />
                </div>
                <div className="z-10 w-full flex justify-center py-8">
                    <NexusVisualizer
                        passion={nexusData.passion}
                        talent={nexusData.talent}
                        mission={nexusData.mission}
                        vocation={nexusData.vocation}
                        convergence={nexusData.convergence}
                        onDomainClick={onDomainClick}
                    />
                </div>
            </div>

            {/* Area 3: Action Panel */}
            <div className="dashboard-action glass">
                <div className="action-label" style={{ color: spotlightMeta.color }}>
                    Current Focus: {spotlightMeta.label}
                </div>
                <h2 className="action-title">{nextAction.title}</h2>
                <p className="action-subtitle">{nextAction.subtitle}</p>
                <div className="action-items">
                    {spotlightItems.map((item, i) => (
                        <div key={i} className="action-chip">{item}</div>
                    ))}
                </div>
                <button className="action-btn" onClick={onStartSession}>
                    {nextAction.programLabel || "Start Session"} 
                    <span className="arrow">→</span>
                </button>
            </div>

            {/* Area 4: Stats */}
            <div className="dashboard-stats">
                {stats.map((s, i) => (
                    <BackgroundGradient key={i} containerClassName="h-full w-full" className="rounded-[var(--radius-md)] h-full w-full">
                        <div 
                            className="stat-card glass animate-fade-in-up w-full h-full" 
                            style={{ animationDelay: `${i * 0.1}s` }}
                        >
                            <div className="stat-val" style={{ color: s.color || "var(--color-text)" }}>{s.value}</div>
                            <div className="stat-label">{s.label}</div>
                        </div>
                    </BackgroundGradient>
                ))}
            </div>

            {/* Area 5: Alignment Meter */}
            <div className="dashboard-meter glass">
                <div className="meter-header">
                    <span>Alignment Sync</span>
                    <span className="meter-val">{convergencePercent}%</span>
                </div>
                <div className="meter-track">
                    <div className="meter-fill" style={{ width: `${convergencePercent}%` }}></div>
                </div>
            </div>

            <style jsx>{`
                .dashboard-grid {
                    display: grid;
                    grid-template-columns: 1fr 340px;
                    grid-template-rows: auto auto auto;
                    grid-template-areas:
                        "hero visualizer"
                        "action visualizer"
                        "stats meter";
                    gap: 20px;
                    padding: 32px;
                    border-radius: var(--radius-lg);
                    background: rgba(0, 0, 0, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.05);
                }

                .dashboard-hero {
                    grid-area: hero;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    padding: 12px 0;
                }
                .hero-kicker {
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.15em;
                    color: var(--color-accent);
                    font-weight: 700;
                }
                .hero-title {
                    font-family: var(--font-display);
                    font-size: 36px;
                    font-weight: 800;
                    margin: 0;
                    background: linear-gradient(135deg, #fff, #aaa);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                }
                .hero-subtitle {
                    color: var(--color-text-secondary);
                    font-size: 15px;
                    line-height: 1.5;
                }

                .dashboard-visualizer {
                    grid-area: visualizer;
                    align-self: center;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 400px;
                    position: relative;
                }
                .dashboard-visualizer::before {
                    content: '';
                    position: absolute;
                    inset: -50%;
                    background: radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 60%);
                    pointer-events: none;
                }

                .dashboard-action {
                    grid-area: action;
                    padding: 24px;
                    border-radius: var(--radius-md);
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    box-shadow: var(--shadow-card);
                }
                .action-label {
                    font-size: 11px;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                }
                .action-title {
                    font-size: 24px;
                    font-family: var(--font-display);
                    margin: 0;
                }
                .action-subtitle {
                    font-size: 14px;
                    color: var(--color-text-secondary);
                    margin: 0;
                }
                .action-items {
                    display: flex;
                    gap: 8px;
                    flex-wrap: wrap;
                }
                .action-chip {
                    padding: 6px 12px;
                    font-size: 12px;
                    border-radius: var(--radius-sm);
                    background: rgba(255,255,255,0.05);
                    border: 1px solid rgba(255,255,255,0.08);
                }
                .action-btn {
                    padding: 14px 20px;
                    border-radius: var(--radius-md);
                    background: var(--color-accent);
                    color: #fff;
                    border: none;
                    font-weight: 700;
                    font-size: 14px;
                    display: inline-flex;
                    align-items: center;
                    justify-content: space-between;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-top: 8px;
                }
                .action-btn:hover {
                    filter: brightness(1.2);
                    box-shadow: 0 4px 16px rgba(224, 122, 58, 0.4);
                }
                .action-btn:hover .arrow {
                    transform: translateX(4px);
                }
                .arrow {
                    transition: transform 0.2s ease;
                }

                .dashboard-stats {
                    grid-area: stats;
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 16px;
                }
                .stat-card {
                    position: relative;
                    padding: 16px;
                    border-radius: var(--radius-md);
                    text-align: center;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    box-shadow: var(--shadow-card);
                    transition: transform 0.2s ease;
                }
                .stat-card:hover {
                    transform: translateY(-4px);
                }
                .stat-val {
                    font-size: 28px;
                    font-family: var(--font-display);
                    font-weight: 800;
                }
                .stat-label {
                    font-size: 11px;
                    color: var(--color-text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                }

                .dashboard-meter {
                    grid-area: meter;
                    padding: 20px;
                    border-radius: var(--radius-md);
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    gap: 12px;
                }
                .meter-header {
                    display: flex;
                    justify-content: space-between;
                    font-size: 12px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.1em;
                    color: var(--color-text-muted);
                }
                .meter-val {
                    color: var(--color-accent);
                    font-size: 16px;
                    font-family: var(--font-display);
                    font-weight: 800;
                }
                .meter-track {
                    height: 8px;
                    background: rgba(255,255,255,0.06);
                    border-radius: var(--radius-full);
                    overflow: hidden;
                    box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);
                }
                .meter-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #4a7fa5, #3a8a5c, #c9952e, #d4622b);
                    border-radius: var(--radius-full);
                    transition: width 1.5s cubic-bezier(0.4, 0, 0.2, 1);
                    position: relative;
                }
                .meter-fill::after {
                    content: '';
                    position: absolute;
                    inset: 0;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                    animation: shine 2s infinite linear;
                }

                @keyframes shine {
                    0% { transform: translateX(-100%) skewX(-20deg); }
                    100% { transform: translateX(200%) skewX(-20deg); }
                }

                @media (max-width: 1024px) {
                    .dashboard-grid {
                        grid-template-columns: 1fr;
                        grid-template-areas:
                            "hero"
                            "visualizer"
                            "action"
                            "stats"
                            "meter";
                        padding: 24px;
                    }
                    .dashboard-visualizer {
                        min-height: 300px;
                    }
                }
                @media (max-width: 600px) {
                    .dashboard-stats {
                        grid-template-columns: 1fr 1fr;
                    }
                }
            `}</style>
        </div>
    );
}
