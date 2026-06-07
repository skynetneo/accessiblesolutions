"use client";

import { useState } from "react";
import { ResumeUpload } from "../ResumeUpload";
import { TextGenerateEffect } from "@/components/ui/text-generate-effect";

interface OnboardingFlowProps {
    onComplete: (data: {
        completed: boolean;
        extractedSkills?: string[];
        resumeText?: string;
        careerGoal?: string;
    }) => void;
}

const GOAL_OPTIONS = [
    { value: "ged", label: "Earn a GED", description: "Build toward GED-ready math, reading, science, and social studies skills." },
    { value: "job_skills", label: "Build job skills", description: "Practice skills that map directly to work, training, and advancement." },
    { value: "both", label: "GED and job skills", description: "Balance credential progress with practical career readiness." },
    { value: "exploring", label: "Explore options", description: "Start broad and let Praxis help narrow the path." },
];

const SECTION_HEADER_RE = /^(skills?|technical skills?|core competencies|competencies|technologies|tools|tooling|stack)\b/i;

const SKILL_ALIASES: Record<string, string> = {
    js: "JavaScript",
    javascript: "JavaScript",
    ts: "TypeScript",
    typescript: "TypeScript",
    react: "React",
    "react.js": "React",
    "next.js": "Next.js",
    nextjs: "Next.js",
    node: "Node.js",
    nodejs: "Node.js",
    "node.js": "Node.js",
    sql: "SQL",
    nosql: "NoSQL",
    aws: "AWS",
    azure: "Azure",
    gcp: "GCP",
    html: "HTML",
    css: "CSS",
    api: "API Design",
    apis: "API Design",
    ci: "CI/CD",
    cd: "CI/CD",
    "ci/cd": "CI/CD",
    ml: "Machine Learning",
    ai: "AI",
    qa: "QA Testing",
    ux: "UX Design",
    ui: "UI Design",
    crm: "CRM",
    seo: "SEO",
    "power bi": "Power BI",
    tableau: "Tableau",
    salesforce: "Salesforce",
    "project management": "Project Management",
    scrum: "Scrum",
    agile: "Agile",
    docker: "Docker",
    kubernetes: "Kubernetes",
    excel: "Excel",
    python: "Python",
    java: "Java",
    "c#": "C#",
    "c++": "C++",
};

const COMMON_SKILL_PATTERNS: Array<{ label: string; pattern: RegExp }> = [
    { label: "Project Management", pattern: /\bproject management\b/i },
    { label: "Data Analysis", pattern: /\bdata analysis\b/i },
    { label: "Machine Learning", pattern: /\bmachine learning\b/i },
    { label: "Communication", pattern: /\bcommunication\b/i },
    { label: "Leadership", pattern: /\bleadership\b/i },
    { label: "Customer Service", pattern: /\bcustomer service\b/i },
    { label: "Salesforce", pattern: /\bsalesforce\b/i },
    { label: "Excel", pattern: /\bexcel\b/i },
    { label: "SQL", pattern: /\bsql\b/i },
    { label: "Python", pattern: /\bpython\b/i },
    { label: "JavaScript", pattern: /\bjavascript\b|\bjs\b/i },
    { label: "TypeScript", pattern: /\btypescript\b|\bts\b/i },
    { label: "React", pattern: /\breact\b/i },
    { label: "Node.js", pattern: /\bnode(?:\.js|js)?\b/i },
    { label: "AWS", pattern: /\baws\b|\bamazon web services\b/i },
    { label: "Azure", pattern: /\bazure\b/i },
    { label: "GCP", pattern: /\bgcp\b|\bgoogle cloud\b/i },
    { label: "Docker", pattern: /\bdocker\b/i },
    { label: "Kubernetes", pattern: /\bkubernetes\b/i },
    { label: "Tableau", pattern: /\btableau\b/i },
    { label: "Power BI", pattern: /\bpower bi\b/i },
    { label: "Figma", pattern: /\bfigma\b/i },
];

const SKILL_STOPWORDS = new Set([
    "skills",
    "skill",
    "summary",
    "profile",
    "experience",
    "responsible",
    "including",
    "strong",
    "ability",
    "years",
    "year",
    "work",
    "team",
    "teams",
    "professional",
    "knowledge",
    "history",
    "resume",
]);

const FREQUENCY_STOPWORDS = new Set([
    "the",
    "and",
    "for",
    "with",
    "from",
    "using",
    "used",
    "developed",
    "managed",
    "support",
    "create",
    "created",
    "maintained",
    "improved",
    "worked",
    "within",
    "across",
    "role",
    "roles",
    "company",
    "education",
    "certification",
    "certifications",
    "objective",
]);

SKILL_STOPWORDS.forEach((word) => {
    FREQUENCY_STOPWORDS.add(word);
});

function extractSkillsFromResume(text: string): string[] {
    const extracted: string[] = [];
    const seen = new Set<string>();

    const addSkill = (rawSkill: string) => {
        const normalized = normalizeSkill(rawSkill);
        if (!normalized) {
            return;
        }

        const canonical = canonicalizeSkill(normalized);
        const key = canonical.toLowerCase();
        if (seen.has(key)) {
            return;
        }
        seen.add(key);
        extracted.push(canonical);
    };

    for (const token of extractSectionSkills(text)) {
        addSkill(token);
    }

    for (const token of extractExperienceSkills(text)) {
        addSkill(token);
    }

    const lowerText = text.toLowerCase();
    for (const item of COMMON_SKILL_PATTERNS) {
        if (item.pattern.test(lowerText)) {
            addSkill(item.label);
        }
    }

    if (extracted.length < 6) {
        for (const token of extractFrequentSkillWords(text)) {
            addSkill(token);
            if (extracted.length >= 12) {
                break;
            }
        }
    }

    return extracted.slice(0, 12);
}

function extractSectionSkills(text: string): string[] {
    const lines = text
        .split(/\r?\n/)
        .map((line) => line.trim())
        .filter(Boolean);
    const candidates: string[] = [];

    for (let i = 0; i < lines.length; i += 1) {
        const line = lines[i];
        if (!SECTION_HEADER_RE.test(line)) {
            continue;
        }

        const inlineParts = line.split(/[:\-]/, 2);
        if (inlineParts.length > 1) {
            candidates.push(...splitSkillCandidates(inlineParts[1]));
        }

        for (let j = i + 1; j < Math.min(lines.length, i + 6); j += 1) {
            const sectionLine = lines[j];
            if (looksLikeHeader(sectionLine)) {
                break;
            }
            candidates.push(...splitSkillCandidates(sectionLine));
        }
    }

    return candidates;
}

function extractExperienceSkills(text: string): string[] {
    const patterns = [
        /(?:proficient|skilled|experienced|expertise)\s+(?:in|with)\s+([^\n.;]+)/gi,
        /(?:experience|background)\s+(?:in|with)\s+([^\n.;]+)/gi,
    ];
    const candidates: string[] = [];

    for (const pattern of patterns) {
        let match = pattern.exec(text);
        while (match) {
            candidates.push(...splitSkillCandidates(match[1]));
            match = pattern.exec(text);
        }
    }

    return candidates;
}

function extractFrequentSkillWords(text: string): string[] {
    const words = text.toLowerCase().match(/\b[a-z][a-z0-9.+#-]{2,}\b/g) ?? [];
    const counts = new Map<string, number>();

    for (const word of words) {
        if (FREQUENCY_STOPWORDS.has(word)) {
            continue;
        }
        counts.set(word, (counts.get(word) ?? 0) + 1);
    }

    return Array.from(counts.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 8)
        .map(([word]) => canonicalizeSkill(word));
}

function splitSkillCandidates(value: string): string[] {
    return value
        .replace(/[|•]/g, ",")
        .split(/,|;|\/|\band\b/gi)
        .map((token) => token.trim())
        .filter(Boolean);
}

function normalizeSkill(raw: string): string {
    let token = raw.trim();
    token = token.replace(/^[-*]\s*/, "");
    token = token.replace(/^[0-9]+\.\s*/, "");
    token = token.replace(/\b\d+\+?\s*(years?|yrs?)\b/gi, "");
    token = token.replace(/\b(proficient|experienced|experience|expertise|knowledge|familiarity)\s+(in|with|of)\b/gi, "");
    token = token.replace(/\s+/g, " ").trim();

    const lower = token.toLowerCase();
    if (!lower) {
        return "";
    }
    if (lower.length < 2 || lower.length > 40) {
        return "";
    }
    if (lower.split(" ").length > 4) {
        return "";
    }
    if (SKILL_STOPWORDS.has(lower)) {
        return "";
    }
    if (/^\d+$/.test(lower)) {
        return "";
    }

    return token;
}

function canonicalizeSkill(token: string): string {
    const normalized = token.toLowerCase().replace(/\s+/g, " ");
    const alias = SKILL_ALIASES[normalized];
    if (alias) {
        return alias;
    }

    return normalized
        .split(" ")
        .map((word) => {
            if (word === "sql") return "SQL";
            if (word === "api") return "API";
            if (word === "aws") return "AWS";
            if (word === "gcp") return "GCP";
            if (word === "ui") return "UI";
            if (word === "ux") return "UX";
            if (word === "qa") return "QA";
            if (word === "crm") return "CRM";
            if (word === "seo") return "SEO";
            return word.charAt(0).toUpperCase() + word.slice(1);
        })
        .join(" ");
}

function looksLikeHeader(line: string): boolean {
    if (SECTION_HEADER_RE.test(line)) {
        return true;
    }

    return /^[A-Z][A-Za-z /&]{2,40}:?$/.test(line) && !line.includes(",");
}

export function OnboardingFlow({ onComplete }: OnboardingFlowProps) {
    const [step, setStep] = useState(1);
    const [careerGoal, setCareerGoal] = useState("ged");
    const [customGoal, setCustomGoal] = useState("");

    const goalForSubmit = customGoal.trim() || careerGoal;
    
    // Smooth, sleek onboarding wizard
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-bg)] bg-opacity-95 backdrop-blur-md">
            <div className="glass w-full max-w-2xl rounded-2xl p-8 shadow-2xl animate-fade-in-up border border-[rgba(255,255,255,0.1)] relative overflow-hidden">
                
                {/* Decorative background glow */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--color-accent)] rounded-full mix-blend-screen filter blur-[100px] opacity-20 pointer-events-none"></div>

                <div className="relative z-10">
                    {step === 1 && (
                        <div className="flex flex-col gap-6 animate-fade-in-up">
                            <h2 className="text-3xl font-bold font-[var(--font-display)] text-[var(--color-text)]">
                                <TextGenerateEffect words="Welcome to Praxis" />
                            </h2>
                            <p className="text-[var(--color-text-secondary)] text-lg leading-relaxed mt-2">
                                Let&apos;s build your <strong className="text-[var(--color-accent)]">Alignment Nexus</strong>—a map combining your passion, talent, mission, and vocation to help you discover a truly fulfilling career path.
                            </p>
                            <button 
                                onClick={() => setStep(2)}
                                className="mt-4 px-6 py-3 bg-[var(--color-accent)] text-white font-bold rounded-xl w-max hover:brightness-110 transition-all shadow-[0_4px_16px_rgba(224,122,58,0.3)] hover:-translate-y-0.5"
                            >
                                Get Started →
                            </button>
                        </div>
                    )}

                    {step === 2 && (
                        <div className="flex flex-col gap-6 animate-fade-in-up">
                            <div>
                                <h2 className="text-2xl font-bold font-[var(--font-display)] text-[var(--color-text)] mb-2">
                                    What are you working toward?
                                </h2>
                                <p className="text-[var(--color-text-secondary)] text-sm mb-6">
                                    Your goal shapes the first assessment and the examples your coach uses.
                                </p>
                            </div>

                            <div className="grid gap-3">
                                {GOAL_OPTIONS.map((option) => (
                                    <button
                                        key={option.value}
                                        type="button"
                                        onClick={() => setCareerGoal(option.value)}
                                        className={`rounded-xl border p-4 text-left transition-all ${
                                            careerGoal === option.value
                                                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)]"
                                                : "border-[rgba(255,255,255,0.12)] bg-[rgba(255,255,255,0.03)] hover:border-[var(--color-accent)]"
                                        }`}
                                    >
                                        <span className="block text-sm font-bold text-[var(--color-text)]">
                                            {option.label}
                                        </span>
                                        <span className="mt-1 block text-xs leading-relaxed text-[var(--color-text-secondary)]">
                                            {option.description}
                                        </span>
                                    </button>
                                ))}
                            </div>

                            <label className="flex flex-col gap-2">
                                <span className="text-xs font-bold uppercase tracking-wide text-[var(--color-text-secondary)]">
                                    Custom goal
                                </span>
                                <input
                                    value={customGoal}
                                    onChange={(event) => setCustomGoal(event.target.value)}
                                    placeholder="Type your own goal"
                                    className="rounded-xl border border-[rgba(255,255,255,0.12)] bg-[rgba(255,255,255,0.04)] px-4 py-3 text-sm text-[var(--color-text)] outline-none transition focus:border-[var(--color-accent)]"
                                />
                            </label>

                            <button
                                onClick={() => setStep(3)}
                                className="mt-2 px-6 py-3 bg-[var(--color-accent)] text-white font-bold rounded-xl w-max hover:brightness-110 transition-all shadow-[0_4px_16px_rgba(224,122,58,0.3)] hover:-translate-y-0.5"
                            >
                                Continue →
                            </button>
                        </div>
                    )}

                    {step === 3 && (
                        <div className="flex flex-col gap-6 animate-fade-in-up">
                            <div>
                                <h2 className="text-2xl font-bold font-[var(--font-display)] text-[var(--color-text)] mb-2">
                                    Establish your Talent Baseline
                                </h2>
                                <p className="text-[var(--color-text-secondary)] text-sm mb-6">
                                    Upload an existing resume or paste your work history. We&apos;ll extract your core skills instantly to power your AI coaching and Nexus map.
                                </p>
                            </div>
                            
                            <ResumeUpload
                                onResumeText={(resumeText) => {
                                    const extractedSkills = extractSkillsFromResume(resumeText);
                                    onComplete({
                                        completed: true,
                                        resumeText,
                                        extractedSkills: extractedSkills.length > 0
                                            ? extractedSkills
                                            : undefined,
                                        careerGoal: goalForSubmit,
                                    });
                                }}
                                onSkip={() => onComplete({ completed: true, careerGoal: goalForSubmit })}
                            />
                        </div>
                    )}
                </div>
                
                {/* Step indicators */}
                <div className="mt-8 flex gap-2">
                    <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-[var(--color-accent)]' : 'bg-[rgba(255,255,255,0.1)]'}`}></div>
                    <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-[var(--color-accent)]' : 'bg-[rgba(255,255,255,0.1)]'}`}></div>
                    <div className={`h-1.5 flex-1 rounded-full ${step >= 3 ? 'bg-[var(--color-accent)]' : 'bg-[rgba(255,255,255,0.1)]'}`}></div>
                </div>
            </div>
        </div>
    );
}
