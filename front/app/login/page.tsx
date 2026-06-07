"use client";

import Link from "next/link";
import { Suspense } from "react";
import { ArrowLeft, Sparkles } from "lucide-react";

import { LoginCard } from "@/components/auth/LoginCard";

function LoginExperience() {
    return (
        <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-[var(--color-bg)] px-4 py-10 text-[var(--color-text)]">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(var(--color-accent-rgb),0.22),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(88,166,232,0.16),transparent_26%),linear-gradient(135deg,rgba(255,255,255,0.04),transparent_42%)]" />
            <div className="absolute inset-x-0 top-0 h-px bg-linear-to-r from-transparent via-white/20 to-transparent" />

            <div className="relative z-10 grid w-full max-w-5xl gap-8 lg:grid-cols-[1fr_420px] lg:items-center">
                <section className="mx-auto max-w-xl text-center lg:mx-0 lg:text-left">
                    <Link
                        href="/"
                        className="mb-8 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-[var(--color-text-secondary)] backdrop-blur-xl transition-colors hover:bg-white/10 hover:text-[var(--color-text)]"
                    >
                        <ArrowLeft className="h-4 w-4" aria-hidden />
                        Back to Accessible Solutions
                    </Link>

                    <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(var(--color-accent-rgb),0.28)] bg-[rgba(var(--color-accent-rgb),0.12)] px-4 py-1.5 text-sm text-[var(--color-accent)]">
                        <Sparkles className="h-4 w-4" aria-hidden />
                        Praxis Learning Platform
                    </div>

                    <h1 className="mt-6 font-[var(--font-display)] text-4xl font-bold leading-tight tracking-normal text-[var(--color-text)] sm:text-5xl">
                        A private path into learning that adapts with you.
                    </h1>
                    <p className="mt-5 text-base leading-7 text-[var(--color-text-secondary)] sm:text-lg">
                        Sign in when you want Praxis to remember progress, tune recommendations,
                        and shape the experience around your goals.
                    </p>
                </section>

                <LoginCard className="mx-auto border-white/[0.12] bg-[rgba(18,18,24,0.68)]" />
            </div>
        </main>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={null}>
            <LoginExperience />
        </Suspense>
    );
}
