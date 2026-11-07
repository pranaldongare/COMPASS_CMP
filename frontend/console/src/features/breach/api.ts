/**
 * Every request the breach register makes (S3-01).
 *
 * The DPO's alone; any other role is answered 404 by the server. Nothing here
 * talks to a regulator: a person sends, and files it here with the proof and
 * the reference the regulator returned.
 */

import { apiDelete, apiDownload, apiGet, apiPost, apiPut, queryString } from "@/lib/api";
import { config } from "@/lib/config";
import type {
  BreachAttachmentKind,
  Breach,
  BreachAffected,
  BreachContacts,
  BreachListKind,
  BreachListReport,
  BreachAssessment,
  BreachAssessmentInput,
  BreachBoardList,
  BreachDocumentFinalise,
  BreachDocumentKind,
  BreachDocuments,
  BreachDocumentsResent,
  BreachInput,
  BreachNoticeWords,
  BreachNotices,
  BreachOutcome,
  BreachPreview,
  BreachProjectOption,
  BreachScope,
  BreachSettings,
  BreachStatus,
  BreachSummary,
  BreachTicket,
  BreachTicketDetail,
  DismissedReport,
  IncidentReport,
  IncidentReportPage,
  MyBreachTicket,
  MyBreachTicketDetail,
  ReturnOutcome,
  Timestamp,
  Uuid,
} from "@/types";

export function listBreaches(status?: BreachStatus): Promise<BreachSummary[]> {
  return apiGet<BreachSummary[]>(`/breaches${queryString({ status })}`);
}

export function getBreach(uuid: Uuid): Promise<Breach> {
  return apiGet<Breach>(`/breaches/${uuid}`);
}

export function recordBreach(body: BreachInput): Promise<Breach> {
  return apiPost<Breach>("/breaches", body);
}

export function determineBreach(
  uuid: Uuid,
  body: { outcome: BreachOutcome; reasoning: string; became_aware_at?: Timestamp | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/determinations`, body);
}

export function listAssessments(uuid: Uuid): Promise<BreachAssessment[]> {
  return apiGet<BreachAssessment[]>(`/breaches/${uuid}/assessments`);
}

export function assessBreach(uuid: Uuid, body: BreachAssessmentInput): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/assessments`, body);
}

export function markCertIn(uuid: Uuid): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/cert-in`, {});
}

/** A mark made in error, whatever validation says. Mails nobody. */
export function setAsideCertIn(uuid: Uuid, reason: string): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/cert-in/not-applicable`, { reason });
}

export function extendReport(
  uuid: Uuid,
  body: {
    requested_at: Timestamp;
    allowed_until: Timestamp;
    reference?: string | null;
    note?: string | null;
  },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/obligations/board_report/extension`, body);
}

export function transitionBreach(
  uuid: Uuid,
  body: { to: BreachStatus; reason?: string | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/transition`, body);
}

/* ------------------------------------------- the shared intake (0058) */

export function listIncidentReports(page: { limit: number; offset: number }): Promise<IncidentReportPage> {
  return apiGet<IncidentReportPage>(`/breaches/intake${queryString(page)}`);
}

/** One waiting report in full. Refused once an office has taken it up. */
export function getIncidentReport(reportUuid: Uuid): Promise<IncidentReport> {
  return apiGet<IncidentReport>(`/breaches/intake/${reportUuid}`);
}

export function listDismissedReports(): Promise<DismissedReport[]> {
  return apiGet<DismissedReport[]>("/breaches/intake/dismissed");
}

export function claimIncidentReport(reportUuid: Uuid): Promise<Breach> {
  return apiPost<Breach>(`/breaches/intake/${reportUuid}/claim`, {});
}

export function dismissIncidentReport(reportUuid: Uuid, reason: string): Promise<unknown> {
  return apiPost(`/breaches/intake/${reportUuid}/dismiss`, { reason });
}

/* ------------------------------------------------- who hears of it (0058) */

export function getBreachSettings(): Promise<BreachSettings> {
  return apiGet<BreachSettings>("/breach-settings");
}

export function setIntakeRoles(roles: string[]): Promise<BreachSettings> {
  return apiPut<BreachSettings>("/breach-settings/intake-roles", { roles });
}

export function addBoardRecipient(body: {
  full_name?: string | null;
  email: string;
}): Promise<BreachSettings> {
  return apiPost<BreachSettings>("/breach-settings/board-recipients", body);
}

export function removeBoardRecipient(recipientUuid: Uuid): Promise<BreachSettings> {
  return apiDelete<BreachSettings>(`/breach-settings/board-recipients/${recipientUuid}`);
}

/** Mandatory goes with every report and cannot be taken off the list until it
 *  is optional again. Every change is mailed to the DPO and the Legal PoC. */
export function setBoardRecipientMandatory(recipientUuid: Uuid, mandatory: boolean): Promise<BreachSettings> {
  return apiPut<BreachSettings>(`/breach-settings/board-recipients/${recipientUuid}/mandatory`, { mandatory });
}

/* ------------------------------------------- the people affected (S3-02) */

export function listAffected(uuid: Uuid, cursor?: string | null): Promise<BreachAffected> {
  return apiGet<BreachAffected>(`/breaches/${uuid}/affected${queryString({ cursor })}`);
}

export function affectedOptions(uuid: Uuid): Promise<{ projects: BreachProjectOption[] }> {
  return apiGet<{ projects: BreachProjectOption[] }>(`/breaches/${uuid}/affected/options`);
}

export function previewAffected(uuid: Uuid, scopes: BreachScope[]): Promise<BreachPreview> {
  return apiPost<BreachPreview>(`/breaches/${uuid}/affected/preview`, { scopes });
}

/* ------------------------------------- a list somebody sends us (2026-10-07) */

/** The Excel file to fill in, as a file to save. */
export function breachListTemplate(uuid: Uuid, kind: BreachListKind) {
  return apiDownload(`/breaches/${uuid}/affected/upload/template${queryString({ kind })}`);
}

const XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

function listForm(kind: BreachListKind, file: File): FormData {
  // A browser that does not type a file sends it untyped; the API checks the type.
  const type = file.name.toLowerCase().endsWith(".xlsx") ? XLSX : "text/csv";
  const typed = file.type ? file : new File([file], file.name, { type });
  const form = new FormData();
  form.set("kind", kind);
  form.set("file", typed, typed.name);
  return form;
}

/** What a list would add, and each row it cannot read. Writes nothing. */
export function checkBreachList(
  uuid: Uuid,
  kind: BreachListKind,
  file: File,
): Promise<BreachListReport> {
  return apiPost<BreachListReport>(`/breaches/${uuid}/affected/upload/check`, listForm(kind, file));
}

/** Add what a list names to the breach's list. */
export function takeBreachList(
  uuid: Uuid,
  kind: BreachListKind,
  file: File,
): Promise<BreachListReport> {
  return apiPost<BreachListReport>(`/breaches/${uuid}/affected/upload`, listForm(kind, file));
}

/** People affected who have no account, and the lists they came in. */
export function listBreachContacts(uuid: Uuid, cursor?: string | null): Promise<BreachContacts> {
  return apiGet<BreachContacts>(`/breaches/${uuid}/affected/contacts${queryString({ cursor })}`);
}

export function confirmAffected(
  uuid: Uuid,
  body: { scopes: BreachScope[]; exclude: Uuid[]; add: Uuid[]; note?: string | null },
): Promise<BreachAffected> {
  return apiPost<BreachAffected>(`/breaches/${uuid}/affected`, body);
}

/* ---------------------------------------------- telling the people (S3-03) */

export function getNotices(uuid: Uuid): Promise<BreachNotices> {
  return apiGet<BreachNotices>(`/breaches/${uuid}/notices`);
}

export function draftNotice(uuid: Uuid, words: Partial<BreachNoticeWords>): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices`, words);
}

export function editNotice(
  uuid: Uuid,
  noticeUuid: Uuid,
  words: Partial<BreachNoticeWords>,
): Promise<BreachNotices> {
  return apiPut<BreachNotices>(`/breaches/${uuid}/notices/${noticeUuid}`, words);
}

export function approveNotice(uuid: Uuid, noticeUuid: Uuid): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices/${noticeUuid}/approve`, {});
}

export function sendNotice(uuid: Uuid): Promise<BreachNotices> {
  return apiPost<BreachNotices>(`/breaches/${uuid}/notices/send`, {});
}

/* -------------------------------------------- reports on a breach (0059) */

const reports = (uuid: Uuid) => `/breaches/${uuid}/reports`;

export function getBreachDocuments(uuid: Uuid): Promise<BreachDocuments> {
  return apiGet<BreachDocuments>(reports(uuid));
}

export function draftBreachDocument(uuid: Uuid, kind: BreachDocumentKind): Promise<BreachDocuments> {
  return apiPost<BreachDocuments>(reports(uuid), { kind });
}

export function editBreachDocument(
  uuid: Uuid,
  reportUuid: Uuid,
  sections: Record<string, string | null>,
): Promise<BreachDocuments> {
  return apiPut<BreachDocuments>(`${reports(uuid)}/${reportUuid}`, { sections });
}

/** The organisation's board list as the finalise window offers it: names and
 *  addresses, and which are mandatory. Read only while the window is open. */
export function getBreachBoardList(uuid: Uuid): Promise<BreachBoardList> {
  return apiGet<BreachBoardList>(`${reports(uuid)}/recipients`);
}

/** Freezes it and mails the board to whoever is chosen; a report to CERT-In
 *  before the first yes is held for it. Never a regulator. */
export function finaliseBreachDocument(
  uuid: Uuid,
  reportUuid: Uuid,
  body: BreachDocumentFinalise,
): Promise<BreachDocuments> {
  return apiPost<BreachDocuments>(`${reports(uuid)}/${reportUuid}/finalise`, body);
}

/** To those this version went to and has not reached; never anyone added to
 *  the list since. */
export function resendBreachDocument(uuid: Uuid, reportUuid: Uuid): Promise<BreachDocumentsResent> {
  return apiPost<BreachDocumentsResent>(`${reports(uuid)}/${reportUuid}/resend`, {});
}

/** Keep the proof of internal approval, or of the mail sent to the regulator. */
export function addBreachDocumentProof(
  uuid: Uuid,
  reportUuid: Uuid,
  input: { file: File; kind: "approval" | "sent_mail" },
): Promise<BreachDocuments> {
  return apiPost<BreachDocuments>(
    `${reports(uuid)}/${reportUuid}/evidence`,
    evidenceForm(input.file, input.kind),
  );
}

export function fileBreachDocument(
  uuid: Uuid,
  reportUuid: Uuid,
  body: { filed_at: Timestamp; reference?: string | null },
): Promise<BreachDocuments> {
  return apiPost<BreachDocuments>(`${reports(uuid)}/${reportUuid}/file`, body);
}

export function breachDocumentPdf(uuid: Uuid, reportUuid: Uuid) {
  return apiDownload(`${reports(uuid)}/${reportUuid}/pdf`);
}

/* -------------------------------------------------- breach tickets (S3-08) */

export interface TicketMessageInput {
  body: string;
  evidence: File | null;
}

function messageForm(input: TicketMessageInput): FormData {
  const form = new FormData();
  form.set("body", input.body);
  if (input.evidence) form.set("evidence", typedFile(input.evidence));
  return form;
}

const tickets = (uuid: Uuid) => `/breaches/${uuid}/tickets`;

/** The type the API checks, read off the extension. A browser often leaves it
 *  blank for a saved email or a log, and Windows with Excel installed calls a
 *  .csv Excel's, so for these the extension has the last word. */
const TYPE_BY_EXTENSION: Record<string, string> = {
  pdf: "application/pdf",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  eml: "message/rfc822",
  msg: "application/vnd.ms-outlook",
  txt: "text/plain",
  log: "text/plain",
  csv: "text/csv",
  docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
};

function typedFile(file: File): File {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  const type = TYPE_BY_EXTENSION[ext];
  return type && type !== file.type ? new File([file], file.name, { type }) : file;
}

/** Keep a file with the incident (2026-10-06): an email, a proof, a chat. */
export function addBreachAttachment(
  uuid: Uuid,
  input: { file: File; kind: BreachAttachmentKind; note?: string | null },
): Promise<Breach> {
  return apiPost<Breach>(`/breaches/${uuid}/attachments`, evidenceForm(input.file, input.kind, input.note));
}

function evidenceForm(file: File, kind: string, note?: string | null): FormData {
  const typed = typedFile(file);
  const form = new FormData();
  form.set("file", typed, typed.name);
  form.set("kind", kind);
  if (note?.trim()) form.set("note", note.trim());
  return form;
}

/** Where a file kept with an incident is downloaded; every download is audited. */
export const breachAttachmentUrl = (uuid: Uuid, attachmentUuid: Uuid) =>
  `${config.apiUrl}/breaches/${uuid}/attachments/${attachmentUuid}`;

export function listBreachTickets(uuid: Uuid): Promise<BreachTicket[]> {
  return apiGet<BreachTicket[]>(tickets(uuid));
}

/** Somebody named by an address rather than picked (S3-09): the server finds
 *  their account, or makes a breach-only login for them. */
export interface PersonByEmail {
  full_name: string;
  email: string;
  mobile?: string | null;
}

export function assignBreachTicket(
  uuid: Uuid,
  body: ({ user_uuid: Uuid } | PersonByEmail) & { instruction: string; answer_by?: string | null },
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(tickets(uuid), body);
}

export function getBreachTicket(uuid: Uuid, ticketUuid: Uuid): Promise<BreachTicketDetail> {
  return apiGet<BreachTicketDetail>(`${tickets(uuid)}/${ticketUuid}`);
}

export function messageBreachHolder(
  uuid: Uuid,
  ticketUuid: Uuid,
  input: TicketMessageInput,
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(`${tickets(uuid)}/${ticketUuid}/messages`, messageForm(input));
}

/** send_back, close, withdraw or reopen: the path is the move, hyphenated. */
export function moveBreachTicket(
  uuid: Uuid,
  ticketUuid: Uuid,
  move: "send_back" | "close" | "withdraw" | "reopen",
  reason?: string,
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(
    `${tickets(uuid)}/${ticketUuid}/${move.replace("_", "-")}`,
    move === "close" ? {} : { reason },
  );
}

/** Move the date to resolve it by, saying why: on the thread and the trail. */
export function changeBreachTicketDate(
  uuid: Uuid,
  ticketUuid: Uuid,
  body: { answer_by: string; reason: string },
): Promise<BreachTicketDetail> {
  return apiPost<BreachTicketDetail>(`${tickets(uuid)}/${ticketUuid}/resolve-by`, body);
}

/** Where the office downloads a file on a ticket's thread. */
export const breachTicketFileUrl = (uuid: Uuid, ticketUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}${tickets(uuid)}/${ticketUuid}/messages/${messageUuid}/evidence`;

export function myBreachTickets(): Promise<MyBreachTicket[]> {
  return apiGet<MyBreachTicket[]>("/breach-tickets");
}

export function myBreachTicket(ticketUuid: Uuid): Promise<MyBreachTicketDetail> {
  return apiGet<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}`);
}

export function messageBreachOffice(ticketUuid: Uuid, input: TicketMessageInput): Promise<MyBreachTicketDetail> {
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/messages`, messageForm(input));
}

export function returnBreachTicket(
  ticketUuid: Uuid,
  input: { summary: string; outcome: ReturnOutcome; evidence: File | null },
): Promise<MyBreachTicketDetail> {
  const form = new FormData();
  form.set("summary", input.summary);
  form.set("outcome", input.outcome);
  if (input.evidence) form.set("evidence", typedFile(input.evidence));
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/return`, form);
}

export function changeMyBreachTicketDate(
  ticketUuid: Uuid,
  body: { answer_by: string; reason: string },
): Promise<MyBreachTicketDetail> {
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/resolve-by`, body);
}

/** A holder brings in a colleague, who gets their own ticket (S3-09). The
 *  answer is the adder's own ticket, whatever happened to the colleague's
 *  account. */
export function addBreachColleague(
  ticketUuid: Uuid,
  body: PersonByEmail & { note: string },
): Promise<MyBreachTicketDetail> {
  return apiPost<MyBreachTicketDetail>(`/breach-tickets/${ticketUuid}/colleagues`, body);
}

/** Where a holder downloads a file on their breach ticket's thread. */
export const myBreachTicketFileUrl = (ticketUuid: Uuid, messageUuid: Uuid) =>
  `${config.apiUrl}/breach-tickets/${ticketUuid}/messages/${messageUuid}/evidence`;
