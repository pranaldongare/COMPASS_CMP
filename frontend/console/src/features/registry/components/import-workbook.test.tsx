/**
 * Processors and data sources from a workbook (2026-10-14): checked before it
 * is imported, every row in error named by its spreadsheet row, nothing
 * importable until the file is clean - and an import the server refuses shows
 * the rows it refused.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ImportWorkbook } from "@/features/registry/components/import-workbook";
import { fireEvent, render, screen, waitFor } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";
import type { RegistryImportReport } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

const CLEAN: RegistryImportReport = {
  kind: "processors",
  applied: false,
  total: 2,
  created: 1,
  skipped: 1,
  errors: 0,
  rows: [
    { row: 2, name: "Pune Gait Research Labs Pvt Ltd", outcome: "ready", message: null, problems: [], uuid: null },
    { row: 3, name: "Test Processor Ltd", outcome: "skipped", message: "Already registered", problems: [], uuid: null },
  ],
};

const BROKEN: RegistryImportReport = {
  ...CLEAN,
  created: 1,
  skipped: 0,
  errors: 1,
  rows: [
    CLEAN.rows[0],
    {
      row: 3,
      name: "Somewhere Ltd",
      outcome: "error",
      message: null,
      problems: [{ column: "Country", message: "'India' is not a two-letter country code" }],
      uuid: null,
    },
  ],
};

function choose() {
  fireEvent.change(screen.getByLabelText("The filled-in workbook"), {
    target: { files: [new File(["PK"], "processors.xlsx", { type: XLSX })] },
  });
}

describe("ImportWorkbook", () => {
  it("checks the workbook, then imports what it would create", async () => {
    const calls: string[] = [];
    server.use(
      http.post(`${API}/processors/import/check`, () => {
        calls.push("check");
        return HttpResponse.json(CLEAN);
      }),
      http.post(`${API}/processors/import`, () => {
        calls.push("import");
        return HttpResponse.json(
          { ...CLEAN, applied: true, rows: [{ ...CLEAN.rows[0], outcome: "created" }, CLEAN.rows[1]] },
          { status: 201 },
        );
      }),
    );
    const onDone = vi.fn();
    const { user } = render(<ImportWorkbook kind="processors" onDone={onDone} />);
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();

    choose();
    await user.click(screen.getByRole("button", { name: "Check the workbook" }));
    expect(await screen.findByText("Already registered - skipped")).toBeInTheDocument();
    expect(screen.getByText("Already registered")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Import 1 processor" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(calls).toEqual(["check", "import"]);
  });

  it("imports nothing while a row needs fixing, and names the row and column", async () => {
    server.use(http.post(`${API}/sources/import/check`, () => HttpResponse.json({ ...BROKEN, kind: "sources" })));
    const { user } = render(<ImportWorkbook kind="sources" onDone={() => {}} />);
    choose();
    await user.click(screen.getByRole("button", { name: "Check the workbook" }));
    expect(await screen.findByText(/Nothing is imported while any row needs fixing/)).toBeInTheDocument();
    expect(screen.getByText(/'India' is not a two-letter country code/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Import" })).toBeDisabled();
  });

  it("shows the rows of an import the server refused", async () => {
    server.use(
      http.post(`${API}/processors/import/check`, () => HttpResponse.json(CLEAN)),
      http.post(`${API}/processors/import`, () =>
        errorResponse("import_rejected", "1 row(s) need fixing. Nothing was imported.", 422, {
          field: "file",
          ...BROKEN,
        }),
      ),
    );
    const { user } = render(<ImportWorkbook kind="processors" onDone={() => {}} />);
    choose();
    await user.click(screen.getByRole("button", { name: "Check the workbook" }));
    await user.click(await screen.findByRole("button", { name: "Import 1 processor" }));
    expect(await screen.findByText(/Nothing was imported/)).toBeInTheDocument();
    expect(screen.getByText(/'India' is not a two-letter country code/)).toBeInTheDocument();
  });
});
