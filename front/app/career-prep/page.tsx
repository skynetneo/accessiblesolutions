"use client";

import Link from "next/link";
import { DocumentBuilder } from "@/components/career/DocumentBuilder";
import { ThemePicker } from "@/components/shared/ThemePicker";
import { FloatingDock } from "@/components/ui/floating-dock";
import { IconHome, IconFileText, IconUser } from "@tabler/icons-react";

export default function CareerPrepPage() {
    const dockItems = [
        { title: "Dashboard", href: "/", icon: <IconHome className="h-full w-full text-neutral-500 dark:text-neutral-300" /> },
        { title: "Career Prep", href: "/career-prep", icon: <IconFileText className="h-full w-full text-neutral-500 dark:text-neutral-300" /> },
        { title: "Profile", href: "#", icon: <IconUser className="h-full w-full text-neutral-500 dark:text-neutral-300" /> },
    ];
    return (
        <div className="relative min-h-screen bg-[var(--color-bg)] flex flex-col">
            <header className="w-full flex justify-between items-center p-6 max-w-7xl mx-auto absolute top-0 left-0 right-0 z-10 pointer-events-none">
                 <div className="sidebar-header pointer-events-auto">
                          <h1 className="logo text-3xl">Praxis</h1>
                 </div>
                 <Link href="/" className="pointer-events-auto px-4 py-2 bg-[rgba(255,255,255,0.05)] rounded-lg text-sm text-[var(--color-text)] hover:bg-[rgba(255,255,255,0.1)] transition flex items-center gap-2">
                     <span>◭</span> Back to Nexus
                 </Link>
            </header>
            <main className="flex-1 flex w-full max-w-5xl mx-auto pt-24 pb-24 items-center justify-center">
                <section className="w-full h-[70vh]">
                    <DocumentBuilder />
                </section>
            </main>
            {/* Adding the elegant floating dock */}
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[100] w-fit">
                <FloatingDock
                    items={dockItems}
                />
            </div>
        </div>
    );
}
