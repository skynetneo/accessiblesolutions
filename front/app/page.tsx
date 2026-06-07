"use client";

import { AnonymousLoginNudge } from "@/components/auth/AnonymousLoginNudge";
import { useSupabaseUser } from "@/lib/hooks/useSupabaseUser";
import { AccessFyndrPreview } from "./home/accessfyndr-preview";
import { CTASection } from "./home/cta-section";
import { HeroSection } from "./home/hero-section";
import { ProgramsSection } from "./home/programs-section";
import { TestimonialsSection } from "./home/testimonials-section";

export default function CompanyHomePage() {
    const { user, loading } = useSupabaseUser();

    return (
        <>
            <HeroSection />
            <ProgramsSection />
            <AccessFyndrPreview />
            <TestimonialsSection />
            <CTASection />
            <AnonymousLoginNudge enabled={!loading && !user} />
        </>
    );
}
