"use client";

import { cn } from "@/lib/utils";
import React from "react";

export const InfiniteMovingCards = ({
  items,
  direction = "left",
  speed = "fast",
  pauseOnHover = true,
  className,
  cardClassName,
}: {
  items: {
    quote: string;
    name: string;
    title: string;
  }[];
  direction?: "left" | "right";
  speed?: "fast" | "normal" | "slow";
  pauseOnHover?: boolean;
  className?: string;
  cardClassName?: string;
}) => {
  const repeatedItems = [...items, ...items];
  const animationStyle = {
    "--animation-direction": direction === "left" ? "forwards" : "reverse",
    "--animation-duration": speed === "fast" ? "20s" : speed === "normal" ? "40s" : "80s",
  } as React.CSSProperties;

  return (
    <div
      style={animationStyle}
      className={cn(
        "scroller relative z-20 w-full overflow-hidden [mask-image:linear-gradient(to_right,transparent,white_12%,white_88%,transparent)]",
        className,
      )}
    >
      <ul
        className={cn(
          "flex w-max min-w-full shrink-0 flex-nowrap gap-5 py-5 animate-scroll",
          pauseOnHover && "hover:[animation-play-state:paused]",
        )}
      >
        {repeatedItems.map((item, idx) => (
          <li
            className={cn(
              "relative flex w-[min(82vw,26rem)] shrink-0 flex-col rounded-2xl border border-border/60 bg-card/70 px-7 py-6 shadow-lg shadow-black/10 backdrop-blur md:w-[28rem]",
              cardClassName,
            )}
            key={`${item.name}-${idx}`}
          >
            <blockquote className="flex h-full flex-col">
              <div
                aria-hidden="true"
                className="user-select-none pointer-events-none absolute -top-0.5 -left-0.5 -z-1 h-[calc(100%_+_4px)] w-[calc(100%_+_4px)]"
              ></div>
              <span className="relative z-20 text-sm leading-6 font-normal text-card-foreground">
                {item.quote}
              </span>
              <div className="relative z-20 mt-auto flex flex-row items-center pt-6">
                <span className="flex flex-col gap-1">
                  <span className="text-sm font-semibold leading-6 text-foreground">
                    {item.name}
                  </span>
                  <span className="text-sm leading-6 text-muted-foreground">
                    {item.title}
                  </span>
                </span>
              </div>
            </blockquote>
          </li>
        ))}
      </ul>
    </div>
  );
};
