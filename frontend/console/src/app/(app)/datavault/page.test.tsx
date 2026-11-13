/**
 * DataVault connection (0070): the administrator sets the address and the
 * key. The key is never shown again; saving without typing one keeps it.
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
  api_key_set: false,
  api_key_header: "X-API-Key",
  enabled: false,
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
          enabled: Boolean(body.enabled),
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
      api_key: "k-123",
      api_key_header: "X-API-Key",
      enabled: true,
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
      api_key_header: "X-API-Key",
      enabled: true,
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
});
