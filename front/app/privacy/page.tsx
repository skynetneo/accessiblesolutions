import Link from "next/link";
import { ShieldCheck } from "lucide-react";

export default function PrivacyPage() {
    return (
        <main className="mx-auto max-w-4xl px-6 py-20">
            <div className="mb-10 inline-flex items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-4 py-2 text-sm text-primary">
                <ShieldCheck className="h-4 w-4" aria-hidden />
                Privacy Policy
            </div>

            <h1 className="text-4xl font-bold tracking-tight text-foreground md:text-5xl">
                Your data should stay under your control.
            </h1>
            <p className="mt-5 text-lg leading-8 text-muted-foreground">
                Accessible Solutions and Praxis are designed around dignity, consent, and useful
                personalization. This page explains our baseline privacy commitments in plain language.
            </p>

            <div className="mt-12 space-y-10 text-muted-foreground">
                <section>
                    <h2 className="text-xl font-semibold text-foreground">What we collect</h2>
                    <p className="mt-3 leading-7">
                        When you use Praxis, we may store account information, learning progress,
                        preferences, and interactions needed to provide a personalized experience.
                        We avoid collecting personally identifying data unless it is needed to provide
                        the service you chose to use.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-foreground">How we use it</h2>
                    <p className="mt-3 leading-7">
                        We use data to keep you signed in, remember progress, adapt learning support,
                        improve reliability, and protect the platform. We do not sell user data.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-foreground">Your control</h2>
                    <p className="mt-3 leading-7">
                        We believe people should own and control their own data. Our goal is to make
                        account data understandable, portable where practical, and removable on request.
                    </p>
                </section>

                <section>
                    <h2 className="text-xl font-semibold text-foreground">Questions</h2>
                    <p className="mt-3 leading-7">
                        Contact us if you have questions about privacy, data access, or deletion.
                        We will keep this policy updated as the platform evolves.
                    </p>
                </section>
            </div>

            <div className="mt-12">
                <Link
                    href="/"
                    className="text-sm font-medium text-primary underline-offset-4 hover:underline"
                >
                    Return to the company site
                </Link>
            </div>
        </main>
    );
}
