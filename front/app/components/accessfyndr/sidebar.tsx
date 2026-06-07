"use client";

import { MapPin, Sparkles } from "lucide-react";
import { useResources } from "@/lib/hooks/use-resources";
import { cn } from "@/lib/utils";
import { FilterBar } from "./FilterBar";

export function Sidebar() {
  const { foundAgencies, selectedAgencyId, setSelectedAgencyId } = useResources();

  return (
    <div className="flex flex-col h-full bg-zinc-950/50 backdrop-blur-xl">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-indigo-500/20">
            <Sparkles className="h-5 w-5 text-indigo-400" />
          </div>
          <h2 className="font-bold text-white">Resource Finder</h2>
        </div>
      </div>

      <FilterBar />

      {/* Results List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {foundAgencies.map((agency) => (
          <button
            key={agency.id}
            onClick={() => setSelectedAgencyId(agency.id)}
            className={cn(
              "w-full text-left p-3 rounded-xl transition-all border",
              selectedAgencyId === agency.id
                ? "bg-indigo-500/10 border-indigo-500/50 ring-1 ring-indigo-500/50"
                : "bg-zinc-900/50 border-zinc-800 hover:bg-zinc-800"
            )}
          >
            <h3 className="font-semibold text-zinc-200 text-sm">{agency.name}</h3>
            <div className="flex items-center gap-1 mt-1 text-xs text-zinc-400">
              <MapPin className="h-3 w-3" />
              <span>{agency.distance_miles ? `${agency.distance_miles} mi` : "N/A"}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {agency.services?.slice(0, 3).map((s, i) => (
                <span key={i} className="px-1.5 py-0.5 bg-zinc-800 rounded text-[10px] text-zinc-400">
                  {s}
                </span>
              ))}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
