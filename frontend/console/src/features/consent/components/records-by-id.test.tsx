/**
 * Consent records by ID (2026-10-15): pasted IDs go to the server as a list,
 * and a list the server refuses names the IDs it did not find, with a way to
 * drop them and go again.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConsentRecordsById } from "@/features/consent/components/records-by-id";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";

const saved = vi.hoisted(() => ({ names: [] as string[] }));

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));
vi.mock("@/providers/auth-provider", () => ({
  useOptionalAuth: () => ({ me: makeMe({ role: "dpo" }) }),
}));
vi.mock("@/lib/format", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/format")>()),
  saveBlob: (_blob: Blob, name: string) => saved.names.push(name),
}));

const A = "46a27302-6b59-417c-bc89-a8d68895bedc";
const B = "655d1760-6f31-4c25-8766-9a16917ae116";

beforeEach(() => {
  saved.names = [];
});

async function open(user: Awaited<ReturnType<typeof render>>["user"], text: string) {
  await user.click(screen.getByRole("button", { name: "By consent IDs" }));
  const box = screen.getByRole("textbox", { name: "Consent IDs" });
  await user.click(box);
  await user.paste(text);
}

describe("ConsentRecordsById", () => {
  it("sends the pasted IDs, once each, and saves the archive", async () => {
    let sent: unknown = null;
    server.use(
      http.post(`${API}/consent-records`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.arrayBuffer(new ArrayBuffer(4), {
          headers: {
            "content-type": "application/zip",
            "content-disposition": 'attachment; filename="consent-records-x.zip"',
          },
        });
      }),
    );
    const { user } = render(<ConsentRecordsById />);
    await open(user, `${A}\n${B}\n${A}`);
    expect(screen.getByText(/2 consent IDs, 1 repeated/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Download 2 records (ZIP)" }));
    await waitFor(() => expect(saved.names).toEqual(["consent-records-x.zip"]));
    expect(sent).toEqual({ consent_uuids: [A, B] });
  });

  it("names the IDs the server did not find and lets them be dropped", async () => {
    server.use(
      http.post(`${API}/consent-records`, () =>
        HttpResponse.json(
          {
            error: {
              code: "consent_records_not_found",
              message: "1 of 2 consent IDs were not found, or are not yours to see.",
              request_id: "r",
              not_found: [B],
            },
          },
          { status: 422 },
        ),
      ),
    );
    const { user } = render(<ConsentRecordsById />);
    await open(user, `${A}, ${B}`);
    await user.click(screen.getByRole("button", { name: "Download 2 records (ZIP)" }));
    expect(await screen.findByText(/1 of 2 consent IDs were not found/)).toBeInTheDocument();
    expect(screen.getByText(B)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Remove it from the list" }));
    expect(screen.getByRole("textbox", { name: "Consent IDs" })).toHaveValue(A);
    expect(screen.getByRole("button", { name: "Download 1 record (ZIP)" })).toBeEnabled();
  });
});
