/**
 * Consents, filtered (2026-10-08): by project, the project's site, full or
 * partial, and when the consent was given - each sent to the API and kept in
 * the URL.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsentsPage from "@/app/(app)/consents/page";
import { makeConsentRow } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

const PROJECT = "11111111-1111-4111-8111-111111111111";
const SITE = "22222222-2222-4222-8222-222222222222";

beforeEach(() => window.history.replaceState(null, "", "/consents"));

describe("Consents filters", () => {
  it("narrows by project, site, partial and dates, and asks the API for exactly that", async () => {
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}/consents`, ({ request }) => {
        asked.push(new URL(request.url).searchParams);
        return HttpResponse.json({ items: [], next_cursor: null, total: 0 });
      }),
      http.get(`${API}/projects`, () =>
        HttpResponse.json({
          items: [{ project_uuid: PROJECT, project_name: "Gait Study 2026" }],
          next_cursor: null,
          total: 1,
        }),
      ),
      http.get(`${API}/projects/${PROJECT}/sites`, () =>
        HttpResponse.json([{ site_uuid: SITE, site_label: "Pune lab" }]),
      ),
    );
    const { user } = render(<ConsentsPage />);

    expect(await screen.findByRole("option", { name: "Gait Study 2026" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Project"), PROJECT);
    await user.selectOptions(await screen.findByLabelText("Site"), await screen.findByRole("option", { name: "Pune lab" }));
    await user.selectOptions(screen.getByLabelText("Status"), "partial");
    await user.type(screen.getByLabelText("Given from"), "2026-10-01");

    await vi.waitFor(() => {
      const last = asked.at(-1)!;
      expect(last.get("project")).toBe(PROJECT);
      expect(last.get("site")).toBe(SITE);
      expect(last.get("status")).toBe("partial");
      expect(last.get("from")).toBe("2026-10-01T00:00:00");
    });
    expect(new URLSearchParams(window.location.search).get("site")).toBe(SITE);
    expect(screen.getByText("No consents match")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await vi.waitFor(() => expect([...asked.at(-1)!.keys()].filter((k) => k !== "limit")).toEqual([]));
  });
});

describe("Consents, by the data subject", () => {
  it("searches by name on Enter, keeps it in the address, and Clear filters takes it off", async () => {
    // 2026-11-12: the first question asked with a person in front of you.
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}/consents`, ({ request }) => {
        asked.push(new URL(request.url).searchParams);
        return HttpResponse.json({ items: [], next_cursor: null, total: 0 });
      }),
      http.get(`${API}/projects`, () => HttpResponse.json({ items: [], next_cursor: null, total: 0 })),
    );
    const { user } = render(<ConsentsPage />);

    const box = screen.getByRole("searchbox", { name: "Data subject" });
    await user.type(box, "Meera");
    // Not as it is typed: a fragment of a contact is not sent anywhere.
    expect(asked.every((a) => !a.has("q"))).toBe(true);
    await user.keyboard("{Enter}");
    await vi.waitFor(() => expect(asked.at(-1)!.get("q")).toBe("Meera"));
    expect(new URLSearchParams(window.location.search).get("q")).toBe("Meera");
    expect(await screen.findByText("No consents match")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await vi.waitFor(() => expect(asked.at(-1)!.has("q")).toBe(false));
    expect(box).toHaveValue("");
  });

  it("says what the server says when the name is too short to search for", async () => {
    server.use(
      http.get(`${API}/consents`, ({ request }) =>
        new URL(request.url).searchParams.get("q") === "Me"
          ? HttpResponse.json(
              { error: { code: "validation_failed", message: "Enter three or more letters of the name", field: "q" } },
              { status: 422 },
            )
          : HttpResponse.json({ items: [], next_cursor: null, total: 0 }),
      ),
      http.get(`${API}/projects`, () => HttpResponse.json({ items: [], next_cursor: null, total: 0 })),
    );
    const { user } = render(<ConsentsPage />);
    await user.type(screen.getByRole("searchbox", { name: "Data subject" }), "Me{Enter}");
    expect(await screen.findByText("Enter three or more letters of the name")).toBeInTheDocument();
  });
});

describe("Consents register", () => {
  it("shows the consent's, the person's and the project's IDs as numbers, beside the names", async () => {
    // 2026-11-12: the three numbers the Data Collection Tool is given, and
    // the ones in the export a collection owner takes - not the uuids.
    server.use(
      http.get(`${API}/consents`, () =>
        HttpResponse.json({
          items: [makeConsentRow({ consent_no: 55210, person_no: 10873, project_no: 412 })],
          next_cursor: null,
          total: 1,
        }),
      ),
      http.get(`${API}/projects`, () => HttpResponse.json({ items: [], next_cursor: null, total: 0 })),
    );
    render(<ConsentsPage />);

    const row = (await screen.findByRole("link", { name: "Meera Iyer" })).closest("tr") as HTMLElement;
    // A row may be a project's or an HR activity's, and the column says so.
    for (const heading of ["Consent ID", "Person ID", "Projects/HR Activity", "Project ID"]) {
      expect(screen.getByRole("columnheader", { name: heading })).toBeInTheDocument();
    }
    const cells = within(row).getAllByRole("cell").map((c) => c.textContent);
    expect(cells[0]).toBe("55210");
    expect(cells[2]).toBe("10873");
    expect(cells[4]).toBe("412");
    // No uuid is shown in their place.
    expect(row.textContent).not.toMatch(/[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}/);
  });
});
