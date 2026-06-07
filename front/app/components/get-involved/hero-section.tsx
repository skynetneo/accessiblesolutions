"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Sparkles, ArrowRight, Users, Heart, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { CanvasRevealEffect } from "@/components/ui/canvas-reveal-effect";

const involvementOptions = [
  {
    id: "volunteer",
    icon: Users,
    title: "Volunteer",
    subtitle: "with Us",
    description: "Join our community of volunteers making a real difference. No matter your skills, there is a role for you.",
    colors: [[59, 130, 246], [99, 102, 241]], // Blue gradient
    iconColor: "text-blue-400",
    glowColor: "shadow-blue-500/50",
  },
  {
    id: "donate",
    icon: Heart,
    title: "Donate",
    subtitle: "Today",
    description: "Your financial support helps us maintain and expand our programs, reaching more people in need.",
    colors: [[236, 72, 153], [244, 114, 182]], // Pink gradient
    iconColor: "text-pink-400",
    glowColor: "shadow-pink-500/50",
  },
  {
    id: "partner",
    icon: Building2,
    title: "Partner",
    subtitle: "with Us",
    description: "Collaborate with us to create lasting impact. We work with organizations of all sizes.",
    colors: [[139, 92, 246], [168, 85, 247]], // Purple gradient
    iconColor: "text-violet-400",
    glowColor: "shadow-violet-500/50",
  },
];

export function HeroSection() {
  return (
    <section className="relative py-20 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5 pointer-events-none" />
      
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <div className="text-center mb-12">
          <motion.span
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary mb-4"
          >
            <Sparkles className="h-4 w-4" />
            Get Involved
          </motion.span>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl"
          >
            Be part of the{" "}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              solution
            </span>
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-6 text-xl text-muted-foreground leading-relaxed max-w-3xl mx-auto"
          >
            Whether you can give time, talent, or treasure, your contribution
            helps us break down barriers and connect people with the resources
            they need.
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid gap-8 md:grid-cols-3 max-w-6xl mx-auto"
        >
          {involvementOptions.map((option, index) => (
            <Card key={option.id} option={option} index={index} />
          ))}
        </motion.div>
      </div>
    </section>
  );
}

function Card({
  option,
  index,
}: {
  option: (typeof involvementOptions)[0];
  index: number;
}) {
  const [hovered, setHovered] = useState(false);
  const Icon = option.icon;

  return (
    <motion.a
      href={`#${option.id}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 + index * 0.1 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="group relative min-h-[280px] rounded-3xl border border-border/30 bg-card/30 backdrop-blur-sm overflow-hidden cursor-pointer"
    >
      {/* Canvas Reveal Effect - Hidden by default, reveals on hover */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="absolute inset-0"
          >
            <CanvasRevealEffect
              animationSpeed={5}
              containerClassName="bg-black"
              colors={option.colors}
              opacities={[0.8, 0.7, 0.6, 0.3, 0.4, 0.4, 0.5, 0.5, 0.6, 0.7]}
              dotSize={3}
            />
            {/* Dark overlay for text readability */}
            <div className="absolute inset-0 bg-black/40" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col items-center justify-center p-8 text-center">
        {/* Icon - Large and centered, fades out on hover */}
        <motion.div
          animate={{
            opacity: hovered ? 0 : 1,
            scale: hovered ? 0.8 : 1,
          }}
          transition={{ duration: 0.3 }}
          className="flex items-center justify-center"
        >
          <Icon 
            className={cn(
              "h-20 w-20 md:h-24 md:w-24",
              option.iconColor
            )} 
            strokeWidth={1.5}
          />
        </motion.div>

        {/* Text content - Hidden by default, reveals on hover */}
        <motion.div
          initial={false}
          animate={{
            opacity: hovered ? 1 : 0,
            y: hovered ? 0 : 20,
            scale: hovered ? 1 : 0.9,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 25, delay: hovered ? 0.1 : 0 }}
          className="absolute inset-x-8 top-1/2 -translate-y-1/2 space-y-3"
        >
          <h3 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
            {option.title}{" "}
            <span className="text-white/80">{option.subtitle}</span>
          </h3>
          
          <p className="text-sm md:text-base text-white/80 leading-relaxed max-w-[280px] mx-auto">
            {option.description}
          </p>
        </motion.div>

        {/* Icon label - visible when not hovered */}
        <motion.span
          animate={{
            opacity: hovered ? 0 : 1,
            y: hovered ? -10 : 0,
          }}
          transition={{ duration: 0.2 }}
          className="mt-4 text-lg font-semibold text-foreground"
        >
          {option.title}
        </motion.span>

        {/* Hover arrow indicator */}
        <motion.div
          initial={false}
          animate={{ 
            opacity: hovered ? 1 : 0,
            y: hovered ? 0 : 10
          }}
          transition={{ duration: 0.2, delay: hovered ? 0.2 : 0 }}
          className="absolute bottom-6 left-1/2 -translate-x-1/2"
        >
          <div className="flex items-center gap-2 text-white/80 text-sm font-medium">
            <span>Learn more</span>
            <ArrowRight className="h-4 w-4" />
          </div>
        </motion.div>
      </div>

      {/* Border glow on hover */}
      <motion.div 
        className="absolute inset-0 rounded-3xl pointer-events-none"
        animate={{
          boxShadow: hovered 
            ? `inset 0 0 0 2px rgba(255,255,255,0.3), 0 0 50px rgba(${option.colors[0].join(',')}, 0.4)`
            : "inset 0 0 0 1px rgba(255,255,255,0.1)"
        }}
        transition={{ duration: 0.3 }}
      />
    </motion.a>
  );
}
