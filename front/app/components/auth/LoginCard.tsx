"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Mail, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

type Mode = "idle" | "sending" | "sent" | "error";

interface LoginCardProps {
    className?: string;
}

function getAuthNetworkErrorMessage(error: unknown): string {
    if (error instanceof Error) {
        if (error.message.toLowerCase().includes("failed to fetch")) {
            return "Could not reach the auth service. Check your network, then try again.";
        }
        return error.message;
    }
    return "Sign-in failed. Please try again.";
}

export function LoginCard({ className }: LoginCardProps) {
    const searchParams = useSearchParams();
    const nextPath = searchParams.get("next") ?? "/learn";
    const errorFromCallback = searchParams.get("error");

    const [email, setEmail] = useState("");
    const [mode, setMode] = useState<Mode>("idle");
    const [message, setMessage] = useState<string | null>(errorFromCallback);

    const siteUrl =
        process.env.NEXT_PUBLIC_SITE_URL ??
        (typeof window !== "undefined" ? window.location.origin : "");
    const redirectTo = `${siteUrl}/auth/callback?next=${encodeURIComponent(nextPath)}`;

    const sending = mode === "sending";
    const sent = mode === "sent";

    async function handleMagicLink(e: React.FormEvent) {
        e.preventDefault();
        if (!email) return;
        setMode("sending");
        setMessage(null);
        try {
            const supabase = createClient();
            const { error } = await supabase.auth.signInWithOtp({
                email,
                options: { emailRedirectTo: redirectTo, shouldCreateUser: true },
            });

            if (error) {
                setMode("error");
                setMessage(error.message);
                return;
            }

            setMode("sent");
            setMessage(`We sent a sign-in link to ${email}.`);
        } catch (error) {
            setMode("error");
            setMessage(getAuthNetworkErrorMessage(error));
        }
    }

    async function handleGoogle() {
        setMode("sending");
        setMessage(null);
        try {
            const supabase = createClient();
            const { error } = await supabase.auth.signInWithOAuth({
                provider: "google",
                options: { redirectTo },
            });
            if (error) {
                setMode("error");
                setMessage(error.message);
                return;
            }
        } catch (error) {
            setMode("error");
            setMessage(getAuthNetworkErrorMessage(error));
        }
    }

    return (
        <div
            style={{
                paddingTop: 64,
                paddingBottom: 40,
                paddingLeft: 40,
                paddingRight: 40,
            }}
            className={cn(
                "relative w-full max-w-md rounded-3xl border border-white/10 bg-(--color-bg-card) shadow-2xl backdrop-blur-xl",
                className,
            )}
        >
            <div
                style={{ top: -32 }}
                className="absolute left-1/2 -translate-x-1/2"
            >
                <div
                    style={{
                        height: 64,
                        width: 64,
                        boxShadow: "0 8px 24px rgba(var(--color-accent-rgb), 0.45)",
                        outline: "4px solid var(--color-bg)",
                    }}
                    className="flex items-center justify-center rounded-full bg-(--color-accent)"
                >
                    <Lock style={{ height: 24, width: 24 }} className="text-white" strokeWidth={2.25} />
                </div>
            </div>

            <div className="flex flex-col items-center gap-2 mb-8 text-center">
                <h1 className="text-2xl font-semibold tracking-tight text-(--color-text)">
                    Welcome to Praxis
                </h1>
                <p className="text-sm text-(--color-text-secondary)">
                    Sign in to start a personalized learning experience.
                </p>
            </div>

            <form onSubmit={handleMagicLink} className="flex flex-col gap-3">
                <div className="relative">
                    <Mail
                        style={{ left: 16, height: 16, width: 16 }}
                        className="pointer-events-none absolute top-1/2 -translate-y-1/2 text-(--color-text-muted) z-10"
                        aria-hidden
                    />
                    <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="Email address"
                        disabled={sending || sent}
                        autoComplete="email"
                        style={{ height: 48, paddingLeft: 44, paddingRight: 16 }}
                        className="w-full rounded-full border border-white/10 bg-white/2 text-sm text-(--color-text) placeholder:text-(--color-text-muted) outline-none transition-colors focus:border-(--color-accent) focus:bg-white/4 disabled:opacity-60"
                    />
                </div>
                <Button
                    type="submit"
                    disabled={sending || sent || !email}
                    style={{ height: 48 }}
                    className="rounded-full text-sm font-semibold"
                >
                    {sending ? "Sending…" : sent ? "Link sent" : "Continue with email"}
                </Button>
            </form>

            <div
                style={{ marginTop: 24, marginBottom: 24, gap: 12 }}
                className="flex items-center"
            >
                <div style={{ height: 1, background: "rgba(255,255,255,0.12)" }} className="flex-1" />
                <span className="text-xs uppercase tracking-wider text-(--color-text-muted)">
                    or
                </span>
                <div style={{ height: 1, background: "rgba(255,255,255,0.12)" }} className="flex-1" />
            </div>

            <Button
                type="button"
                variant="outline"
                onClick={handleGoogle}
                disabled={sending}
                style={{ height: 48 }}
                className="w-full rounded-full text-sm"
            >
                Continue with Google
            </Button>

            {message && (
                <p
                    className={cn(
                        "mt-5 text-center text-sm",
                        mode === "error"
                            ? "text-(--color-warn)"
                            : "text-(--color-text-secondary)",
                    )}
                >
                    {message}
                </p>
            )}

            <p className="mt-6 text-center text-xs text-(--color-text-muted)">
                New here? Enter your email — we&apos;ll create your account.
            </p>
        </div>
    );
}
