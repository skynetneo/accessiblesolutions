"use client";

import { useRef, useMemo, useState, useEffect, useCallback } from "react";
import { motion } from "motion/react";
import { geoMercator, geoPath, type GeoPermissibleObjects } from "d3-geo";
import { feature } from "topojson-client";

interface MapProps {
  dots?: Array<{
    start: { lat: number; lng: number; label?: string };
    end: { lat: number; lng: number; label?: string };
  }>;
  lineColor?: string;
}

type CountyFeature = GeoPermissibleObjects & { id?: string | number };
type FeatureCollectionLike = {
  type: "FeatureCollection";
  features: CountyFeature[];
};
type FeatureInput = Parameters<typeof feature>;
type UsAtlasTopology = FeatureInput[0] & {
  objects: {
    counties: FeatureInput[1];
  };
};

function AnimatedDashPath(props: {
  d: string;
  stroke: string;
  strokeWidth?: number;
  delay?: number;
  drawDur?: number;
  eraseDur?: number;
  pauseDur?: number; // pause while fully drawn
  tailPauseDur?: number; // pause after fully disappeared
}) {
  const {
    d,
    stroke,
    strokeWidth = 2,
    delay = 0,
    drawDur = 1.0,
    eraseDur = 1.0,
    pauseDur = 0.6,
    tailPauseDur = 0.5,
  } = props;

  const pathRef = useRef<SVGPathElement | null>(null);
  const [len, setLen] = useState<number>(0);

  useEffect(() => {
    if (!pathRef.current) return;
    try {
      const L = pathRef.current.getTotalLength();
      if (Number.isFinite(L) && L > 0) setLen(L);
    } catch {
      // ignore
    }
  }, [d]);

  if (!len) {
    return (
      <path
        ref={pathRef}
        d={d}
        fill="none"
        stroke={stroke}
        strokeWidth={strokeWidth}
        opacity={0}
      />
    );
  }

  // Timeline: draw -> hold -> peel -> invisible hold
  const total = drawDur + pauseDur + eraseDur + tailPauseDur;
  const tDrawEnd = drawDur / total;
  const tHoldEnd = (drawDur + pauseDur) / total;
  const tEraseEnd = (drawDur + pauseDur + eraseDur) / total;

  return (
    <motion.path
      ref={pathRef}
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={len}
      initial={{ strokeDashoffset: len, opacity: 0 }}
      animate={{
        // Draw: len -> 0
        // Peel (erase from SOURCE/start of this path): 0 -> len
        // Then stay gone
        strokeDashoffset: [len, 0, 0, len, len],
        opacity: [0, 1, 1, 0, 0],
      }}
      transition={{
        duration: total,
        delay,
        repeat: Infinity,
        ease: "easeInOut",
        times: [0, tDrawEnd, tHoldEnd, tEraseEnd, 1],
      }}
    />
  );
}

export default function CatchmentMap({
  dots = [],
  lineColor = "#10b981",
}: MapProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [geography, setGeography] = useState<CountyFeature[]>([]);

  // 1) Load Map Data
  useEffect(() => {
    fetch("https://cdn.jsdelivr.net/npm/us-atlas@3/counties-10m.json")
      .then((response) => response.json())
      .then((us: UsAtlasTopology) => {
        const data = feature(us, us.objects.counties) as unknown as
          | FeatureCollectionLike
          | CountyFeature;
        const features = "features" in data ? data.features : [data];

        const oregonFeatures = features.filter((d) =>
          String(d.id ?? "").padStart(5, "0").startsWith("41")
        );

        setGeography(oregonFeatures);
      })
      .catch(() => {
        setGeography([]);
      });
  }, []);

  // 2) Projection: fit to dots if present, else Oregon
  const projection = useMemo(() => {
    if (geography.length === 0) return null;

    const width = 800;
    const height = 400;
    const padding = 40;

    const oregonFC = {
      type: "FeatureCollection" as const,
      features: geography,
    } as unknown as GeoPermissibleObjects;

    const fitTarget: GeoPermissibleObjects =
      dots.length > 0
        ? {
            type: "MultiPoint" as const,
            coordinates: dots.flatMap((d) => [
              [d.start.lng, d.start.lat],
              [d.end.lng, d.end.lat],
            ]),
          }
        : oregonFC;

    return geoMercator().fitExtent(
      [
        [padding, padding],
        [width - padding, height - padding],
      ],
      fitTarget
    );
  }, [geography, dots]);

  const pathGenerator = useMemo(() => {
    if (!projection) return null;
    return geoPath().projection(projection);
  }, [projection]);

  const projectPoint = useCallback((lat: number, lng: number) => {
    if (!projection) return { x: 0, y: 0 };
    const [x, y] = projection([lng, lat]) || [0, 0];
    return { x, y };
  }, [projection]);

  const createCurvedPath = (
    start: { x: number; y: number },
    end: { x: number; y: number }
  ) => {
    const midX = (start.x + end.x) / 2;
    const midY = Math.min(start.y, end.y) - 40;
    return `M ${start.x} ${start.y} Q ${midX} ${midY} ${end.x} ${end.y}`;
  };

  // Hub label (deduped)
  const hubLabel = useMemo(() => {
    if (!projection || dots.length === 0) return null;
    const hub = dots[0].end;
    const { x, y } = projectPoint(hub.lat, hub.lng);
    return { x, y, label: hub.label };
  }, [projection, dots, projectPoint]);

  return (
    <div className="w-full aspect-[2/1] bg-neutral-950 rounded-lg relative font-sans overflow-hidden border border-neutral-800">
      {/* Base map */}
      <svg
        viewBox="0 0 800 400"
        className="w-full h-full absolute inset-0 pointer-events-none select-none"
      >
        {pathGenerator &&
          geography.map((geo, i) => (
            <path
              key={i}
              d={pathGenerator(geo) || ""}
              fill="#171717"
              stroke="#262626"
              strokeWidth="0.5"
              className="hover:fill-neutral-800 transition-colors duration-300"
            />
          ))}
      </svg>

      {/* Overlays: paths + points */}
      <svg
        ref={svgRef}
        viewBox="0 0 800 400"
        className="w-full h-full absolute inset-0 pointer-events-none select-none"
      >
        {/* Animated routes */}
        {projection &&
          dots.map((dot, i) => {
            const startPoint = projectPoint(dot.start.lat, dot.start.lng);
            const hubPoint = projectPoint(dot.end.lat, dot.end.lng);

            const outD = createCurvedPath(startPoint, hubPoint);
            const backD = createCurvedPath(hubPoint, startPoint);

            const baseDelay = i * 0.35;

            // Timing knobs
            const drawDur = 1.0;
            const pauseDur = 0.6; // pause while fully drawn at destination
            const eraseDur = 1.0; // peel off from source
            const tailPauseDur = 0.5; // dead air after fully gone

            const outboundTotal = drawDur + pauseDur + eraseDur + tailPauseDur;

            return (
              <g key={`route-${i}`}>
                {/* Outbound: town -> hub, then peel from town toward hub */}
                <AnimatedDashPath
                  d={outD}
                  stroke="url(#path-gradient)"
                  strokeWidth={2}
                  delay={baseDelay}
                  drawDur={drawDur}
                  pauseDur={pauseDur}
                  eraseDur={eraseDur}
                  tailPauseDur={tailPauseDur}
                />

                {/* Return: hub -> town, then peel from hub toward town */}
                <AnimatedDashPath
                  d={backD}
                  stroke="url(#path-gradient)"
                  strokeWidth={2}
                  delay={baseDelay + outboundTotal}
                  drawDur={drawDur}
                  pauseDur={pauseDur}
                  eraseDur={eraseDur}
                  tailPauseDur={tailPauseDur}
                />
              </g>
            );
          })}

        <defs>
          <linearGradient id="path-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0" />
            <stop offset="50%" stopColor={lineColor} stopOpacity="1" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Hub label (render once, below the dot like the others) */}
        {projection && hubLabel?.label && (
          <text
            x={hubLabel.x}
            y={hubLabel.y + 20}
            fill="white"
            fontSize="12"
            textAnchor="middle"
            className="opacity-90 font-semibold"
          >
            {hubLabel.label}
          </text>
        )}

        {/* Points */}
        {projection &&
          dots.map((dot, i) => (
            <g key={`points-group-${i}`}>
              {/* Start marker + label */}
              <g key={`start-${i}`}>
                <circle
                  cx={projectPoint(dot.start.lat, dot.start.lng).x}
                  cy={projectPoint(dot.start.lat, dot.start.lng).y}
                  r="3"
                  fill={lineColor}
                />
                {dot.start.label && (
                  <text
                    x={projectPoint(dot.start.lat, dot.start.lng).x}
                    y={projectPoint(dot.start.lat, dot.start.lng).y + 12}
                    fill="white"
                    fontSize="10"
                    textAnchor="middle"
                    className="opacity-70 font-medium"
                  >
                    {dot.start.label}
                  </text>
                )}
              </g>

              {/* Hub marker + pulse (still rendered per-dot; ok visually) */}
              <g key={`end-${i}`}>
                <circle
                  cx={projectPoint(dot.end.lat, dot.end.lng).x}
                  cy={projectPoint(dot.end.lat, dot.end.lng).y}
                  r="4"
                  fill={lineColor}
                />
                <circle
                  cx={projectPoint(dot.end.lat, dot.end.lng).x}
                  cy={projectPoint(dot.end.lat, dot.end.lng).y}
                  r="4"
                  fill={lineColor}
                  opacity="0.5"
                >
                  <animate
                    attributeName="r"
                    from="4"
                    to="20"
                    dur="2s"
                    begin="0s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    from="0.5"
                    to="0"
                    dur="2s"
                    begin="0s"
                    repeatCount="indefinite"
                  />
                </circle>
              </g>
            </g>
          ))}
      </svg>
    </div>
  );
}
