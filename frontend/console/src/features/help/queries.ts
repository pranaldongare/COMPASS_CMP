/**
 * Who to contact, for the manual's closing panel.
 *
 * Read from the same public `/rights` answer the portal's rights page shows,
 * so the address in the manual is the Privacy Office's current one rather
 * than a copy written into the page.
 */
"use client";

import { useQuery } from "@tanstack/react-query";

import { apiGet } from "@/lib/api/client";
import type { ApiError } from "@/lib/errors";
import { keys } from "@/lib/query";

export interface HelpContact {
  dpo_contact: string;
  response_time: string;
  board_complaint: string;
}

export function useHelpContact() {
  return useQuery<HelpContact, ApiError>({
    queryKey: keys.help.contact,
    queryFn: () => apiGet<HelpContact>("/rights"),
    staleTime: 60 * 60_000,
    retry: false,
  });
}
