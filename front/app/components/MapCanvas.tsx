"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, type ComponentProps, type ComponentType } from "react";
import {
  CircleMarker as CircleMarkerBase,
  MapContainer as MapContainerBase,
  Marker as MarkerBase,
  Popup as PopupBase,
  TileLayer as TileLayerBase,
  Tooltip as TooltipBase,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import type { LeafletMouseEvent } from "leaflet";

import { cn } from "@/lib/utils";
import { useResources } from "@/lib/hooks/use-resources";
import { ResourceCard } from "@/components/ResourceCard";

const MapContainer = MapContainerBase as ComponentType<ComponentProps<typeof MapContainerBase>>;
const TileLayer = TileLayerBase as ComponentType<ComponentProps<typeof TileLayerBase>>;
const Marker = MarkerBase as ComponentType<ComponentProps<typeof MarkerBase>>;
const Popup = PopupBase as ComponentType<ComponentProps<typeof PopupBase>>;
const Tooltip = TooltipBase as ComponentType<ComponentProps<typeof TooltipBase>>;
const CircleMarker = CircleMarkerBase as ComponentType<ComponentProps<typeof CircleMarkerBase>>;

// 1. CONFIGURATION
// Colors mapped to service keywords returned by your Python backend
const CATEGORY_COLORS: Record<string, string> = {
  "Food": "#22c55e",       // Emerald
  "Medical": "#3b82f6",    // Blue
  "Housing": "#f59e0b",    // Amber
  "Legal": "#8b5cf6",      // Violet
  "Mental": "#ec4899",     // Pink
  "Youth": "#06b6d4",      // Cyan
  "Family": "#6366f1",     // Indigo
  "default": "#3b82f6",    // Default Blue
};

// 2. HELPER: Custom Marker Generator
// Creates a CSS-based marker to avoid Next.js image loader issues with Leaflet
const createCustomIcon = (color: string, isSelected: boolean, index: number) => {
  return L.divIcon({
    className: "custom-marker-container",
    html: `
      <div class="relative flex items-center justify-center transition-transform duration-300 ${isSelected ? 'scale-125 z-[50]' : 'hover:scale-110'}">
        <div style="background-color: ${color}; border-color: white;" 
             class="w-8 h-8 rounded-full border-2 shadow-lg flex items-center justify-center text-white font-bold text-xs">
          ${index + 1}
        </div>
        <div style="background-color: ${color};" 
             class="absolute -bottom-1 w-2 h-2 rotate-45 border-r border-b border-white"></div>
        ${isSelected ? '<div class="absolute -bottom-3 w-8 h-1 bg-black/30 blur-sm rounded-full"></div>' : ''}
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

// 3. SUB-COMPONENT: Map Controller
// Handles programmatic moves (FlyTo, FitBounds) based on Global State changes
function MapUpdater() {
  const map = useMap();
  const { foundAgencies, selectedAgencyId, userLocation } = useResources();

  useEffect(() => {
    // A. If specific agency is selected, fly to it
    if (selectedAgencyId) {
      const selected = foundAgencies.find(a => a.id === selectedAgencyId);
      if (selected?.latitude && selected?.longitude) {
        map.flyTo([selected.latitude, selected.longitude], 15, { 
          animate: true,
          duration: 1.5 
        });
        return;
      }
    }

    // B. Otherwise, fit bounds to show all search results
    const validAgencies = foundAgencies.filter(a => a.latitude && a.longitude);
    if (validAgencies.length > 0) {
      const bounds = L.latLngBounds(validAgencies.map(a => [a.latitude!, a.longitude!]));
      map.fitBounds(bounds, { 
        padding: [50, 50], 
        maxZoom: 14,
        animate: true
      });
      return;
    }

    if (userLocation?.latitude && userLocation?.longitude) {
      map.flyTo([userLocation.latitude, userLocation.longitude], 13, {
        animate: true,
        duration: 1.2,
      });
    }
  }, [foundAgencies, selectedAgencyId, userLocation, map]);

  return null;
}

function LocationPicker({
  enabled,
  onPick,
}: {
  enabled: boolean;
  onPick?: (lat: number, lng: number) => void;
}) {
  useMapEvents({
    click: (e: LeafletMouseEvent) => {
      if (!enabled || !onPick) return;
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// 4. MAIN COMPONENT
export default function MapCanvas({
  className,
  isPickingLocation = false,
  onPickLocation,
}: {
  className?: string;
  isPickingLocation?: boolean;
  onPickLocation?: (lat: number, lng: number) => void;
}) {
  const { foundAgencies, selectedAgencyId, setSelectedAgencyId, userLocation } = useResources();
  
  // Default: Eugene, OR (Fallback center)
  const defaultCenter: [number, number] = [44.0521, -123.0868];

  return (
    <div className={cn("relative w-full h-full bg-zinc-950 isolate", className)}>
      <MapContainer
        center={defaultCenter}
        zoom={13}
        scrollWheelZoom={true}
        className={cn("w-full h-full z-0", isPickingLocation && "cursor-crosshair")}
        zoomControl={false} // We can add custom controls later if needed
      >
        {/* Dark Mode Tiles */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        {/* Logic to update map view based on state */}
        <MapUpdater />
        {isPickingLocation && <LocationPicker enabled={isPickingLocation} onPick={onPickLocation} />}

        {userLocation?.latitude && userLocation?.longitude && (
          <CircleMarker
            center={[userLocation.latitude, userLocation.longitude]}
            radius={7}
            pathOptions={{
              color: "#38bdf8",
              weight: 2,
              fillColor: "#0ea5e9",
              fillOpacity: 0.9,
            }}
          >
            <Tooltip direction="top" offset={[0, -12]} opacity={0.9}>
              You are here
            </Tooltip>
          </CircleMarker>
        )}

        {/* Render Markers */}
        {foundAgencies.map((agency, index) => {
          if (!agency.latitude || !agency.longitude) return null;

          const isSelected = selectedAgencyId === agency.id;
          
          // Determine Color based on Services
          // Matches the first keyword found in the agency's services list
          const serviceStr = (agency.services || []).join(" ");
          const matchedKey = Object.keys(CATEGORY_COLORS).find(key => 
            serviceStr.includes(key)
          );
          const color = matchedKey ? CATEGORY_COLORS[matchedKey] : CATEGORY_COLORS.default;

          return (
            <Marker
              key={agency.id}
              position={[agency.latitude, agency.longitude]}
              icon={createCustomIcon(color, isSelected, index)}
              eventHandlers={{
                click: () => setSelectedAgencyId(agency.id),
              }}
              // Z-Index Offset ensures selected marker stays on top
              zIndexOffset={isSelected ? 1000 : 0} 
            >
              <Tooltip 
                direction="top" 
                offset={[0, -32]} 
                opacity={0.9}
                className="font-sans font-semibold text-xs"
              >
                {agency.name}
              </Tooltip>

              {/* Popup uses our custom ResourceCard */}
              <Popup 
                className="agency-map-popup" 
                maxWidth={320}
                closeButton={false} // ResourceCard has its own styling, we hide default X
              >
                 <ResourceCard agency={agency} />
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Decorative Overlay for "Loading" or "Empty" states could go here */}
      {foundAgencies.length === 0 && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none z-[400]">
          <div className="bg-zinc-900/80 backdrop-blur-sm px-6 py-4 rounded-2xl border border-zinc-800 shadow-2xl">
            <p className="text-zinc-400 text-sm">Search or ask the AI to find resources.</p>
          </div>
        </div>
      )}
    </div>
  );
}
