"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, MapPin, GraduationCap, Users, Atom } from "lucide-react";
import { cn } from "@/lib/utils";
import { Meteors } from "@/components/ui/meteors";

const programs = [
  {
    id: "accessfyndr",
    name: "AccessFyndr",
    tagline: "AI-Powered Resource Discovery",
    description: "Our flagship agentic map that helps you find accessible services, support programs, and community resources near you using natural language search.",
    icon: MapPin,
    href: "/accessfyndr",
    gradient: "from-primary to-blue-500",
    featured: true,
  },
  {
    id: "accessed",
    name: "AccessEd",
    tagline: "Education & Training",
    description: "Comprehensive accessibility education and training programs for individuals, organizations, and communities.",
    icon: GraduationCap,
    href: "/programs#accessed",
    gradient: "from-accent to-pink-500",
    featured: false,
  },
  {
    id: "accesshub",
    name: "AccessHub",
    tagline: "Community Connection",
    description: "A community portal connecting people with peer support, local events, volunteer opportunities, and partner organizations.",
    icon: Users,
    href: "/programs#accesshub",
    gradient: "from-emerald-500 to-teal-500",
    featured: false,
  },
  {
    id: "accessstem",
    name: "AccessSTEM",
    tagline: "STEM Accessibility",
    description: "Initiatives and programs making STEM education and careers more accessible to people of all abilities.",
    icon: Atom,
    href: "/programs#accessstem",
    gradient: "from-violet-500 to-purple-500",
    featured: false,
  },
];

export function ProgramsSection() {
  return (
    <section className="relative py-24 overflow-hidden">
      {/* Background elements */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-secondary/20 to-transparent pointer-events-none" />
      
      <div className="relative z-10 mx-auto max-w-7xl px-6">
        {/* Section header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <span className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">
            Our Programs
          </span>
          <h2 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl lg:text-5xl">
            Four pillars of{" "}
            <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
              accessible support
            </span>
          </h2>
          <p className="mt-4 mx-auto max-w-2xl text-muted-foreground">
            Each program addresses a unique aspect of accessibility and support, 
            working together to create a comprehensive ecosystem of resources.
          </p>
        </motion.div>

        {/* Programs grid */}
        <div className="grid gap-6 md:grid-cols-2">
          {programs.map((program, index) => (
            <motion.div
              key={program.id}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: index * 0.1 }}
              className="h-full"
            >
              <Link href={program.href} className="group block h-full">
                <div
                  className={cn(
                    "relative h-full overflow-hidden rounded-2xl border border-border/50 bg-card/50 p-8 transition-all duration-300",
                    "hover:-translate-y-1 hover:scale-[1.02] hover:border-primary/30 hover:bg-card hover:shadow-xl hover:shadow-primary/5",
                    program.featured && "md:col-span-2 md:row-span-1"
                  )}
                >
                  {/* Meteor effect for featured card */}
                  {program.featured && (
                    <div className="absolute inset-0 overflow-hidden">
                      <Meteors number={10} className="opacity-50" />
                    </div>
                  )}

                  <div className="relative z-10">
                    {/* Icon and badge */}
                    <div className="flex items-start justify-between mb-6">
                      <div className={cn(
                        "flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br shadow-lg transition-transform duration-300 group-hover:scale-110",
                        program.gradient
                      )}>
                        <program.icon className="h-7 w-7 text-white transition-transform duration-300 group-hover:scale-110" />
                      </div>
                      {program.featured && (
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                          <span className="relative flex h-2 w-2">
                            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
                            <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
                          </span>
                          Featured
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="space-y-3">
                      <div>
                        <h3 className="text-xl font-bold text-foreground group-hover:text-primary transition-colors">
                          {program.name}
                        </h3>
                        <p className="text-sm text-muted-foreground">{program.tagline}</p>
                      </div>
                      <p className="text-muted-foreground leading-relaxed">
                        {program.description}
                      </p>
                    </div>

                    {/* CTA */}
                    <div className="mt-6 flex items-center gap-2 text-sm font-medium text-primary">
                      <span>Learn more</span>
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1 group-hover:scale-110" />
                    </div>
                  </div>

                  {/* Hover gradient */}
                  <div className={cn(
                    "absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100 pointer-events-none",
                    "bg-gradient-to-br",
                    program.gradient.replace("from-", "from-").replace("to-", "to-") + "/5"
                  )} />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
