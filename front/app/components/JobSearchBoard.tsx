"use client";

import { useResources } from "@/lib/hooks/use-resources";
import { Briefcase, Building2, MapPin, ExternalLink, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export function JobSearchBoard() {
  const { jobListings } = useResources();

  if (!jobListings || jobListings.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-muted-foreground p-8 text-center">
        <div className="h-16 w-16 rounded-2xl bg-muted/50 flex items-center justify-center mb-4">
          <Search className="h-8 w-8 opacity-50" />
        </div>
        <h3 className="text-lg font-semibold text-foreground">No Jobs Found Yet</h3>
        <p className="max-w-sm mt-2">
          Ask the Assistant to &quot;Find construction jobs in Eugene&quot; or &quot;Search for entry-level IT roles&quot;.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 p-4 md:grid-cols-2 lg:grid-cols-3">
      {jobListings.map((job, idx) => (
        <div 
            key={job.id || idx} 
            className="group relative flex flex-col justify-between rounded-xl border border-border/50 bg-card p-5 transition-all hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
        >
          <div>
            <div className="flex items-start justify-between mb-2">
                <h3 className="font-bold text-foreground line-clamp-2">{job.title}</h3>
                <div className="p-2 rounded-lg bg-accent/10 text-accent">
                    <Briefcase className="h-4 w-4" />
                </div>
            </div>
            
            <div className="space-y-1.5 mb-4">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Building2 className="h-3.5 w-3.5" />
                    <span>{job.company}</span>
                </div>
                {job.location && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <MapPin className="h-3.5 w-3.5" />
                        <span>{job.location}</span>
                    </div>
                )}
                {job.salary && (
                    <div className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 mt-1">
                        {job.salary}
                    </div>
                )}
            </div>
            
            <p className="text-xs text-muted-foreground line-clamp-3 mb-4">
                {job.description}
            </p>
          </div>

          <Button 
            variant="outline" 
            className="w-full justify-between group-hover:bg-primary group-hover:text-white transition-colors"
            asChild
          >
            <a href={job.url} target="_blank" rel="noopener noreferrer">
              View details
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        </div>
      ))}
    </div>
  );
}
