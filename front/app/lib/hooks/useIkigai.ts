"use client";

import { useState, useEffect } from "react";

export interface IkigaiCircle {
    score: number;
    top_items: string[];
}

export interface IkigaiData {
    learner_id: string;
    convergence: number;
    passion: IkigaiCircle;
    talent: IkigaiCircle;
    mission: IkigaiCircle;
    vocation: IkigaiCircle;
}

export function useIkigai(learnerId: string | null) {
    const [data, setData] = useState<IkigaiData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!learnerId) return;

        const base = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";
        const controller = new AbortController();

        setLoading(true);
        setError(null);

        fetch(`${base}/api/ikigai/${learnerId}`, {
            signal: controller.signal,
        })
            .then((res) => {
                if (!res.ok) {
                    const message = res.status >= 500
                        ? "Ikigai service is temporarily unavailable"
                        : `Failed to load ikigai data (${res.status})`;
                    throw new Error(message);
                }
                return res.json() as Promise<IkigaiData>;
            })
            .then(setData)
            .catch((err: unknown) => {
                if (err instanceof DOMException && err.name === "AbortError") {
                    return;
                }
                setError(err instanceof Error ? err.message : "Failed to load ikigai data");
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, [learnerId]);

    return { data, loading, error };
}
