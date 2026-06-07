// app/layout.tsx
import type { Metadata, Viewport } from "next";
import { SiteShell } from "@/components/site-shell";
import "./globals.css";

export const metadata: Metadata = {
    title: "Praxis — Your Path Forward",
    description: "Adaptive learning that meets you where you are.",
    manifest: "/manifest.json",
    appleWebApp: {
        capable: true,
        statusBarStyle: "default",
        title: "Praxis",
    },
};

export const viewport: Viewport = {
    width: "device-width",
    initialScale: 1,
    maximumScale: 1,               // prevent zoom on input focus (accessibility tradeoff, but critical for app feel)
    userScalable: false,
    viewportFit: "cover",          // for safe-area-inset on iPhone
    themeColor: "#faf8f5",         // matches --color-bg
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
                <link
                    href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300..700;1,9..40,300..700&family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..900&display=swap"
                    rel="stylesheet"
                />
                {/* PWA: apple touch icon */}
                <link rel="apple-touch-icon" href="/icons/icon-192.png" />
            </head>
            <body>
                <SiteShell>{children}</SiteShell>
            </body>
        </html>
    );
}
