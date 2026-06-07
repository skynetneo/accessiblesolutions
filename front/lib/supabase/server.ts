// Server Supabase client — used in Server Components, Route Handlers, and
// Server Actions. Reads/writes session cookies via next/headers so the
// session refreshed in middleware is visible to the render.

import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

export async function createClient() {
    const cookieStore = await cookies();

    return createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return cookieStore.getAll();
                },
                setAll(cookiesToSet) {
                    try {
                        cookiesToSet.forEach(({ name, value, options }) =>
                            cookieStore.set(name, value, options),
                        );
                    } catch {
                        // Called from a Server Component — cookie writes are
                        // performed in middleware instead.
                    }
                },
            },
        },
    );
}
