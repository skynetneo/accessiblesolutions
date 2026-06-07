"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import CopilotOverlay from "@/components/copilot-overlay";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ResourceProvider } from "@/lib/hooks/use-resources";

export function SiteShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const isLearningApp = pathname?.startsWith("/learn");
  const isLogin = pathname?.startsWith("/login");
  const isCareerPrep = pathname?.startsWith("/career-prep");

  if (isLearningApp) {
    return (
      <CopilotKit
        runtimeUrl="/api/copilotkit"
        agent="praxis"
        showDevConsole={false}
        enableInspector={false}
      >
        <div className="praxis-pwa">{children}</div>
      </CopilotKit>
    );
  }

  if (isLogin) {
    return <>{children}</>;
  }

  if (isCareerPrep) {
    return (
      <CopilotKit
        runtimeUrl="/api/copilotkit"
        agent="praxis"
        showDevConsole={false}
        enableInspector={false}
      >
        <TooltipProvider>
          <ResourceProvider>
            {children}
            <CopilotOverlay />
          </ResourceProvider>
        </TooltipProvider>
      </CopilotKit>
    );
  }

  return (
    <CopilotKit
      runtimeUrl="/api/copilotkit"
      agent="praxis"
      showDevConsole={false}
      enableInspector={false}
    >
      <TooltipProvider>
        <ResourceProvider>
          <div className="relative min-h-screen w-full min-w-0 overflow-x-clip bg-background text-foreground">
            <SiteHeader />
            <div className="min-w-0">{children}</div>
            <SiteFooter />
            <CopilotOverlay />
          </div>
        </ResourceProvider>
      </TooltipProvider>
    </CopilotKit>
  );
}
