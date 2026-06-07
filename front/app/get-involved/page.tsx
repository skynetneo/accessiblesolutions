import { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Heart,
  Users,
  Building2,
  Megaphone,
  Mail,
  CheckCircle2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { HeroSection } from "@/components/get-involved/hero-section";
import {
  VolunteerCard,
  type IconName,
} from "@/components/get-involved/volunteer-card";
import { DonationCard } from "@/components/get-involved/donation-card";
import { ApplyButton } from "@/components/get-involved/apply-button";

export const metadata: Metadata = {
  title: "Get Involved",
  description:
    "Join Accessible Solutions as a volunteer, donor, or partner. Help us make vital resources accessible to everyone.",
};

const volunteerRoles: Array<{
  iconName: IconName;
  title: string;
  description: string;
  commitment: string;
}> = [
  {
    iconName: "MapPin",
    title: "Resource Mapper",
    description:
      "Help verify and add accessible locations to our AccessFyndr database.",
    commitment: "2-4 hours/week",
  },
  {
    iconName: "Code",
    title: "Tech Volunteer",
    description:
      "Contribute to our open-source projects and help build accessible technology.",
    commitment: "Flexible",
  },
  {
    iconName: "BookOpen",
    title: "Content Creator",
    description:
      "Write educational materials and accessibility guides for AccessEd.",
    commitment: "4-6 hours/week",
  },
  {
    iconName: "Users",
    title: "Community Ambassador",
    description:
      "Represent Accessible Solutions at events and connect with local organizations.",
    commitment: "5-10 hours/month",
  },
];

const donationTiers = [
  {
    amount: "$25",
    impact: "Provides accessibility training for one community navigator",
    popular: false,
  },
  {
    amount: "$50",
    impact: "Maps 10 new accessible locations in underserved areas",
    popular: false,
  },
  {
    amount: "$100",
    impact: "Supports one student through our AccessSTEM program for a month",
    popular: true,
  },
  {
    amount: "$250",
    impact: "Funds development of new accessibility features",
    popular: false,
  },
];

const partnerBenefits = [
  "Co-branded visibility on our platform",
  "Access to our resource database API",
  "Employee volunteer opportunities",
  "Impact reports and recognition",
  "Direct line to our community",
  "Tax-deductible contributions",
];

export default function GetInvolvedPage() {
  return (
    <div className="flex min-h-screen flex-col">

      <main className="flex-1">
        {/* Hero Section with Canvas Reveal Effect */}
        <HeroSection />

        {/* Volunteer Section */}
        <section id="volunteer" className="py-24 bg-secondary/20">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-16">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 mb-4">
                <Users className="h-6 w-6 text-primary" />
              </div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                Volunteer with <span className="text-primary">Us</span>
              </h2>
              <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
                Join our community of volunteers making a real difference. No
                matter your skills, there is a role for you.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-12">
              {volunteerRoles.map((role) => (
                <VolunteerCard
                  key={role.title}
                  iconName={role.iconName}
                  title={role.title}
                  description={role.description}
                  commitment={role.commitment}
                />
              ))}
            </div>

            <div className="text-center">
              <ApplyButton />
            </div>
          </div>
        </section>

        {/* Donate Section */}
        <section id="donate" className="py-24">
          <div className="mx-auto max-w-7xl px-6">
            <div className="text-center mb-16">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 mb-4">
                <Heart className="h-6 w-6 text-accent" />
              </div>
              <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
                Support Our <span className="text-accent">Mission</span>
              </h2>
              <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
                Your donation directly impacts people in need. Every
                contribution helps us expand our reach and improve our programs.
              </p>
            </div>

            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 max-w-5xl mx-auto mb-12">
              {donationTiers.map((tier) => (
                <DonationCard
                  key={tier.amount}
                  amount={tier.amount}
                  impact={tier.impact}
                  popular={tier.popular}
                />
              ))}
            </div>

            <div className="text-center">
              <p className="text-sm text-muted-foreground mb-4">
                Looking to make a custom donation or set up recurring giving?
              </p>
              <Button variant="outline" className="border-border/50 bg-transparent gap-2">
                <Mail className="h-4 w-4" />
                Contact Our Giving Team
              </Button>
            </div>
          </div>
        </section>

        {/* Partner Section */}
        <section id="partner" className="py-24 bg-secondary/20">
          <div className="mx-auto max-w-7xl px-6">
            <div className="grid gap-12 lg:grid-cols-2 items-center">
              <div>
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 mb-6">
                  <Building2 className="h-6 w-6 text-primary" />
                </div>
                <h2 className="text-3xl font-bold tracking-tight md:text-4xl mb-4">
                  Partner with{" "}
                  <span className="text-primary">Accessible Solutions</span>
                </h2>
                <p className="text-muted-foreground mb-8 leading-relaxed">
                  We collaborate with businesses, government agencies, and
                  non-profits to expand our impact. Partnership opportunities
                  include sponsorship, data sharing, technology integration, and
                  more.
                </p>

                <ul className="space-y-3 mb-8">
                  {partnerBenefits.map((benefit) => (
                    <li
                      key={benefit}
                      className="flex items-center gap-3 text-sm text-muted-foreground"
                    >
                      <CheckCircle2 className="h-5 w-5 text-primary shrink-0" />
                      {benefit}
                    </li>
                  ))}
                </ul>

                <Button
                  size="lg"
                  className="bg-linear-to-r from-primary to-accent hover:opacity-90 gap-2"
                >
                  Become a Partner
                  <ArrowRight className="h-5 w-5" />
                </Button>
              </div>

              <div className="rounded-2xl border border-border/50 bg-card/50 p-8">
                <h3 className="text-xl font-semibold mb-6">
                  Partnership Inquiry
                </h3>
                <form className="space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="org-name">Organization Name</Label>
                      <Input
                        id="org-name"
                        placeholder="Your organization"
                        className="bg-background/50"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contact-name">Contact Name</Label>
                      <Input
                        id="contact-name"
                        placeholder="Your name"
                        className="bg-background/50"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@organization.com"
                      className="bg-background/50"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="interest">Partnership Interest</Label>
                    <Textarea
                      id="interest"
                      placeholder="Tell us how you'd like to partner with us..."
                      rows={4}
                      className="bg-background/50"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full bg-primary hover:bg-primary/90"
                  >
                    Submit Inquiry
                  </Button>
                </form>
              </div>
            </div>
          </div>
        </section>

        {/* Ambassador Program */}
        <section className="py-24">
          <div className="mx-auto max-w-7xl px-6">
            <div className="rounded-2xl border border-border/50 bg-linear-to-br from-primary/5 via-card/50 to-accent/5 p-8 md:p-12">
              <div className="grid gap-8 md:grid-cols-2 items-center">
                <div>
                  <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 mb-6">
                    <Megaphone className="h-6 w-6 text-accent" />
                  </div>
                  <h2 className="text-3xl font-bold tracking-tight md:text-4xl mb-4">
                    Become an Ambassador
                  </h2>
                  <p className="text-muted-foreground mb-6 leading-relaxed">
                    Our Ambassador Program empowers passionate advocates to
                    spread the word about accessible resources in their
                    communities. As an ambassador, you will receive training,
                    resources, and support to make a difference locally.
                  </p>
                  <ul className="space-y-2 mb-8">
                    <li className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-accent" />
                      Exclusive training and resources
                    </li>
                    <li className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-accent" />
                      Direct connection to our team
                    </li>
                    <li className="flex items-center gap-2 text-sm text-muted-foreground">
                      <CheckCircle2 className="h-4 w-4 text-accent" />
                      Recognition and networking opportunities
                    </li>
                  </ul>
                  <Button
                    size="lg"
                    variant="outline"
                    className="border-accent text-accent hover:bg-accent/10 bg-transparent gap-2"
                  >
                    Learn More
                    <ArrowRight className="h-5 w-5" />
                  </Button>
                </div>
                <div className="relative">
                  <div className="aspect-square rounded-2xl bg-linear-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                    <div className="text-center">
                      <span className="text-6xl font-bold bg-linear-to-r from-primary to-accent bg-clip-text text-transparent">
                        50+
                      </span>
                      <p className="text-muted-foreground mt-2">
                        Active Ambassadors
                      </p>
                      <p className="text-sm text-muted-foreground">
                        across 12 states
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 bg-linear-to-br from-primary/10 via-background to-accent/10">
          <div className="mx-auto max-w-4xl px-6 text-center">
            <h2 className="text-3xl font-bold tracking-tight md:text-4xl mb-4">
              Every action counts
            </h2>
            <p className="text-muted-foreground mb-8 max-w-2xl mx-auto">
              Not sure where to start? Reach out and we will help you find the
              perfect way to contribute to our mission.
            </p>
            <Button
              size="lg"
              className="bg-linear-to-r from-primary to-accent hover:opacity-90 gap-2"
              asChild
            >
              <Link href="/contact">
                Get in Touch
                <ArrowRight className="h-5 w-5" />
              </Link>
            </Button>
          </div>
        </section>
      </main>

    </div>
  );
}
