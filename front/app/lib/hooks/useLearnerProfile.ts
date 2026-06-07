"use client";

import { useCallback, useEffect, useState } from "react";

export interface CompetencyScore {
    competency: string;
    score: number;
    demonstrated_count: number;
}

export interface LearnerProfile {
    learner_id: string;
    name: string;
    email: string;
    interests: string[];
    learning_style: string;
    career_goal: string;
    xp: number;
    level: number;
    streak_days: number;
    shields_available: number;
    badges_earned: string[];
    competencies: CompetencyScore[];
}

export function useLearnerProfile(learnerId: string | null) {
    const [data, setData] = useState<LearnerProfile | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [refreshKey, setRefreshKey] = useState(0);

    const refetch = useCallback(() => {
        setRefreshKey((key) => key + 1);
    }, []);

    useEffect(() => {
        if (!learnerId) return;

        const base = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8223";
        const controller = new AbortController();

        Promise.resolve()
            .then(() => {
                setLoading(true);
                setError(null);

                return fetch(`${base}/api/learner/me?learner_id=${encodeURIComponent(learnerId)}`, {
                    signal: controller.signal,
                });
            })
            .then((res) => {
                if (!res.ok) {
                    const message = res.status >= 500
                        ? "Profile service is temporarily unavailable"
                        : `Failed to load profile (${res.status})`;
                    throw new Error(message);
                }
                return res.json() as Promise<LearnerProfile>;
            })
            .then(setData)
            .catch((err: unknown) => {
                if (err instanceof DOMException && err.name === "AbortError") {
                    return;
                }
                setError(err instanceof Error ? err.message : "Failed to load profile");
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, [learnerId, refreshKey]);

    return { data, loading, error, refetch };
}
