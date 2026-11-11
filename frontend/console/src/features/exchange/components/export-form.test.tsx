/**
 * Generating an export (2026-11-11): the project export, or the consented list
 * the Data Collection Tool loads. The choice decides the route and the warning;
 * an HR activity is offered only the project export.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ExportForm } from "@/features/exchange/components/export-form";
import { render, screen, waitFor } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const PROJECT = "66666666-6666-4666-8666-666666666666";

function serve() {
  const hit: string[] = [];
  server.use(
    http.post(`${API}/projects/${PROJECT}/exports`, () => {
      hit.push("project_export");
      return HttpResponse.json({ export_uuid: "e1", row_count: 3 }, { status: 201 });
    }),
    http.post(`${API}/projects/${PROJECT}/exports/dct-consented-list`, () => {
      hit.push("dct_consented_list");
      return HttpResponse.json(
        {
          export_uuid: "e2",
          row_count: 2,
          left_out: { withdrawn: 1, partial: 0, lapsed: 0, no_name: 1 },
        },
        { status: 201 },
      );
    }),
  );
  return hit;
}

describe("ExportForm", () => {
  it("generates the project export by default", async () => {
    const hit = serve();
    const onDone = vi.fn();
    const { user } = render(<ExportForm projectUuid={PROJECT} onDone={onDone} />);
    expect(screen.getByText(/name, email and mobile number/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate the export" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(hit).toEqual(["project_export"]);
  });

  it("generates the DCT's consented list, and says who was left off", async () => {
    const hit = serve();
    const onDone = vi.fn();
    const { user } = render(<ExportForm projectUuid={PROJECT} onDone={onDone} />);
    await user.click(screen.getByRole("radio", { name: /Consented list for the Data Collection Tool/ }));
    expect(screen.getByText(/goes onto collection laptops/)).toBeInTheDocument();
    expect(screen.queryByText(/name, email and mobile number/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate the consented list" }));

    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(hit).toEqual(["dct_consented_list"]);
    expect(toast.success).toHaveBeenCalledWith(
      "Consented list generated",
      expect.stringContaining("2 people on it. Left off: 1 withdrawn, 1 with no name on record."),
    );
  });

  it("shows why a list could not be made, and stays open", async () => {
    serve();
    server.use(
      http.post(`${API}/projects/${PROJECT}/exports/dct-consented-list`, () =>
        errorResponse("nobody_consented", "Nobody on this project has a consent in force", 409),
      ),
    );
    const onDone = vi.fn();
    const { user } = render(<ExportForm projectUuid={PROJECT} onDone={onDone} />);
    await user.click(screen.getByRole("radio", { name: /Consented list for the Data Collection Tool/ }));
    await user.click(screen.getByRole("button", { name: "Generate the consented list" }));
    expect(await screen.findByText(/Nobody on this project has a consent in force/)).toBeInTheDocument();
    expect(onDone).not.toHaveBeenCalled();
  });

  it("offers an HR activity only the project export", () => {
    render(<ExportForm projectUuid={PROJECT} onDone={() => {}} dct={false} />);
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate the export" })).toBeInTheDocument();
  });
});
