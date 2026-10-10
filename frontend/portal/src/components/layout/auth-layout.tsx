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

import { CircleHelp } from "lucide-react";
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
  return (
    <main
      id="main"
      className="min-h-dvh bg-surface lg:grid lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]"
    >
      {/* ------------------------------------------------- the brand panel */}
      <section className="auth-brand relative hidden overflow-hidden border-r border-[#e6ebf2] lg:flex lg:flex-col lg:items-center lg:justify-between lg:px-6 lg:py-10">

        <div className="relative flex items-center gap-3 text-[#1f5c9e]">
          <BrandMark className="size-9" />
          <p className="text-3xl font-bold tracking-[0.12em]">{config.productName}</p>
        </div>

        <div className="relative flex w-full flex-col items-center">
          <div className="relative w-full max-w-[820px]">
            <WorldDots className="w-full" />
          </div>
          <p className="mt-6 max-w-md text-center text-lg leading-relaxed font-semibold text-[#1d2433]">
            {config.pitch.heading}
          </p>
          <p className="mt-1.5 max-w-md text-center text-sm leading-relaxed text-[#4b5567]">
            {config.pitch.lede}
          </p>
        </div>

        <div className="relative w-full max-w-sm text-center text-[#1d2433]">
          <p className="text-sm font-semibold">{config.pitch.footerTitle}</p>
          <hr className="mx-auto my-2 w-full border-[#d5dfeb]" />
          <p className="text-sm text-[#4b5567]">
            {config.pitch.footerTags.map((tag, i) => (
              <React.Fragment key={tag}>
                {i > 0 && <span className="mx-2.5 text-[#a7b3c4]">|</span>}
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
