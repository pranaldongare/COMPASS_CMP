/**
 * The words of every message the platform sends.
 *
 * One card per junction, grouped by what the message is about: signing in,
 * consent, rights, staff. Each card is the editor for that message on each of
 * its channels. The list comes from the server and is complete by
 * construction: the code cannot send a message that is not a junction, so a
 * message added later appears here on the day it lands, with its variables
 * and its default words.
 *
 * Reachable by the administrator and the DPO. Everyone else receives these
 * words; these two roles choose them.
 */
"use client";

import { MessageSquareText } from "lucide-react";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Skeleton,
} from "@/components/ui/primitives";
import { useMessages } from "@/features/messages";
import { MessageEditor } from "@/features/messages/components/message-editor";
import type { MessageTemplate } from "@/types";

export default function MessagesPage() {
  const messages = useMessages();

  const groups = React.useMemo(() => {
    const order: string[] = [];
    const byGroup = new Map<string, MessageTemplate[]>();
    for (const m of messages.data ?? []) {
      if (!byGroup.has(m.group)) {
        order.push(m.group);
        byGroup.set(m.group, []);
      }
      byGroup.get(m.group)!.push(m);
    }
    return order.map((g) => ({ group: g, items: byGroup.get(g) ?? [] }));
  }, [messages.data]);

  return (
    <>
      <PageHeader
        eyebrow="Oversight"
        title="Messages"
        description="The words of every email and SMS the platform sends. Change them here; the default is what goes out until you do, and is one click away if you change your mind."
      />

      <Alert tone="info" className="mb-6">
        Placeholders such as <code className="font-mono">{"{code}"}</code> are filled in
        when a message is sent. Each message lists the ones it provides; a save that names
        any other is refused. Email and SMS are edited separately, because a phone screen is
        not an inbox.
      </Alert>

      {messages.isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : messages.isError ? (
        <Alert tone="danger" title="Could not load the messages">
          {messages.error.userMessage()}
        </Alert>
      ) : (
        <div className="space-y-8">
          {groups.map(({ group, items }) => (
            <section key={group} aria-labelledby={`group-${group}`}>
              <h2
                id={`group-${group}`}
                className="mb-3 flex items-center gap-2 text-sm font-semibold tracking-wide text-text-muted uppercase"
              >
                <MessageSquareText className="size-4" aria-hidden="true" />
                {group}
              </h2>
              <div className="space-y-4">
                {items.map((m) => (
                  <Card key={m.key} id={`message-${m.key}`}>
                    <CardHeader>
                      <CardTitle>{m.title}</CardTitle>
                      <p className="mt-1 text-sm text-text-muted">{m.description}</p>
                    </CardHeader>
                    <CardBody>
                      <MessageEditor message={m} />
                    </CardBody>
                  </Card>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </>
  );
}
