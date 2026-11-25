/**
 * Employee check (ADR 0046): VerifyEmail and the organisation's email domains.
 *
 * The administrator's page. The server makes every call to VerifyEmail - at a
 * console sign-in, and after a portal sign-in by the worker - and the console
 * never talks to it or holds its key. The domains are the one list of who is
 * inside the organisation: who is checked, and who may hold a breach or a
 * rights ticket as staff.
 */
import { apiDelete, apiGet, apiPost, apiPut } from "@/lib/api";
import type { Timestamp } from "@/types";

export interface OrganisationDomain {
  domain: string;
  added_at: Timestamp;
  added_by_name: string | null;
}

export interface EmployeeCheckSettings {
  /** Where VerifyEmail is: the platform adds /VerifyEmail. */
  base_url: string | null;
  /** Whether a key is stored. The key itself is never served. */
  api_key_set: boolean;
  api_key_header: string;
  enabled: boolean;
  /** Staff on none of the domains sign in to the console unchecked. */
  allow_other_domains: boolean;
  domains: OrganisationDomain[];
  updated_at: Timestamp | null;
  updated_by_name: string | null;
}

export interface EmployeeCheckInput {
  base_url: string | null;
  /** A new key; left out, the stored one stays. */
  api_key?: string;
  clear_api_key?: boolean;
  api_key_header: string;
  enabled: boolean;
  allow_other_domains: boolean;
}

export interface EmployeeCheckTest {
  /** active, inactive or failed. */
  result: "active" | "inactive" | "failed";
  message: string;
  on_company_domain: boolean;
}

export const employeeCheckKeys = {
  settings: ["employee-check"] as const,
};

export function getEmployeeCheck(): Promise<EmployeeCheckSettings> {
  return apiGet<EmployeeCheckSettings>("/employee-check");
}

export function saveEmployeeCheck(
  body: EmployeeCheckInput,
): Promise<EmployeeCheckSettings> {
  return apiPut<EmployeeCheckSettings>("/employee-check", body);
}

export function addDomain(domain: string): Promise<OrganisationDomain[]> {
  return apiPost<OrganisationDomain[]>("/employee-check/domains", { domain });
}

export function removeDomain(domain: string): Promise<OrganisationDomain[]> {
  return apiDelete<OrganisationDomain[]>(
    `/employee-check/domains/${encodeURIComponent(domain)}`,
  );
}

export function testAddress(email: string): Promise<EmployeeCheckTest> {
  return apiPost<EmployeeCheckTest>("/employee-check/test", { email });
}
