// Completes onboarding for the current user:
//   1) bootstraps the learner profile on the backend (idempotent)
//   2) optionally saves the resume text
// Requires an authenticated Supabase session.

import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

interface CompleteRequest {
    extractedSkills?: string[];
    resumeText?: string;
    resumeFilename?: string;
    name?: string;
    careerGoal?: string;
}

export async function POST(request: NextRequest) {
    const supabase = await createClient();
    const {
        data: { user },
    } = await supabase.auth.getUser();

    if (!user) {
        return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = (await request.json().catch(() => ({}))) as CompleteRequest;

    const backend = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8223";

    const bootstrapRes = await fetch(`${backend}/api/learner/bootstrap`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
            learner_id: user.id,
            email: user.email ?? null,
            name: body.name ?? user.user_metadata?.full_name ?? null,
            career_goal: body.careerGoal ?? null,
            extracted_skills: body.extractedSkills ?? [],
        }),
    });

    if (!bootstrapRes.ok) {
        const detail = await bootstrapRes.text().catch(() => "");
        return NextResponse.json(
            { error: "Failed to bootstrap profile", detail },
            { status: 502 },
        );
    }

    if (body.resumeText && body.resumeText.trim().length > 0) {
        await fetch(`${backend}/api/resume/save`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
                learner_id: user.id,
                text: body.resumeText,
                filename: body.resumeFilename ?? "resume",
            }),
        }).catch(() => {
            // Resume save is best-effort; profile already bootstrapped.
        });
    }

    return NextResponse.json({ ok: true, learner_id: user.id });
}
