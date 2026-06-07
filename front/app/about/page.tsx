"use client";

import { AboutCTASection } from "@/about/cta-section";
import { AboutHeroSection } from "@/about/hero-section";
import { MissionVision } from "@/about/mission-vision";
import { TeamSection } from "@/about/team-section";
import { TimelineSection } from "@/about/timeline-section";
import { ValuesSection } from "@/about/values-section";

export default function AboutPage() {
  return (
    <main className="flex flex-col">
      <AboutHeroSection />
      <MissionVision />
      <ValuesSection />
      <TimelineSection />
      <TeamSection />
      <AboutCTASection />
    </main>
  );
}
