"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";

const milestones = [
  {
    year: "2023",
    event: "Founded with a mission to make support accessible",
    description: "Started as a small team with a big vision to transform how people find help.",
  },
  {
    year: "2024",
    event: "Launched AccessFyndr beta with 500+ resources",
    description: "Our flagship product went live, connecting people with vital services.",
  },
  {
    year: "2025",
    event: "Collected and analyzed impact data",
    description: "Feedback from the community on what was missing and how existing agencies failed to meet their needs.",
  },
  {
    year: "2026",
    event: "Expanding to 4 core programs",
    description: "AccessFyndr, AccessEd, AccessHub, and AccessSTEM working together.",
  },
];

function TimelineItem({
  milestone,
  index,
  isLast,
}: {
  milestone: (typeof milestones)[0];
  index: number;
  isLast: boolean;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const isEven = index % 2 === 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: isEven ? -30 : 30 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.15 }}
      className={cn(
        "relative flex items-start gap-8 pb-12",
        isEven ? "md:flex-row" : "md:flex-row-reverse"
      )}
    >
      {/* Content Card */}
      <div className={cn("flex-1", isEven ? "md:text-right" : "md:text-left")}>
        <motion.div
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          animate={{
            y: isHovered ? -5 : 0,
            scale: isHovered ? 1.02 : 1,
          }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="relative inline-block rounded-2xl border border-border/50 bg-card/50 p-6 cursor-pointer overflow-hidden max-w-md"
        >
          {/* Gradient background on hover */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-br from-primary/10 to-accent/10"
            animate={{ opacity: isHovered ? 1 : 0 }}
            transition={{ duration: 0.3 }}
          />

          <div className="relative z-10">
            <motion.span
              animate={{ scale: isHovered ? 1.1 : 1 }}
              className="inline-block text-lg font-bold text-primary mb-2"
            >
              {milestone.year}
            </motion.span>
            <h3 className="font-semibold text-foreground mb-2">{milestone.event}</h3>
            <motion.p
              initial={{ height: 0, opacity: 0 }}
              animate={{
                height: isHovered ? "auto" : 0,
                opacity: isHovered ? 1 : 0,
              }}
              transition={{ duration: 0.3 }}
              className="text-sm text-muted-foreground overflow-hidden"
            >
              {milestone.description}
            </motion.p>
          </div>

          {/* Shine effect */}
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -skew-x-12 pointer-events-none"
            initial={{ x: "-200%" }}
            animate={{ x: isHovered ? "200%" : "-200%" }}
            transition={{ duration: 0.6 }}
          />
        </motion.div>
      </div>

      {/* Timeline Node */}
      <div className="absolute left-4 md:left-1/2 -translate-x-1/2 flex flex-col items-center">
        <motion.div
          animate={{
            scale: isHovered ? 1.5 : 1,
            boxShadow: isHovered
              ? "0 0 20px rgba(99, 102, 241, 0.5)"
              : "0 0 0px transparent",
          }}
          transition={{ type: "spring", stiffness: 300, damping: 20 }}
          className="h-4 w-4 rounded-full bg-primary border-4 border-background z-10"
        />
        {!isLast && (
          <div className="w-px h-full bg-gradient-to-b from-primary/50 to-border absolute top-4" />
        )}
      </div>

      {/* Empty space for the other side */}
      <div className="flex-1 hidden md:block" />
    </motion.div>
  );
}

export function TimelineSection() {
  return (
    <section className="py-24 bg-secondary/20">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Our <span className="text-accent">Journey</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            From a small idea to a growing movement for accessibility.
          </p>
        </motion.div>

        <div className="relative max-w-4xl mx-auto">
          {/* Central line */}
          <div className="absolute left-4 top-0 bottom-0 w-px bg-border md:left-1/2 md:-translate-x-1/2" />

          {milestones.map((milestone, index) => (
            <TimelineItem
              key={index}
              milestone={milestone}
              index={index}
              isLast={index === milestones.length - 1}
            />
          ))}
        </div>
      </div>
    </section>
  );
}
