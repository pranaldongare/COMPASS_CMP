/**
 * Notices about a personal data breach, written to her account.
 */

import { apiGet } from "@/lib/api";
import type { MyBreachNotice } from "@/types";

export function listMyBreachNotices(): Promise<MyBreachNotice[]> {
  return apiGet<MyBreachNotice[]>("/me/breach-notices");
}
