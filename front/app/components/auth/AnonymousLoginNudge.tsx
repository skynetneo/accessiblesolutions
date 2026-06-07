"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogIn, ShieldCheck, X } from "lucide-react";

import { Button } from "@/components/ui/button";

const DISMISS_KEY = "praxis.anonymous-login-nudge.dismissed";
const SHOW_DELAY_MS = 4000;

interface AnonymousLoginNudgeProps {
    enabled: boolean;
}

export function AnonymousLoginNudge({ enabled }: AnonymousLoginNudgeProps) {
    const router = useRouter();
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        if (!enabled) {
            return;
        }

        if (window.localStorage.getItem(DISMISS_KEY) === "true") {
            return;
        }

        const timer = window.setTimeout(() => {
            setVisible(true);
        }, SHOW_DELAY_MS);

        return () => window.clearTimeout(timer);
    }, [enabled]);

    function dismiss() {
        window.localStorage.setItem(DISMISS_KEY, "true");
        setVisible(false);
    }

    function logIn() {
        router.push("/login?next=%2Flearn");
    }

    if (!enabled || !visible) return null;

    return (
        <aside
            className="fixed inset-x-3 bottom-3 z-40 mx-auto max-w-lg overflow-hidden rounded-2xl border border-white/[0.12] bg-[rgba(18,18,24,0.72)] p-5 text-[var(--color-text)] shadow-[0_24px_80px_rgba(0,0,0,0.45)] backdrop-blur-2xl sm:inset-x-auto sm:right-5 sm:bottom-5 sm:mx-0"
            aria-label="Login suggestion"
        >
            <div className="pointer-events-none absolute -right-16 -top-20 h-44 w-44 rounded-full bg-[rgba(var(--color-accent-rgb),0.24)] blur-3xl" />
            <div className="pointer-events-none absolute -bottom-20 left-4 h-36 w-36 rounded-full bg-[rgba(88,166,232,0.16)] blur-3xl" />

            <div className="relative flex gap-3">
                <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.08]">
                    <ShieldCheck className="h-5 w-5 text-[var(--color-accent)]" aria-hidden />
                </div>

                <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-3">
                        <h2 className="text-base font-semibold leading-tight">
                            Hey, it looks like you are new here.
                        </h2>
                        <button
                            type="button"
                            onClick={dismiss}
                            className="ml-auto flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-[var(--color-text-muted)] transition-colors hover:bg-white/10 hover:text-[var(--color-text)]"
                            aria-label="Dismiss login suggestion"
                        >
                            <X className="h-4 w-4" aria-hidden />
                        </button>
                    </div>

                    <p className="mt-2 text-sm leading-6 text-[var(--color-text-secondary)]">
                        Logging in to Praxis helps us provide a custom learning experience. We do not sell your data,
                        and we believe everyone should own and control their data. You can read our{" "}
                        <Link
                            href="/privacy"
                            className="font-medium text-[var(--color-accent)] underline-offset-4 hover:underline"
                        >
                            Privacy Policy
                        </Link>
                        .
                    </p>

                    <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                        <Button
                            type="button"
                            onClick={logIn}
                            className="h-11 rounded-full px-5 sm:min-w-36"
                        >
                            <LogIn className="h-4 w-4" aria-hidden />
                            Log in to Praxis
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            onClick={dismiss}
                            className="h-11 rounded-full border-white/[0.12] bg-white/5 px-5 hover:bg-white/10"
                        >
                            Not now
                        </Button>
                    </div>
                </div>
            </div>
        </aside>
    );
}
