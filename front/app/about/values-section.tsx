"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Heart, Users, Globe, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

const values = [
  {
    icon: Heart,
    title: "Dignity First",
    description:
      "Every person deserves to access resources with dignity and respect, regardless of their circumstances.",
    color: "from-rose-500 to-pink-500",
    shadowColor: "shadow-rose-500/30",
  },
  {
    icon: Users,
    title: "Community Driven",
    description:
      "Our programs are shaped by and for the communities we serve, ensuring relevance and impact.",
    color: "from-blue-500 to-cyan-500",
    shadowColor: "shadow-blue-500/30",
  },
  {
    icon: Globe,
    title: "Universal Access",
    description:
      "We design for accessibility from the ground up, ensuring no one is left behind.",
    color: "from-emerald-500 to-teal-500",
    shadowColor: "shadow-emerald-500/30",
  },
  {
    icon: Sparkles,
    title: "Innovation",
    description:
      "We leverage cutting-edge technology to solve age-old problems in new ways.",
    color: "from-violet-500 to-purple-500",
    shadowColor: "shadow-violet-500/30",
  },
];

function ValueCard({
  value,
  index,
}: {
  value: (typeof values)[0];
  index: number;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const Icon = value.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="group relative"
    >
      <motion.div
        animate={{
          y: isHovered ? -8 : 0,
          scale: isHovered ? 1.02 : 1,
        }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative rounded-2xl border border-border/50 bg-card/50 p-6 text-center overflow-hidden h-full"
      >
        {/* Background gradient on hover */}
        <motion.div
          className={cn(
            "absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-500",
            value.color
          )}
          animate={{ opacity: isHovered ? 0.1 : 0 }}
        />

        {/* Icon container */}
        <motion.div
          animate={{
            scale: isHovered ? 1.15 : 1,
            rotate: isHovered ? 5 : 0,
          }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className={cn(
            "relative inline-flex h-16 w-16 items-center justify-center rounded-2xl mb-4 transition-all duration-300 mx-auto",
            isHovered
              ? `bg-gradient-to-br ${value.color} shadow-lg ${value.shadowColor}`
              : "bg-gradient-to-br from-primary/10 to-accent/10"
          )}
        >
          <Icon
            className={cn(
              "h-8 w-8 transition-all duration-300",
              isHovered ? "text-white" : "text-primary"
            )}
          />
        </motion.div>

        {/* Title */}
        <motion.h3
          animate={{ y: isHovered ? -2 : 0 }}
          className={cn(
            "font-semibold text-lg mb-2 transition-colors duration-300",
            isHovered ? "text-foreground" : "text-foreground"
          )}
        >
          {value.title}
        </motion.h3>

        {/* Description */}
        <p className="text-sm text-muted-foreground leading-relaxed">
          {value.description}
        </p>

        {/* Hover indicator */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="absolute bottom-4 left-1/2 -translate-x-1/2"
            >
              <div className={cn("h-1 w-12 rounded-full bg-gradient-to-r", value.color)} />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Shine effect */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 pointer-events-none"
          initial={{ x: "-200%" }}
          animate={{ x: isHovered ? "200%" : "-200%" }}
          transition={{ duration: 0.7, ease: "easeInOut" }}
        />

        {/* Border glow */}
        <motion.div
          className="absolute inset-0 rounded-2xl pointer-events-none"
          animate={{
            boxShadow: isHovered
              ? "inset 0 0 0 2px rgba(255,255,255,0.1)"
              : "inset 0 0 0 0px transparent",
          }}
          transition={{ duration: 0.3 }}
        />
      </motion.div>
    </motion.div>
  );
}

export function ValuesSection() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Our <span className="text-primary">Values</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            These principles guide everything we do.
          </p>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {values.map((value, index) => (
            <ValueCard key={value.title} value={value} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
