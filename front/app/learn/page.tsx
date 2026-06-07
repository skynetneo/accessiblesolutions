// app/page.tsx
"use client";

/**
 * Root page — the PWA entry point.
 *
 * Manages:
 *   - Active tab state
 *   - Learner data fetching
 *   - Session lifecycle (start → learn → summary → home)
 *   - Tab content rendering
 *
 * The page itself is thin — all UI logic lives in the tab components.
 * This is just the router/coordinator.
 */

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { TabShell, type TabId } from "@/components/shell/TabShell";
import { HomeView } from "@/components/home/HomeView";
import { SessionSummary } from "@/components/engagement/SessionSummary";
import { IkigaiDashboard } from "@/components/ikigai/IkigaiDashboard";
import { OnboardingFlow } from "@/components/onboarding/OnboardingFlow";
import { useIkigai } from "@/lib/hooks/useIkigai";
import { useInteractiveUI } from "@/lib/hooks/useInteractiveUI";
import { useLearningActions } from "@/lib/hooks/useLearningActions";
import { useLearnerProfile } from "@/lib/hooks/useLearnerProfile";
import { useSupabaseUser } from "@/lib/hooks/useSupabaseUser";

type SessionMode = "continue" | "quick" | "review";
type SessionPhase = "onboarding" | "placement" | "learning" | "review" | "employment" | "wrap_up" | "resuming";

interface ActiveSession {
    sessionId: string;
    phase: SessionPhase;
}

interface BackendSessionStart {
    session_id: string;
    phase: SessionPhase;
}

interface BackendSessionSummary {
    session_id: string;
    items_completed: number;
    accuracy: number;
    xp_earned: number;
    xp_total: number;
    streak: number;
    skills_practiced: string[];
    ikigai_delta: number;
    duration_minutes: number;
    next_recommendation: string;
}

interface SessionSummaryState {
    sessionId: string;
    itemsCompleted: number;
    accuracy: number;
    xpEarned: number;
    xpTotal: number;
    streak: number;
    skillsPracticed: string[];
    convergenceBefore: number;
    convergenceAfter: number;
    sessionMinutes: number;
    nextRecommendation: string;
    noProgress: boolean;
}

function backendBaseUrl() {
    return (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8223").replace(/\/+$/, "");
}

// Placeholder views for tabs we haven't built yet
function LearnView({
    mode,
    phase,
    sessionError,
    onSessionEnd,
}: {
    mode: SessionMode;
    phase: SessionPhase | null;
    sessionError: string | null;
    onSessionEnd: () => void;
}) {
    const modeLabel =
        mode === "quick"
            ? "Quick Practice"
            : mode === "review"
                ? "Review Session"
                : "Learning Session";
    const phaseMessage =
        phase === "placement"
            ? "Placement assessment is ready. Your coach will start with a few adaptive questions."
            : phase === "onboarding"
                ? "Goal intake is ready. Your coach will collect context before assessment."
                : "Coaching interface renders here.";

    return (
        <div style={{ padding: 24, textAlign: "center", color: "var(--color-text-muted)" }}>
            <p style={{ fontSize: 15 }}>{modeLabel} active — {phaseMessage}</p>
            {sessionError && (
                <p style={{ marginTop: 12, fontSize: 13, color: "var(--color-warn)" }}>{sessionError}</p>
            )}
            <button
                onClick={onSessionEnd}
                style={{
                    marginTop: 16, padding: "10px 20px",
                    background: "var(--color-accent)", color: "white",
                    border: "none", borderRadius: "var(--radius-md)",
                    fontFamily: "var(--font-body)", fontSize: 14, fontWeight: 600,
                    cursor: "pointer",
                }}
            >
                End Session
            </button>
        </div>
    );
}

function PathView() {
    return (
        <div style={{ padding: 24, textAlign: "center", color: "var(--color-text-muted)" }}>
            <h2 style={{ fontFamily: "var(--font-display)", fontSize: 24, color: "var(--color-text)", marginBottom: 8 }}>
                Skill Path
            </h2>
            <p style={{ fontSize: 14 }}>Your learning journey visualization.</p>
        </div>
    );
}

function IkigaiView({ learnerId }: { learnerId: string | null }) {
    const { data, loading, error } = useIkigai(learnerId);

    if (loading) {
        return (
            <div style={{ padding: 24, textAlign: "center", color: "var(--color-text-muted)" }}>
                <p style={{ fontSize: 14 }}>Loading your alignment compass…</p>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div style={{ padding: 24, textAlign: "center", color: "var(--color-text-muted)" }}>
                <h2 style={{ fontFamily: "var(--font-display)", fontSize: 24, color: "var(--color-text)", marginBottom: 8 }}>
                    Ikigai
                </h2>
                <p style={{ fontSize: 14 }}>Your alignment compass — complete more sessions to see your scores.</p>
            </div>
        );
    }

    return <IkigaiDashboard data={data} />;
}

function ProfileView({ email }: { email: string | null }) {
    return (
        <div style={{ padding: 24, textAlign: "center", color: "var(--color-text-muted)" }}>
            <h2 style={{ fontFamily: "var(--font-display)", fontSize: 24, color: "var(--color-text)", marginBottom: 8 }}>
                Profile
            </h2>
            {email && (
                <p style={{ fontSize: 14, marginBottom: 16 }}>Signed in as {email}</p>
            )}
            <form action="/auth/signout" method="post">
                <button
                    type="submit"
                    style={{
                        padding: "10px 20px",
                        background: "transparent",
                        color: "var(--color-text)",
                        border: "1px solid var(--color-border)",
                        borderRadius: "var(--radius-md)",
                        fontFamily: "var(--font-body)",
                        fontSize: 14,
                        cursor: "pointer",
                    }}
                >
                    Sign out
                </button>
            </form>
        </div>
    );
}

// ── Main page ────────────────────────────────────────────────

export default function AppPage() {
    const router = useRouter();
    const [activeTab, setActiveTab] = useState<TabId>("home");
    const [sessionMode, setSessionMode] = useState<SessionMode>("continue");
    const [sessionActive, setSessionActive] = useState(false);
    const [showSummary, setShowSummary] = useState(false);
    const [activeSession, setActiveSession] = useState<ActiveSession | null>(null);
    const [sessionSummary, setSessionSummary] = useState<SessionSummaryState | null>(null);
    const [sessionError, setSessionError] = useState<string | null>(null);
    const [onboardingDismissed, setOnboardingDismissed] = useState(false);
    const [onboardingError, setOnboardingError] = useState<string | null>(null);

    const { user, loading: userLoading } = useSupabaseUser();
    const learnerId = user?.id ?? null;

    const {
        data: profileData,
        loading: profileLoading,
        error: profileError,
        refetch: refetchProfile,
    } = useLearnerProfile(learnerId);
    const handleCelebration = useCallback(() => {
        // Registered for award_progress tool callbacks.
    }, []);
    const handleReinforcement = useCallback(() => {
        // Registered for award_progress tool callbacks.
    }, []);

    useInteractiveUI();
    useLearningActions(handleCelebration, handleReinforcement);

    // A profile counts as "onboarded" once it has a name. The backend returns
    // an empty string when no row exists, so we use that as the signal.
    const needsOnboarding =
        !userLoading &&
        !!user &&
        !profileLoading &&
        !profileError &&
        !profileData?.name &&
        !onboardingDismissed;

    const handleStartSession = useCallback(async (mode: SessionMode) => {
        if (!learnerId) return;

        setSessionMode(mode);
        setSessionError(null);
        setSessionSummary(null);
        setShowSummary(false);

        try {
            const response = await fetch(`${backendBaseUrl()}/api/session/start`, {
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({ learner_id: learnerId }),
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => null) as { detail?: string } | null;
                throw new Error(payload?.detail ?? "Failed to start session");
            }

            const payload = await response.json() as BackendSessionStart;
            setActiveSession({
                sessionId: payload.session_id,
                phase: payload.phase,
            });
            setSessionActive(true);
            setActiveTab("learn");
        } catch (error) {
            setSessionError(error instanceof Error ? error.message : "Failed to start session");
            setSessionActive(false);
        }
    }, [learnerId]);

    const handleOnboardingComplete = useCallback(
        async (data: { completed: boolean; extractedSkills?: string[]; resumeText?: string; careerGoal?: string }) => {
            if (!user) return;
            setOnboardingError(null);
            try {
                const response = await fetch("/api/onboarding/complete", {
                    method: "POST",
                    headers: { "content-type": "application/json" },
                    body: JSON.stringify({
                        extractedSkills: data.extractedSkills,
                        resumeText: data.resumeText,
                        careerGoal: data.careerGoal,
                    }),
                });

                if (!response.ok) {
                    const payload = await response.json().catch(() => null) as { error?: string } | null;
                    throw new Error(payload?.error ?? "Failed to complete onboarding");
                }

                setOnboardingDismissed(true);
                refetchProfile();
                router.refresh();
                await handleStartSession("continue");
            } catch (error) {
                setOnboardingError(error instanceof Error ? error.message : "Failed to complete onboarding");
            }
        },
        [user, refetchProfile, router, handleStartSession],
    );

    useEffect(() => {
        if (!userLoading && !user) {
            router.replace("/login");
        }
    }, [user, userLoading, router]);

    // Learner state — live from API when available, fallback to safe defaults
    const learner = {
        name: profileData?.name ?? "Learner",
        streak: {
            current: profileData?.streak_days ?? 0,
            longest: profileData?.streak_days ?? 0,
            fireTier: profileData?.streak_days != null && profileData.streak_days >= 14 ? 2 : profileData?.streak_days != null && profileData.streak_days >= 7 ? 1 : 0,
            shieldsAvailable: profileData?.shields_available ?? 0,
            maxShields: 1,
            shieldActive: false,
            status: "pending" as const,
            recoveryDeadline: null,
            milestoneMessage: null,
        },
        stats: {
            programProgress: 0,
            programLabel: "GED Math",
            xpTotal: profileData?.xp ?? 0,
            accuracy: 0,
            skillsMastered: 0,
            totalSkills: 0,
        },
        nextAction: {
            title: "Continue Learning",
            subtitle: "",
            programLabel: "GED Math",
            estimatedMinutes: 7,
            progressInSkill: 0,
            skillId: "",
        },
    };

    // ── Session lifecycle ─────────────────────────────────────

    const handleSessionEnd = useCallback(async () => {
        if (!learnerId || !activeSession) {
            setSessionActive(false);
            setActiveSession(null);
            setActiveTab("home");
            return;
        }

        setSessionError(null);
        try {
            const response = await fetch(`${backendBaseUrl()}/api/session/wrap-up`, {
                method: "POST",
                headers: { "content-type": "application/json" },
                body: JSON.stringify({
                    learner_id: learnerId,
                    session_id: activeSession.sessionId,
                }),
            });

            if (!response.ok) {
                const payload = await response.json().catch(() => null) as { detail?: string } | null;
                throw new Error(payload?.detail ?? "Failed to end session");
            }

            const payload = await response.json() as BackendSessionSummary;
            const ikigaiDelta = payload.items_completed > 0 ? payload.ikigai_delta : 0;
            setSessionSummary({
                sessionId: payload.session_id,
                itemsCompleted: payload.items_completed,
                accuracy: payload.accuracy,
                xpEarned: payload.xp_earned,
                xpTotal: payload.xp_total,
                streak: payload.streak,
                skillsPracticed: payload.items_completed > 0 ? payload.skills_practiced : [],
                convergenceBefore: 0,
                convergenceAfter: ikigaiDelta,
                sessionMinutes: payload.duration_minutes,
                nextRecommendation: payload.items_completed > 0
                    ? payload.next_recommendation
                    : "No progress recorded yet. Start the assessment when you're ready.",
                noProgress: payload.items_completed === 0,
            });
            setSessionActive(false);
            setActiveSession(null);
            setShowSummary(true);
            refetchProfile();
        } catch (error) {
            setSessionError(error instanceof Error ? error.message : "Failed to end session");
        }
    }, [activeSession, learnerId, refetchProfile]);

    const handleSummaryContinue = useCallback(() => {
        setShowSummary(false);
        setSessionSummary(null);
        void handleStartSession(sessionMode);
    }, [handleStartSession, sessionMode]);

    const handleSummaryDone = useCallback(() => {
        setShowSummary(false);
        setSessionSummary(null);
        setActiveTab("home");
    }, []);

    const handleNavigate = useCallback((target: "career" | "path" | "ikigai") => {
        if (target === "path") setActiveTab("path");
        else if (target === "ikigai") setActiveTab("ikigai");
        else if (target === "career") router.push("/career-prep");
    }, [router]);

    // ── Tab switching ─────────────────────────────────────────

    const handleTabChange = useCallback((tab: TabId) => {
        // If leaving Learn tab during active session, don't stop it
        setActiveTab(tab);
    }, []);

    // ── Render active tab ────────────────────────────────────

    const renderTab = () => {
        switch (activeTab) {
            case "home":
                return (
                    <HomeView
                        learner={learner}
                        onStartSession={handleStartSession}
                        onNavigate={handleNavigate}
                    />
                );
            case "learn":
                return (
                    <LearnView
                        mode={sessionMode}
                        phase={activeSession?.phase ?? null}
                        sessionError={sessionError}
                        onSessionEnd={handleSessionEnd}
                    />
                );
            case "path":
                return <PathView />;
            case "ikigai":
                return <IkigaiView learnerId={learnerId} />;
            case "profile":
                return <ProfileView email={user?.email ?? null} />;
            default:
                return null;
        }
    };

    return (
        <>
            <TabShell
                activeTab={activeTab}
                onTabChange={handleTabChange}
                sessionActive={sessionActive}
                hasNotification={{
                    learn: sessionActive,
                }}
            >
                {renderTab()}
            </TabShell>

            {needsOnboarding && (
                <OnboardingFlow onComplete={handleOnboardingComplete} />
            )}

            {(profileError || onboardingError || (sessionError && activeTab !== "learn")) && (
                <div
                    role="alert"
                    style={{
                        position: "fixed",
                        left: "50%",
                        bottom: 24,
                        transform: "translateX(-50%)",
                        zIndex: 80,
                        maxWidth: 420,
                        padding: "12px 16px",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--color-warn)",
                        background: "var(--color-bg-card)",
                        color: "var(--color-text)",
                        boxShadow: "var(--shadow-elevated)",
                        fontSize: 14,
                    }}
                >
                    {onboardingError ?? profileError ?? sessionError}
                </div>
            )}

            {/* Session summary overlay */}
            {showSummary && sessionSummary && (
                <SessionSummary
                    itemsCompleted={sessionSummary.itemsCompleted}
                    accuracy={sessionSummary.accuracy}
                    xpEarned={sessionSummary.xpEarned}
                    xpTotal={sessionSummary.xpTotal}
                    streak={sessionSummary.streak}
                    skillsPracticed={sessionSummary.skillsPracticed}
                    convergenceBefore={sessionSummary.convergenceBefore}
                    convergenceAfter={sessionSummary.convergenceAfter}
                    sessionMinutes={sessionSummary.sessionMinutes}
                    nextRecommendation={sessionSummary.nextRecommendation}
                    onContinue={handleSummaryContinue}
                    onDone={handleSummaryDone}
                />
            )}
        </>
    );
}
