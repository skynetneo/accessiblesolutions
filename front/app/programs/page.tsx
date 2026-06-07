"use client";

import { ArrowRight, MapPin, GraduationCap, Users, Atom, Sparkles } from "lucide-react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useState } from "react";


const programs = [
  {
    id: "accessfyndr",
    name: "AccessFyndr",
    tagline: "AI-Powered Resource Discovery",
    description: "Our flagship agentic map that helps you find accessible services, support programs, and community resources near you using natural language search. Powered by advanced AI to understand your needs and connect you with the right help.",
    features: [
      "Natural language search - describe what you need in your own words",
      "Location-aware results with directions",
      "Accessibility feature filtering",
      "Real-time availability information",
      "Save and share resource lists",
    ],
    icon: MapPin,
    href: "/accessfyndr",
    gradient: "from-primary to-blue-500",
    featured: true,
    status: "Live",
  },
  {
    id: "accessed",
    name: "AccessEd",
    tagline: "Education & Training",
    description: "Comprehensive accessibility education and training programs for individuals, organizations, and communities. Learn best practices, gain certifications, and build more inclusive environments.",
    features: [
      "Self-paced online courses",
      "Organization training programs",
      "Accessibility certification tracks",
      "Community workshops",
      "Resource library access",
    ],
    icon: GraduationCap,
    href: "/programs",
    gradient: "from-accent to-pink-500",
    featured: false,
    status: "Coming Soon",
  },
  {
    id: "accesshub",
    name: "AccessHub",
    tagline: "Community Connection",
    description: "A community portal connecting people with peer support, local events, volunteer opportunities, and partner organizations. Build meaningful connections and find your support network.",
    features: [
      "Peer support matching",
      "Local accessibility events",
      "Volunteer opportunities",
      "Partner organization directory",
      "Community forums",
    ],
    icon: Users,
    href: "/programs",
    gradient: "from-emerald-500 to-teal-500",
    featured: false,
    status: "Coming Soon",
  },
  {
    id: "accessstem",
    name: "AccessSTEM",
    tagline: "STEM Accessibility",
    description: "Initiatives and programs making STEM education and careers more accessible to people of all abilities. From mentorship to adaptive tools, we are opening doors in science and technology.",
    features: [
      "STEM mentorship programs",
      "Adaptive technology resources",
      "Scholarship information",
      "Career pathway guidance",
      "Partner institution connections",
    ],
    icon: Atom,
    href: "/programs#accessstem",
    gradient: "from-violet-500 to-purple-500",
    featured: false,
    status: "Coming Soon",
  },
];

export default function ProgramsPage() {
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <div className="flex min-h-screen flex-col">
      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative py-24 overflow-hidden">
          <div className="absolute inset-0 bg-linear-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />
          
          <div className="relative z-10 mx-auto max-w-7xl px-6 text-center">
            <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
              <Sparkles className="h-4 w-4" />
              Our Programs
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight md:text-5xl lg:text-6xl">
              Four pillars of{" "}
              <span className="bg-linear-to-r from-primary to-accent bg-clip-text text-transparent">
                accessible support
              </span>
            </h1>
            <p className="mt-6 mx-auto max-w-2xl text-lg text-muted-foreground">
              Each program addresses a unique aspect of accessibility and support, 
              working together to create a comprehensive ecosystem of resources.
            </p>
          </div>
        </section>

        {/* Programs Grid */}
        <section className="py-12 pb-24">
          <div className="mx-auto max-w-7xl px-6">
            <div className="grid items-start gap-6 lg:grid-cols-2">
              {programs.map((program) => {
                const isOpen = openId === program.id;
                return (
                  <article
                    id={program.id}
                    key={program.id}
                    className={cn(
                      "group relative overflow-hidden rounded-3xl border border-border/50 bg-card/50 transition-all duration-300",
                      "hover:-translate-y-1 hover:scale-[1.01] hover:border-primary/30 hover:bg-card hover:shadow-xl hover:shadow-primary/5",
                      isOpen && "border-primary/30 bg-card shadow-xl shadow-primary/5 ring-1 ring-primary/20",
                      program.featured && "lg:col-span-2"
                    )}
                    onMouseEnter={() => setOpenId(program.id)}
                  >
                    <button
                      type="button"
                      onClick={() => setOpenId(isOpen ? null : program.id)}
                      className={cn(
                        "relative z-10 w-full text-left",
                        program.featured ? "p-8 md:p-10" : "p-6 md:p-8"
                      )}
                      aria-expanded={isOpen}
                      aria-controls={`${program.id}-panel`}
                    >
                      <div className={cn(
                        "grid gap-6",
                        program.featured ? "md:grid-cols-[auto_1fr_auto]" : "md:grid-cols-[auto_1fr]"
                      )}>
                        <div className={cn(
                          "flex items-center justify-center rounded-2xl bg-linear-to-br shadow-lg transition-transform duration-300 group-hover:scale-110",
                          program.gradient,
                          program.featured ? "h-16 w-16 md:h-20 md:w-20" : "h-14 w-14"
                        )}>
                          <program.icon className={cn(
                            "text-white transition-transform duration-300 group-hover:scale-110",
                            program.featured ? "h-8 w-8 md:h-10 md:w-10" : "h-7 w-7"
                          )} />
                        </div>

                        <div className="min-w-0 space-y-3">
                          <div className="flex flex-wrap items-center gap-3">
                            <h2 className={cn(
                              "font-bold text-foreground transition-colors group-hover:text-primary",
                              program.featured ? "text-3xl md:text-4xl" : "text-2xl"
                            )}>
                              {program.name}
                            </h2>
                            <span className={cn(
                              "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium",
                              program.status === "Live"
                                ? "bg-emerald-500/10 text-emerald-500"
                                : "bg-muted text-muted-foreground"
                            )}>
                              {program.status === "Live" && (
                                <span className="relative flex h-2 w-2">
                                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-75" />
                                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                                </span>
                              )}
                              {program.status}
                            </span>
                          </div>
                          <p className="text-muted-foreground">{program.tagline}</p>
                          <p className={cn(
                            "text-muted-foreground leading-relaxed transition-all duration-300",
                            isOpen ? "max-h-32 opacity-100" : "max-h-0 overflow-hidden opacity-0"
                          )}>
                            {program.description}
                          </p>
                        </div>

                        <span
                          className={cn(
                            buttonVariants({ variant: program.featured ? "default" : "ghost", size: "sm" }),
                            "w-fit gap-2 self-start",
                            program.featured && "bg-linear-to-r from-primary to-accent hover:opacity-90"
                          )}
                        >
                          {isOpen ? "Collapse" : "Learn more"}
                          <ArrowRight className={cn("h-4 w-4 transition-transform", isOpen ? "rotate-90" : "group-hover:translate-x-1 group-hover:scale-110")} aria-hidden />
                        </span>
                      </div>
                    </button>

                    <div
                      id={`${program.id}-panel`}
                      className={cn(
                        "relative z-10 grid overflow-hidden px-6 transition-all duration-300 md:px-8",
                        isOpen ? "grid-rows-[1fr] pb-8 opacity-100" : "grid-rows-[0fr] opacity-0"
                      )}
                    >
                      <div className="min-h-0">
                        <div className="grid gap-6 border-t border-border/30 pt-6 md:grid-cols-2">
                          <div>
                            <h3 className="text-lg font-semibold text-foreground">What you can do</h3>
                            <ul className="mt-3 grid gap-2">
                              {program.features.map((feature) => (
                                <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground">
                                  <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                                  {feature}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h3 className="text-lg font-semibold text-foreground">Program status</h3>
                            <p className="mt-3 text-sm text-muted-foreground">
                              {program.status === "Live"
                                ? "This program is live and ready to use today."
                                : "This program is in development. Join the waitlist to get updates."}
                            </p>
                            <div className="mt-4 flex flex-wrap gap-2">
                              <Link
                                href={program.status === "Live" ? program.href : "/contact"}
                                className={cn(
                                  buttonVariants({ variant: program.status === "Live" ? "default" : "outline" }),
                                  "gap-2",
                                  program.status === "Live" && "bg-linear-to-r from-primary to-accent hover:opacity-90"
                                )}
                              >
                                {program.status === "Live" ? "Open program" : "Join waitlist"}
                                <ArrowRight className="h-4 w-4" aria-hidden />
                              </Link>
                              <Link href="/programs" className={cn(buttonVariants({ variant: "ghost" }), "gap-2")}>
                                View roadmap
                              </Link>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className={cn(
                      "pointer-events-none absolute -bottom-24 -right-24 h-48 w-48 rounded-full bg-linear-to-br opacity-20 blur-3xl",
                      program.gradient
                    )} />
                  </article>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
