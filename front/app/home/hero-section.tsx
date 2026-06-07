"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, MapPin, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FlipWords } from "@/components/ui/flip-words";
import { Vortex } from "@/components/ui/vortex";

const flipWords = ["help", "hope", "support", "resources", "community"];

export function HeroSection() {
  return (
    <section className="relative min-h-[calc(100vh-4rem)] flex items-center justify-center overflow-hidden">
      {/* Vortex Background - Full screen below navbar */}
      <Vortex
        backgroundColor="transparent"
        baseHue={270}
        rangeY={400}
        particleCount={700}
        baseSpeed={0.1}
        rangeSpeed={1.2}
        baseRadius={1}
        rangeRadius={2}
        containerClassName="absolute inset-0 w-full h-full"
        className="w-full h-full"
      />

      {/* Gradient overlays */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-transparent to-background pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-accent/5 pointer-events-none" />

      {/* Content */}
      <div className="relative z-10 mx-auto max-w-5xl px-6 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-8"
        >
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary"
          >
            <Sparkles className="h-4 w-4" />
            <span>AI-Powered Resource Discovery</span>
          </motion.div>

          {/* Main heading */}
          <h1 className="flex flex-col items-center gap-2 text-4xl font-bold leading-none tracking-tight sm:gap-3 sm:text-5xl md:text-6xl lg:text-7xl">
            <span className="block text-foreground">Access to</span>
            <span className="block min-h-[1em]">
              <FlipWords words={flipWords} className="text-primary" />
            </span>
            <span className="block bg-gradient-to-r from-primary via-accent to-primary bg-clip-text text-transparent">
              starts here
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground md:text-xl leading-relaxed">
            Accessible Solutions helps people discover vital services, assistive resources, 
            and community support. Our AI-powered tools make finding help simple and dignified.
          </p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="flex flex-col items-center justify-center gap-4 sm:flex-row"
          >
            <Button 
              size="lg" 
              className="h-14 px-8 text-base bg-gradient-to-r from-primary to-accent hover:opacity-90 gap-2 shadow-lg shadow-primary/25"
              asChild
            >
              <Link href="/accessfyndr">
                <MapPin className="h-5 w-5" />
                Find Resources Near You
                <ArrowRight className="h-5 w-5" />
              </Link>
            </Button>
            <Button 
              variant="outline" 
              size="lg" 
              className="h-14 px-8 text-base border-border/50 hover:bg-secondary/50 bg-transparent"
              asChild
            >
              <Link href="/programs">
                Explore Our Programs
              </Link>
            </Button>
          </motion.div>

          {/* Stats preview */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="pt-8 flex flex-wrap items-center justify-center gap-8 text-sm text-muted-foreground"
          >
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-foreground">2,500+</span>
              <span>Resources Mapped</span>
            </div>
            <div className="h-4 w-px bg-border" />
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-foreground">15K+</span>
              <span>People Helped</span>
            </div>
            <div className="h-4 w-px bg-border hidden sm:block" />
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold text-foreground">4</span>
              <span>Core Programs</span>
            </div>
          </motion.div>
        </motion.div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent pointer-events-none" />
    </section>
  );
}
