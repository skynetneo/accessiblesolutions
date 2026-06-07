import Link from "next/link";
import { Sparkles, Mail, MapPin, Heart, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

const footerLinks = {
  programs: [
    { href: "/accessfyndr", label: "AccessFyndr" },
    { href: "/programs#accessed", label: "AccessEd" },
    { href: "/programs#accesshub", label: "AccessHub" },
    { href: "/programs#accessstem", label: "AccessSTEM" },
  ],
  organization: [
    { href: "/about", label: "About Us" },
    { href: "/get-involved", label: "Get Involved" },
    { href: "/contact", label: "Contact" },
    { href: "/accessibility", label: "Accessibility Statement" },
  ],
  resources: [
    { href: "/accessfyndr", label: "Get Help" },
    { href: "/accessfyndr", label: "Find Resources" },
    { href: "/faq", label: "FAQ" },
    { href: "/privacy", label: "Privacy Policy" },
  ],
};

export function SiteFooter() {
  return (
    <footer className="relative border-t border-border/40 bg-card/50">
      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-linear-to-t from-background to-transparent pointer-events-none" />
      
      <div className="relative w-full py-16">
        <div className="mx-auto max-w-7xl">
        <div className="grid gap-12 lg:grid-cols-[1.5fr_1fr_1fr_1fr]">
          {/* Brand Column */}
          <div className="space-y-6">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="relative">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-linear-to-br from-primary to-accent shadow-lg shadow-primary/25">
                  <Sparkles className="h-5 w-5 text-white" />
                </div>
              </div>
              <div className="flex flex-col">
                <span className="text-lg font-bold">Accessible Solutions</span>
                <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Finding Resources with Dignity
                </span>
              </div>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-xs">
              We help people find vital services, assistive resources, and community 
              support with dignity and ease. Everyone deserves access.
            </p>
            <div className="flex flex-col gap-2 text-sm text-muted-foreground">
              <a href="mailto:hello@accessiblesolutions.org" className="flex items-center gap-2 hover:text-foreground transition-colors">
                <Mail className="h-4 w-4 text-primary" />
                hello@accessiblesolutions.org
              </a>
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-accent" />
                Springfield, Oregon
              </div>
            </div>
          </div>

          {/* Programs */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground">
              Programs
            </h3>
            <nav className="flex flex-col gap-2">
              {footerLinks.programs.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Organization */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground">
              Organization
            </h3>
            <nav className="flex flex-col gap-2">
              {footerLinks.organization.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
          </div>

          {/* Resources */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-foreground">
              Resources
            </h3>
            <nav className="flex flex-col gap-2">
              {footerLinks.resources.map((link) => (
                <Link
                  key={`${link.href}-${link.label}`}
                  href={link.href}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors"
                >
                  {link.label}
                </Link>
              ))}
            </nav>
            <Button size="sm" variant="outline" className="mt-4 gap-2 border-primary/50 text-primary hover:bg-primary/10 bg-transparent" asChild>
              <Link href="/get-involved">
                Support Our Mission
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-16 flex flex-col items-center justify-between gap-4 border-t border-border/40 pt-8 md:flex-row">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Accessible Solutions. All rights reserved.
          </p>
          <p className="flex items-center gap-1 text-xs text-muted-foreground">
            Made with <Heart className="h-3 w-3 text-accent fill-accent" /> for our community
          </p>
        </div>
        </div>
      </div>
    </footer>
  );
}
