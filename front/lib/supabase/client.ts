// Browser Supabase client — used in Client Components.
// Wraps @supabase/ssr.createBrowserClient so cookies stay in sync with the
// middleware + server clients.

import { createBrowserClient } from "@supabase/ssr";

export function createClient() {
    return createBrowserClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    );
}
