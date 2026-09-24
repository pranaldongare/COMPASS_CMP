/**
 * Withdrawing one purpose is not withdrawing the consent. The record it writes
 * is marked as a withdrawal - that is the act - but while anything is still
 * granted it reads Partial and can still be withdrawn from here.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import MyConsentsPage from "@/app/(app)/my-consents/page";
import { ToastProvider } from "@/providers/toast-provider";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";
import type { MyConsent } from "@/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/my-consents",
}));

function consent(overrides: Partial<MyConsent>): MyConsent {
  return {
    consent_uuid: "11111111-1111-4111-8111-111111111111",
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Gait Identification Study 2026",
    notice_uuid: "33333333-3333-4333-8333-333333333333",
    notice_code: "NTC-GAIT-2026",
    version: 1,
    language_code: "english",
    affirmative_action_at: "2026-09-20T10:00:00Z",
    is_withdrawal: false,
    granted_count: 2,
    purpose_count: 2,
    ...overrides,
  } as MyConsent;
}

function serve(c: MyConsent) {
  server.use(
    http.get(`${API}/me/consents`, () => HttpResponse.json([c])),
    // The page's other panels, empty: not what is under test.
    http.get(`${API}/me/disclosures`, () => HttpResponse.json([])),
    http.get(`${API}/me/nominations`, () => HttpResponse.json([])),
    http.get(`${API}/me/nominee-of`, () => HttpResponse.json([])),
    http.get(`${API}/me/requests`, () => HttpResponse.json([])),
  );
}

function page() {
  return render(
    <ToastProvider>
      <MyConsentsPage />
    </ToastProvider>,
  );
}

describe("My consents", () => {
  it("reads a one-of-two withdrawal as Partial, and still offers to withdraw the rest", async () => {
    serve(consent({ is_withdrawal: true, granted_count: 1, purpose_count: 2 }));
    page();
    expect(await screen.findByText(/partial/i)).toBeInTheDocument();
    expect(screen.queryByText(/^withdrawn$/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /withdraw everything/i })).toBeInTheDocument();
  });

  it("reads a withdrawal that left nothing as Withdrawn, with nothing left to withdraw", async () => {
    serve(consent({ is_withdrawal: true, granted_count: 0, purpose_count: 2 }));
    page();
    expect(await screen.findByText(/withdrawn/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /withdraw everything/i })).not.toBeInTheDocument();
  });
});
