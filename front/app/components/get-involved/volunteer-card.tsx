"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Calendar, ArrowRight, MapPin, Code, BookOpen, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const iconMap = {
  MapPin,
  Code,
  BookOpen,
  Users,
} as const;

export type IconName = keyof typeof iconMap;

interface VolunteerCardProps {
  iconName: IconName;
  title: string;
  description: string;
  commitment: string;
}

export function VolunteerCard({
  iconName,
  title,
  description,
  commitment,
}: VolunteerCardProps) {
  const Icon = iconMap[iconName];
  const [isHovered, setIsHovered] = useState(false);

  return (
    <motion.div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      whileHover={{ y: -8, scale: 1.02 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      className="group relative rounded-2xl border border-border/50 bg-card/50 p-6 cursor-pointer overflow-hidden"
    >
      {/* Background gradient on hover */}
      <div className="absolute inset-0 bg-linear-to-br from-primary/0 via-primary/0 to-accent/0 group-hover:from-primary/10 group-hover:via-transparent group-hover:to-accent/10 transition-all duration-500" />
      
      {/* Animated border */}
      <motion.div 
        className="absolute inset-0 rounded-2xl pointer-events-none"
        animate={{
          boxShadow: isHovered 
            ? "inset 0 0 0 2px rgba(99, 102, 241, 0.4), 0 0 20px rgba(99, 102, 241, 0.2)"
            : "inset 0 0 0 0px transparent"
        }}
        transition={{ duration: 0.3 }}
      />
      
      <div className="relative z-10">
        {/* Icon with enhanced hover effects */}
        <motion.div
          animate={{
            scale: isHovered ? 1.2 : 1,
            rotate: isHovered ? 10 : 0,
            y: isHovered ? -5 : 0,
          }}
          transition={{ type: "spring", stiffness: 400, damping: 15 }}
          className={cn(
            "inline-flex h-14 w-14 items-center justify-center rounded-xl mb-4 transition-all duration-300",
            isHovered 
              ? "bg-linear-to-br from-primary to-accent shadow-lg shadow-primary/30" 
              : "bg-linear-to-br from-primary/10 to-accent/10"
          )}
        >
          <motion.div
            animate={{
              scale: isHovered ? 1.1 : 1,
            }}
          >
            <Icon className={cn(
              "h-7 w-7 transition-colors duration-300",
              isHovered ? "text-white" : "text-primary"
            )} />
          </motion.div>
        </motion.div>
        
        <motion.h3 
          animate={{ x: isHovered ? 5 : 0 }}
          className="font-semibold text-foreground mb-2 group-hover:text-primary transition-colors duration-300"
        >
          {title}
        </motion.h3>
        <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
          {description}
        </p>
        
        <div className="flex items-center justify-between">
          <motion.span
            animate={{ opacity: isHovered ? 1 : 0.7 }}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary"
          >
            <Calendar className="h-3.5 w-3.5" />
            {commitment}
          </motion.span>
          
          {/* Arrow that appears on hover */}
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="text-primary"
              >
                <ArrowRight className="h-4 w-4" />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Shine effect on hover */}
      <motion.div 
        className="absolute inset-0 bg-linear-to-r from-transparent via-white/10 to-transparent -skew-x-12 pointer-events-none"
        initial={{ x: "-200%" }}
        animate={{ x: isHovered ? "200%" : "-200%" }}
        transition={{ duration: 0.7, ease: "easeInOut" }}
      />
    </motion.div>
  );
}
