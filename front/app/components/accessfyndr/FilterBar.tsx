"use client";

import { useCallback, useState } from "react";
import { Loader2 } from "lucide-react";
import { useResources } from "@/lib/hooks/use-resources";
import { cn } from "@/lib/utils";

const SERVICE_CHIPS: Array<{ key: string; label: string }> = [
    { key: "food", label: "Food" },
    { key: "housing", label: "Housing" },
    { key: "legal", label: "Legal" },
    { key: "medical", label: "Medical" },
    { key: "utilities", label: "Utilities" },
    { key: "domestic violence", label: "DV" },
];

const DISTANCE_OPTIONS = [5, 10, 25, 50];

const AGENT_URL =
    (
        process.env.NEXT_PUBLIC_AGENT_URL ??
        process.env.NEXT_PUBLIC_BACKEND_URL ??
        "http://localhost:8223"
    ).replace(/\/+$/, "");

export function FilterBar() {
    const { userLocation, requestLocation, applyFilteredResults } = useResources();

    const [serviceType, setServiceType] = useState<string | null>(null);
    const [maxDistance, setMaxDistance] = useState<number>(15);
    const [useMyLocation, setUseMyLocation] = useState<boolean>(true);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const runFilter = useCallback(
        async (nextService: string | null, nextDistance: number, nextNearMe: boolean) => {
            setLoading(true);
            setError(null);
            try {
                let coords: { latitude: number; longitude: number } | null = null;
                if (nextNearMe) {
                    coords = userLocation ?? (await requestLocation());
                }

                const res = await fetch(`${AGENT_URL}/filter`, {
                    method: "POST",
                    headers: { "content-type": "application/json" },
                    body: JSON.stringify({
                        service_type: nextService,
                        latitude: coords?.latitude ?? null,
                        longitude: coords?.longitude ?? null,
                        max_distance_miles: nextDistance,
                    }),
                });

                if (!res.ok) {
                    throw new Error(`Filter failed (${res.status})`);
                }

                const data = (await res.json()) as { results: unknown[]; count: number };
                applyFilteredResults((data.results ?? []) as Parameters<typeof applyFilteredResults>[0]);
            } catch (err) {
                setError(err instanceof Error ? err.message : "Filter failed");
            } finally {
                setLoading(false);
            }
        },
        [userLocation, requestLocation, applyFilteredResults]
    );

    const handleServiceChip = (key: string) => {
        const next = serviceType === key ? null : key;
        setServiceType(next);
        void runFilter(next, maxDistance, useMyLocation);
    };

    const handleDistance = (value: number) => {
        setMaxDistance(value);
        void runFilter(serviceType, value, useMyLocation);
    };

    const handleNearMe = () => {
        const next = !useMyLocation;
        setUseMyLocation(next);
        void runFilter(serviceType, maxDistance, next);
    };

    return (
        <div className="border-b border-zinc-800 px-4 py-3 space-y-3">
            <div className="flex flex-wrap gap-1.5">
                {SERVICE_CHIPS.map((chip) => {
                    const active = chip.key === serviceType;
                    return (
                        <button
                            key={chip.key}
                            type="button"
                            onClick={() => handleServiceChip(chip.key)}
                            className={cn(
                                "px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors",
                                active
                                    ? "bg-indigo-500/20 border-indigo-500/50 text-indigo-200"
                                    : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:bg-zinc-800"
                            )}
                        >
                            {chip.label}
                        </button>
                    );
                })}
            </div>

            <div className="flex items-center justify-between gap-2 text-[11px]">
                <div className="flex items-center gap-1">
                    <span className="text-zinc-500">Within</span>
                    {DISTANCE_OPTIONS.map((d) => (
                        <button
                            key={d}
                            type="button"
                            onClick={() => handleDistance(d)}
                            className={cn(
                                "px-2 py-0.5 rounded-md border text-[11px]",
                                maxDistance === d
                                    ? "bg-zinc-700 border-zinc-600 text-zinc-100"
                                    : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:bg-zinc-800"
                            )}
                        >
                            {d}mi
                        </button>
                    ))}
                </div>
                <button
                    type="button"
                    onClick={handleNearMe}
                    className={cn(
                        "px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors",
                        useMyLocation
                            ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200"
                            : "bg-zinc-900/60 border-zinc-800 text-zinc-400 hover:bg-zinc-800"
                    )}
                >
                    Near me
                </button>
            </div>

            <div className="h-4 flex items-center text-[11px] text-zinc-500">
                {loading && (
                    <span className="inline-flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Filtering…
                    </span>
                )}
                {!loading && error && <span className="text-red-400">{error}</span>}
            </div>
        </div>
    );
}
