"use client";

import { useEffect, useState } from "react";
import type { User } from "@supabase/supabase-js";
import { createClient } from "@/lib/supabase/client";

interface State {
    user: User | null;
    loading: boolean;
}

export function useSupabaseUser(): State {
    const [state, setState] = useState<State>({ user: null, loading: true });

    useEffect(() => {
        const supabase = createClient();

        supabase.auth.getUser().then(({ data }) => {
            setState({ user: data.user, loading: false });
        });

        const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
            setState({ user: session?.user ?? null, loading: false });
        });

        return () => sub.subscription.unsubscribe();
    }, []);

    return state;
}
