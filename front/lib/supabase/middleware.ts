// Middleware Supabase helper — refreshes the session cookie on every request
// and redirects unauthenticated users away from authenticated-only routes.

import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Routes that should be reachable without an authenticated session.
const PUBLIC_PATHS = [
    "/",
    "/login",
    "/auth",
    "/about",
    "/accessfyndr",
    "/contact",
    "/get-involved",
    "/privacy",
    "/programs",
];

function isPublicPath(pathname: string): boolean {
    return PUBLIC_PATHS.some((prefix) => {
        if (prefix === "/") return pathname === "/";
        return pathname === prefix || pathname.startsWith(`${prefix}/`);
    });
}

export async function updateSession(request: NextRequest) {
    let response = NextResponse.next({ request });

    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll();
                },
                setAll(cookiesToSet) {
                    cookiesToSet.forEach(({ name, value }) =>
                        request.cookies.set(name, value),
                    );
                    response = NextResponse.next({ request });
                    cookiesToSet.forEach(({ name, value, options }) =>
                        response.cookies.set(name, value, options),
                    );
                },
            },
        },
    );

    // IMPORTANT: getUser() revalidates the token. Do not remove.
    const {
        data: { user },
    } = await supabase.auth.getUser();

    const { pathname } = request.nextUrl;

    if (!user && !isPublicPath(pathname)) {
        const loginUrl = request.nextUrl.clone();
        loginUrl.pathname = "/login";
        loginUrl.searchParams.set("next", pathname);
        return NextResponse.redirect(loginUrl);
    }

    if (user && pathname === "/login") {
        const appUrl = request.nextUrl.clone();
        appUrl.pathname = "/";
        appUrl.search = "";
        return NextResponse.redirect(appUrl);
    }

    return response;
}
