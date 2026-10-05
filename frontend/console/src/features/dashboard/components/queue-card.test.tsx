/**
 * A queue row opens what it is about, and a cut-short queue says so (UX review).
 */
import { describe, expect, it } from "vitest";

import { QueueCard } from "@/features/dashboard/components/queue-card";
import { render, screen } from "@/test/render";

describe("QueueCard", () => {
  it("opens the destination the server gave the row, not its project", () => {
    render(
      <QueueCard
        name="Import exceptions"
        items={[
          {
            collection_uuid: "c-1",
            project_uuid: "p-1",
            source_collection_ref: "RUN-7",
            href: "/collections/c-1",
          },
        ]}
      />,
    );
    expect(screen.getByRole("link")).toHaveAttribute("href", "/collections/c-1");
  });

  it("names a site row by its site, with its project beside it", () => {
    render(
      <QueueCard
        name="Sites awaiting a data source"
        items={[{ site_label: "Campus A", project_name: "Gait 2026", project_uuid: "p-2" }]}
      />,
    );
    expect(screen.getByText("Campus A · Gait 2026")).toBeInTheDocument();
  });

  it("does not call a capped queue complete", () => {
    const items = Array.from({ length: 25 }, (_, i) => ({ project_uuid: `p-${i}`, project_name: `P${i}` }));
    render(<QueueCard name="Pending Approval" items={items} capped href="/projects" />);
    expect(screen.getByText("25+")).toBeInTheDocument();
    expect(screen.queryByText(/All 25/)).not.toBeInTheDocument();
  });
});
