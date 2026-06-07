"use client";

import type { IkigaiData } from "@/lib/hooks/useIkigai";

interface Props {
    data: IkigaiData;
}

const CIRCLES: { key: keyof Omit<IkigaiData, "learner_id" | "convergence">; label: string; color: string }[] = [
    { key: "passion",  label: "Passion",  color: "var(--color-accent)" },
    { key: "talent",   label: "Talent",   color: "#6b9e78" },
    { key: "mission",  label: "Mission",  color: "#7b8ec8" },
    { key: "vocation", label: "Vocation", color: "#c8936b" },
];

export function IkigaiDashboard({ data }: Props) {
    const convergencePct = Math.round(data.convergence * 100);

    return (
        <div style={{ padding: "24px 16px", maxWidth: 480, margin: "0 auto" }}>
            {/* Convergence score */}
            <div style={{ textAlign: "center", marginBottom: 32 }}>
                <div style={{
                    display: "inline-flex", flexDirection: "column", alignItems: "center",
                    gap: 4, background: "var(--color-surface)", border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-lg)", padding: "20px 40px",
                }}>
                    <span style={{ fontFamily: "var(--font-display)", fontSize: 48, fontWeight: 700, color: "var(--color-accent)", lineHeight: 1 }}>
                        {convergencePct}%
                    </span>
                    <span style={{ fontSize: 13, color: "var(--color-text-muted)", fontFamily: "var(--font-body)" }}>
                        Alignment
                    </span>
                </div>
                <p style={{ marginTop: 12, fontSize: 14, color: "var(--color-text-muted)", lineHeight: 1.5 }}>
                    Your ikigai is where passion, talent, mission, and vocation converge.
                </p>
            </div>

            {/* Four circles */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                {CIRCLES.map(({ key, label, color }) => {
                    const circle = data[key];
                    const pct = Math.round(circle.score * 100);
                    return (
                        <div key={key} style={{
                            background: "var(--color-surface)",
                            border: "1px solid var(--color-border)",
                            borderRadius: "var(--radius-md)",
                            padding: "16px 14px",
                        }}>
                            {/* Header */}
                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                                <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text)", fontFamily: "var(--font-body)" }}>
                                    {label}
                                </span>
                                <span style={{ fontSize: 18, fontWeight: 700, color, fontFamily: "var(--font-display)" }}>
                                    {pct}%
                                </span>
                            </div>

                            {/* Progress bar */}
                            <div style={{
                                height: 4, borderRadius: 2,
                                background: "var(--color-border)", marginBottom: 10,
                            }}>
                                <div style={{
                                    height: "100%", borderRadius: 2,
                                    width: `${pct}%`, background: color,
                                    transition: "width 0.6s ease",
                                }} />
                            </div>

                            {/* Top items */}
                            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 3 }}>
                                {circle.top_items.slice(0, 3).map((item) => (
                                    <li key={item} style={{ fontSize: 11, color: "var(--color-text-muted)", lineHeight: 1.4 }}>
                                        · {item}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
