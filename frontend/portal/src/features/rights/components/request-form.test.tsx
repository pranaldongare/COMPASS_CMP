/**
 * The signed-in request form (2026-10-07): three kinds, no project or consent
 * to pick, and documents sent once the request is recorded. A file the API
 * would refuse is said before anything is sent; one the API refuses anyway
 * does not undo the request.
 */
import type * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { MyRequestForm as Form } from "@/features/rights/components/request-form";
import { ToastProvider } from "@/providers/toast-provider";
import { makeMyRequest } from "@/test/fixtures";
import { fireEvent, render, screen, waitFor } from "@/test/render";
import { API, errorResponse, HttpResponse, http, server } from "@/test/server";

const created = makeMyRequest({ request_uuid: "12121212-1212-4212-8212-121212121212" });

function MyRequestForm(props: React.ComponentProps<typeof Form>) {
  return (
    <ToastProvider>
      <Form {...props} />
    </ToastProvider>
  );
}

function fileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector<HTMLInputElement>('input[type="file"]');
  if (!input) throw new Error("no file input");
  return input;
}

describe("MyRequestForm", () => {
  it("offers access, erasure and a grievance, and nothing to scope it to", () => {
    render(<MyRequestForm onDone={() => {}} />);
    const options = Array.from(
      screen.getByLabelText(/what are you asking for/i).querySelectorAll("option"),
    ).map((o) => o.getAttribute("value"));
    expect(options).toEqual(["access", "erasure", "grievance"]);
    expect(screen.queryByText(/project/i, { selector: "label" })).not.toBeInTheDocument();
    expect(screen.getByText(/every project and every consent/i)).toBeInTheDocument();
  });

  it("sends each document after the request is recorded", async () => {
    const order: string[] = [];
    server.use(
      http.post(`${API}/me/requests`, async ({ request }) => {
        order.push("request");
        const body = (await request.json()) as Record<string, unknown>;
        expect(body).not.toHaveProperty("consent_uuid");
        return HttpResponse.json(created, { status: 201 });
      }),
      http.post(`${API}/me/requests/${created.request_uuid}/attachments`, () => {
        order.push("document");
        return HttpResponse.json(created, { status: 201 });
      }),
    );
    const onDone = vi.fn();
    const { container, user } = render(<MyRequestForm onDone={onDone} />);
    await user.type(screen.getByLabelText(/your request/i), "Everything you hold about me");
    await user.upload(fileInput(container), [
      new File(["%PDF-1.4"], "id-proof.pdf", { type: "application/pdf" }),
      new File(["hello"], "letter.txt", { type: "text/plain" }),
    ]);
    expect(screen.getByText("id-proof.pdf")).toBeInTheDocument();
    expect(screen.getByText("letter.txt")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /send the request/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(order).toEqual(["request", "document", "document"]);
  });

  it("says what it will not take, and lets a chosen file be taken off", async () => {
    const { container, user } = render(<MyRequestForm onDone={() => {}} />);
    // Past the picker's own filter, as a drag-and-drop or "All files" would be.
    fireEvent.change(fileInput(container), {
      target: {
        files: [
          new File(["MZ"], "setup.exe", { type: "application/octet-stream" }),
          new File(["x"], "photo.png", { type: "image/png" }),
        ],
      },
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/setup\.exe is not a PDF/);
    expect(screen.queryByText("setup.exe", { selector: "span" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove photo.png" }));
    expect(screen.queryByText("photo.png")).not.toBeInTheDocument();
  });

  it("keeps the request when a document is refused", async () => {
    server.use(
      http.post(`${API}/me/requests`, () => HttpResponse.json(created, { status: 201 })),
      http.post(`${API}/me/requests/${created.request_uuid}/attachments`, () =>
        errorResponse("validation_failed", "That file type is not accepted", 422),
      ),
    );
    const onDone = vi.fn();
    const { container, user } = render(<MyRequestForm onDone={onDone} />);
    await user.type(screen.getByLabelText(/your request/i), "Erase my data");
    await user.upload(fileInput(container), new File(["x"], "scan.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: /send the request/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(created));
  });
});
