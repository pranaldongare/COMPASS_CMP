/**
 * The dashboard's four figures (2026-10-10): per role, from the counts the
 * server sent, each a link; amber when something is late.
 */
import { describe, expect, it, vi } from "vitest";

import { KpiRow } from "@/features/dashboard/components/kpi-row";
import { render, screen } from "@/test/render";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

describe("KpiRow", () => {
  it("shows the DPO's four figures, each linked, late breach duties in amber", () => {
    render(
      <KpiRow
        role="dpo"
        counts={{
          requests_open: 147,
          requests_overdue: 0,
          requests_due_7d: 3,
          open_breaches: 90,
          breach_duties_late: 143,
          total_consents: 190,
          withdrawals: 23,
          pending_approval: 2,
        }}
      />,
    );
    const breaches = screen.getByRole("link", { name: /Open breaches/ });
    expect(breaches).toHaveAttribute("href", "/breaches");
    expect(breaches).toHaveTextContent("143 duties late");
    // Late duties: the amber edge (2026-10-10: an inset top edge, not a border).
    expect(breaches.className).toContain("var(--warning)");
    expect(screen.getByRole("link", { name: /Open rights requests/ })).toHaveTextContent(
      "3 due within 7 days",
    );
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("shows the Legal PoC its office's requests, with the shared intake to claim", () => {
    render(
      <KpiRow
        role="legal"
        counts={{
          requests_open: 4,
          requests_in_intake: 2,
          requests_overdue: 0,
          open_breaches: 1,
          breach_duties_late: 0,
          activities_live: 3,
          total_consents: 40,
          versions_in_draft: 1,
        }}
      />,
    );
    expect(screen.getByRole("link", { name: /Open rights requests/ })).toHaveTextContent(
      "2 in the shared intake",
    );
    expect(screen.getByRole("link", { name: /Live activities/ })).toHaveTextContent("40 consents");
    expect(screen.getByRole("link", { name: /Template versions in draft/ })).toHaveTextContent(
      "to approve",
    );
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("warns an HR PoC of a link about to stop taking consent", () => {
    render(
      <KpiRow
        role="hr_user"
        counts={{ activities_live: 2, consents: 9, withdrawals_7d: 1, links_expiring_7d: 1, tickets_for_me: 0 }}
      />,
    );
    const ending = screen.getByRole("link", { name: /Activity links ending within 7 days/ });
    expect(ending).toHaveTextContent("extend or let close");
    expect(ending.className).toContain("var(--warning)");
    expect(screen.getByRole("link", { name: /Consents/ })).toHaveTextContent("1 withdrawn this week");
  });

  it("leaves out a figure the server did not send, and a role it does not know", () => {
    const { unmount } = render(
      <KpiRow role="dco" counts={{ approved_projects: 1, consents: 2 }} />,
    );
    expect(screen.getAllByRole("link")).toHaveLength(2);
    unmount();
    const { container } = render(<KpiRow role="data_subject" counts={{ x: 1 }} />);
    expect(container).toBeEmptyDOMElement();
  });
});
