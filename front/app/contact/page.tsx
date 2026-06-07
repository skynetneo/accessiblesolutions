"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, MapPin, Phone, Send, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const contactInfo = [
  {
    icon: Mail,
    label: "Email",
    value: "hello@accessiblesolutions.org",
    href: "mailto:hello@accessiblesolutions.org",
  },
  {
    icon: Phone,
    label: "Phone",
    value: "(541) 555-0113",
    href: "tel:+15415550113",
  },
  {
    icon: MapPin,
    label: "Location",
    value: "Springfield, Oregon",
    href: null,
  },
];

export default function ContactPage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsSubmitting(true);

    await new Promise((resolve) => setTimeout(resolve, 1500));

    setIsSubmitting(false);
    setIsSubmitted(true);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <main className="flex-1">
        <section className="relative py-24 overflow-hidden">
          <div className="absolute inset-0 bg-linear-to-br from-primary/10 via-transparent to-accent/5 pointer-events-none" />

          <div className="relative z-10 mx-auto max-w-7xl px-6">
            <div className="max-w-3xl">
              <h1 className="text-4xl font-bold tracking-tight md:text-5xl">
                Get in{" "}
                <span className="bg-linear-to-r from-primary to-accent bg-clip-text text-transparent">
                  touch
                </span>
              </h1>
              <p className="mt-6 text-xl text-muted-foreground">
                Have a question, want to partner, or need assistance? We would love to hear from you.
              </p>
            </div>
          </div>
        </section>

        <section className="py-12 pb-24">
          <div className="mx-auto max-w-7xl px-6">
            <div className="grid gap-12 lg:grid-cols-[1fr_1.5fr]">
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-bold mb-4">Contact Information</h2>
                  <p className="text-muted-foreground">
                    Reach out to us through any of these channels. We typically respond within 24-48 hours.
                  </p>
                </div>

                <div className="space-y-4">
                  {contactInfo.map((item) => (
                    <div key={item.label} className="flex items-center gap-4">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                        <item.icon className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">{item.label}</p>
                        {item.href ? (
                          <a
                            href={item.href}
                            className="font-medium text-foreground hover:text-primary transition-colors"
                          >
                            {item.value}
                          </a>
                        ) : (
                          <p className="font-medium text-foreground">{item.value}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="rounded-2xl border border-border/50 bg-card/50 p-6">
                  <h3 className="font-semibold mb-2">Need immediate help?</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    If you are in crisis or need immediate assistance finding resources, use AccessFyndr to find help now.
                  </p>
                  <Button asChild className="bg-linear-to-r from-primary to-accent hover:opacity-90">
                    <Link href="/accessfyndr">Find Resources</Link>
                  </Button>
                </div>
              </div>

              <div className="rounded-2xl border border-border/50 bg-card/50 p-8">
                {isSubmitted ? (
                  <div className="flex flex-col items-center justify-center h-full py-12 text-center">
                    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10 mb-6">
                      <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                    </div>
                    <h3 className="text-2xl font-bold mb-2">Message Sent!</h3>
                    <p className="text-muted-foreground mb-6">
                      Thank you for reaching out. We will get back to you within 24-48 hours.
                    </p>
                    <Button onClick={() => setIsSubmitted(false)} variant="outline">
                      Send Another Message
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid gap-6 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label htmlFor="firstName">First Name</Label>
                        <Input
                          id="firstName"
                          placeholder="John"
                          required
                          className="bg-secondary/50 border-border/50"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="lastName">Last Name</Label>
                        <Input
                          id="lastName"
                          placeholder="Doe"
                          required
                          className="bg-secondary/50 border-border/50"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="email">Email</Label>
                      <Input
                        id="email"
                        type="email"
                        placeholder="john@example.com"
                        required
                        className="bg-secondary/50 border-border/50"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="subject">Subject</Label>
                      <Input
                        id="subject"
                        placeholder="How can we help?"
                        required
                        className="bg-secondary/50 border-border/50"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="message">Message</Label>
                      <Textarea
                        id="message"
                        placeholder="Tell us more about how we can help you..."
                        required
                        rows={5}
                        className="bg-secondary/50 border-border/50 resize-none"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="inquiryType">Type of Inquiry</Label>
                      <select
                        id="inquiryType"
                        className="w-full rounded-md bg-secondary/50 border border-border/50 py-2 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                        required
                      >
                        <option value="">Select an option</option>
                        <option value="general">General Question</option>
                        <option value="partnership">Partnership Inquiry</option>
                        <option value="volunteer">Volunteer Interest</option>
                        <option value="technical">Technical Support</option>
                        <option value="media">Media/Press</option>
                        <option value="other">Other</option>
                      </select>
                    </div>

                    <Button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full bg-linear-to-r from-primary to-accent hover:opacity-90 gap-2"
                    >
                      {isSubmitting ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Sending...
                        </>
                      ) : (
                        <>
                          <Send className="h-4 w-4" />
                          Send Message
                        </>
                      )}
                    </Button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
