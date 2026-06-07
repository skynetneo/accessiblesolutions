"use client";

import React from "react";
import { motion } from "motion/react";
import { Sparkles } from "lucide-react";
import { ShootingStars } from "@/components/ui/shooting-stars";
import { StarsBackground } from "@/components/ui/stars-background";
import { FlipWords } from "@/components/ui/flip-words";

export function AboutHeroSection() {
  return (
    <section className="relative min-h-[60vh] flex items-center overflow-hidden bg-background">
      {/* Stars Background */}
      <StarsBackground className="absolute inset-0" />
      
      {/* Shooting Stars */}
      <ShootingStars
        minSpeed={5}
        maxSpeed={25}
        minDelay={1000}
        maxDelay={3000}
        starColor="#ec4899"
        trailColor="#6366f1"
        starWidth={15}
        starHeight={2}
        className="absolute inset-0"
      />

      <div className="relative z-10 mx-auto max-w-7xl px-6 py-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl"
        >
          <motion.span
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary mb-4"
          >
            <Sparkles className="h-4 w-4" />
            About Us
          </motion.span>

          <h1 className="text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl mb-6 inline-flex items-center gap-3 whitespace-nowrap">
            <span className="text-foreground">Making</span>
            <span>
              <FlipWords 
                words={["Support", "Housing", "Education", "Healthcare", "Employment"]} 
                className="text-primary"
              />
            </span>
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              Accessible
            </span>
          </h1>

          
        </motion.div>
      </div>
    </section>
  );
}
