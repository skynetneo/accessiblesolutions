"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, MapPin, Search, MessageSquare, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PlaceholdersAndVanishInput } from "@/components/ui/placeholders-and-vanish-input";

const placeholders = [
  "Find food banks near me...",
  "Wheelchair accessible medical clinics...",
  "Mental health support services...",
  "Housing assistance programs...",
  "Free legal aid in my area...",
];

const mockLocations = [
  { name: "Lane County Food Bank", type: "Food Assistance", distance: "1.2 mi" },
  { name: "Community Health Center", type: "Medical Care", distance: "0.8 mi" },
  { name: "Family Support Services", type: "Social Services", distance: "2.1 mi" },
];

export function AccessFyndrPreview() {
  return (
    <section className="relative py-24 overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-background to-accent/5 pointer-events-none" />
      
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-center">
          {/* Content */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="space-y-8"
          >
            <div>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-accent">
                <Sparkles className="h-4 w-4" />
                Flagship Program
              </span>
              <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl lg:text-5xl">
                <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                  AccessFyndr
                </span>
              </h2>
              <p className="mt-4 text-lg text-muted-foreground leading-relaxed">
                Our AI-powered agentic map transforms how people discover resources. 
                Simply describe what you need in plain language, and let our intelligent 
                system find the best matches near you.
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <MessageSquare className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Natural Language Search</h3>
                  <p className="text-sm text-muted-foreground">
                    Describe your needs in your own words. No complex forms or categories to navigate.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-accent/10">
                  <MapPin className="h-5 w-5 text-accent" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Location-Aware Results</h3>
                  <p className="text-sm text-muted-foreground">
                    Get results sorted by distance with directions to each resource.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10">
                  <Search className="h-5 w-5 text-emerald-500" />
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Smart Filtering</h3>
                  <p className="text-sm text-muted-foreground">
                    Filter by accessibility features, hours, services, and more.
                  </p>
                </div>
              </div>
            </div>

            <Button 
              size="lg" 
              className="bg-gradient-to-r from-primary to-accent hover:opacity-90 gap-2"
              asChild
            >
              <Link href="/accessfyndr">
                Try AccessFyndr Now
                <ArrowRight className="h-5 w-5" />
              </Link>
            </Button>
          </motion.div>

          {/* Interactive Preview */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="relative"
          >
            <div className="relative rounded-2xl border border-border/50 bg-card/80 backdrop-blur-sm p-6 shadow-2xl shadow-primary/10">
              {/* Mock header */}
              <div className="flex items-center gap-2 mb-6">
                <div className="h-3 w-3 rounded-full bg-red-500/80" />
                <div className="h-3 w-3 rounded-full bg-yellow-500/80" />
                <div className="h-3 w-3 rounded-full bg-green-500/80" />
                <span className="ml-4 text-xs text-muted-foreground">accessfyndr.app</span>
              </div>

              {/* Search input */}
              <div className="mb-6">
                <PlaceholdersAndVanishInput
                  placeholders={placeholders}
                  onChange={() => {}}
                  onSubmit={(e) => e.preventDefault()}
                />
              </div>

              {/* Mock map */}
              <div className="relative h-48 rounded-xl bg-secondary/50 overflow-hidden mb-4">
                <div className="absolute inset-0 bg-gradient-to-br from-primary/10 to-accent/10" />
                {/* Map pins */}
                <div className="absolute top-8 left-12 flex h-8 w-8 items-center justify-center rounded-full bg-primary shadow-lg">
                  <MapPin className="h-4 w-4 text-white" />
                </div>
                <div className="absolute top-16 right-16 flex h-8 w-8 items-center justify-center rounded-full bg-accent shadow-lg">
                  <MapPin className="h-4 w-4 text-white" />
                </div>
                <div className="absolute bottom-12 left-1/3 flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500 shadow-lg">
                  <MapPin className="h-4 w-4 text-white" />
                </div>
                {/* Center marker (user) */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                  <div className="relative">
                    <div className="h-4 w-4 rounded-full bg-blue-500 border-2 border-white shadow-lg" />
                    <div className="absolute inset-0 h-4 w-4 rounded-full bg-blue-500 animate-ping opacity-75" />
                  </div>
                </div>
              </div>

              {/* Mock results */}
              <div className="space-y-2">
                {mockLocations.map((location, index) => (
                  <motion.div
                    key={location.name}
                    initial={{ opacity: 0, y: 10 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                    className="flex items-center justify-between rounded-lg bg-secondary/50 p-3 hover:bg-secondary/80 transition-colors cursor-pointer"
                  >
                    <div>
                      <p className="text-sm font-medium text-foreground">{location.name}</p>
                      <p className="text-xs text-muted-foreground">{location.type}</p>
                    </div>
                    <span className="text-xs font-medium text-primary">{location.distance}</span>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Decorative elements */}
            <div className="absolute -top-4 -right-4 h-24 w-24 rounded-full bg-gradient-to-br from-primary/20 to-transparent blur-2xl" />
            <div className="absolute -bottom-4 -left-4 h-24 w-24 rounded-full bg-gradient-to-br from-accent/20 to-transparent blur-2xl" />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
