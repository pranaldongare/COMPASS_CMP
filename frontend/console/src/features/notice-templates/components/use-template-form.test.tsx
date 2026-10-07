/**
 * Using a notice template on a project (0044): the ID is looked up first and
 * what it carries is shown; then the project's own draft notice is made and
 * opened. An unknown ID says so; a retired template cannot be used.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { UseTemplateForm } from "@/features/notice-templates/components/use-template-form";
import { makeTemplate } from "@/test/notice-templates";
import { render, screen, waitFor } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";

const push = vi.fn();
const PROJECT = "91919191-9191-4191-8191-919191919191";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

describe("UseTemplateForm", () => {
  it("looks the ID up, shows what it carries, and makes the project's notice", async () => {
    const body = vi.fn();
    server.use(
      http.get(`${API}/notice-templates/by-code/TPL-0007`, () =>
        HttpResponse.json(makeTemplate()),
      ),
      http.post(`${API}/projects/${PROJECT}/notices/from-template`, async ({ request }) => {
        body(await request.json());
        return HttpResponse.json(
          { notice_uuid: "81818181-8181-4181-8181-818181818181", notice_code: "NTC-GAIT-2026" },
          { status: 201 },
        );
      }),
    );
    const onDone = vi.fn();
    const { user } = render(<UseTemplateForm projectUuid={PROJECT} onDone={onDone} />);
    const make = screen.getByRole("button", { name: /Make this project's notice/ });
    expect(make).toBeDisabled();

    await user.type(screen.getByLabelText(/Template ID/), "tpl-0007");
    await user.click(screen.getByRole("button", { name: /Look up/ }));
    expect(await screen.findByText(/Gait video studies, adults/)).toBeInTheDocument();
    expect(screen.getByText(/Gait model training/)).toBeInTheDocument();

    await user.click(make);
    await waitFor(() =>
      expect(push).toHaveBeenCalledWith("/notices/81818181-8181-4181-8181-818181818181"),
    );
    expect(body).toHaveBeenCalledWith({ template_code: "TPL-0007" });
    expect(onDone).toHaveBeenCalled();
  });

  it("says when there is no such template", async () => {
    server.use(
      http.get(`${API}/notice-templates/by-code/TPL-9999`, () =>
        errorResponse("not_found", "Notice template not found", 404),
      ),
    );
    const { user } = render(<UseTemplateForm projectUuid={PROJECT} onDone={() => {}} />);
    await user.type(screen.getByLabelText(/Template ID/), "TPL-9999");
    await user.click(screen.getByRole("button", { name: /Look up/ }));
    expect(await screen.findByText(/There is no template TPL-9999/)).toBeInTheDocument();
  });

  it("will not use a retired template", async () => {
    server.use(
      http.get(`${API}/notice-templates/by-code/TPL-0007`, () =>
        HttpResponse.json(makeTemplate({ status: "retired" })),
      ),
    );
    const { user } = render(<UseTemplateForm projectUuid={PROJECT} onDone={() => {}} />);
    await user.type(screen.getByLabelText(/Template ID/), "TPL-0007");
    await user.click(screen.getByRole("button", { name: /Look up/ }));
    expect(await screen.findByText(/has retired this template/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Make this project's notice/ })).toBeDisabled();
  });
});
