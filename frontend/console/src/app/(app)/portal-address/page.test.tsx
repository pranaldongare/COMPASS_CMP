/**
 * Portal address (0072): the administrator sets the address links to the
 * portal start with, and a consent link copied afterwards starts with it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PortalAddressPage from "@/app/(app)/portal-address/page";
import { consentLinkUrl } from "@/features/consent/link-url";
import { isPortalAddress, portalUrl, setPortalUrl, type PortalAddress } from "@/features/portal-address";
import { config } from "@/lib/config";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() }));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const CONFIGURED = "http://localhost:3001";
const unset: PortalAddress = {
  portal_url: null,
  configured_url: CONFIGURED,
  in_use: CONFIGURED,
  updated_at: null,
  updated_by_name: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  setPortalUrl(null);
});

describe("the address a link starts with", () => {
  it("is the build's own until the server says another, then the server's", () => {
    expect(portalUrl()).toBe(config.subjectPortalUrl.replace(/\/+$/, ""));
    setPortalUrl("http://10.20.30.40:3001/");
    expect(portalUrl()).toBe("http://10.20.30.40:3001");
    expect(consentLinkUrl("/c/TOKEN")).toBe("http://10.20.30.40:3001/c/TOKEN");
    setPortalUrl(undefined);
    expect(consentLinkUrl("/c/TOKEN")).toBe(`${config.subjectPortalUrl}/c/TOKEN`);
  });

  it.each([
    ["http://10.20.30.40:3001", true],
    ["https://portal.example.org/", true],
    ["10.20.30.40:3001", false],
    ["https://portal.example.org/c", false],
    ["https://portal.example.org?x=1", false],
    ["ftp://portal.example.org", false],
  ])("%s is an address: %s", (typed, ok) => {
    expect(isPortalAddress(typed)).toBe(ok);
  });
});

describe("Portal address", () => {
  it("shows the configured address while none is set", async () => {
    server.use(http.get(`${API}/portal-address`, () => HttpResponse.json(unset)));
    render(<PortalAddressPage />);

    expect(await screen.findByText(/This is the configured address/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use the configured address" })).not.toBeInTheDocument();
  });

  it("saves an address, and links copied in this tab start with it at once", async () => {
    const sent: unknown[] = [];
    server.use(
      http.get(`${API}/portal-address`, () => HttpResponse.json(unset)),
      http.put(`${API}/portal-address`, async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json({
          ...unset,
          portal_url: "http://10.20.30.40:3001",
          in_use: "http://10.20.30.40:3001",
          updated_at: "2026-11-16T09:00:00Z",
        });
      }),
    );
    const { user } = render(<PortalAddressPage />);

    await user.type(await screen.findByLabelText("Portal address"), " http://10.20.30.40:3001 ");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("button", { name: "Use the configured address" })).toBeInTheDocument();
    expect(sent).toEqual([{ portal_url: "http://10.20.30.40:3001" }]);
    expect(toast.success).toHaveBeenCalledWith(
      "Portal address saved",
      "Links now start with http://10.20.30.40:3001.",
    );
    expect(consentLinkUrl("/c/TOKEN")).toBe("http://10.20.30.40:3001/c/TOKEN");
  });

  it("does not send what is not an address", async () => {
    const sent: unknown[] = [];
    server.use(
      http.get(`${API}/portal-address`, () => HttpResponse.json(unset)),
      http.put(`${API}/portal-address`, async ({ request }) => {
        sent.push(await request.json());
        return HttpResponse.json(unset);
      }),
    );
    const { user } = render(<PortalAddressPage />);

    await user.type(await screen.findByLabelText("Portal address"), "10.20.30.40:3001/c");
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/http:\/\/ or https:\/\//);
    expect(sent).toEqual([]);
  });
});
