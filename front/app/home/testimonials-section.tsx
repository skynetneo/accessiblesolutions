"use client";

import { motion } from "motion/react";
import { InfiniteMovingCards } from "@/components/ui/infinite-moving-cards";

const testimonials = [
  {
    quote: "AccessFyndr helped me find a food bank and medical clinic within minutes. As someone with mobility challenges, knowing about wheelchair accessibility beforehand was life-changing.",
    name: "Maria S.",
    title: "Community Member",
  },
  {
    quote: "With Accessible Solutions, I didn't have to jump through a million hoops just to prove I needed help. It’s so rare to find a place that makes the process dignified and simple.",
    name: "James W.",
    title: "Community Member",
  },
  {
    quote: "AccessCareer took the anxiety out of applying for jobs. It helped me build a resume and cover letter that highlighted my strengths without me having to guess what employers wanted.",
    name: "Elena R.",
    title: "Job Seeker",
  },
  {
    quote: "I’ve always struggled with writing about myself, but AccessCareer made it easy. I created a professional cover letter in minutes and finally feel confident hitting 'send' on applications.",
    name: "David M.",
    title: "Recent Graduate",
  },
  {
    quote: "Using AccessFyndr felt different. There was no judgment, no feeling like I was 'lesser than' for needing assistance. Just genuine support when I needed it most.",
    name: "Sarah K.",
    title: "Peer Support Volunteer",
  },
  {
    quote: "The natural language search on AccessFyndr is amazing. I just described what I needed and it found exactly the right services. No confusing menus or forms.",
    name: "Robert H.",
    title: "Veteran",
  },
  {
    quote: "AccessFyndr made it easy to find childcare and transportation options that actually fit my schedule. It saved me hours of phone calls.",
    name: "Tanya L.",
    title: "Single Parent",
  },
  {
    quote: "AccessCareer gave me a clear path to reskill and land interviews. The guidance felt tailored to my experience.",
    name: "Omar N.",
    title: "Career Changer",
  },
  {
    quote: "I found a mental health support group nearby in seconds. Having access to verified, updated resources matters so much.",
    name: "Priya D.",
    title: "Community Member",
  },
  {
    quote: "The accessibility details are accurate and helpful. I can finally plan visits without worrying about surprises.",
    name: "Liam P.",
    title: "Mobility Advocate",
  },
  {
    quote: "AccessCareer helped me organize my skills and achievements into a resume that actually got callbacks.",
    name: "Chen Y.",
    title: "Job Seeker",
  },
  {
    quote: "I used AccessFyndr to locate legal aid and housing support quickly. The experience was straightforward and respectful.",
    name: "Alicia G.",
    title: "Community Member",
  },
];

const topRow = testimonials.slice(0, 3);
const bottomRow = testimonials.slice(3);
export function TestimonialsSection() {
  return (
    <section className="relative py-24 overflow-hidden">
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">
            Community Voices
          </span>
          <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">
            Stories from our{" "}
            <span className="bg-linear-to-r from-primary to-accent bg-clip-text text-transparent">
              community
            </span>
          </h2>
          <p className="mt-4 mx-auto max-w-2xl text-muted-foreground">
            Real experiences from people who have found support through our programs.
          </p>
        </motion.div>

        {/* Testimonials carousel */}
        <div className="relative space-y-3">
          <InfiniteMovingCards
            items={topRow}
            direction="left"
            speed="slow"
            pauseOnHover={true}
            className="py-2"
            cardClassName="h-56"
          />
          <InfiniteMovingCards
            items={bottomRow}
            direction="right"
            speed="slow"
            pauseOnHover={true}
            className="py-2"
            cardClassName="h-56"
          />
        </div>
      </div>
    </section>
  );
}
