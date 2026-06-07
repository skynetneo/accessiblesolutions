"use client";

import { useCoAgent, useCopilotChatInternal, useCopilotReadable } from "@copilotkit/react-core";
import { createContext, useContext, ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ResourceState, Agency, JobListing, CareerView } from "@/lib/types";
import { COPILOT_ROLE, createCopilotTextMessage, toCopilotTextMessage } from "@/lib/copilot-messages";

type ResourceContextType = {
  // Map
  foundAgencies: Agency[];
  visibleAgencies: Agency[];
  savedAgencies: Agency[];
  selectedAgencyId: string | null;
  setSelectedAgencyId: (id: string | null) => void;
  saveAgency: (agency: Agency) => void;
  removeAgency: (id: string) => void;
  performSearch: (query: string) => void;
  applyFilteredResults: (agencies: Agency[]) => void;
  requestLocation: () => Promise<UserLocation | null>;
  refreshLocation: () => Promise<UserLocation | null>;
  setManualLocation: (lat: number, lng: number) => void;
  userLocation: UserLocation | null;
  locationStatus: LocationStatus;
  locationSource: LocationSource;
  showMore: () => void;
  hasMore: boolean;
  
  // Career
  resumeMarkdown: string;
  coverLetterMarkdown: string;
  jobListings: JobListing[];
  careerView: CareerView;
  setCareerView: (view: CareerView) => void;
};

type UserLocation = {
  latitude: number;
  longitude: number;
  accuracy?: number;
};

type LocationStatus = "idle" | "requesting" | "granted" | "denied" | "unavailable" | "error";
type LocationSource = "browser" | "manual" | null;

const ResourceContext = createContext<ResourceContextType | undefined>(undefined);

const RESOURCE_REPLY_PATTERN =
  /(resources near you|food resources|food bank|food pantry|shelter|housing resources|legal aid|medical resources|clinic|free food|meals)/i;
const RESUME_DRAFT_PATTERN = /RESUME_DRAFT_START\s*([\s\S]*?)\s*RESUME_DRAFT_END/i;

const DEFAULT_EUGENE_LOCATION: UserLocation = {
  latitude: 44.0521,
  longitude: -123.0868,
};

function parseAssistantResources(content: string, location: UserLocation | null): Agency[] {
  if (!RESOURCE_REPLY_PATTERN.test(content)) return [];

  const base = location ?? parseCoordinates(content) ?? DEFAULT_EUGENE_LOCATION;
  const sections = content.split(/(?=^#{2,4}\s+)/gm);
  const candidates = sections
    .map((section, index) => parseResourceSection(section, index, base))
    .filter((agency): agency is Agency => agency !== null);

  return candidates.slice(0, 12);
}

function parseCoordinates(content: string): UserLocation | null {
  const match = content.match(
    /lat(?:itude)?[=:]\s*(-?\d+(?:\.\d+)?).*?(?:lng|lon|longitude)[=:]\s*(-?\d+(?:\.\d+)?)/i
  );
  if (!match) return null;
  const latitude = Number(match[1]);
  const longitude = Number(match[2]);
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;
  return { latitude, longitude };
}

function parseResourceSection(section: string, index: number, base: UserLocation): Agency | null {
  const heading = section.match(/^#{2,4}\s*(?:[^\w#*]+)?\s*(.+)$/m);
  if (!heading) return null;

  const name = cleanResourceText(heading[1]);
  if (!name || /resources near you|food resources|housing resources|legal resources|medical resources/i.test(name)) {
    return null;
  }

  const address = extractResourceField(section, "Address");
  const phone = extractResourceField(section, "Phone");
  const website = extractResourceField(section, "Website");
  const description =
    extractResourceField(section, "What they do") ||
    extractResourceField(section, "Description") ||
    extractResourceField(section, "Notes");
  const coordinates = parseCoordinates(section) ?? estimatedCoordinates(base, index);
  const service = inferService(section);

  return {
    id: slugifyAgencyId(`${name}-${address || index}`),
    name,
    description: [description, phone && `Phone: ${phone}`, website && `Website: ${website}`]
      .filter(Boolean)
      .join(" | "),
    address,
    contacts: [phone, website].filter((value): value is string => Boolean(value)),
    services: [service],
    fees: /free|no cost|without charge/i.test(section) ? "Free" : undefined,
    latitude: coordinates.latitude,
    longitude: coordinates.longitude,
    distance_miles: estimateMiles(base, coordinates),
  };
}

function extractResourceField(section: string, label: string): string | undefined {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = section.match(
    new RegExp(`(?:[-*]\\s*)?(?:\\*\\*)?${escaped}(?:\\*\\*)?\\s*:?\\s*([^\\n]+)`, "i")
  );
  return match ? cleanResourceText(match[1]) : undefined;
}

function cleanResourceText(value: string): string {
  return value
    .replace(/\*\*/g, "")
    .replace(/^[-:\s]+/, "")
    .replace(/\s+-\s*$/, "")
    .trim();
}

function estimatedCoordinates(base: UserLocation, index: number): UserLocation {
  const angle = (index * 137.508 * Math.PI) / 180;
  const radiusMiles = 0.45 + index * 0.22;
  const latOffset = (radiusMiles / 69) * Math.cos(angle);
  const lngOffset = (radiusMiles / (69 * Math.cos((base.latitude * Math.PI) / 180))) * Math.sin(angle);
  return {
    latitude: Number((base.latitude + latOffset).toFixed(6)),
    longitude: Number((base.longitude + lngOffset).toFixed(6)),
  };
}

function estimateMiles(from: UserLocation, to: UserLocation): number {
  const milesPerDegreeLat = 69;
  const milesPerDegreeLng = 69 * Math.cos((from.latitude * Math.PI) / 180);
  const dLat = (to.latitude - from.latitude) * milesPerDegreeLat;
  const dLng = (to.longitude - from.longitude) * milesPerDegreeLng;
  return Number(Math.sqrt(dLat * dLat + dLng * dLng).toFixed(1));
}

function inferService(section: string): string {
  if (/food|meal|pantr|grocery/i.test(section)) return "Food";
  if (/shelter|housing|rent|eviction/i.test(section)) return "Housing";
  if (/legal|law|attorney/i.test(section)) return "Legal";
  if (/medical|clinic|health|doctor/i.test(section)) return "Medical";
  return "Resource";
}

function slugifyAgencyId(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function extractResumeDraft(content: string): string | null {
  const match = content.match(RESUME_DRAFT_PATTERN);
  const draft = match?.[1]?.trim();
  return draft || null;
}

export const ResourceProvider = ({ children }: { children: ReactNode }) => {
  const router = useRouter();
  const { sendMessage, messages: aguiMessages, visibleMessages: legacyVisibleMessages } = useCopilotChatInternal();

  const { state, setState } = useCoAgent<ResourceState>({
    name: "praxis",
    initialState: {
      found_agencies: [],
      saved_agencies: [],
      selected_agency_id: null,
      resume_markdown: "",
      cover_letter_markdown: "",
      job_listings: [],
      career_view: 'jobs' // Default start view
    }
  });

  const [visibleCount, setVisibleCount] = useState(5);
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null);
  const [locationStatus, setLocationStatus] = useState<LocationStatus>("idle");
  const [locationSource, setLocationSource] = useState<LocationSource>(null);
  const locationPromiseRef = useRef<Promise<UserLocation | null> | null>(null);
  const processedNavigationRef = useRef<string | null>(null);
  const stateRef = useRef(state);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        setVisibleCount(5);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [state.found_agencies]);

  const visibleAgencies = useMemo(() => {
    return (state.found_agencies || []).slice(0, visibleCount);
  }, [state.found_agencies, visibleCount]);

  const hasMore = (state.found_agencies?.length || 0) > visibleCount;

  const showMore = () => {
    setVisibleCount((prev) => prev + 5);
  };

  const requestLocation = useCallback((force = false): Promise<UserLocation | null> => {
    if (!force && userLocation) return Promise.resolve(userLocation);
    if (!force && (locationStatus === "denied" || locationStatus === "unavailable")) {
      return Promise.resolve(null);
    }
    if (locationPromiseRef.current) return locationPromiseRef.current;
    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setLocationStatus("unavailable");
      return Promise.resolve(null);
    }

    setLocationStatus("requesting");
    locationPromiseRef.current = new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const next = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            accuracy: pos.coords.accuracy,
          };
          setUserLocation(next);
          setLocationStatus("granted");
          setLocationSource("browser");
          locationPromiseRef.current = null;
          resolve(next);
        },
        (err) => {
          setLocationStatus(err.code === 1 ? "denied" : "error");
          locationPromiseRef.current = null;
          resolve(null);
        },
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 }
      );
    });

    return locationPromiseRef.current;
  }, [userLocation, locationStatus]);

  const refreshLocation = useCallback(() => requestLocation(true), [requestLocation]);

  const setManualLocation = useCallback((lat: number, lng: number) => {
    setUserLocation({ latitude: lat, longitude: lng });
    setLocationStatus("granted");
    setLocationSource("manual");
  }, []);

  useCopilotReadable(
    {
      description: "User location coordinates (lat/lng) if available",
      value: userLocation ? { ...userLocation, source: locationSource } : null,
      available: userLocation ? "enabled" : "disabled",
    },
    [userLocation, locationSource]
  );

  // --- Helpers ---
  const performSearch = async (query: string) => {
    const trimmed = query.trim();
    if (!trimmed) return;
    const location = await requestLocation();
    const locationHint = location
      ? ` My location coordinates: lat=${location.latitude}, lng=${location.longitude}.`
      : "";
    await sendMessage(
      createCopilotTextMessage(COPILOT_ROLE.user, `Find resources for: ${trimmed}.${locationHint}`)
    ).catch((error: unknown) => {
      console.error("Failed to send resource search to CopilotKit", error);
    });
  };

  const saveAgency = (agency: Agency) => {
    if (!state.saved_agencies.some(a => a.id === agency.id)) {
      setState({ ...state, saved_agencies: [...state.saved_agencies, agency] });
    }
  };

  const removeAgency = (id: string) => {
    setState({ ...state, saved_agencies: state.saved_agencies.filter(a => a.id !== id) });
  };

  const applyFilteredResults = useCallback(
    (agencies: Agency[]) => {
      setState({
        ...state,
        found_agencies: agencies,
        selected_agency_id: agencies[0]?.id ?? null,
      });
    },
    [state, setState]
  );
  
  // Navigation Handler
  useEffect(() => {
    const visibleMessages = Array.isArray(aguiMessages) && aguiMessages.length > 0
      ? aguiMessages
      : Array.isArray(legacyVisibleMessages)
        ? legacyVisibleMessages
        : [];
    if (!visibleMessages?.length) return;
    const lastMessage = toCopilotTextMessage(visibleMessages[visibleMessages.length - 1]);
    if (lastMessage?.role === COPILOT_ROLE.assistant) {
      const content = lastMessage.content;
      const resumeDraft = extractResumeDraft(content);
      if (resumeDraft) {
        if (processedNavigationRef.current === content) return;
        processedNavigationRef.current = content;

        setState({
          ...stateRef.current,
          resume_markdown: resumeDraft,
          career_view: "resume",
        });
        router.push("/career-prep");
        return;
      }

      if (content.includes("NAVIGATE_TO:")) {
        if (processedNavigationRef.current === content) return;
        processedNavigationRef.current = content;

        const page = content.split("NAVIGATE_TO:")[1]?.trim().toLowerCase() ?? "";
        if (page.includes("map") || page.includes("fyndr")) router.push("/accessfyndr");
        else if (page.includes("career")) {
          setState({
            ...stateRef.current,
            career_view: "resume",
          });
          router.push("/career-prep");
        }
        else if (page.includes("about")) router.push("/about");
        return;
      }

      const agencies = parseAssistantResources(content, userLocation);
      if (agencies.length > 0) {
        if (processedNavigationRef.current === content) return;
        processedNavigationRef.current = content;

        setState({
          ...stateRef.current,
          found_agencies: agencies,
          selected_agency_id: agencies[0]?.id ?? null,
        });
        router.push("/accessfyndr");
      }
    }
  }, [aguiMessages, legacyVisibleMessages, router, setState, userLocation]);

  // Sync CareerView Helpers
  const setCareerView = (view: CareerView) => {
    setState({ ...state, career_view: view });
  };

  return (
    <ResourceContext.Provider value={{
      foundAgencies: state.found_agencies || [],
      visibleAgencies,
      savedAgencies: state.saved_agencies || [],
      selectedAgencyId: state.selected_agency_id,
      setSelectedAgencyId: (id) => setState({ ...state, selected_agency_id: id }),
      saveAgency,
      removeAgency,
      performSearch,
      applyFilteredResults,
      requestLocation,
      refreshLocation,
      setManualLocation,
      userLocation,
      locationStatus,
      locationSource,
      showMore,
      hasMore,
      
      resumeMarkdown: state.resume_markdown || "",
      coverLetterMarkdown: state.cover_letter_markdown || "",
      jobListings: state.job_listings || [],
      careerView: state.career_view || 'jobs',
      setCareerView
    }}>
      {children}
    </ResourceContext.Provider>
  );
};

export const useResources = () => {
  const context = useContext(ResourceContext);
  if (!context) throw new Error("useResources must be used within a ResourceProvider");
  return context;
};
