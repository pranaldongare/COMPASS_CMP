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
    expect(breaches.className).toContain("border-warning-border");
    expect(screen.getByRole("link", { name: /Open rights requests/ })).toHaveTextContent(
      "3 due within 7 days",
    );
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("leaves out a figure the server did not send, and a role it does not know", () => {
    const { unmount } = render(<KpiRow role="dco" counts={{ approved_projects: 1, consents: 2 }} />);
    expect(screen.getAllByRole("link")).toHaveLength(2);
    unmount();
    const { container } = render(<KpiRow role="data_subject" counts={{ x: 1 }} />);
    expect(container).toBeEmptyDOMElement();
  });
});
