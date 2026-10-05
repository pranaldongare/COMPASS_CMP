/**
 * The four lines a request page opens on (UX review 2026-10-05): when it is
 * due, where it is, who has it, and the next move or what stops it.
 */

import { describe, expect, it } from "vitest";

import { RequestSummary } from "@/features/rights/components/request-summary";
import { makeClock, makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";

describe("RequestSummary", () => {
  it("leads with the due date, the days left and the next checkpoint", () => {
    render(<RequestSummary request={makeRequestDetail()} actionsHref="#actions" />);

    expect(screen.getByText("Due")).toBeInTheDocument();
    expect(screen.getByText(/90 days left/)).toBeInTheDocument();
    expect(screen.getByText(/next: acknowledge by/i)).toBeInTheDocument();
    expect(screen.getByText("Data Protection Officer")).toBeInTheDocument();
  });

  it("says overdue in so many words", () => {
    render(
      <RequestSummary
        request={makeRequestDetail({
          clock: makeClock({ overdue: true, days_remaining: -3 }),
        })}
        actionsHref="#actions"
      />,
    );

    expect(screen.getByText(/overdue by 3 days/i)).toBeInTheDocument();
  });

  it("points the next move at the controls that make it", () => {
    render(
      <RequestSummary
        request={makeRequestDetail({
          transitions: [{ to: "in_progress", allowed: true, via: "transition" }],
        })}
        actionsHref="#actions"
      />,
    );

    expect(screen.getByRole("link", { name: /move to in progress/i })).toHaveAttribute(
      "href",
      "#actions",
    );
  });

  it("names what blocks the next move when nothing is open", () => {
    render(
      <RequestSummary
        request={makeRequestDetail({
          transitions: [
            {
              to: "closed",
              allowed: false,
              via: "respond",
              blocked_by: "Two holders have not returned their tickets",
            },
          ],
        })}
        actionsHref="#actions"
      />,
    );

    expect(screen.getByRole("link", { name: /respond and close/i })).toBeInTheDocument();
    expect(
      screen.getByText("Two holders have not returned their tickets"),
    ).toBeInTheDocument();
  });

  it("does not put a complaint about the DPO with the DPO", () => {
    render(
      <RequestSummary
        request={makeRequestDetail({ request_type: "grievance", about_dpo: true })}
        actionsHref="#actions"
      />,
    );

    expect(screen.queryByText("Data Protection Officer")).not.toBeInTheDocument();
    expect(screen.getByText("Nobody yet")).toBeInTheDocument();
    expect(screen.getByText(/an administrator names a reviewer/i)).toBeInTheDocument();
  });

  it("shows how it ended once closed", () => {
    render(
      <RequestSummary
        request={makeRequestDetail({
          status: "closed",
          outcome: "complete",
          closed_at: "2026-10-01T09:00:00+05:30",
        })}
        actionsHref="#actions"
      />,
    );

    expect(screen.getAllByText("Closed").length).toBeGreaterThan(0);
    expect(screen.getByText("Complete")).toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});
