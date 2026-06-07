"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, Sparkles, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/programs", label: "Programs" },
  { href: "/accessfyndr", label: "AccessFyndr" },
  { href: "/programs#accessed", label: "AccessEd" },
  { href: "/about", label: "About" },
  { href: "/get-involved", label: "Get Involved" },
  { href: "/contact", label: "Contact" },
];

export function SiteHeader() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  // Check if a nav item is active
  const isActive = (href: string) => {
    if (href.includes("#")) return false;
    if (href === "/") return pathname === "/";
    // Exact match for specific pages
    if (pathname === href) return true;
    // For /programs, only match if we're on /programs exactly.
    if (href === "/programs") return pathname === "/programs";
    // For other routes, check if pathname starts with href
    return pathname.startsWith(href + "/");
  };

  return (
    <header className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-xl">
      <div className="flex w-full items-center gap-4 py-4">
        {/* Logo - Far Left */}
        <Link href="/" className="flex items-center gap-3 group">
          <div className="relative">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-linear-to-br from-primary to-accent shadow-lg shadow-primary/25">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div className="absolute -inset-1 rounded-xl bg-linear-to-br from-primary to-accent opacity-0 blur-lg transition-opacity group-hover:opacity-50" />
          </div>
          <div className="flex flex-col">
            <span className={cn("text-lg font-bold tracking-tight transition-colors", pathname === "/" ? "text-accent" : "")}>
              Accessible Solutions
            </span>
            <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">Finding Resources with Dignity</span>
          </div>
        </Link>

        {/* Desktop Navigation - Center */}
        <nav className="hidden flex-1 items-center justify-center gap-2 min-[900px]:flex">
          {navItems.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={`${item.href}-${item.label}`}
                href={item.href}
                className={cn(
                  "relative rounded-lg px-4 py-2.5 text-base font-medium transition-colors",
                  active 
                    ? "text-accent hover:text-accent/80" 
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
                )}
              >
                {item.label}
                {active && (
                  <span className="absolute -top-1 left-1/2 -translate-x-1/2 flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Desktop CTA - Far Right */}
        <div className="hidden items-center gap-3.5 min-[900px]:flex">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/accessfyndr">Get Help</Link>
          </Button>
          <Button size="sm" className="gap-2 bg-linear-to-r from-primary to-accent px-4 hover:opacity-90" asChild>
            <Link href="/accessfyndr">
              Try AccessFyndr
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </div>

        {/* Spacer for mobile */}
        <div className="flex-1 min-[900px]:hidden" />

        {/* Mobile Menu Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary/50 min-[900px]:hidden"
          aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="border-t border-border/40 bg-background min-[900px]:hidden">
          <nav className="flex flex-col gap-1 p-4">
            {navItems.map((item) => {
              const active = isActive(item.href);
              return (
                <Link
                  key={`${item.href}-${item.label}`}
                  href={item.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center justify-between rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                    active
                      ? "bg-accent/10 text-accent"
                      : "text-muted-foreground hover:bg-secondary/50 hover:text-foreground"
                  )}
                >
                  {item.label}
                  {active && <Sparkles className="h-4 w-4" />}
                </Link>
              );
            })}
            <div className="mt-4 flex flex-col gap-2">
              <Button variant="outline" className="w-full bg-transparent" asChild>
                <Link href="/accessfyndr">Get Help</Link>
              </Button>
              <Button className="w-full bg-linear-to-r from-primary to-accent" asChild>
                <Link href="/accessfyndr">Try AccessFyndr</Link>
              </Button>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
