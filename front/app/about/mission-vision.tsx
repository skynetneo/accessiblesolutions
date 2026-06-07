"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import { HandshakeIcon, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { CanvasRevealEffect } from "@/components/ui/canvas-reveal-effect";

const cards = [
  {
    icon: HandshakeIcon,
    title: "Our Mission",
    description:
      "To break down barriers to essential services by creating innovative, accessible tools that connect people with the resources they need, when they need them most.",
    colors: [[236, 72, 153], [244, 114, 182]], // Pink gradient
    iconColor: "text-primary",
  },
  {
    icon: Eye,
    title: "Our Vision",
    description:
      "A world where finding help is as simple as describing what you need, where technology serves humanity, and where no one falls through the cracks of our support systems.",
    colors: [[139, 92, 246], [168, 85, 247]], // Purple gradient
    iconColor: "text-accent",
  },
];

function MissionVisionCard({
  card,
  index,
}: {
  card: (typeof cards)[0];
  index: number;
}) {
  const [hovered, setHovered] = useState(false);
  const Icon = card.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.2 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="group relative rounded-3xl border border-border/50 bg-card/50 overflow-hidden cursor-pointer min-h-[300px]"
    >
      {/* Canvas Reveal Effect */}
      <motion.div
        className="absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.4 }}
      >
        <CanvasRevealEffect
          animationSpeed={5}
          containerClassName="bg-black"
          colors={card.colors}
          opacities={[0.4, 0.5, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8, 0.2, 0.3]}
          dotSize={3}
        />
        <div className="absolute inset-0 bg-black/40" />
      </motion.div>

      {/* Content */}
      <div className="relative z-10 h-full flex flex-col p-8">
        <motion.div
          animate={{
            scale: hovered ? 1.1 : 1,
            y: hovered ? -5 : 0,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className={cn(
            "inline-flex h-14 w-14 items-center justify-center rounded-2xl mb-6 transition-all duration-300",
            hovered
              ? "bg-transparent"
              : "bg-gradient-to-br from-primary/10 to-accent/10"
          )}
        >
          <Icon
            className={cn(
              "h-7 w-7 transition-all duration-300",
              hovered ? cn(card.iconColor, "brightness-125") : card.iconColor
            )}
          />
        </motion.div>

        <motion.h2
          animate={{ x: hovered ? 5 : 0 }}
          className={cn(
            "text-2xl font-bold mb-4 transition-colors duration-300",
            hovered ? "text-white" : "text-foreground"
          )}
        >
          {card.title}
        </motion.h2>

        <p
          className={cn(
            "leading-relaxed transition-colors duration-300",
            hovered ? "text-white/90" : "text-muted-foreground"
          )}
        >
          {card.description}
        </p>
      </div>

      {/* Border glow */}
      <motion.div
        className="absolute inset-0 rounded-3xl pointer-events-none"
        animate={{
          boxShadow: hovered
            ? `inset 0 0 0 2px rgba(255,255,255,0.2), 0 0 40px rgba(${card.colors[0].join(",")}, 0.3)`
            : "inset 0 0 0 1px rgba(255,255,255,0.05)",
        }}
        transition={{ duration: 0.3 }}
      />
    </motion.div>
  );
}

export function MissionVision() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-8 md:grid-cols-2">
          {cards.map((card, index) => (
            <MissionVisionCard key={card.title} card={card} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
