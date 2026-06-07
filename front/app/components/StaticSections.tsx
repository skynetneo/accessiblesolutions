import Link from "next/link";
import { ArrowRight, HeartHandshake, Mail, Phone } from "lucide-react";

const navItems = [
	{ href: "/about", label: "About" },
	{ href: "/programs", label: "Programs" },
	{ href: "/accessfyndr", label: "Get Help" },
	{ href: "/impact", label: "Impact" },
	{ href: "/get-involved", label: "Get Involved" },
	{ href: "/resources", label: "Resources" },
	{ href: "/contact", label: "Contact" },
];

export function SiteHeader() {
	return (
		<header className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur">
			<div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
				<Link href="/" className="flex items-center gap-2 text-lg font-semibold">
					<span className="flex h-8 w-8 items-center justify-center rounded-xl bg-primary text-primary-foreground">
						<HeartHandshake size={18} />
					</span>
					Accessible Solutions
				</Link>
				<nav className="hidden items-center gap-5 text-sm text-muted-foreground md:flex">
					{navItems.map((item) => (
						<Link
							key={`${item.href}-${item.label}`}
							href={item.href}
							className="transition-colors hover:text-foreground"
						>
							{item.label}
						</Link>
					))}
				</nav>
				<div className="flex items-center gap-3">
					<Link
						href="/accessfyndr"
						className="hidden rounded-full border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:border-primary md:inline-flex"
					>
						Get Help
					</Link>
					<Link
						href="/get-involved"
						className="inline-flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition hover:opacity-90"
					>
						Donate
						<ArrowRight size={16} />
					</Link>
				</div>
			</div>
		</header>
	);
}

export function SiteFooter() {
	return (
		<footer className="border-t border-border bg-background">
			<div className="mx-auto grid w-full max-w-6xl gap-10 px-6 py-12 md:grid-cols-[1.2fr_1fr_1fr]">
				<div className="space-y-4">
					<div className="flex items-center gap-2 text-lg font-semibold">
						<span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
							<HeartHandshake size={18} />
						</span>
						Accessible Solutions
					</div>
					<p className="text-sm text-muted-foreground">
						We help people find vital services, assistive resources, and community
						support with dignity and ease.
					</p>
					<div className="space-y-2 text-sm text-muted-foreground">
						<div className="flex items-center gap-2">
							<Mail size={16} />
							hello@accessiblesolutions.org
						</div>
						<div className="flex items-center gap-2">
							<Phone size={16} />
							(541) 555-0113
						</div>
					</div>
				</div>
				<div className="space-y-3 text-sm">
					<p className="font-semibold">Quick Links</p>
					<div className="grid gap-2 text-muted-foreground">
						{navItems.map((item) => (
							<Link key={`${item.href}-${item.label}`} href={item.href} className="hover:text-foreground">
								{item.label}
							</Link>
						))}
						<Link href="/accessibility" className="hover:text-foreground">
							Accessibility Statement
						</Link>
					</div>
				</div>
				<div className="space-y-4 text-sm">
					<p className="font-semibold">Stay Connected</p>
					<p className="text-muted-foreground">
						Get updates about new services, events, and ways to get involved.
					</p>
					<Link
						href="/contact"
						className="inline-flex items-center gap-2 rounded-full border border-border px-4 py-2 font-medium text-foreground transition hover:border-primary"
					>
						Contact Us
						<ArrowRight size={16} />
					</Link>
					<p className="text-xs text-muted-foreground">
						© 2026 Accessible Solutions. All rights reserved.
					</p>
				</div>
			</div>
		</footer>
	);
}

export function SectionHeading({
	eyebrow,
	title,
	description,
}: {
	eyebrow?: string;
	title: string;
	description?: string;
}) {
	return (
		<div className="space-y-3">
			{eyebrow && (
				<p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
					{eyebrow}
				</p>
			)}
			<h2 className="text-2xl font-semibold text-foreground md:text-3xl">
				{title}
			</h2>
			{description && <p className="text-muted-foreground">{description}</p>}
		</div>
	);
}

export function Pill({ label }: { label: string }) {
	return (
		<span className="rounded-full border border-border bg-background px-3 py-1 text-xs font-semibold text-muted-foreground">
			{label}
		</span>
	);
}

export function StatCard({ label, value }: { label: string; value: string }) {
	return (
		<div className="rounded-2xl border border-border bg-card p-5 shadow-sm">
			<p className="text-2xl font-semibold text-foreground">{value}</p>
			<p className="text-sm text-muted-foreground">{label}</p>
		</div>
	);
}

export function ProgramCard({
	title,
	description,
	meta,
}: {
	title: string;
	description: string;
	meta: string;
}) {
	return (
		<div className="rounded-3xl border border-border bg-card p-6 shadow-sm">
			<p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">
				{meta}
			</p>
			<h3 className="mt-3 text-lg font-semibold text-foreground">{title}</h3>
			<p className="mt-2 text-sm text-muted-foreground">{description}</p>
		</div>
	);
}

export function CTASection({
	title,
	description,
	primaryLabel,
	primaryHref,
	secondaryLabel,
	secondaryHref,
}: {
	title: string;
	description: string;
	primaryLabel: string;
	primaryHref: string;
	secondaryLabel?: string;
	secondaryHref?: string;
}) {
	return (
		<div className="rounded-3xl border border-border bg-linear-to-br from-card via-card to-background p-8 shadow-sm md:flex md:items-center md:justify-between">
			<div className="space-y-3">
				<h3 className="text-xl font-semibold text-foreground">{title}</h3>
				<p className="text-sm text-muted-foreground">{description}</p>
			</div>
			<div className="mt-6 flex flex-wrap gap-3 md:mt-0">
				<Link
					href={primaryHref}
					className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition hover:opacity-90"
				>
					{primaryLabel}
					<ArrowRight size={16} />
				</Link>
				{secondaryLabel && secondaryHref && (
					<Link
						href={secondaryHref}
						className="inline-flex items-center gap-2 rounded-full border border-border px-5 py-2 text-sm font-semibold text-foreground transition hover:border-primary"
					>
						{secondaryLabel}
					</Link>
				)}
			</div>
		</div>
	);
}
