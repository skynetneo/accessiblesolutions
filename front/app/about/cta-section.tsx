"use client";

import React from "react";
import Link from "next/link";
import { motion } from "motion/react";
import { Heart, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ShootingStars } from "@/components/ui/shooting-stars";
import { StarsBackground } from "@/components/ui/stars-background";

export function AboutCTASection() {
  return (
    <section className="relative min-h-[400px] overflow-hidden">
      {/* Background effects */}
      <StarsBackground className="absolute inset-0" starDensity={0.0003} />
      <ShootingStars
        minSpeed={10}
        maxSpeed={30}
        minDelay={2000}
        maxDelay={4000}
        starColor="#ec4899"
        trailColor="#6366f1"
        starWidth={12}
        starHeight={2}
        className="absolute inset-0"
      />
      
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background/50" />

      <div className="relative z-10 mx-auto max-w-4xl px-6 py-24 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="space-y-6"
        >
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Ready to make a{" "}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              difference
            </span>
            ?
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Whether you need help finding resources or want to support our mission, 
            there is a place for you in our community.
          </p>

          {/* Buttons */}
          <div className="flex flex-col gap-4 sm:flex-row justify-center pt-4">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Button
                size="lg"
                className="bg-gradient-to-r from-primary to-accent hover:opacity-90 gap-2 h-12 px-8"
                asChild
              >
                <Link href="/accessfyndr">
                  <Sparkles className="h-5 w-5" />
                  Get Help Now
                </Link>
              </Button>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Button
                size="lg"
                variant="outline"
                className="border-accent/50 bg-transparent hover:bg-accent/10 h-12 px-8 gap-2"
                asChild
              >
                <Link href="/get-involved">
                  <Heart className="h-5 w-5" />
                  Support Our Mission
                </Link>
              </Button>
            </motion.div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
