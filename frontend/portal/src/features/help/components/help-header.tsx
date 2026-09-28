/**
 * The manual's own top bar. The manual is open to everyone - the sign-in page
 * links to it - so it stands outside the signed-in shell, and this bar offers
 * the way back: to the app when signed in, to sign-in when not.
 */
"use client";

import { ArrowLeft, Moon, Sun } from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/ui/graphics";
import { Button } from "@/components/ui/primitives";
import { config } from "@/lib/config";
import { useTheme } from "@/providers";

export function HelpHeader({ back }: { back: { href: string; label: string } }) {
  const { resolved, setTheme } = useTheme();
  const next = resolved === "dark" ? "light" : "dark";
  return (
    <header className="glass sticky top-0 z-30 border-b border-border">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-3 px-4 sm:px-6">
        <Link
          href="/help"
          className="flex min-w-0 items-center gap-2.5 rounded-lg font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-subtle)]"
        >
          <span className="brand-gradient grid size-8 shrink-0 place-items-center rounded-lg shadow-[var(--shadow-sm)]">
            <BrandMark className="size-5 text-white" />
          </span>
          <span className="min-w-0 leading-tight">
            <span className="block truncate text-sm">{config.appName}</span>
            <span className="block text-2xs font-normal text-text-subtle">Help manual</span>
          </span>
        </Link>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(next)}
          aria-label={`Switch to ${next} theme`}
          title={`Switch to ${next} theme`}
        >
          {resolved === "dark" ? <Sun /> : <Moon />}
        </Button>
        <Button variant="secondary" size="sm" asChild>
          <Link href={back.href}>
            <ArrowLeft className="size-4" aria-hidden="true" />
            {back.label}
          </Link>
        </Button>
      </div>
    </header>
  );
}
