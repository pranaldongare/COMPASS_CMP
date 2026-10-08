/**
 * Log an incident asks what else is known (2026-10-08): every answer
 * optional, free text, sent as typed; and "is it a cyber attack?" as a
 * choice that can be left, or cleared.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { RecordBreachForm } from "@/features/breach/components/record-breach";
import { fireEvent, render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

function serve(onBody: (b: Record<string, unknown>) => void) {
  server.use(
    http.post(`${API}/breaches`, async ({ request }) => {
      onBody((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(
        { breach_uuid: "11111111-1111-4111-8111-111111111111", reference: "INC-2026-0001" },
        { status: 201 },
      );
    }),
  );
}

async function basics(user: ReturnType<typeof render>["user"]) {
  await user.type(screen.getByLabelText(/^Title/), "A shared folder left open");
  fireEvent.change(screen.getByLabelText(/^First noticed/), {
    target: { value: "2026-10-08T09:00" },
  });
}

describe("Log an incident: what is known so far", () => {
  it("sends what was answered, and nothing for what was left", async () => {
    let body: Record<string, unknown> = {};
    serve((b) => (body = b));
    const { user } = render(<RecordBreachForm onDone={() => {}} />);
    await basics(user);
    await user.type(screen.getByLabelText(/^Where it started/), "A vendor's file share");
    await user.type(screen.getByLabelText(/^Third parties involved/), "Annotation Partners");
    await user.click(screen.getByRole("radio", { name: /Yes - reportable to CERT-In/ }));
    await user.click(screen.getByRole("button", { name: "Log the incident" }));
    await waitFor(() => expect(body.title).toBe("A shared folder left open"));
    expect(body.origin).toBe("A vendor's file share");
    expect(body.third_parties).toBe("Annotation Partners");
    expect(body.incident_details).toBeNull();
    expect(body.cyber_attack).toBe("yes");
  });

  it("logs with every question left, and a cleared choice is no answer", async () => {
    let body: Record<string, unknown> = {};
    serve((b) => (body = b));
    const { user } = render(<RecordBreachForm onDone={() => {}} />);
    await basics(user);
    await user.click(screen.getByRole("radio", { name: "No" }));
    await user.click(screen.getByRole("button", { name: "Clear" }));
    await user.click(screen.getByRole("button", { name: "Log the incident" }));
    await waitFor(() => expect(body.title).toBeTruthy());
    expect(body.cyber_attack).toBeNull();
    expect(body.origin).toBeNull();
  });
});
