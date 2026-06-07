"use client";

import React from "react";
import { motion } from "motion/react";
import { Heart, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface DonationCardProps {
  amount: string;
  impact: string;
  popular?: boolean;
}

export function DonationCard({ amount, impact, popular = false }: DonationCardProps) {
  return (
    <motion.div
      whileHover={{ y: -10, scale: 1.03 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className={cn(
        "group relative rounded-2xl border p-6 text-center cursor-pointer overflow-hidden",
        popular ? "border-accent bg-accent/5" : "border-border/50 bg-card/50"
      )}
    >
      {/* Popular badge */}
      {popular && (
        <motion.span
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="absolute -top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 inline-flex items-center gap-1 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground"
        >
          <Sparkles className="h-3 w-3" />
          Most Popular
        </motion.span>
      )}

      {/* Animated background */}
      <div className="absolute inset-0 bg-gradient-to-br from-transparent via-transparent to-transparent group-hover:from-accent/10 group-hover:via-transparent group-hover:to-primary/10 transition-all duration-500" />

      {/* Floating heart animation */}
      <motion.div
        initial={{ opacity: 0, scale: 0 }}
        whileHover={{ opacity: 0.1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="absolute top-4 right-4"
      >
        <Heart className="h-20 w-20 text-accent fill-accent" />
      </motion.div>

      <div className="relative z-10">
        <motion.span
          whileHover={{ scale: 1.1 }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className={cn(
            "inline-block text-4xl font-bold transition-colors duration-300",
            popular
              ? "text-accent group-hover:text-accent"
              : "text-foreground group-hover:text-primary"
          )}
        >
          {amount}
        </motion.span>
        
        <p className="mt-4 text-sm text-muted-foreground leading-relaxed">
          {impact}
        </p>

        <motion.div
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          <Button
            className={cn(
              "mt-6 w-full transition-all duration-300",
              popular
                ? "bg-accent hover:bg-accent/90 text-accent-foreground group-hover:shadow-lg group-hover:shadow-accent/25"
                : "bg-primary/10 hover:bg-primary text-primary hover:text-primary-foreground group-hover:bg-primary group-hover:text-primary-foreground"
            )}
          >
            Donate {amount}
          </Button>
        </motion.div>
      </div>

      {/* Shine effect */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -skew-x-12 -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
      </div>
    </motion.div>
  );
}
