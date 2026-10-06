/**
 * A saved email or a log often reaches the browser with no type; the API
 * refuses a file whose type it does not accept. The type is read off the
 * extension for those, and a file that has one is sent as it is.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiPost = vi.fn();
vi.mock("@/lib/api", () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  queryString: () => "",
  apiPost: (...args: unknown[]) => apiPost(...args),
}));

import { addBreachAttachment } from "@/features/breach/api";

const UUID = "66666666-6666-4666-8666-666666666666";

function sent(): FormData {
  return apiPost.mock.calls.at(-1)?.[1] as FormData;
}

beforeEach(() => apiPost.mockReset());

describe("addBreachAttachment", () => {
  it("gives a saved email with no type the one the API checks", async () => {
    await addBreachAttachment(UUID, { file: new File(["From: x"], "tip-off.eml", { type: "" }), kind: "email" });
    const file = sent().get("file") as File;
    expect([file.name, file.type]).toEqual(["tip-off.eml", "message/rfc822"]);
    expect(sent().get("kind")).toBe("email");
    expect(sent().get("note")).toBeNull();
    expect(apiPost.mock.calls[0][0]).toBe(`/breaches/${UUID}/attachments`);
  });

  it("sends a typed file as it is, with its note", async () => {
    await addBreachAttachment(UUID, {
      file: new File(["%PDF"], "proof.pdf", { type: "application/pdf" }),
      kind: "proof",
      note: "  Signed statement  ",
    });
    expect((sent().get("file") as File).type).toBe("application/pdf");
    expect(sent().get("note")).toBe("Signed statement");
  });
});
