"use client";

import React, { useCallback, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

type Star = {
  x: number; // base position in CSS px
  y: number;
  radius: number;
  baseOpacity: number;
  twinklePeriod: number | null; // seconds per cycle
  phase: number;
  appearAt: number; // seconds from mount; star is invisible before this
};

interface StarBackgroundProps {
  starDensity?: number;
  density?: number;
  allStarsTwinkle?: boolean;
  twinkleProbability?: number;
  minTwinkleSpeed?: number;
  maxTwinkleSpeed?: number;
  minStars?: number;
  maxStars?: number;
  colors?: number[][];
  meteorRate?: number;
  drift?: number;
  twinkle?: number;
  className?: string;
  /** Whether the starfield reacts to pointer movement. */
  interactive?: boolean;
  /** Per-star delay (ms) so stars fade in one after another. 0 = all at once. */
  staggerAppearMs?: number;
  /** Per-star fade-in duration (ms). */
  appearFadeMs?: number;
}

export const StarsBackground: React.FC<StarBackgroundProps> = ({
  starDensity,
  density,
  allStarsTwinkle = false,
  twinkleProbability = 0.5,
  minTwinkleSpeed = 0.5,
  maxTwinkleSpeed = 1,
  className,
  interactive = true,
  staggerAppearMs = 0,
  appearFadeMs = 600,
}) => {
  const resolvedStarDensity = starDensity ?? density ?? 0.00015;
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const starsRef = useRef<Star[]>([]);
  const sizeRef = useRef({ w: 0, h: 0 });
  const lastTimeRef = useRef<number>(0);

  // Camera offset in CSS px (wraps in [0,w) / [0,h))
  const offsetRef = useRef<{ ox: number; oy: number }>({ ox: 0, oy: 0 });

  // Persistent starfield velocity in CSS px/s
  const fieldVelRef = useRef<{ vx: number; vy: number }>({ vx: 0, vy: 0 });

  // Pointer velocity measurement
  const lastPointerRef = useRef<{ x: number; y: number; t: number } | null>(null);

  const mountTimeRef = useRef<number>(0);

  const generateStars = useCallback(
    (w: number, h: number): Star[] => {
      const area = w * h;
      const numStars = Math.floor(area * resolvedStarDensity);

      // Random ordering so the appearance feels organic, not row-by-row.
      const order = Array.from({ length: numStars }, (_, i) => i);
      for (let i = order.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [order[i], order[j]] = [order[j], order[i]];
      }

      const stagger = Math.max(0, staggerAppearMs) / 1000;
      const stars: Star[] = new Array(numStars);
      for (let i = 0; i < numStars; i++) {
        const shouldTwinkle = allStarsTwinkle || Math.random() < twinkleProbability;
        stars[i] = {
          x: Math.random() * w,
          y: Math.random() * h,
          radius: Math.random() * 0.9 + 0.5,
          baseOpacity: Math.random() * 0.6 + 0.3,
          twinklePeriod: shouldTwinkle
            ? minTwinkleSpeed + Math.random() * (maxTwinkleSpeed - minTwinkleSpeed)
            : null,
          phase: Math.random() * Math.PI * 2,
          appearAt: order[i] * stagger,
        };
      }
      return stars;
    },
    [resolvedStarDensity, allStarsTwinkle, twinkleProbability, minTwinkleSpeed, maxTwinkleSpeed, staggerAppearMs]
  );

  // Resize + regenerate
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(1, Math.floor(rect.width));
      const h = Math.max(1, Math.floor(rect.height));
      const dpr = Math.max(1, window.devicePixelRatio || 1);

      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      // draw in CSS pixels
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      sizeRef.current = { w, h };
      starsRef.current = generateStars(w, h);

      offsetRef.current.ox = 0;
      offsetRef.current.oy = 0;
    };

    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [generateStars]);

  // Pointer -> persistent velocity (no decay)
  useEffect(() => {
    if (!interactive) return;
    const onMove = (e: PointerEvent) => {
      const now = performance.now();
      const last = lastPointerRef.current;
      lastPointerRef.current = { x: e.clientX, y: e.clientY, t: now };
      if (!last) return;

      const dt = Math.max((now - last.t) / 1000, 1 / 240);

      // Prefer movementX/Y if present
      const dx = typeof e.movementX === "number" ? e.movementX : e.clientX - last.x;
      const dy = typeof e.movementY === "number" ? e.movementY : e.clientY - last.y;

      let pvx = dx / dt; // pointer velocity (px/s)
      let pvy = dy / dt;

      // Clamp insane spikes
      const MAX_POINTER_V = 5000;
      if (pvx > MAX_POINTER_V) pvx = MAX_POINTER_V;
      if (pvx < -MAX_POINTER_V) pvx = -MAX_POINTER_V;
      if (pvy > MAX_POINTER_V) pvy = MAX_POINTER_V;
      if (pvy < -MAX_POINTER_V) pvy = -MAX_POINTER_V;

      // Map pointer speed -> starfield speed (opposite direction)
      // Increase GAIN to make it “more spaceship”, decrease if it’s too spicy.
      const GAIN = 0.020; // (starfield px/s) per (pointer px/s)

      const targetVx = -pvx * GAIN;
      const targetVy = -pvy * GAIN;

      // Smooth to avoid jitter, but keep inertia: we’re just filtering the measurement.
      const SMOOTH = 0.25; // 0..1 (higher = snappier)
      fieldVelRef.current.vx = fieldVelRef.current.vx + (targetVx - fieldVelRef.current.vx) * SMOOTH;
      fieldVelRef.current.vy = fieldVelRef.current.vy + (targetVy - fieldVelRef.current.vy) * SMOOTH;

      // Optional: clamp resulting field speed
      const MAX_FIELD_V = 2000; // px/s
      const vx = fieldVelRef.current.vx;
      const vy = fieldVelRef.current.vy;
      const mag = Math.hypot(vx, vy);
      if (mag > MAX_FIELD_V) {
        const s = MAX_FIELD_V / mag;
        fieldVelRef.current.vx *= s;
        fieldVelRef.current.vy *= s;
      }
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, [interactive]);

  // Render loop with motion blur
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let raf = 0;
    mountTimeRef.current = performance.now();
    const fadeInSec = Math.max(1, appearFadeMs) / 1000;

    // Motion blur controls
    const BLUR_MULT = 3.0; // streak length = (frame travel) * BLUR_MULT
    const BLUR_THRESHOLD = 0.8; // px/frame before switching to streaks

    const render = (t: number) => {
      const last = lastTimeRef.current;
      const dt = last ? Math.min((t - last) / 1000, 0.05) : 0;
      lastTimeRef.current = t;
      const elapsed = (t - mountTimeRef.current) / 1000;

      const { w, h } = sizeRef.current;
      if (w <= 0 || h <= 0) {
        raf = requestAnimationFrame(render);
        return;
      }

      // Integrate persistent velocity into global offset.
      const vx = fieldVelRef.current.vx;
      const vy = fieldVelRef.current.vy;

      offsetRef.current.ox += vx * dt;
      offsetRef.current.oy += vy * dt;

      // Wrap offsets to keep numbers bounded.
      offsetRef.current.ox = ((offsetRef.current.ox % w) + w) % w;
      offsetRef.current.oy = ((offsetRef.current.oy % h) + h) % h;

      // Clear
      ctx.clearRect(0, 0, w, h);

      // Frame travel vector in px/frame (CSS px)
      const fx = vx * dt;
      const fy = vy * dt;
      const frameSpeed = Math.hypot(fx, fy);

      const stars = starsRef.current;
      const ox = offsetRef.current.ox;
      const oy = offsetRef.current.oy;

      for (let i = 0; i < stars.length; i++) {
        const s = stars[i];

        // Base translated position (wrap)
        let x = s.x + ox;
        let y = s.y + oy;
        x = x % w; if (x < 0) x += w;
        y = y % h; if (y < 0) y += h;

        // Sequential appearance: each star starts invisible until appearAt,
        // then fades in over fadeInSec.
        const appearProgress =
          s.appearAt <= 0
            ? 1
            : Math.max(0, Math.min(1, (elapsed - s.appearAt) / fadeInSec));
        if (appearProgress <= 0) continue;

        // Twinkle
        let alpha = s.baseOpacity;
        if (s.twinklePeriod !== null) {
          const tw = 0.5 + 0.5 * Math.sin((t / 1000) * (Math.PI * 2) / s.twinklePeriod + s.phase);
          alpha = s.baseOpacity * (0.6 + 0.4 * tw);
        }
        alpha *= appearProgress;

        ctx.globalAlpha = alpha;

        // Avoid ugly edge-spanning streaks when wrapping: only streak if travel is modest relative to canvas.
        const safeForStreak =
          Math.abs(fx) < w * 0.25 && Math.abs(fy) < h * 0.25;

        if (frameSpeed > BLUR_THRESHOLD && safeForStreak) {
          // Streak from previous along motion direction (opposite of travel gives the trailing tail)
          const tailX = x - fx * BLUR_MULT;
          const tailY = y - fy * BLUR_MULT;

          ctx.beginPath();
          ctx.moveTo(tailX, tailY);
          ctx.lineTo(x, y);
          ctx.lineCap = "round";
          ctx.lineWidth = Math.max(1, s.radius * 2);
          ctx.strokeStyle = "white";
          ctx.stroke();
        } else {
          ctx.beginPath();
          ctx.arc(x, y, s.radius, 0, Math.PI * 2);
          ctx.fillStyle = "white";
          ctx.fill();
        }
      }

      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(render);
    };

    raf = requestAnimationFrame(render);
    return () => cancelAnimationFrame(raf);
  }, [appearFadeMs]);

  return <canvas ref={canvasRef} className={cn("absolute inset-0 h-full w-full", className)} />;
};
