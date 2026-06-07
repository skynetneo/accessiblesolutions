"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Sidebar } from "@/components/accessfyndr/sidebar";
import { Loader2 } from "lucide-react";
import { useResources } from "@/lib/hooks/use-resources";

// 1. Dynamic Import for Map
// Leaflet relies on the 'window' object, so we must disable SSR for it.
const MapCanvas = dynamic(
  () => import("@/components/MapCanvas"),
  { 
    ssr: false,
    loading: () => (
      <div className="h-full w-full flex items-center justify-center bg-zinc-950 text-zinc-500 gap-2">
        <Loader2 className="h-5 w-5 animate-spin" />
        <span className="text-sm font-medium">Initializing Map...</span>
      </div>
    )
  }
);

export default function AccessFyndrPage() {
  const { setManualLocation } = useResources();
  const [isPickingLocation, setIsPickingLocation] = useState(false);

  return (
    <>
      <AutoLocationRequester />
      <div className="flex h-[calc(100vh-4rem)] w-full overflow-hidden bg-background">
        <aside className="hidden lg:block w-96 shrink-0 z-10 relative shadow-2xl">
          <Sidebar />
        </aside>

        <main className="flex-1 relative z-0">
          <MapCanvas
            isPickingLocation={isPickingLocation}
            onPickLocation={(lat, lng) => {
              setManualLocation(lat, lng);
              setIsPickingLocation(false);
            }}
          />
          <LocationControls
            isPickingLocation={isPickingLocation}
            onTogglePick={() => setIsPickingLocation((prev) => !prev)}
          />
          <div className="lg:hidden absolute top-4 left-4 z-500 pointer-events-none">
            <div className="bg-background/80 backdrop-blur px-3 py-1.5 rounded-lg border border-border text-xs text-muted-foreground">
              Tap markers to view details
            </div>
          </div>
        </main>
      </div>
    </>
  );
}

function AutoLocationRequester() {
  const { requestLocation } = useResources();

  useEffect(() => {
    requestLocation();
  }, [requestLocation]);

  return null;
}

function LocationControls({
  isPickingLocation,
  onTogglePick,
}: {
  isPickingLocation: boolean;
  onTogglePick: () => void;
}) {
  const {
    userLocation,
    locationStatus,
    locationSource,
    refreshLocation,
  } = useResources();

  const label =
    userLocation && locationSource === "manual"
      ? "Location set (manual)"
      : userLocation
        ? "Location set (GPS)"
        : locationStatus === "denied"
          ? "Location denied"
          : "Location unknown";

  return (
    <div className="absolute right-4 top-4 z-600 flex flex-col gap-2">
      <div className="rounded-xl border border-border/60 bg-background/80 backdrop-blur px-3 py-2 text-xs text-muted-foreground">
        {label}
      </div>
      <button
        type="button"
        onClick={() => refreshLocation()}
        className="rounded-xl border border-border/60 bg-background/90 backdrop-blur px-3 py-2 text-xs font-medium text-foreground hover:bg-background"
      >
        Update location
      </button>
      <button
        type="button"
        onClick={onTogglePick}
        className="rounded-xl border border-border/60 bg-background/90 backdrop-blur px-3 py-2 text-xs font-medium text-foreground hover:bg-background"
      >
        {isPickingLocation ? "Click map to set location" : "Set location on map"}
      </button>
    </div>
  );
}
