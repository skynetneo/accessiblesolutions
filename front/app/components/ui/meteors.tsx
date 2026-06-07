"use client";
import { cn } from "@/lib/utils";
import { motion } from "motion/react";
import React from "react";

export const Meteors = ({
  number,
  className,
}: {
  number?: number;
  className?: string;
}) => {
  const meteorCount = number || 20;
  const meteors = Array.from({ length: meteorCount }, (_, idx) => {
    const seed = (idx + 1) * 137;

    return {
      left: idx * (800 / meteorCount) - 400,
      delay: ((seed % 500) / 100).toFixed(2),
      duration: 5 + (seed % 5),
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      {meteors.map((meteor, idx) => {
        return (
          <span
            key={"meteor" + idx}
            className={cn(
              "animate-meteor-effect absolute h-0.5 w-0.5 rotate-[45deg] rounded-[9999px] bg-slate-500 shadow-[0_0_0_1px_#ffffff10]",
              "before:absolute before:top-1/2 before:h-[1px] before:w-[50px] before:-translate-y-[50%] before:transform before:bg-gradient-to-r before:from-[#64748b] before:to-transparent before:content-['']",
              className,
            )}
            style={{
              top: "-40px", // Start above the container
              left: `${meteor.left}px`,
              animationDelay: `${meteor.delay}s`,
              animationDuration: `${meteor.duration}s`,
            }}
          ></span>
        );
      })}
    </motion.div>
  );
};
