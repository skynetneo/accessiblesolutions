"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, Heart, Users, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { BackgroundBeamsWithCollision } from "@/components/ui/background-beams-with-collision";

function CTAContent() {
  return (
    <div className="relative z-10 mx-auto max-w-4xl px-6 py-24 text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="space-y-8"
      >
        <h2 className="text-3xl font-bold tracking-tight md:text-4xl lg:text-5xl">
          Ready to make a{" "}
          <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            difference
          </span>
          ?
        </h2>
        <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
          Whether you need help finding resources or want to support our mission, 
          there is a place for you in our community.
        </p>

        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button 
            size="lg" 
            className="h-14 px-8 text-base bg-gradient-to-r from-primary to-accent hover:opacity-90 gap-2"
            asChild
          >
            <Link href="/accessfyndr">
              <Sparkles className="h-5 w-5" />
              Get Help Now
            </Link>
          </Button>
          <Button 
            size="lg" 
            variant="outline" 
            className="h-14 px-8 text-base border-accent/50 text-accent hover:bg-accent/10 gap-2 bg-transparent"
            asChild
          >
            <Link href="/get-involved">
              <Heart className="h-5 w-5" />
              Support Our Mission
            </Link>
          </Button>
        </div>

        <div className="pt-8 flex flex-wrap items-center justify-center gap-8">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="h-5 w-5 text-primary" />
            <span>Volunteer with us</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Heart className="h-5 w-5 text-accent" />
            <span>Donate to the cause</span>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <ArrowRight className="h-5 w-5 text-emerald-500" />
            <span>Partner with us</span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export function CTASection() {
  return (
    <BackgroundBeamsWithCollision className="min-h-[500px] bg-gradient-to-br from-background via-secondary/20 to-background">
      <CTAContent />
    </BackgroundBeamsWithCollision>
  );
}
