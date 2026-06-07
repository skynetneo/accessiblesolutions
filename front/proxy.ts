import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

export async function proxy(request: NextRequest) {
    return await updateSession(request);
}

export const config = {
    matcher: [
        // Run on everything except static assets, Next internals, images,
        // the CopilotKit runtime, and files with an extension.
        "/((?!_next/static|_next/image|favicon.ico|api/copilotkit|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|css|js|json|webmanifest|txt|xml)$).*)",
    ],
};
