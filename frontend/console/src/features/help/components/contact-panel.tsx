/**
 * The manual's closing panel: who to ask when the manual does not answer.
 *
 * The Privacy Office's address comes from the public `/rights` answer; if that
 * cannot be read, the panel still says where to go, without an address.
 */
"use client";

import { Mail } from "lucide-react";
import type * as React from "react";

import { SignalField } from "@/components/ui/graphics";
import { useHelpContact } from "@/features/help/queries";

export function ContactPanel({ children }: { children?: React.ReactNode }) {
  const contact = useHelpContact();
  return (
    <section
      aria-labelledby="help-contact-title"
      className="brand-gradient relative overflow-hidden rounded-2xl px-6 py-8 text-white shadow-[var(--shadow-card)] sm:px-10 sm:py-10"
    >
      <SignalField className="pointer-events-none absolute -top-24 -right-20 h-80 w-80 text-white/25" />
      <div className="relative max-w-2xl">
        <h2
          id="help-contact-title"
          className="text-2xl font-semibold tracking-tight sm:text-3xl"
        >
          Have any questions? <span className="text-white/80">Contact us</span>
        </h2>
        <p className="mt-3 leading-relaxed text-white/85">
          If this manual does not answer it, the Privacy Office will.
          {contact.data?.response_time ? ` ${contact.data.response_time}` : ""}
        </p>
        {contact.data?.dpo_contact && (
          <a
            href={`mailto:${contact.data.dpo_contact}`}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-white/15 px-4 py-2.5 text-sm font-semibold text-white ring-1 ring-white/40 backdrop-blur-sm transition-[background-color,transform] hover:-translate-y-px hover:bg-white/25"
          >
            <Mail className="size-4" aria-hidden="true" />
            {contact.data.dpo_contact}
          </a>
        )}
        {children && (
          <div className="mt-5 text-sm leading-relaxed text-white/85">{children}</div>
        )}
      </div>
    </section>
  );
}
