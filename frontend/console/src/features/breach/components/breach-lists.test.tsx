/**
 * A breach's people from a list somebody sends us (2026-10-07): the file, an
 * Excel workbook since 2026-11-06, is checked before it is taken - counts and
 * unreadable rows shown, nothing written - and only then added. People with no
 * account are listed apart, told by email and SMS.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { BreachContacts, UploadList } from "@/features/breach/components/breach-lists";
import { fireEvent, render, screen, waitFor } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";
import type { Breach, BreachListReport } from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));

vi.mock("@/providers", () => ({
  useToast: () => toast,
}));

const UUID = "44444444-4444-4444-8444-444444444444";
const breach = { breach_uuid: UUID, status: "open" } as Breach;

const REPORT: BreachListReport = {
  kind: "contacts",
  rows_read: 4,
  matched_people: 1,
  new_contacts: 2,
  already_listed: 0,
  unreadable: 1,
  untraceable: 0,
  would_add: 3,
  errors: [{ row: 5, message: "Neither an email nor a mobile" }],
  more_errors: 0,
};

function choose(file: File) {
  const input = screen.getByLabelText("The filled-in list");
  fireEvent.change(input, { target: { files: [file] } });
}

describe("UploadList", () => {
  it("checks the file, shows what it would add and what it cannot read, then adds it", async () => {
    const calls: string[] = [];
    server.use(
      http.post(`${API}/breaches/${UUID}/affected/upload/check`, async ({ request }) => {
        calls.push(`check:${(await request.text()).includes("contacts")}`);
        return HttpResponse.json(REPORT);
      }),
      http.post(`${API}/breaches/${UUID}/affected/upload`, () => {
        calls.push("take");
        return HttpResponse.json({ ...REPORT, upload_uuid: UUID }, { status: 201 });
      }),
    );
    const onDone = vi.fn();
    const { user } = render(<UploadList breach={breach} onDone={onDone} />);
    const add = screen.getByRole("button", { name: /Add to the list/ });
    expect(add).toBeDisabled();

    choose(new File(["name,email,mobile\nAsha,a@example.org,\n"], "people.csv", { type: "text/csv" }));
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByText("Not on the platform, to be listed")).toBeInTheDocument();
    expect(screen.getByText(/Row 5: Neither an email nor a mobile/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Add 3 to the list" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(calls).toEqual(["check:true", "take"]);
    expect(toast.success).toHaveBeenCalledWith(
      "3 people added to the list",
      "Next: draft and approve the notice below, then send it.",
    );
  });

  it("takes the Excel template, and says so in plain words", () => {
    render(<UploadList breach={breach} onDone={() => {}} />);
    expect(screen.getByLabelText("The filled-in list")).toHaveAttribute("accept", ".xlsx,.csv");
    expect(screen.getByRole("radio", { name: /People: name, mail ID, mobile number/ })).toBeChecked();
    expect(screen.getByText(/An Excel file \(\.xlsx\) made from the template/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Save As|CSV|\.csv|touched/);
  });

  it("hears the same path chosen again, once the file is corrected", async () => {
    const asked: string[] = [];
    server.use(
      http.post(`${API}/breaches/${UUID}/affected/upload/check`, () => {
        asked.push("check");
        return HttpResponse.json(REPORT);
      }),
    );
    const { user } = render(<UploadList breach={breach} onDone={() => {}} />);
    const input = screen.getByLabelText("The filled-in list");
    const file = new File(["PK"], "people.xlsx");

    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByRole("button", { name: "Add 3 to the list" })).toBeEnabled();

    // The test's picker, like a browser's, stays quiet if the input already
    // holds this file, and the old report would still be on the screen.
    await user.upload(input, file);
    expect(screen.queryByRole("button", { name: "Add 3 to the list" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add to the list" })).toBeDisabled();
    expect(asked).toEqual(["check"]);
  });

  it("offers Back in place of Cancel when it is a step in something longer", async () => {
    const onBack = vi.fn();
    const onDone = vi.fn();
    const { user } = render(<UploadList breach={breach} onBack={onBack} onDone={onDone} />);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(onBack).toHaveBeenCalled();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("asks for asset IDs when that is what the list holds", async () => {
    let kind = "";
    server.use(
      http.post(`${API}/breaches/${UUID}/affected/upload/check`, async ({ request }) => {
        kind = (await request.text()).includes("assets") ? "assets" : "contacts";
        return HttpResponse.json({ ...REPORT, kind: "assets", untraceable: 2 });
      }),
    );
    const { user } = render(<UploadList breach={breach} onDone={() => {}} />);
    await user.click(screen.getByText("Only have asset IDs?"));
    await user.click(screen.getByRole("radio", { name: /Asset IDs/ }));
    choose(new File(["asset_id\nGAIT-0417\n"], "assets.csv", { type: "text/csv" }));
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByText("In the assets but consented to nothing - cannot be traced")).toBeInTheDocument();
    expect(kind).toBe("assets");
  });

  it("says why a file was refused", async () => {
    server.use(
      http.post(`${API}/breaches/${UUID}/affected/upload/check`, () =>
        errorResponse("validation_failed", "This sheet has no mail ID or mobile number in it", 422),
      ),
    );
    const { user } = render(<UploadList breach={breach} onDone={() => {}} />);
    choose(new File(["PK"], "people.xlsx"));
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByText(/no mail ID or mobile number/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add to the list/ })).toBeDisabled();
  });
});

describe("BreachContacts", () => {
  it("lists the people with no account, and the lists they came in", async () => {
    server.use(
      http.get(`${API}/breaches/${UUID}/affected/contacts`, () =>
        HttpResponse.json({
          total: 1,
          next_cursor: null,
          contacts: [
            {
              contact_uuid: "55555555-5555-4555-8555-555555555555",
              full_name: "Asha Rao",
              email: "asha@example.org",
              mobile: "+919876543210",
              added_at: "2026-10-07T10:00:00Z",
              upload_uuid: UUID,
              upload_kind: "contacts",
            },
          ],
          uploads: [],
        }),
      ),
    );
    render(<BreachContacts breach={breach} />);
    expect(await screen.findByText("Asha Rao")).toBeInTheDocument();
    expect(screen.getByText(/not on the platform - told by email and SMS/)).toBeInTheDocument();
    expect(screen.getByText("+919876543210")).toBeInTheDocument();
  });

  describe("Show more", () => {
    const contact = (n: number) => ({
      contact_uuid: `55555555-5555-4555-8555-55555555555${n}`,
      full_name: `Person ${n}`,
      email: null,
      mobile: null,
      added_at: "2026-10-07T10:00:00Z",
      upload_uuid: UUID,
      upload_kind: "contacts",
    });

    function servePages(next: () => Response | Promise<Response>) {
      server.use(
        http.get(`${API}/breaches/${UUID}/affected/contacts`, ({ request }) =>
          new URL(request.url).searchParams.get("cursor")
            ? next()
            : HttpResponse.json({ total: 2, next_cursor: "page-2", contacts: [contact(1)], uploads: [] }),
        ),
      );
    }

    it("says when the next page cannot be had, and lets it be asked for again", async () => {
      servePages(() => errorResponse("server_error", "Something failed", 500));
      const { user } = render(<BreachContacts breach={breach} />);

      await user.click(await screen.findByRole("button", { name: "Show more" }));
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Could not load more", expect.any(String)),
      );
      expect(screen.getByRole("button", { name: "Show more" })).toBeEnabled();
    });

    it("asks once at a time, so a page is never listed twice", async () => {
      let asked = 0;
      let answer = () => {};
      servePages(async () => {
        asked += 1;
        await new Promise<void>((resolve) => {
          answer = resolve;
        });
        return HttpResponse.json({ total: 2, next_cursor: null, contacts: [contact(2)], uploads: [] });
      });
      const { user } = render(<BreachContacts breach={breach} />);

      const more = await screen.findByRole("button", { name: "Show more" });
      await user.click(more);
      await waitFor(() => expect(more).toBeDisabled());
      await waitFor(() => expect(asked).toBe(1));
      answer();
      expect(await screen.findByText("Person 2")).toBeInTheDocument();
      expect(asked).toBe(1);
    });
  });
});
