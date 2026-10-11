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
 * The panel's picture (2026-10-10) is the world as blue dots on a white,
 * dotted field, Samsung's sites round the world joined by arcs to Bengaluru:
 * decorative, and still for anyone who asks for reduced motion.
 *
 * The form's look - taller rounded fields with an icon at their end, a
 * centred submit button - is `styles/auth.css`, scoped to `.auth-form`, so
 * each page's form is unchanged.
 */
"use client";

import { Check, CircleHelp } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { BrandMark } from "@/components/ui/graphics";
import { WorldDots } from "@/components/ui/world-map";
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
  const headingParts = config.pitch.heading.split(/,\s+(.+)/).filter(Boolean);
  return (
    <main
      id="main"
      className="min-h-dvh bg-surface lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]"
    >
      {/* ------------------------------------------------- the brand panel */}
      {/* The sign-in design (2026-10-11, "Light split"): the name at the top
          left, the message, the world, and three cards saying what the product
          keeps - on one left edge, 64 px in. */}
      <section className="auth-brand relative hidden overflow-hidden lg:flex lg:flex-col lg:px-16 lg:py-14">
        <Lockup />

        <div className="relative mt-11">
          <p className="text-xs font-bold tracking-[0.1em] text-[#1f5c9e] uppercase">
            {config.appName}
          </p>
          {/* Two lines, broken after the first clause where there is one:
              "Consent and privacy work, / in one place." */}
          <p className="mt-2.5 max-w-[40rem] text-[2.5rem] leading-[1.12] font-bold tracking-[-0.03em] text-[#16202e]">
            {headingParts.length === 2 ? (
              <>
                {headingParts[0]},<br />
                {headingParts[1]}
              </>
            ) : (
              config.pitch.heading
            )}
          </p>
          <p className="mt-3 max-w-[35rem] text-base leading-relaxed text-[#566275]">
            {config.pitch.lede}
          </p>
        </div>

        <div className="relative my-auto w-full max-w-[52rem] py-6">
          <WorldDots className="w-full" />
        </div>

        <ul className="relative grid max-w-[40rem] grid-cols-3 gap-3.5">
          {config.pitch.highlights.map((h) => (
            <li
              key={h.title}
              className="rounded-[14px] border border-[#e3e8ef] bg-white/85 px-4 py-3.5 backdrop-blur-sm"
            >
              <p className="text-base font-bold text-[#16202e]">{h.title}</p>
              <p className="mt-0.5 text-xs leading-snug text-[#566275]">{h.text}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* -------------------------------------------------- the form panel */}
      {/* The form on a floating card, centred in a soft panel. On a phone the
          brand panel goes and the name heads the card. */}
      <section className="auth-panel relative flex min-h-dvh flex-col items-center justify-center px-4 py-10 sm:px-8 lg:min-h-0 lg:border-l lg:border-[#eef1f5]">
        <div className="mb-8 lg:hidden">
          <Lockup />
        </div>
        <div className="animate-in w-full max-w-[30rem] rounded-[22px] border border-border bg-surface px-6 py-9 shadow-[0_24px_60px_rgb(16_30_60/0.10)] sm:px-10">
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h1 className="text-[1.75rem] font-bold tracking-[-0.02em]">{title}</h1>
            {aside && <div className="text-sm text-text-muted">{aside}</div>}
          </div>
          {subtitle && (
            <p className="mt-1.5 text-sm leading-relaxed text-text-muted">{subtitle}</p>
          )}

          <div className="auth-form mt-6">{children}</div>

          {footer && <div className="mt-6 text-center text-[0.8125rem]">{footer}</div>}

          {/* What is true of this app, quietly, under a rule. */}
          <ul className="mt-6 flex flex-wrap justify-center gap-x-3.5 gap-y-1 border-t border-border pt-5 text-[0.71875rem] whitespace-nowrap text-text-subtle">
            {config.pitch.trust.map((t) => (
              <li key={t} className="inline-flex items-center gap-1.5">
                <Check className="size-3.5 text-[#13a89e]" aria-hidden="true" />
                {t}
              </li>
            ))}
          </ul>
        </div>

        {help && (
          <Link
            href="/help"
            className="mt-5 inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-text-muted hover:text-text"
          >
            <CircleHelp className="size-4" aria-hidden="true" />
            Need help?
          </Link>
        )}
      </section>
    </main>
  );
}

/** The product's lockup: the shield and the two-tone name. */
function Lockup() {
  return (
    <div className="relative flex items-center gap-2.5">
      <BrandMark className="size-8 text-[#1f5c9e]" />
      <span className="text-[1.75rem] leading-none font-extrabold tracking-tight">
        <span className="text-[#1f5c9e]">{config.productName.slice(0, 3)}</span>
        <span className="text-[#5d6a7d]">{config.productName.slice(3)}</span>
      </span>
    </div>
  );
}
