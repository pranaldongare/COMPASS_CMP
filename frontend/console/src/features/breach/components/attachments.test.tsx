/**
 * Files kept with an incident (2026-10-06): listed with their kind, name and
 * hash, downloadable, and added while the breach is open. Logging an incident
 * sends the files chosen with it, once it exists. (The test DOM's File loses
 * its name and type on the way into a request; api.test.ts checks those.)
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { AttachmentsCard } from "@/features/breach/components/attachments";
import { RecordBreachForm } from "@/features/breach/components/record-breach";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach } from "@/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const UUID = "66666666-6666-4666-8666-666666666666";
const ATT = {
  attachment_uuid: "77777777-7777-4777-8777-777777777777",
  kind: "email" as const,
  note: "The report, as it came",
  file_name: "report.eml",
  sha256: "a".repeat(64),
  size_bytes: 2048,
  content_type: "message/rfc822",
  added_at: "2026-10-06T09:00:00Z",
  added_by_name: "Priya Menon",
};
/** A multipart field as the request carries it. The test DOM's File and
 *  Node's differ, so the body is read as text rather than parsed. */
const field = (body: string, name: string) =>
  new RegExp(`name="${name}"\r\n\r\n([^\r]*)`).exec(body)?.[1] ?? null;

const breach = (over: Partial<Breach> = {}) =>
  ({ breach_uuid: UUID, status: "open", attachments: [ATT], ...over }) as Breach;

describe("AttachmentsCard", () => {
  it("lists each file with its kind, and downloads it from its own address", () => {
    render(<AttachmentsCard breach={breach()} />);
    const row = screen.getByText("report.eml").closest("li") as HTMLElement;
    expect(within(row).getByText("Email")).toBeInTheDocument();
    expect(within(row).getByText("The report, as it came")).toBeInTheDocument();
    expect(within(row).getByRole("link", { name: /download/i })).toHaveAttribute(
      "href",
      expect.stringContaining(`/breaches/${UUID}/attachments/${ATT.attachment_uuid}`),
    );
  });

  it("attaches a file with what it is and a note", async () => {
    let body = "";
    server.use(
      http.post(`${API}/breaches/${UUID}/attachments`, async ({ request }) => {
        body = await request.text();
        return HttpResponse.json(breach(), { status: 201 });
      }),
    );
    const { user } = render(<AttachmentsCard breach={breach({ attachments: [] })} />);

    await user.click(screen.getByRole("button", { name: "Attach a file" }));
    await user.upload(screen.getByLabelText(/^File/), new File(["From: x"], "tip-off.eml", { type: "" }));
    await user.selectOptions(screen.getByLabelText("What it is"), "email");
    await user.type(screen.getByLabelText(/^Note/), "Forwarded by the helpdesk");
    await user.click(screen.getByRole("button", { name: "Attach" }));

    await vi.waitFor(() => expect(body).not.toBe(""));
    expect(field(body, "kind")).toBe("email");
    expect(field(body, "note")).toBe("Forwarded by the helpdesk");
  });

  it("offers no way to add once the breach is closed", () => {
    render(<AttachmentsCard breach={breach({ status: "closed" })} />);
    expect(screen.queryByRole("button", { name: "Attach a file" })).not.toBeInTheDocument();
  });
});

describe("RecordBreachForm", () => {
  it("logs the incident, then sends the files chosen with it", async () => {
    const order: string[] = [];
    server.use(
      http.post(`${API}/breaches`, () => {
        order.push("logged");
        return HttpResponse.json({ breach_uuid: UUID, reference: "INC-2026-0050" }, { status: 201 });
      }),
      http.post(`${API}/breaches/${UUID}/attachments`, async ({ request }) => {
        const body = await request.text();
        order.push(`attached:${field(body, "kind")}`);
        return HttpResponse.json(breach(), { status: 201 });
      }),
    );
    const { user } = render(<RecordBreachForm onDone={vi.fn()} />);

    await user.type(screen.getByLabelText(/^Title/), "A list sent to the wrong address");
    await user.type(screen.getByLabelText(/^First noticed/), "2026-10-06T09:00");
    await user.click(screen.getByRole("button", { name: "Attach a file" }));
    await user.upload(screen.getByLabelText(/^File 1/), new File(["%PDF-1.4"], "proof.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Log the incident" }));

    await vi.waitFor(() => expect(order).toEqual(["logged", "attached:email"]));
    expect(push).toHaveBeenCalledWith(`/breaches/${UUID}`);
  });
});
