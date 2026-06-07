"use client";

import React, { useMemo } from "react";
import {
  Card,
  CardTitle,
  CardContent,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Agency } from "@/lib/types";
import {
  MapPin,
  Globe,
  Phone,
  Mail,
  ExternalLink,
  Check,
  Plus,
  Info,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useResources } from "@/lib/hooks/use-resources";
import { cn } from "@/lib/utils";
import { Tooltip } from "@/components/ui/tooltip";

type AgencyCardProps = {
  agency: Agency;
  className?: string;
};

export function AgencyCard({ agency, className }: AgencyCardProps) {
  const { saveAgency, savedAgencies } = useResources();
  const isSaved = savedAgencies.some((a) => a.id === agency.id);

  const hasEspanol =
    agency.espanol === true ||
    (Array.isArray(agency.espanol) && agency.espanol.length > 0);

  const distanceLabel = useMemo(() => {
    if (typeof agency.distance_miles !== "number") return undefined;
    const fixed = agency.distance_miles.toFixed(1);
    return fixed.endsWith(".0") ? fixed.slice(0, -2) : fixed;
  }, [agency.distance_miles]);

  const getFeeBadge = (fees?: string) => {
    const feeLower = fees?.toLowerCase() || "";
    if (
      feeLower.includes("free") ||
      feeLower.includes("no fee") ||
      feeLower.includes("none")
    ) {
      return (
        <Badge
          variant="secondary"
          className="bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border-emerald-500/30"
        >
          Free Services
        </Badge>
      );
    }
    if (fees) {
      return (
        <Badge
          variant="outline"
          className="text-amber-400 border-amber-500/30 bg-amber-500/10"
        >
          {fees}
        </Badge>
      );
    }
    return null;
  };

  const renderContact = (contact: string, idx: number) => {
    const isEmail = contact.includes("@");
    const isUrl = contact.startsWith("http") || contact.includes("www.");
    const cleanPhone = contact.replace(/[^\d+]/g, "");

    if (isUrl) {
      const href = contact.startsWith("http") ? contact : `https://${contact}`;
      return (
        <a
          key={idx}
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          <span>Website</span>
        </a>
      );
    }

    if (isEmail) {
      return (
        <a
          key={idx}
          href={`mailto:${contact}`}
          className="flex items-center gap-2 text-sm text-primary hover:text-primary/80 transition-colors"
        >
          <Mail className="w-3 h-3" />
          <span className="break-all">{contact}</span>
        </a>
      );
    }

    return (
      <a
        key={idx}
        href={`tel:${cleanPhone}`}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
      >
        <Phone className="w-3 h-3" />
        <span>{contact}</span>
      </a>
    );
  };

  const services = Array.isArray(agency.services) ? agency.services : [];
  const servicesHead = services.slice(0, 4);
  const servicesTail = services.slice(4);

  const contacts = Array.isArray(agency.contacts) ? agency.contacts : [];
  const contactsHead = contacts.slice(0, 3);
  const contactsTail = contacts.slice(3);

  return (
    <Card
      className={cn(
        "w-full max-w-[350px] border-l-4 bg-card/50 backdrop-blur-sm transition-all duration-300 hover:bg-card/80 hover:shadow-lg hover:shadow-primary/10",
        isSaved ? "border-l-emerald-500" : "border-l-primary",
        className
      )}
    >
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start gap-2">
          <CardTitle className="text-lg font-bold leading-tight text-foreground">
            {agency.name}
          </CardTitle>

          {distanceLabel !== undefined && (
            <Badge
              variant="secondary"
              className="font-mono text-xs whitespace-nowrap bg-secondary text-secondary-foreground"
            >
              {distanceLabel} mi
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap gap-2 mt-2">
          {getFeeBadge(agency.fees)}

          {hasEspanol && (
            <Badge
              variant="outline"
              className="flex items-center gap-1 border-accent/30 bg-accent/10 text-accent"
            >
              <Globe className="w-3 h-3" /> Español
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="pb-2 space-y-3">
        <div className="flex items-start gap-2 text-sm text-muted-foreground">
          <MapPin className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
          <span>{agency.address || "Address unavailable"}</span>
        </div>

        {agency.description && (
          <Tooltip
            containerClassName="block w-full"
            content={
              <div className="max-w-[22rem] whitespace-pre-wrap leading-relaxed">
                {agency.description}
              </div>
            }
          >
            <div className="flex items-start gap-2 text-xs text-muted-foreground bg-secondary/50 p-2 rounded-md border border-border/50">
              <Info className="w-4 h-4 mt-0.5 shrink-0 text-muted-foreground" />
              <p className="line-clamp-3 leading-relaxed">{agency.description}</p>
            </div>
          </Tooltip>
        )}

        {contactsHead.length > 0 && (
          <div className="pt-1 flex flex-col gap-1.5">
            {contactsHead.map((c, i) => renderContact(c, i))}

            {contactsTail.length > 0 && (
              <Tooltip
                containerClassName="inline-flex"
                content={
                  <div className="max-w-[22rem] space-y-1">
                    <div className="text-xs font-semibold text-muted-foreground">
                      Additional contacts
                    </div>
                    <div className="text-xs whitespace-pre-wrap">
                      {contactsTail.join("\n")}
                    </div>
                  </div>
                }
              >
                <span className="text-xs text-muted-foreground cursor-default">
                  +{contactsTail.length} more
                </span>
              </Tooltip>
            )}
          </div>
        )}

        {services.length > 0 && (
          <div className="pt-2">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase mb-1">
              Services
            </p>

            <div className="flex flex-wrap gap-1">
              {servicesHead.map((s, i) => (
                <span
                  key={i}
                  className="text-xs bg-secondary text-secondary-foreground px-2 py-0.5 rounded-full border border-border/50"
                >
                  {s}
                </span>
              ))}

              {servicesTail.length > 0 && (
                <Tooltip
                  content={
                    <div className="max-w-[22rem]">
                      <div className="text-xs font-semibold text-muted-foreground mb-1">
                        More services
                      </div>
                      <div className="text-xs whitespace-pre-wrap">
                        {servicesTail.join("\n")}
                      </div>
                    </div>
                  }
                >
                  <span className="text-xs text-muted-foreground px-1 cursor-default">
                    +{servicesTail.length}
                  </span>
                </Tooltip>
              )}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-2">
        <Button
          className={cn(
            "w-full transition-all",
            isSaved
              ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30"
              : "bg-gradient-to-r from-primary to-accent hover:opacity-90"
          )}
          variant={isSaved ? "secondary" : "default"}
          onClick={(e) => {
            e.stopPropagation();
            saveAgency(agency);
          }}
          disabled={isSaved}
        >
          {isSaved ? (
            <>
              <Check className="w-4 h-4 mr-2" /> Saved to Plan
            </>
          ) : (
            <>
              <Plus className="w-4 h-4 mr-2" /> Add to Resource Plan
            </>
          )}
        </Button>
      </CardFooter>
    </Card>
  );
}
