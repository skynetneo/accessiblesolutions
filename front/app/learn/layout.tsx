import type { Metadata, Viewport } from "next";
import "../globals.css";

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
    viewportFit: "cover",          // for safe-area-inset on iPhone
    themeColor: "#faf8f5",         // matches --color-bg
};

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return children;
}
