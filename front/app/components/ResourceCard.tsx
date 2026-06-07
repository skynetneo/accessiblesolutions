"use client";

import { Agency } from "@/lib/types";
import { 
  MapPin, 
  Phone, 
  Navigation, 
  Globe, 
  CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ResourceCardProps {
  agency: Agency;
  className?: string;
}

export function ResourceCard({ agency, className }: ResourceCardProps) {
  // 1. Generate Google Maps Navigation Link
  const googleMapsUrl = agency.latitude && agency.longitude
    ? `https://www.google.com/maps/dir/?api=1&destination=${agency.latitude},${agency.longitude}`
    : null;

  // 2. Normalize "Espanol" data (Python might return bool, string, or list)
  const hasSpanish = Array.isArray(agency.espanol) 
    ? agency.espanol.length > 0 
    : Boolean(agency.espanol);

  // 3. Format Services (Limit to 4 tags to fit in popup)
  const visibleServices = agency.services?.slice(0, 4) || [];

  return (
    <div className={cn(
      "w-full max-w-[320px] bg-zinc-950 border border-zinc-800 rounded-xl shadow-xl overflow-hidden font-sans",
      className
    )}>
      
      {/* Header Section */}
      <div className="p-4 border-b border-zinc-800 bg-zinc-900/50">
        <div className="flex justify-between items-start gap-2">
          <h3 className="font-bold text-white text-base leading-tight">
            {agency.name}
          </h3>
          {/* Status Badge */}
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Open
          </span>
        </div>

        {/* Tags Row */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {hasSpanish && (
            <span className="inline-flex items-center gap-1 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] text-blue-400 border border-blue-500/20">
              <Globe className="h-3 w-3" /> Spanish
            </span>
          )}
          {agency.fees && (
            <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-[10px] text-amber-400 border border-amber-500/20">
              $ {agency.fees}
            </span>
          )}
        </div>
      </div>

      {/* Body Section */}
      <div className="p-4 space-y-4">
        
        {/* Services List */}
        {visibleServices.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {visibleServices.map((service, i) => (
              <span 
                key={i} 
                className="px-2 py-1 rounded-md bg-zinc-800 text-zinc-300 text-xs border border-zinc-700"
              >
                {service}
              </span>
            ))}
          </div>
        )}

        {/* Info Grid */}
        <div className="space-y-2.5">
            {/* Address / Distance */}
            <div className="flex items-start gap-3 text-sm text-zinc-400">
                <MapPin className="h-4 w-4 shrink-0 mt-0.5 text-zinc-500" />
                <div className="flex flex-col">
                    <span className="leading-snug">
                        {agency.address || "Address not available"}
                    </span>
                    {agency.distance_miles !== undefined && (
                        <span className="text-xs text-indigo-400 mt-0.5 font-medium">
                           {agency.distance_miles.toFixed(1)} miles away
                        </span>
                    )}
                </div>
            </div>

            {/* Description (Truncated) */}
            {agency.description && (
                <div className="flex items-start gap-3 text-xs text-zinc-500 italic">
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                    <p className="line-clamp-2 leading-relaxed">
                        {agency.description}
                    </p>
                </div>
            )}
        </div>

        {/* Actions Footer */}
        <div className="grid grid-cols-2 gap-2 pt-2">
            {googleMapsUrl ? (
                <a
                    href={googleMapsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-2 text-xs font-semibold transition-colors"
                >
                    <Navigation className="h-3.5 w-3.5" />
                    Directions
                </a>
            ) : (
                <button disabled className="flex items-center justify-center gap-2 rounded-lg bg-zinc-800 text-zinc-500 px-3 py-2 text-xs font-semibold cursor-not-allowed">
                    <Navigation className="h-3.5 w-3.5" />
                    No Location
                </button>
            )}

            {/* Note: Ideally we'd have a phone number in the Agency type. 
                Assuming it might be part of 'description' or added later. 
                This is a placeholder button. */}
            <button className="flex items-center justify-center gap-2 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-zinc-300 px-3 py-2 text-xs font-semibold transition-colors">
                <Phone className="h-3.5 w-3.5" />
                Call Agency
            </button>
        </div>
      </div>
    </div>
  );
}
