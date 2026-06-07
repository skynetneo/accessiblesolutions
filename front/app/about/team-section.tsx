"use client";

import React, { useState } from "react";
import { motion } from "motion/react";
import { Linkedin, Twitter, Mail } from "lucide-react";
import { cn } from "@/lib/utils";

const team = [
  {
    name: "Sarah Chen",
    role: "Executive Director",
    bio: "Former social worker with 15 years of experience in community services.",
    color: "from-rose-500 to-pink-500",
  },
  {
    name: "Marcus Johnson",
    role: "Technology Lead",
    bio: "Software engineer passionate about using tech for social good.",
    color: "from-blue-500 to-cyan-500",
  },
  {
    name: "Dr. Lisa Park",
    role: "Accessibility Advisor",
    bio: "Researcher specializing in inclusive design and assistive technology.",
    color: "from-violet-500 to-purple-500",
  },
  {
    name: "James Wilson",
    role: "Community Outreach",
    bio: "Community organizer connecting people with the resources they need.",
    color: "from-emerald-500 to-teal-500",
  },
];

function TeamCard({
  member,
  index,
}: {
  member: (typeof team)[0];
  index: number;
}) {
  const [isHovered, setIsHovered] = useState(false);
  const initials = member.name
    .split(" ")
    .map((n) => n[0])
    .join("");

  return (
    <motion.div
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="group relative"
    >
      <motion.div
        animate={{
          y: isHovered ? -10 : 0,
        }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        className="relative rounded-2xl border border-border/50 bg-card/50 p-6 text-center overflow-hidden"
      >
        {/* Avatar */}
        <div className="relative mx-auto mb-4">
          <motion.div
            animate={{
              scale: isHovered ? 1.1 : 1,
              rotate: isHovered ? 5 : 0,
            }}
            transition={{ type: "spring", stiffness: 300, damping: 20 }}
            className={cn(
              "h-24 w-24 rounded-full mx-auto flex items-center justify-center bg-gradient-to-br",
              member.color
            )}
          >
            <span className="text-3xl font-bold text-white">{initials}</span>
          </motion.div>

          {/* Floating ring on hover */}
          <motion.div
            className={cn(
              "absolute inset-0 rounded-full border-2 mx-auto",
              `border-${member.color.split(" ")[0].replace("from-", "")}`
            )}
            style={{ width: 96, height: 96, left: "50%", transform: "translateX(-50%)" }}
            animate={{
              scale: isHovered ? 1.3 : 1,
              opacity: isHovered ? 0.5 : 0,
            }}
            transition={{ duration: 0.4 }}
          />
        </div>

        {/* Name and role */}
        <motion.h3
          animate={{ y: isHovered ? -2 : 0 }}
          className="font-semibold text-foreground text-lg"
        >
          {member.name}
        </motion.h3>
        <p className="text-sm text-primary mb-3">{member.role}</p>

        {/* Bio - expands on hover */}
        <motion.div
          animate={{
            height: isHovered ? "auto" : 0,
            opacity: isHovered ? 1 : 0,
          }}
          initial={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.3 }}
          className="overflow-hidden"
        >
          <p className="text-xs text-muted-foreground mb-4">{member.bio}</p>

          {/* Social links */}
          <div className="flex justify-center gap-3">
            {[Linkedin, Twitter, Mail].map((Icon, i) => (
              <motion.button
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 + i * 0.05 }}
                whileHover={{ scale: 1.2 }}
                className="h-8 w-8 rounded-full bg-secondary/50 flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
              >
                <Icon className="h-4 w-4" />
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Compact bio when not hovered */}
        <motion.p
          animate={{
            height: isHovered ? 0 : "auto",
            opacity: isHovered ? 0 : 1,
          }}
          className="text-xs text-muted-foreground overflow-hidden"
        >
          {member.bio}
        </motion.p>

        {/* Bottom gradient line */}
        <motion.div
          className={cn(
            "absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r",
            member.color
          )}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: isHovered ? 1 : 0 }}
          transition={{ duration: 0.3 }}
        />

        {/* Shine effect */}
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -skew-x-12 pointer-events-none"
          initial={{ x: "-200%" }}
          animate={{ x: isHovered ? "200%" : "-200%" }}
          transition={{ duration: 0.7 }}
        />
      </motion.div>
    </motion.div>
  );
}

export function TeamSection() {
  return (
    <section className="py-24">
      <div className="mx-auto max-w-7xl px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl font-bold tracking-tight md:text-4xl">
            Our <span className="text-primary">Team</span>
          </h2>
          <p className="mt-4 text-muted-foreground max-w-2xl mx-auto">
            Passionate people working to make a difference.
          </p>
        </motion.div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {team.map((member, index) => (
            <TeamCard key={member.name} member={member} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}
