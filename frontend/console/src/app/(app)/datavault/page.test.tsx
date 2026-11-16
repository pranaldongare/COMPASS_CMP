/**
 * DataVault connection (0070, 0071): the administrator sets the addresses and
 * the key, how IDs are sent, and whether consent changes go out by themselves.
 * The key is never shown again; saving without typing one keeps it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DataVaultConnectionPage from "@/app/(app)/datavault/page";
import type { DataVaultConnection } from "@/features/datavault/api";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const saved = (over: Partial<DataVaultConnection> = {}): DataVaultConnection => ({
  base_url: null,
  erasure_url: null,
  api_key_set: false,
  api_key_header: "X-API-Key",
  enabled: false,
  id_format: "numeric",
  consent_changes: false,
  consent_changes_waiting: 0,
  consent_changes_last_delivered_at: null,
  consent_changes_last_failure: null,
  updated_at: null,
  updated_by_name: null,
  ...over,
});

function serve(now: DataVaultConnection) {
  const sent: unknown[] = [];
  server.use(
    http.get(`${API}/datavault-connection`, () => HttpResponse.json(now)),
    http.put(`${API}/datavault-connection`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return HttpResponse.json(
        saved({
          base_url: body.base_url as string | null,
          erasure_url: body.erasure_url as string | null,
          enabled: Boolean(body.enabled),
          id_format: body.id_format as DataVaultConnection["id_format"],
          consent_changes: Boolean(body.consent_changes),
          api_key_set: Boolean(body.api_key) || (now.api_key_set && !body.clear_api_key),
        }),
      );
    }),
  );
  return sent;
}

beforeEach(() => vi.clearAllMocks());

describe("DataVault connection", () => {
  it("saves the address and the key, and switches it on", async () => {
    const sent = serve(saved());
    const { user } = render(<DataVaultConnectionPage />);
    await user.type(
      await screen.findByLabelText("DataVault address"),
      "https://dv.internal/api",
    );
    await user.type(screen.getByLabelText("API key"), "k-123");
    await user.click(screen.getByLabelText("Switched on"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toEqual({
      base_url: "https://dv.internal/api",
      erasure_url: null,
      api_key: "k-123",
      api_key_header: "X-API-Key",
      enabled: true,
      // As it starts: the numbers the console shows, and nothing sent by itself.
      id_format: "numeric",
      consent_changes: false,
    });
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalled());
    expect(screen.getByLabelText("API key")).toHaveValue("");
  });

  it("keeps the stored key when none is typed, and never shows it", async () => {
    const sent = serve(
      saved({ base_url: "https://dv.internal/api", api_key_set: true, enabled: true }),
    );
    const { user } = render(<DataVaultConnectionPage />);
    expect(
      await screen.findByText(/A key is stored\. It is not shown again/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("API key")).toHaveValue("");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toEqual({
      base_url: "https://dv.internal/api",
      erasure_url: null,
      api_key_header: "X-API-Key",
      enabled: true,
      id_format: "numeric",
      consent_changes: false,
    });
  });

  it("removes the stored key only when asked", async () => {
    const sent = serve(saved({ base_url: "https://dv.internal/api", api_key_set: true }));
    const { user } = render(<DataVaultConnectionPage />);
    await user.click(await screen.findByLabelText("Remove the stored key"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toMatchObject({ clear_api_key: true });
  });

  it("will not be switched on without an address", async () => {
    const sent = serve(saved());
    const { user } = render(<DataVaultConnectionPage />);
    await user.click(await screen.findByLabelText("Switched on"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(
      await screen.findByText(/Enter DataVault's address before switching it on/),
    ).toBeInTheDocument();
    expect(sent).toHaveLength(0);
  });

  it("sets the erasure address, switches IDs to UUIDs and consent changes on", async () => {
    const sent = serve(
      saved({ base_url: "https://dv.internal/api", api_key_set: true, enabled: true }),
    );
    const { user } = render(<DataVaultConnectionPage />);
    await user.type(
      await screen.findByLabelText("Erasure address"),
      "https://dv-erase.internal/api/v1",
    );
    await user.click(screen.getByRole("radio", { name: /UUIDs/ }));
    await user.click(screen.getByLabelText("Tell DataVault of consent changes"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    await vi.waitFor(() => expect(sent).toHaveLength(1));
    expect(sent[0]).toMatchObject({
      erasure_url: "https://dv-erase.internal/api/v1",
      id_format: "uuid",
      consent_changes: true,
    });
    // Switched on: the queue's card says how it stands.
    expect(await screen.findByText("Nothing waiting.")).toBeInTheDocument();
  });

  it("will not switch consent changes on without the address they go to", async () => {
    const sent = serve(saved({ base_url: "https://dv.internal/api", enabled: true }));
    const { user } = render(<DataVaultConnectionPage />);
    await user.click(await screen.findByLabelText("Tell DataVault of consent changes"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(
      await screen.findByText(
        /Enter the erasure address before switching consent changes on/,
      ),
    ).toBeInTheDocument();
    expect(sent).toHaveLength(0);
  });

  it("says how the consent-change queue stands, and why the last try failed", async () => {
    serve(
      saved({
        base_url: "https://dv.internal/api",
        erasure_url: "https://dv-erase.internal/api/v1",
        enabled: true,
        consent_changes: true,
        consent_changes_waiting: 3,
        consent_changes_last_delivered_at: "2026-11-13T09:00:00Z",
        consent_changes_last_failure: "DataVault could not be reached.",
      }),
    );
    render(<DataVaultConnectionPage />);
    expect(await screen.findByText(/3 waiting to be delivered\./)).toBeInTheDocument();
    expect(screen.getByText(/Last delivered/)).toBeInTheDocument();
    expect(
      screen.getByText(/DataVault could not be reached\. It is tried again by itself\./),
    ).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /Numeric IDs/ })).toBeChecked();
  });

  it("shows no queue while consent changes have never been on", async () => {
    serve(saved({ base_url: "https://dv.internal/api", enabled: true }));
    render(<DataVaultConnectionPage />);
    expect(await screen.findByLabelText("Erasure address")).toBeInTheDocument();
    expect(screen.queryByText("Consent changes")).not.toBeInTheDocument();
  });
});
