/**
 * A saved email or a log often reaches the browser with no type, and Windows
 * with Excel installed calls a .csv Excel's; the API refuses a file whose type
 * it does not accept. So the extension says the type, wherever a breach sends
 * a file, and a file with any other extension is sent as it is.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

const apiPost = vi.fn();
vi.mock("@/lib/api", () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
  queryString: () => "",
  apiPost: (...args: unknown[]) => apiPost(...args),
}));

import {
  addBreachAttachment,
  addBreachDocumentProof,
  changeBreachTicketDate,
  changeMyBreachTicketDate,
  messageBreachHolder,
  messageBreachOffice,
  returnBreachTicket,
} from "@/features/breach/api";

const UUID = "66666666-6666-4666-8666-666666666666";
const OTHER = "77777777-7777-4777-8777-777777777777";
const EXCELS = "application/vnd.ms-excel";
const WORD = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

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

describe("a file's type", () => {
  async function typeOf(name: string, type: string) {
    await addBreachAttachment(UUID, { file: new File(["x"], name, { type }), kind: "other" });
    return (sent().get("file") as File).type;
  }

  it("is the extension's, whatever the browser called it", async () => {
    expect(await typeOf("people.csv", EXCELS)).toBe("text/csv");
    expect(await typeOf("PEOPLE.CSV", EXCELS)).toBe("text/csv");
  });

  it("is read off a Word document, a PDF and a picture too when the browser says nothing", async () => {
    expect(await typeOf("letter.docx", "")).toBe(WORD);
    expect(await typeOf("letter.pdf", "")).toBe("application/pdf");
    expect(await typeOf("photo.jpeg", "")).toBe("image/jpeg");
  });

  it("is left alone on an extension the API does not know", async () => {
    expect(await typeOf("app.exe", "application/x-msdownload")).toBe("application/x-msdownload");
  });

  it("is the same on a ticket's thread, from either side, and on a return", async () => {
    const evidence = new File(["a,b"], "people.csv", { type: EXCELS });
    await messageBreachHolder(UUID, OTHER, { body: "See this", evidence });
    expect((sent().get("evidence") as File).type).toBe("text/csv");
    await messageBreachOffice(OTHER, { body: "See this", evidence });
    expect((sent().get("evidence") as File).type).toBe("text/csv");
    await returnBreachTicket(OTHER, { summary: "Done", outcome: "done", evidence });
    expect((sent().get("evidence") as File).type).toBe("text/csv");
  });

  it("sends a message with no file as words alone", async () => {
    await messageBreachOffice(OTHER, { body: "No file", evidence: null });
    expect(sent().get("evidence")).toBeNull();
  });
});

describe("addBreachDocumentProof", () => {
  it("types a saved email the same way, and says which proof it is", async () => {
    await addBreachDocumentProof(UUID, OTHER, {
      file: new File(["From: x"], "to-the-board.eml", { type: "" }),
      kind: "sent_mail",
    });
    const file = sent().get("file") as File;
    expect([file.name, file.type]).toEqual(["to-the-board.eml", "message/rfc822"]);
    expect(sent().get("kind")).toBe("sent_mail");
    expect(apiPost.mock.calls[0][0]).toBe(`/breaches/${UUID}/reports/${OTHER}/evidence`);
  });
});

describe("moving a breach ticket's date", () => {
  const body = { answer_by: "2030-01-15", reason: "The vendor needs another week" };

  it("posts to the office's ticket and to the holder's own", async () => {
    await changeBreachTicketDate(UUID, OTHER, body);
    expect(apiPost).toHaveBeenLastCalledWith(`/breaches/${UUID}/tickets/${OTHER}/resolve-by`, body);
    await changeMyBreachTicketDate(OTHER, body);
    expect(apiPost).toHaveBeenLastCalledWith(`/breach-tickets/${OTHER}/resolve-by`, body);
  });
});
