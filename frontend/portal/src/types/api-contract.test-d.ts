/**
 * The hand-written types, checked against the generated ones.
 *
 * `src/types/*.ts` is written by hand. That is a deliberate choice — the
 * generated file is 8,800 lines of `components["schemas"]["ProjectOut"]`, which
 * is unreadable at a call site and carries none of the reasoning that makes the
 * hand-written modules worth having. But a hand-written type drifts from the
 * API silently: the server renames a field, every page keeps compiling, and the
 * failure surfaces as an undefined at runtime in front of a user.
 *
 * So this file closes the loop. It contains no runtime code and no assertions
 * in the testing sense — every check here is a *type* assertion, and `tsc` is
 * what runs them. If the API changes shape, `npm run api:types` regenerates the
 * schema, and this file stops compiling.
 *
 * ## When this file fails
 *
 * Read the error, then fix the hand-written type in `src/types/`. It is the one
 * that is wrong: the generated file came from the server's own OpenAPI
 * document, so it is by construction the truth about what the API sends.
 *
 * ## Why assignability, and in this direction
 *
 * The check is `Local extends Generated` — "a value of the hand-written type
 * would satisfy the generated one". That direction is chosen deliberately, and
 * it catches exactly the failures worth catching:
 *
 * * The server **adds a required field** → the local type lacks it → fails.
 * * The server **renames a field** → the local type still has the old name and
 *   lacks the new one → fails.
 * * The server **changes a field's type** incompatibly → fails.
 *
 * while permitting the one difference that is intended: the hand-written types
 * **narrow**. `Me.role` is a union of the five roles the API can return, where
 * the generated type says `string`. That is the point of writing them by hand,
 * and a narrower type is still assignable to a wider one.
 *
 * Exact equality would reject every one of those narrowings, so this file would
 * either be deleted or filled with exceptions until it checked nothing.
 *
 * Assignability alone missed the other half (ARCH-2): a field the server
 * **stopped sending** - an extra local property is still assignable - and a
 * field the server **may now send as null** while the local type says it never
 * is. `Covers` checks both as well, per field, so narrowing stays allowed.
 * (Not "may leave out": the schema marks every field with a default optional,
 * and the API sends those fields every time, so that check would be noise.)
 * A local field that is meant to exist only in the client is named in
 * `Extra`, which says so at the line that declares it.
 */

import type { components } from "@/types/api-schema";
import type {
  Acknowledged,
  ApprovalListRow,
  AuditEntry,
  CollectionListRow,
  ConsentListRow,
  ConsentRow,
  ExportListRow,
  LinkListRow,
  LinkStats,
  LoginResponse,
  Me,
  MeProfile,
  MyBreachNotice,
  NoticeListRow,
  Notice,
  DataSource,
  Processor,
  Project,
  Purpose,
  SiteListRow,
  User,
} from "@/types";

type Schemas = components["schemas"];

/**
 * Assert that `Local` covers every field of `Generated`, compatibly.
 *
 * Resolves to `Generated` when it holds and to a descriptive error type when it
 * does not, so the compiler's message names the type that drifted instead of
 * saying "true is not assignable to false".
 */
type Covers<Name extends string, Generated, Local, Extra extends PropertyKey = never> = [
  Local extends Generated ? true : false,
  Exclude<keyof Local, keyof Generated | Extra>,
  NullGaps<Generated, Local>,
] extends [true, never, never]
  ? true
  : {
      error: `${Name} has drifted from the API`;
      notAssignable: Local extends Generated ? never : { expected: Generated; got: Local };
      /** Fields the local type has and the server no longer sends. */
      noLongerSent: Exclude<keyof Local, keyof Generated | Extra>;
      /** Fields the server may send as null that the local type says cannot be. */
      mayBeNull: NullGaps<Generated, Local>;
    };

/**
 * The fields of `Local` the server may send as null where `Local` says they
 * cannot be. Checked per field rather than by assigning the whole generated
 * type to the local one, which would reject every intended narrowing.
 */
type NullGaps<Generated, Local> = {
  [K in keyof Generated & keyof Local]-?: unknown extends Generated[K]
    ? never // the schema does not say: an untyped field cannot be judged
    : null extends Generated[K]
      ? null extends Local[K]
        ? never
        : K
      : never;
}[keyof Generated & keyof Local];

// Each line is one type. A drift turns the right-hand side into the error
// object above, and `true` stops being assignable.
export type _Me = Covers<"Me", Schemas["MeResponse"], Me>;
export type _MeProfile = Covers<"MeProfile", Schemas["MeProfile"], MeProfile>;
export type _LoginResponse = Covers<
  "LoginResponse",
  Schemas["LoginResponse"],
  LoginResponse
>;
export type _Acknowledged = Covers<"Acknowledged", Schemas["Acknowledged"], Acknowledged>;

export type _Project = Covers<"Project", Schemas["ProjectOut"], Project>;
export type _Site = Covers<"Site", Schemas["SiteListRow"], SiteListRow>;
export type _ApprovalListRow = Covers<
  "ApprovalListRow",
  Schemas["ApprovalListRow"],
  ApprovalListRow
>;

export type _Notice = Covers<"Notice", Schemas["NoticeOut"], Notice>;
export type _NoticeListRow = Covers<
  "NoticeListRow",
  Schemas["NoticeListRow"],
  NoticeListRow
>;

// `is_mandatory` and `display_order` come with a purpose read through a
// notice (`PurposeOnNotice`), not from the registry: named, not ignored.
export type _Purpose = Covers<
  "Purpose",
  Schemas["PurposeOut"],
  Purpose,
  "is_mandatory" | "display_order"
>;
export type _Processor = Covers<"Processor", Schemas["ProcessorOut"], Processor>;
// Absent until a field the API returns silently stopped arriving: the column
// was joined and selected, the response model did not declare it, and the
// payload lost it with nothing failing anywhere.
export type _DataSource = Covers<"DataSource", Schemas["SourceOut"], DataSource>;

export type _ConsentRow = Covers<"ConsentRow", Schemas["ConsentRow"], ConsentRow>;
export type _ConsentListRow = Covers<
  "ConsentListRow",
  Schemas["ConsentListRow"],
  ConsentListRow
>;
export type _LinkListRow = Covers<"LinkListRow", Schemas["LinkListRow"], LinkListRow>;
export type _LinkStats = Covers<"LinkStats", Schemas["LinkStats"], LinkStats>;

export type _ExportListRow = Covers<
  "ExportListRow",
  Schemas["ExportListRow"],
  ExportListRow
>;
export type _CollectionListRow = Covers<
  "CollectionListRow",
  Schemas["CollectionListRow"],
  CollectionListRow
>;

export type _AuditEntry = Covers<"AuditEntry", Schemas["AuditEntry"], AuditEntry>;
export type _User = Covers<"User", Schemas["UserOut"], User>;
// A breach notice in her account (S3-03).
export type _MyBreachNotice = Covers<"MyBreachNotice", Schemas["MyBreachNoticeOut"], MyBreachNotice>;

/**
 * The check itself.
 *
 * Every entry above has to be `true`. One that has drifted is the error object,
 * which is not assignable, and the compiler names it.
 */
const _contractHolds: {
  Me: _Me;
  MeProfile: _MeProfile;
  LoginResponse: _LoginResponse;
  Acknowledged: _Acknowledged;
  Project: _Project;
  SiteListRow: _Site;
  ApprovalListRow: _ApprovalListRow;
  Notice: _Notice;
  NoticeListRow: _NoticeListRow;
  Purpose: _Purpose;
  Processor: _Processor;
  DataSource: _DataSource;
  ConsentRow: _ConsentRow;
  ConsentListRow: _ConsentListRow;
  LinkListRow: _LinkListRow;
  LinkStats: _LinkStats;
  ExportListRow: _ExportListRow;
  CollectionListRow: _CollectionListRow;
  AuditEntry: _AuditEntry;
  User: _User;
  MyBreachNotice: _MyBreachNotice;
} = {
  Me: true,
  MeProfile: true,
  LoginResponse: true,
  Acknowledged: true,
  Project: true,
  SiteListRow: true,
  ApprovalListRow: true,
  Notice: true,
  NoticeListRow: true,
  Purpose: true,
  Processor: true,
  DataSource: true,
  ConsentRow: true,
  ConsentListRow: true,
  LinkListRow: true,
  LinkStats: true,
  ExportListRow: true,
  CollectionListRow: true,
  AuditEntry: true,
  User: true,
  MyBreachNotice: true,
};

void _contractHolds;

/**
 * The check catches what the server takes away, not only what it adds
 * (review 2026-10-01, ARCH-2).
 *
 * `Local extends Generated` alone let a local type keep a field the server had
 * stopped sending - an extra property is still assignable - and keep calling
 * a field non-null after the server began sending null. A probe removed
 * `SourceOut.is_in_house` from the generated schema and this file stayed
 * silent. These two must stay errors; if either compiles, the check has been
 * weakened.
 */
type _Removed = Covers<"Removed", { kept: string }, { kept: string; gone: boolean }>;
// @ts-expect-error - `gone` is no longer sent, so the check must not hold.
const _removalIsCaught: _Removed = true;

type _NowNullable = Covers<"NowNullable", { name: string | null }, { name: string }>;
// @ts-expect-error - the server may send null where the local type says string.
const _nullIsCaught: _NowNullable = true;

// Narrowing stays allowed: a union of the roles where the API says string.
type _Narrowed = Covers<"Narrowed", { role: string }, { role: "dpo" | "admin" }>;
const _narrowingIsAllowed: _Narrowed = true;

void _removalIsCaught;
void _nullIsCaught;
void _narrowingIsAllowed;
