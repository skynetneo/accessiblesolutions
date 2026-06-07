// Auth callback — exchanges the one-time `code` from a magic link or OAuth
// provider for a persisted session cookie, then redirects into the app.

import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
    const url = request.nextUrl.clone();
    const code = url.searchParams.get("code");
    const next = url.searchParams.get("next") ?? "/";

    if (code) {
        const supabase = await createClient();
        const { error } = await supabase.auth.exchangeCodeForSession(code);
        if (!error) {
            const redirect = request.nextUrl.clone();
            redirect.pathname = next.startsWith("/") ? next : "/";
            redirect.search = "";
            return NextResponse.redirect(redirect);
        }
    }

    const failure = request.nextUrl.clone();
    failure.pathname = "/login";
    failure.search = "";
    failure.searchParams.set("error", "Sign-in link is invalid or has expired.");
    return NextResponse.redirect(failure);
}
