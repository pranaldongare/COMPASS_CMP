/**
 * The frame around every unauthenticated screen: sign-in, MFA, reset and
 * sign-up.
 *
 * A split panel (restyled 2026-10-10). The left is the product's: its name,
 * a picture of what it does, and a few words at the foot. The right is white
 * and carries the logo, then the one job the visitor came to do - the title
 * with, beside it, the way to the other door ("New here? Create an account"),
 * the form, and a Need help? button. Below `lg` the blue panel goes and the
 * logo heads the form: a person opening a consent link on a phone at a
 * collection site should see the form without scrolling past decoration.
 *
 * The panel's picture (2026-10-10) is the world as a honeycomb, the places
 * consent is collected joined by arcs to one hub, over a faint honeycomb, with
 * three glass chips naming what the product keeps: decorative, and still for
 * anyone who asks for reduced motion.
 *
 * The form's look - taller rounded fields with an icon at their end, a
 * centred submit button - is `styles/auth.css`, scoped to `.auth-form`, so
 * each page's form is unchanged.
 */
"use client";

import { CircleHelp, LockKeyhole, MapPin, Scale, ShieldCheck } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { BrandMark } from "@/components/ui/graphics";
import { HUB_AT, HoneycombBackdrop, WorldHoneycomb } from "@/components/ui/world-map";
import { config } from "@/lib/config";

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
  aside,
  help = true,
  /** Kept for the pages that pass it; the restyled panel shows a picture and
   *  the product's tags instead of a list. */
  assurances: _assurances,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  /** Beside the title, at the right: the way to the other door. */
  aside?: React.ReactNode;
  /** The Need help? button under the form. */
  help?: boolean;
  assurances?: string[];
}) {
  return (
    <main
      id="main"
      className="min-h-dvh bg-surface lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]"
    >
      {/* ------------------------------------------------- the brand panel */}
      <section className="auth-brand relative hidden overflow-hidden lg:flex lg:flex-col lg:items-center lg:justify-between lg:px-6 lg:py-10">
        <HoneycombBackdrop className="pointer-events-none absolute inset-0 size-full" />

        <div className="relative flex items-center gap-3 text-white">
          <BrandMark className="size-9 text-[#8fd0ff]" />
          <p className="text-3xl font-bold tracking-[0.12em]">{config.productName}</p>
        </div>

        <div className="relative flex w-full flex-col items-center">
          <div className="relative w-full max-w-[820px]">
            <WorldHoneycomb className="w-full drop-shadow-[0_8px_30px_rgb(10_30_70/0.45)]" />
            <AuthChip className="top-[4%] left-[2%]" icon={ShieldCheck} label="Consent recorded" />
            <AuthChip className="top-[0%] right-[2%] [animation-delay:-2s]" icon={LockKeyhole} label="Data sealed" />
            {/* Bengaluru, Karnataka: where the arcs meet. */}
            <span
              aria-hidden="true"
              className="absolute flex -translate-x-1/2 translate-y-3 items-center gap-1.5 rounded-lg border border-[#ffc96b]/50 bg-[#0a2547]/80 px-2.5 py-1.5 text-xs font-semibold whitespace-nowrap text-white shadow-[0_6px_18px_rgb(5_20_50/0.45)] backdrop-blur-sm"
              style={{ left: `${HUB_AT.left}%`, top: `${HUB_AT.top}%` }}
            >
              <MapPin className="size-3.5 text-[#ffc96b]" />
              Bengaluru, Karnataka
              <span className="font-medium text-white/70">India</span>
            </span>
            <AuthChip className="bottom-[2%] left-[14%] [animation-delay:-4s]" icon={Scale} label="Rights honoured" />
          </div>
          <p className="mt-6 max-w-md text-center text-lg leading-relaxed font-semibold text-white">
            {config.pitch.heading}
          </p>
          <p className="mt-1.5 max-w-md text-center text-sm leading-relaxed text-white/80">
            {config.pitch.lede}
          </p>
        </div>

        <div className="relative w-full max-w-sm text-center text-white">
          <p className="text-sm font-semibold">{config.pitch.footerTitle}</p>
          <hr className="mx-auto my-2 w-full border-white/40" />
          <p className="text-sm text-white/85">
            {config.pitch.footerTags.map((tag, i) => (
              <React.Fragment key={tag}>
                {i > 0 && <span className="mx-2.5 text-white/50">|</span>}
                {tag}
              </React.Fragment>
            ))}
          </p>
        </div>
      </section>

      {/* -------------------------------------------------- the form panel */}
      <section className="relative flex min-h-dvh flex-col items-center bg-surface px-4 py-10 sm:px-8 lg:min-h-0 lg:px-16">
        <div className="animate-in relative flex w-full max-w-md flex-1 flex-col">
          <Logo />

          <div className="my-auto pt-10">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <h1 className="text-[1.65rem] font-bold tracking-tight">{title}</h1>
              {aside && <div className="text-sm text-text-muted">{aside}</div>}
            </div>
            {subtitle && (
              <p className="mt-2 text-sm leading-relaxed text-text-muted">{subtitle}</p>
            )}

            <div className="auth-form mt-7">{children}</div>

            {footer && <div className="mt-8">{footer}</div>}

            {help && (
              <div className="mt-8 flex justify-center">
                <Link
                  href="/help"
                  className="inline-flex items-center gap-2 rounded-xl border border-border bg-bg px-4 py-2.5 text-sm font-semibold text-text shadow-[var(--shadow-sm)] transition-colors hover:bg-surface-hover"
                >
                  <CircleHelp className="size-5 text-text-muted" aria-hidden="true" />
                  Need Help?
                </Link>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

/** A pane of glass floating over the map, naming one thing the product keeps. */
function AuthChip({
  icon: Icon,
  label,
  className,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  className?: string;
}) {
  return (
    <span
      aria-hidden="true"
      className={`auth-chip absolute flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-3 py-2 text-xs font-semibold text-white shadow-[0_8px_24px_rgb(5_20_50/0.35)] backdrop-blur-md ${className ?? ""}`}
    >
      <span className="grid size-6 place-items-center rounded-lg bg-[#5ec4ff]/25 text-[#bfe6ff]">
        {React.createElement(Icon, { className: "size-3.5" })}
      </span>
      {label}
    </span>
  );
}

/** The product's lockup: the shield, the name, and the app's own line under it. */
function Logo() {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="flex items-center gap-2">
        <span className="text-[2.1rem] leading-none font-semibold tracking-tight">
          <span className="auth-logo-strong">{config.productName.slice(0, 3)}</span>
          <span className="auth-logo-soft">{config.productName.slice(3)}</span>
        </span>
        <BrandMark className="auth-logo-strong size-9" />
      </div>
      <p className="mt-1 border-t border-border pt-0.5 text-xs tracking-wide text-text-muted">
        {config.appName}
      </p>
    </div>
  );
}
