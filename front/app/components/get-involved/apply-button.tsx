"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { ArrowRight, Sparkles, Check } from "lucide-react";
import { cn } from "@/lib/utils";

const hoverParticles = [
  { initialX: -46, targetX: -28 },
  { initialX: -22, targetX: 18 },
  { initialX: 4, targetX: -8 },
  { initialX: 28, targetX: 38 },
  { initialX: 48, targetX: -36 },
];

export function ApplyButton() {
  const [isHovered, setIsHovered] = useState(false);
  const [isClicked, setIsClicked] = useState(false);

  const handleClick = () => {
    setIsClicked(true);
    setTimeout(() => setIsClicked(false), 2000);
  };

  return (
    <motion.button
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={handleClick}
      animate={{
        scale: isClicked ? 0.95 : 1,
      }}
      transition={{
        type: "spring",
        stiffness: 400,
        damping: 25,
      }}
      className={cn(
        "relative group overflow-hidden",
        "h-14 rounded-2xl font-semibold text-base",
        "bg-gradient-to-r from-primary via-primary to-accent",
        "text-white shadow-lg",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50"
      )}
    >
      {/* Animated width container */}
      <motion.div
        className="flex items-center justify-center gap-3 h-full"
        animate={{
          paddingLeft: isHovered ? "3rem" : "2rem",
          paddingRight: isHovered ? "3rem" : "2rem",
        }}
        transition={{
          type: "spring",
          stiffness: 300,
          damping: 25,
        }}
      >
        {/* Sparkle icons that appear on hover */}
        <AnimatePresence>
          {isHovered && (
            <motion.div
              initial={{ opacity: 0, scale: 0, x: -10 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0, x: -10 }}
              transition={{ duration: 0.2 }}
            >
              <Sparkles className="h-5 w-5" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Main text */}
        <motion.span
          animate={{
            scale: isHovered ? 1.05 : 1,
          }}
          className="relative z-10 whitespace-nowrap"
        >
          {isClicked ? "Application Started!" : "Apply to Volunteer"}
        </motion.span>

        {/* Arrow that transforms on hover */}
        <motion.div
          animate={{
            x: isHovered ? 5 : 0,
            rotate: isClicked ? 90 : 0,
          }}
          transition={{
            type: "spring",
            stiffness: 400,
            damping: 20,
          }}
        >
          {isClicked ? (
            <Check className="h-5 w-5" />
          ) : (
            <ArrowRight className="h-5 w-5" />
          )}
        </motion.div>
      </motion.div>

      {/* Shine sweep effect */}
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent -skew-x-12"
        initial={{ x: "-200%" }}
        animate={{ x: isHovered ? "200%" : "-200%" }}
        transition={{
          duration: 0.7,
          ease: "easeInOut",
        }}
      />

      {/* Glow effect on hover */}
      <motion.div
        className="absolute inset-0 rounded-2xl pointer-events-none"
        animate={{
          boxShadow: isHovered
            ? "0 0 30px rgba(99, 102, 241, 0.5), 0 0 60px rgba(236, 72, 153, 0.3)"
            : "0 4px 14px rgba(0, 0, 0, 0.1)",
        }}
        transition={{ duration: 0.3 }}
      />

      {/* Pulse ring on click */}
      <AnimatePresence>
        {isClicked && (
          <motion.div
            initial={{ scale: 1, opacity: 0.8 }}
            animate={{ scale: 2, opacity: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="absolute inset-0 rounded-2xl border-2 border-white pointer-events-none"
          />
        )}
      </AnimatePresence>

      {/* Floating particles on hover */}
      <AnimatePresence>
        {isHovered && (
          <>
            {hoverParticles.map((particle, i) => (
              <motion.div
                key={i}
                initial={{ 
                  opacity: 0, 
                  y: 20,
                  x: particle.initialX,
                }}
                animate={{ 
                  opacity: [0, 1, 0], 
                  y: -30,
                  x: particle.targetX,
                }}
                exit={{ opacity: 0 }}
                transition={{ 
                  duration: 1,
                  delay: i * 0.1,
                  repeat: Number.POSITIVE_INFINITY,
                  repeatDelay: 0.5
                }}
                className="absolute bottom-2 left-1/2"
              >
                <Sparkles className="h-3 w-3 text-white/60" />
              </motion.div>
            ))}
          </>
        )}
      </AnimatePresence>
    </motion.button>
  );
}
