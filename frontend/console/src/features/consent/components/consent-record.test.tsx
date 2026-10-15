/**
 * The consent record as a PDF (2026-10-15): offered to the staff who read
 * consents in full, and to nobody else; a click downloads and saves it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  DownloadConsentRecord,
  DownloadConsentRecords,
} from "@/features/consent/components/consent-record";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";

const auth = vi.hoisted(() => ({ role: "dpo" }));
const saved = vi.hoisted(() => ({ names: [] as string[] }));

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

vi.mock("@/providers/auth-provider", () => ({
  useOptionalAuth: () => ({ me: makeMe({ role: auth.role as never }) }),
}));

vi.mock("@/lib/format", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/format")>()),
  saveBlob: (_blob: Blob, name: string) => saved.names.push(name),
}));

const UUID = "55555555-5555-4555-8555-555555555555";

beforeEach(() => {
  saved.names = [];
});

describe("consent record downloads", () => {
  it("lets the DPO download one record and saves it under its consent ID", async () => {
    auth.role = "dpo";
    server.use(
      http.get(`${API}/consents/${UUID}/record`, () =>
        HttpResponse.arrayBuffer(new TextEncoder().encode("%PDF-1.7").buffer, {
          headers: {
            "content-type": "application/pdf",
            "content-disposition": `attachment; filename="consent-${UUID}.pdf"`,
          },
        }),
      ),
    );
    const { user } = render(<DownloadConsentRecord uuid={UUID} />);
    await user.click(screen.getByRole("button", { name: "Download PDF" }));
    await waitFor(() => expect(saved.names).toEqual([`consent-${UUID}.pdf`]));
  });

  it.each(["dco", "dco_admin", "rco"])("offers it to the %s", (role) => {
    auth.role = role;
    render(<DownloadConsentRecords filters={{}} />);
    expect(screen.getByRole("button", { name: "Download PDFs (ZIP)" })).toBeInTheDocument();
  });

  it.each(["rnd_user", "admin"])("offers nothing to the %s: the PDF names the person", (role) => {
    auth.role = role;
    const { container } = render(
      <>
        <DownloadConsentRecord uuid={UUID} />
        <DownloadConsentRecords filters={{}} />
      </>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("asks for the archive with the filters on screen", async () => {
    auth.role = "dpo";
    let asked = "";
    server.use(
      http.get(`${API}/consent-records`, ({ request }) => {
        asked = new URL(request.url).search;
        return HttpResponse.arrayBuffer(new ArrayBuffer(4), {
          headers: {
            "content-type": "application/zip",
            "content-disposition": 'attachment; filename="consent-records-x.zip"',
          },
        });
      }),
    );
    const { user } = render(
      <DownloadConsentRecords filters={{ project: UUID, from: "2026-10-01T00:00:00" }} />,
    );
    await user.click(screen.getByRole("button", { name: "Download PDFs (ZIP)" }));
    await waitFor(() => expect(saved.names).toEqual(["consent-records-x.zip"]));
    expect(asked).toContain(`project=${UUID}`);
    expect(asked).toContain("from=2026-10-01");
  });
});
