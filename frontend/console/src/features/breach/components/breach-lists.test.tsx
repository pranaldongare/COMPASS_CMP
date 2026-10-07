/**
 * A breach's people from a list somebody sends us (2026-10-07): the file is
 * checked before it is taken - counts and unreadable rows shown, nothing
 * written - and only then added. People with no account are listed apart,
 * told by email and SMS.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { BreachContacts, UploadList } from "@/features/breach/components/breach-lists";
import { fireEvent, render, screen, waitFor } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";
import type { Breach, BreachListReport } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
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
    await user.click(screen.getByRole("radio", { name: /Asset IDs/ }));
    choose(new File(["asset_id\nGAIT-0417\n"], "assets.csv", { type: "text/csv" }));
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByText("In the assets but consented to nothing - cannot be traced")).toBeInTheDocument();
    expect(kind).toBe("assets");
  });

  it("says why a file was refused", async () => {
    server.use(
      http.post(`${API}/breaches/${UUID}/affected/upload/check`, () =>
        errorResponse("validation_failed", "That is an Excel workbook. Save it as CSV", 422),
      ),
    );
    const { user } = render(<UploadList breach={breach} onDone={() => {}} />);
    choose(new File(["PK"], "people.xlsx"));
    await user.click(screen.getByRole("button", { name: "Check the file" }));
    expect(await screen.findByText(/Save it as CSV/)).toBeInTheDocument();
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
});
