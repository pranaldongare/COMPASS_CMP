--
-- PostgreSQL database dump
--

\restrict unFgVPf0byVBjujp72hF1EEPO4qjyTYMEFlLYfipX5CiEBNddX1VrRJpaAZ6h2Y

-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: action_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.action_type AS ENUM (
    'checkbox_click',
    'button_press',
    'signature'
);


--
-- Name: approval_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.approval_type AS ENUM (
    'security',
    'legal',
    'other'
);


--
-- Name: asset_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.asset_type AS ENUM (
    'image',
    'video',
    'audio',
    'sensor',
    'document',
    'other'
);


--
-- Name: batch_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.batch_status AS ENUM (
    'received',
    'validating',
    'accepted',
    'partial',
    'rejected'
);


--
-- Name: change_class; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.change_class AS ENUM (
    'material',
    'superficial'
);


--
-- Name: disposition; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.disposition AS ENUM (
    'active',
    'redacted',
    'erased',
    'quarantined'
);


--
-- Name: erasure_trigger; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.erasure_trigger AS ENUM (
    'withdrawal',
    'purpose_served',
    'period_elapsed',
    'inactivity'
);


--
-- Name: exchange_mode; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.exchange_mode AS ENUM (
    'file_export',
    'file_import',
    'manual_upload',
    'api'
);


--
-- Name: export_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.export_type AS ENUM (
    'collection_pack',
    'consented_list',
    'project_export'
);


--
-- Name: TYPE export_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.export_type IS 'project_export is the only reachable value. collection_pack and consented_list are retained because export_log rows name them, and an export is a disclosure record: rewriting what it says was disclosed would falsify the table that exists to be trusted.';


--
-- Name: language_code; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language_code AS ENUM (
    'english',
    'hindi',
    'marathi',
    'tamil',
    'telugu',
    'kannada',
    'bengali',
    'gujarati'
);


--
-- Name: lapse_behaviour; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lapse_behaviour AS ENUM (
    'quarantine',
    'erase',
    'none'
);


--
-- Name: lawful_basis; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lawful_basis AS ENUM (
    'consent_s6',
    'legitimate_use_s7'
);


--
-- Name: link_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.link_status AS ENUM (
    'active',
    'expired',
    'revoked'
);


--
-- Name: nomination_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.nomination_status AS ENUM (
    'pending',
    'active',
    'declined',
    'revoked'
);


--
-- Name: notice_audience; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notice_audience AS ENUM (
    'data_subject',
    'employee',
    'ex_employee',
    'others'
);


--
-- Name: TYPE notice_audience; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.notice_audience IS 'Who a notice is written for. Deliberately separate from person_type: that records what somebody *is*, this records who a document *addresses*, and the two answer different questions even where the words overlap.';


--
-- Name: notice_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.notice_status AS ENUM (
    'draft',
    'approved',
    'published',
    'superseded'
);


--
-- Name: person_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.person_type AS ENUM (
    'external',
    'employee',
    'ex_employee',
    'vendor'
);


--
-- Name: processor_request_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.processor_request_status AS ENUM (
    'pending',
    'approved',
    'rejected'
);


--
-- Name: TYPE processor_request_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.processor_request_status IS 'Where a project-to-processor link stands. Only ''approved'' counts as one of the project''s processors - a pending one is a request, not a collector.';


--
-- Name: processor_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.processor_type AS ENUM (
    'lab',
    'tool',
    'other'
);


--
-- Name: project_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.project_status AS ENUM (
    'in_draft',
    'under_process',
    'pending_approval',
    'approved',
    'closed'
);


--
-- Name: TYPE project_status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TYPE public.project_status IS 'in_draft covers assembly and revision. under_process is retained for historical rows in project_status_history and is unreachable: no transition names it. See cmp.domain.projects.state_machine.';


--
-- Name: purpose_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.purpose_status AS ENUM (
    'draft',
    'pending_approval',
    'active',
    'retired'
);


--
-- Name: record_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.record_status AS ENUM (
    'active',
    'suspended',
    'terminated'
);


--
-- Name: retention_basis; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.retention_basis AS ENUM (
    'statutory',
    'contractual',
    'business_policy'
);


--
-- Name: rights_holder_source; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_holder_source AS ENUM (
    'export_line',
    'asset_consent',
    'manual'
);


--
-- Name: rights_item_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_item_state AS ENUM (
    'proposed',
    'decided',
    'instructed',
    'applied'
);


--
-- Name: rights_request_channel; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_request_channel AS ENUM (
    'portal',
    'public_form',
    'staff_logged',
    'nominee'
);


--
-- Name: rights_request_outcome; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_request_outcome AS ENUM (
    'complete',
    'partial',
    'no_records',
    'refused',
    'not_verified',
    'reclassified_withdrawal',
    'upheld',
    'not_upheld'
);


--
-- Name: rights_request_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_request_status AS ENUM (
    'received',
    'in_progress',
    'awaiting_holders',
    'collating',
    'closed'
);


--
-- Name: rights_request_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_request_type AS ENUM (
    'access',
    'correction',
    'erasure',
    'grievance'
);


--
-- Name: rights_scope_decision; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_scope_decision AS ENUM (
    'erase',
    'redact',
    'retain',
    'quarantine'
);


--
-- Name: rights_ticket_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_ticket_status AS ENUM (
    'pending',
    'issued',
    'escalated',
    'returned',
    'unreturned',
    'withdrawn'
);


--
-- Name: rights_trigger_event; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_trigger_event AS ENUM (
    'death',
    'incapacity'
);


--
-- Name: rights_verification_method; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_verification_method AS ENUM (
    'session',
    'code',
    'manual'
);


--
-- Name: rights_verification_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.rights_verification_status AS ENUM (
    'pending',
    'verified',
    'failed'
);


--
-- Name: s7_clause; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.s7_clause AS ENUM (
    's7_a_voluntary',
    's7_i_employment',
    's7_other'
);


--
-- Name: source_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.source_role AS ENUM (
    'identity',
    'collection',
    'both'
);


--
-- Name: subject_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.subject_role AS ENUM (
    'consented',
    'incidental',
    'unidentified'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'dpo',
    'dco',
    'rnd_user',
    'admin',
    'data_subject',
    'dco_admin',
    'rco'
);


--
-- Name: user_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_status AS ENUM (
    'pending',
    'active',
    'suspended',
    'deactivated'
);


--
-- Name: cmp_append_only(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  RAISE EXCEPTION
    USING MESSAGE = format('%s is append-only: %s is refused', TG_TABLE_NAME, TG_OP),
          ERRCODE = '42501',
          HINT    = 'Record a new row that supersedes the old one.';
END;
$$;


--
-- Name: cmp_audit_chain(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_audit_chain() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  prev_hash text;
  payload   text;
BEGIN
  -- Serialise chain construction. Two concurrent inserts that both read the same
  -- predecessor would produce two rows claiming the same position, and the chain
  -- would verify against neither.
  PERFORM pg_advisory_xact_lock(hashtext('cmp_audit_chain'));

  -- The position is drawn here, inside the lock - not by a column default, which
  -- would draw it before the wait. Rows are chained in the order the lock was
  -- granted, so that is the order their ids must have. Whatever the statement
  -- supplied for log_id is discarded.
  NEW.log_id := nextval(pg_get_serial_sequence('audit_log', 'log_id'));

  SELECT detail_json ->> '_hash' INTO prev_hash
  FROM audit_log ORDER BY log_id DESC LIMIT 1;

  payload := concat_ws('|',
    NEW.event_type,
    coalesce(NEW.actor_user_id::text, ''),
    coalesce(NEW.subject_user_id::text, ''),
    NEW.entity_type,
    NEW.entity_id::text,
    to_char(NEW.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.USOF'),
    coalesce(NEW.detail_json - '_hash' - '_prev', '{}'::jsonb)::text
  );

  NEW.detail_json := coalesce(NEW.detail_json, '{}'::jsonb)
    || jsonb_build_object(
         '_prev', prev_hash,
         '_hash', encode(digest(concat_ws('|', coalesce(prev_hash, ''), payload), 'sha256'), 'hex')
       );
  RETURN NEW;
END;
$$;


--
-- Name: cmp_audit_verify(bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_audit_verify(from_log_id bigint DEFAULT 0) RETURNS TABLE(log_id bigint, log_uuid uuid, occurred_at timestamp with time zone, reason text)
    LANGUAGE plpgsql STABLE
    AS $$
DECLARE
  r          record;
  prev_hash  text;
  payload    text;
  expected   text;
  seeded     boolean := false;
BEGIN
  FOR r IN
    SELECT * FROM audit_log a WHERE a.log_id >= from_log_id ORDER BY a.log_id
  LOOP
    IF NOT seeded THEN
      prev_hash := r.detail_json ->> '_prev';
      seeded := true;
    END IF;

    IF (r.detail_json ->> '_prev') IS DISTINCT FROM prev_hash THEN
      log_id := r.log_id; log_uuid := r.log_uuid; occurred_at := r.occurred_at;
      reason := 'predecessor hash does not match the previous row';
      RETURN NEXT;
      RETURN;
    END IF;

    payload := concat_ws('|',
      r.event_type,
      coalesce(r.actor_user_id::text, ''),
      coalesce(r.subject_user_id::text, ''),
      r.entity_type,
      r.entity_id::text,
      to_char(r.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.USOF'),
      coalesce(r.detail_json - '_hash' - '_prev', '{}'::jsonb)::text
    );
    expected := encode(
      digest(concat_ws('|', coalesce(prev_hash, ''), payload), 'sha256'), 'hex');

    IF (r.detail_json ->> '_hash') IS DISTINCT FROM expected THEN
      log_id := r.log_id; log_uuid := r.log_uuid; occurred_at := r.occurred_at;
      reason := 'row content does not match its recorded hash';
      RETURN NEXT;
      RETURN;
    END IF;

    prev_hash := expected;
  END LOOP;
END;
$$;


--
-- Name: cmp_consent_coherent(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_consent_coherent() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  lang_notice int;
  lang_hash   text;
  lnk_notice  int;
  n_status    notice_status;
BEGIN
  SELECT nl.notice_id, nl.content_hash INTO lang_notice, lang_hash
  FROM notice_language nl WHERE nl.notice_language_id = NEW.notice_language_id;

  IF lang_notice IS DISTINCT FROM NEW.notice_id THEN
    RAISE EXCEPTION USING
      MESSAGE = 'notice_language belongs to a different notice', ERRCODE = '23514';
  END IF;

  IF NEW.notice_content_hash IS DISTINCT FROM lang_hash THEN
    RAISE EXCEPTION USING
      MESSAGE = 'notice_content_hash must be the hash of the text served (INV-4)',
      ERRCODE = '23514';
  END IF;

  SELECT cl.notice_id INTO lnk_notice FROM consent_link cl WHERE cl.link_id = NEW.link_id;
  IF lnk_notice IS DISTINCT FROM NEW.notice_id THEN
    RAISE EXCEPTION USING
      MESSAGE = 'consent link belongs to a different notice', ERRCODE = '23514';
  END IF;

  SELECT status INTO n_status FROM notice WHERE notice_id = NEW.notice_id;
  IF n_status NOT IN ('published', 'superseded') THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Consent cannot be recorded against an unpublished notice (s.5(1))',
      ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$$;


--
-- Name: cmp_contact_belongs_to_one_person(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_contact_belongs_to_one_person() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.secondary_email_hash IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.email_hash = NEW.secondary_email_hash) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  IF NEW.email_hash IS NOT NULL AND EXISTS (
       SELECT 1 FROM auth_user u
        WHERE u.id <> NEW.id AND u.secondary_email_hash = NEW.email_hash) THEN
    RAISE EXCEPTION 'that address belongs to another account'
      USING ERRCODE = 'unique_violation';
  END IF;
  RETURN NEW;
END $$;


--
-- Name: cmp_delegators_of(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_delegators_of(p_user_id integer) RETURNS TABLE(delegator_user_id integer)
    LANGUAGE sql STABLE
    AS $$
  SELECT d.delegator_user_id
    FROM delegation d
   WHERE d.delegate_user_id = p_user_id
     AND d.revoked_at IS NULL
     AND d.starts_at <= now()
     AND (d.ends_at IS NULL OR d.ends_at > now());
$$;


--
-- Name: FUNCTION cmp_delegators_of(p_user_id integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.cmp_delegators_of(p_user_id integer) IS 'The people this user is currently covering for. "Active" is defined here once - not revoked, started, not ended - so a second definition cannot drift from it.';


--
-- Name: cmp_grant_in_notice(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_grant_in_notice() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  ok boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1
    FROM consent_artefact ca
    JOIN notice_purpose np ON np.notice_id = ca.notice_id
    WHERE ca.consent_id = NEW.consent_id AND np.purpose_id = NEW.purpose_id
  ) INTO ok;
  IF NOT ok THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Purpose is not part of the notice this consent was given against',
      ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_is_minor(date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_is_minor(until date) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
  SELECT CASE WHEN until IS NULL THEN NULL ELSE until > CURRENT_DATE END;
$$;


--
-- Name: cmp_link_coherent(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_link_coherent() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  notice_project int;
  site_project   int;
  proj_status    project_status;
BEGIN
  SELECT project_id INTO notice_project FROM notice      WHERE notice_id = NEW.notice_id;
  SELECT project_id INTO site_project   FROM project_site WHERE site_id  = NEW.site_id;

  IF notice_project IS DISTINCT FROM site_project THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Consent link site and notice belong to different projects',
      ERRCODE = '23514';
  END IF;

  SELECT project_status INTO proj_status FROM project WHERE project_id = notice_project;
  IF proj_status <> 'approved' THEN
    RAISE EXCEPTION USING
      MESSAGE = 'A consent link may only exist for a project in approved',
      ERRCODE = '23514';
  END IF;

  RETURN NEW;
END;
$$;


--
-- Name: cmp_link_use_count_guard(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_link_use_count_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.max_uses IS NOT NULL AND NEW.use_count > NEW.max_uses THEN
    RAISE EXCEPTION USING
      MESSAGE = 'Consent link use cap exceeded', ERRCODE = '23514';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_nominee_needs_mobile(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_nominee_needs_mobile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.nominee_mobile IS NULL THEN
    RAISE EXCEPTION 'a nominee needs a mobile'
      USING ERRCODE = 'check_violation', CONSTRAINT = 'nomination_mobile_required';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_notice_freeze(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_notice_freeze() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF OLD.status = 'published' THEN
    -- superseded is the one permitted transition out of published: a new version
    -- replaces this one, and this row records that it was replaced.
    IF NEW.status = 'superseded'
       AND NEW.notice_code       = OLD.notice_code
       AND NEW.version           = OLD.version
       AND NEW.withdraw_url      = OLD.withdraw_url
       AND NEW.exercise_rights_url = OLD.exercise_rights_url
       AND NEW.board_complaint_url = OLD.board_complaint_url
       AND NEW.dpo_contact       = OLD.dpo_contact
       AND NEW.recipients_text   IS NOT DISTINCT FROM OLD.recipients_text
       AND NEW.published_at      IS NOT DISTINCT FROM OLD.published_at THEN
      RETURN NEW;
    END IF;
    RAISE EXCEPTION
      USING MESSAGE = 'A published notice is immutable; publish a new version instead',
            ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_notice_language_freeze(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_notice_language_freeze() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  parent_status notice_status;
BEGIN
  SELECT status INTO parent_status FROM notice WHERE notice_id = OLD.notice_id;
  IF parent_status IN ('published', 'superseded')
     AND (NEW.rendered_text <> OLD.rendered_text
          OR NEW.content_hash <> OLD.content_hash) THEN
    RAISE EXCEPTION
      USING MESSAGE = 'The text a data subject was shown cannot be edited (INV-4)',
            ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_notice_purpose_freeze(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_notice_purpose_freeze() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  target_notice int;
  parent_status notice_status;
BEGIN
  target_notice := CASE TG_OP WHEN 'DELETE' THEN OLD.notice_id ELSE NEW.notice_id END;
  SELECT status INTO parent_status FROM notice WHERE notice_id = target_notice;
  IF parent_status IN ('published', 'superseded') THEN
    RAISE EXCEPTION
      USING MESSAGE = 'Purposes cannot change on a published notice; publish a new version',
            ERRCODE = '42501';
  END IF;
  RETURN CASE TG_OP WHEN 'DELETE' THEN OLD ELSE NEW END;
END;
$$;


--
-- Name: cmp_primary_site_dco(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_primary_site_dco(p_project_id integer) RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT coalesce(s.dco_override_user_id, d.owner_user_id)
    FROM project_site s
    LEFT JOIN data_source d ON d.source_id = s.source_id
   WHERE s.site_id = cmp_primary_site_id(p_project_id);
$$;


--
-- Name: FUNCTION cmp_primary_site_dco(p_project_id integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.cmp_primary_site_dco(p_project_id integer) IS 'The DCO a project routes to. Derived from cmp_primary_site_id so the two can never name different sites.';


--
-- Name: cmp_primary_site_id(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_primary_site_id(p_project_id integer) RETURNS integer
    LANGUAGE sql STABLE
    AS $$
  SELECT s.site_id
    FROM project_site s
    LEFT JOIN data_source d ON d.source_id = s.source_id
   WHERE s.project_id = p_project_id
     AND s.status = 'active'
     AND coalesce(s.dco_override_user_id, d.owner_user_id) IS NOT NULL
   ORDER BY s.site_id
   LIMIT 1;
$$;


--
-- Name: FUNCTION cmp_primary_site_id(p_project_id integer); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.cmp_primary_site_id(p_project_id integer) IS 'A project''s primary site: the earliest-registered active site that has an owner. The tie-break is site_id rather than a flag, because a flag is a thing somebody has to set and will forget.';


--
-- Name: cmp_site_owner_changed(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_site_owner_changed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  affected int;
  owner    int;
BEGIN
  affected := COALESCE(NEW.project_id, OLD.project_id);
  owner := cmp_primary_site_dco(affected);

  -- Sites decide only when they have an opinion.
  --
  -- A NULL here means no active site has an owner yet, and that is not the same
  -- as "nobody owns this project". A project can be assigned before any site
  -- exists, and adding an unowned site to it must not quietly orphan it - an
  -- orphaned project is invisible to every DCO, which is a worse failure than a
  -- slightly stale owner and a much quieter one.
  --
  -- The consequence, stated so it is a decision rather than an oversight:
  -- un-assigning the last owned site leaves the project where it was. The
  -- person stays accountable until somebody else takes a site on it.
  IF owner IS NULL THEN
    RETURN COALESCE(NEW, OLD);
  END IF;

  UPDATE project
     SET dco_user_id = owner,
         updated_at  = now()
   WHERE project_id = affected
     AND dco_user_id IS DISTINCT FROM owner;

  RETURN COALESCE(NEW, OLD);
END;
$$;


--
-- Name: FUNCTION cmp_site_owner_changed(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.cmp_site_owner_changed() IS 'Re-derives project.dco_user_id when a site is added, reassigned, deactivated or removed. This is what makes "move the site and the project follows" true rather than merely intended.';


--
-- Name: cmp_source_owner_changed(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_source_owner_changed() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
  affected int;
  owner    int;
BEGIN
  FOR affected IN
    SELECT DISTINCT s.project_id FROM project_site s WHERE s.source_id = NEW.source_id
  LOOP
    owner := cmp_primary_site_dco(affected);

    IF owner IS NOT NULL THEN
      UPDATE project
         SET dco_user_id = owner, updated_at = now()
       WHERE project_id = affected
         AND dco_user_id IS DISTINCT FROM owner;

    ELSIF OLD.owner_user_id IS NOT NULL THEN
      -- Somebody has just stopped being accountable for this source, and no
      -- other source deployed on the project has an owner either.
      --
      -- The site trigger treats a NULL owner as "no opinion" and leaves the
      -- project where it was, because adding a site nobody runs yet must not
      -- orphan a project. This is a different thing wearing the same NULL: an
      -- explicit relinquishment. Leaving the name on the project would read as
      -- current, and an answer that reads as current is worse than none.
      --
      -- Only where they were the one holding it. A project assigned directly to
      -- somebody else is not theirs to vacate.
      UPDATE project
         SET dco_user_id = NULL, updated_at = now()
       WHERE project_id = affected
         AND dco_user_id = OLD.owner_user_id;
    END IF;
  END LOOP;
  RETURN NEW;
END;
$$;


--
-- Name: FUNCTION cmp_source_owner_changed(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.cmp_source_owner_changed() IS 'Re-routes every project collecting from a source when that source changes hands. The site-level trigger from 0005 covers sites moving between projects; this covers the source moving between people.';


--
-- Name: cmp_subject_needs_mobile(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_subject_needs_mobile() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  IF NEW.role = 'data_subject' AND NEW.mobile IS NULL THEN
    RAISE EXCEPTION 'a data principal needs a mobile'
      USING ERRCODE = 'check_violation', CONSTRAINT = 'auth_user_subject_mobile_required';
  END IF;
  RETURN NEW;
END;
$$;


--
-- Name: cmp_touch_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.cmp_touch_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: asset_consent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.asset_consent (
    asset_consent_id integer NOT NULL,
    asset_id integer NOT NULL,
    consent_id integer,
    subject_role public.subject_role NOT NULL,
    disposition public.disposition,
    disposition_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT consent_matches_role CHECK ((((subject_role = 'consented'::public.subject_role) AND (consent_id IS NOT NULL)) OR ((subject_role <> 'consented'::public.subject_role) AND (consent_id IS NULL))))
);


--
-- Name: asset_consent_asset_consent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.asset_consent_asset_consent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: asset_consent_asset_consent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.asset_consent_asset_consent_id_seq OWNED BY public.asset_consent.asset_consent_id;


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    log_id bigint NOT NULL,
    log_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    event_type character varying(80) NOT NULL,
    actor_user_id integer,
    subject_user_id integer,
    entity_type character varying(60) NOT NULL,
    entity_id integer NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    detail_json jsonb
);


--
-- Name: audit_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_log_id_seq OWNED BY public.audit_log.log_id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.auth_user (
    id integer NOT NULL,
    uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    username text,
    full_name text NOT NULL,
    email text,
    mobile text,
    organization_id text,
    role public.user_role DEFAULT 'data_subject'::public.user_role NOT NULL,
    person_type public.person_type,
    status public.user_status DEFAULT 'pending'::public.user_status NOT NULL,
    registered_via_link_id integer,
    password_hash character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    dob text,
    mobile_verified_at timestamp with time zone,
    email_verified_at timestamp with time zone,
    secondary_email text,
    secondary_email_verified_at timestamp with time zone,
    email_hash text,
    secondary_email_hash text,
    mobile_hash text,
    username_hash text,
    organization_id_hash text,
    minor_until date,
    full_name_ngrams text[],
    CONSTRAINT auth_user_email_indexed CHECK (((email IS NULL) OR (email_hash IS NOT NULL))),
    CONSTRAINT auth_user_mobile_indexed CHECK (((mobile IS NULL) OR (mobile_hash IS NOT NULL))),
    CONSTRAINT auth_user_organization_id_indexed CHECK (((organization_id IS NULL) OR (organization_id_hash IS NOT NULL))),
    CONSTRAINT auth_user_secondary_email_differs CHECK (((secondary_email_hash IS NULL) OR (email_hash IS NULL) OR (secondary_email_hash <> email_hash))),
    CONSTRAINT auth_user_secondary_email_indexed CHECK (((secondary_email IS NULL) OR (secondary_email_hash IS NOT NULL))),
    CONSTRAINT auth_user_staff_email_required CHECK (((role = 'data_subject'::public.user_role) OR (email IS NOT NULL))),
    CONSTRAINT auth_user_username_indexed CHECK (((username IS NULL) OR (username_hash IS NOT NULL)))
);


--
-- Name: COLUMN auth_user.full_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.auth_user.full_name IS 'Sealed by the key service on write; the portals decrypt. Length is bounded by the API, not the column';


--
-- Name: COLUMN auth_user.dob; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.auth_user.dob IS 'Date of birth, sealed by the key service; text because ciphertext is not a date. The s.9 test reads minor_until';


--
-- Name: COLUMN auth_user.secondary_email; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.auth_user.secondary_email IS 'A second address the person added themselves; signs them in only once a code sent to it has come back';


--
-- Name: COLUMN auth_user.secondary_email_verified_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.auth_user.secondary_email_verified_at IS 'When a code sent to secondary_email came back; NULL means it never has';


--
-- Name: COLUMN auth_user.minor_until; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.auth_user.minor_until IS 'The date this person stops being a child under s.9: date of birth plus eighteen years. Kept in the clear so the test stays a comparison; dob itself is sealed';


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.auth_user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.auth_user_id_seq OWNED BY public.auth_user.id;


--
-- Name: collection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.collection (
    collection_id integer NOT NULL,
    collection_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id integer NOT NULL,
    source_collection_ref character varying(120) NOT NULL,
    project_id integer NOT NULL,
    site_id integer,
    batch_id integer NOT NULL,
    agent_ref character varying(120),
    collected_on date NOT NULL,
    declared_asset_count integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: collection_collection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.collection_collection_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: collection_collection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.collection_collection_id_seq OWNED BY public.collection.collection_id;


--
-- Name: consent_artefact; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consent_artefact (
    consent_id integer NOT NULL,
    consent_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    auth_user_id integer NOT NULL,
    notice_id integer NOT NULL,
    notice_language_id integer NOT NULL,
    notice_content_hash text NOT NULL,
    link_id integer NOT NULL,
    served_at timestamp with time zone NOT NULL,
    affirmative_action_at timestamp with time zone NOT NULL,
    action_type public.action_type NOT NULL,
    ip_address text,
    is_withdrawal boolean DEFAULT false NOT NULL,
    supersedes_consent_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT served_before_action CHECK ((served_at <= affirmative_action_at))
);


--
-- Name: COLUMN consent_artefact.ip_address; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.consent_artefact.ip_address IS 'The address she consented from, sealed by the key service; text rather than inet because ciphertext is not an address';


--
-- Name: consent_artefact_consent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consent_artefact_consent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consent_artefact_consent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consent_artefact_consent_id_seq OWNED BY public.consent_artefact.consent_id;


--
-- Name: consent_link; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consent_link (
    link_id integer NOT NULL,
    link_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    notice_id integer NOT NULL,
    site_id integer NOT NULL,
    token character varying(64) NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    max_uses integer,
    use_count integer DEFAULT 0 NOT NULL,
    status public.link_status DEFAULT 'active'::public.link_status NOT NULL,
    created_by integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    revoked_by integer,
    revoked_at timestamp with time zone,
    token_sealed bytea
);


--
-- Name: COLUMN consent_link.token; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.consent_link.token IS 'Keyed digest of the token, and still the only thing lookups match on. A request presents a token, it is fingerprinted, and this column is compared - token_sealed is never used to authenticate, only to re-display.';


--
-- Name: COLUMN consent_link.token_sealed; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.consent_link.token_sealed IS 'The link token, encrypted under a key derived from the application secret. Lets the URL be shown again to whoever needs to share it. NULL on links minted before 0011, whose tokens were never kept - those stay unrecoverable and the interface says so rather than showing a blank link.';


--
-- Name: consent_link_link_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consent_link_link_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consent_link_link_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consent_link_link_id_seq OWNED BY public.consent_link.link_id;


--
-- Name: consent_purpose_grant; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consent_purpose_grant (
    grant_id integer NOT NULL,
    consent_id integer NOT NULL,
    purpose_id integer NOT NULL,
    granted boolean NOT NULL
);


--
-- Name: consent_purpose_grant_grant_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consent_purpose_grant_grant_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: consent_purpose_grant_grant_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consent_purpose_grant_grant_id_seq OWNED BY public.consent_purpose_grant.grant_id;


--
-- Name: data_asset; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_asset (
    asset_id integer NOT NULL,
    asset_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id integer NOT NULL,
    source_asset_ref character varying(160) NOT NULL,
    collection_id integer NOT NULL,
    asset_type public.asset_type NOT NULL,
    storage_ref text,
    has_unmapped_subjects boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: data_asset_asset_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_asset_asset_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_asset_asset_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_asset_asset_id_seq OWNED BY public.data_asset.asset_id;


--
-- Name: data_source; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_source (
    source_id integer NOT NULL,
    source_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    source_code character varying(60) NOT NULL,
    name character varying(200) NOT NULL,
    source_role public.source_role NOT NULL,
    exchange_mode public.exchange_mode NOT NULL,
    id_scheme character varying(120),
    processor_id integer,
    site_id integer,
    is_authoritative_for text[] DEFAULT '{}'::text[] NOT NULL,
    status public.record_status DEFAULT 'active'::public.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    owner_user_id integer
);


--
-- Name: COLUMN data_source.owner_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.data_source.owner_user_id IS 'The DCO or RCO accountable for this source. One answer, here, because the same rig serving three projects had its owner recorded three times when this lived on project_site - and nothing stopped those three disagreeing.';


--
-- Name: data_source_source_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.data_source_source_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: data_source_source_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.data_source_source_id_seq OWNED BY public.data_source.source_id;


--
-- Name: delegation; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.delegation (
    delegation_id integer NOT NULL,
    delegation_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    delegator_user_id integer NOT NULL,
    delegate_user_id integer NOT NULL,
    reason text,
    starts_at timestamp with time zone DEFAULT now() NOT NULL,
    ends_at timestamp with time zone,
    revoked_at timestamp with time zone,
    revoked_by integer,
    created_by integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ends_after_start CHECK (((ends_at IS NULL) OR (ends_at > starts_at))),
    CONSTRAINT not_self CHECK ((delegator_user_id <> delegate_user_id)),
    CONSTRAINT revocation_is_attributed CHECK ((((revoked_at IS NULL) AND (revoked_by IS NULL)) OR ((revoked_at IS NOT NULL) AND (revoked_by IS NOT NULL))))
);


--
-- Name: TABLE delegation; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.delegation IS 'One person covering another''s row access for a period. Grants, never transfers: ownership stays where it is and the access lapses on its own.';


--
-- Name: delegation_delegation_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.delegation_delegation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: delegation_delegation_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.delegation_delegation_id_seq OWNED BY public.delegation.delegation_id;


--
-- Name: export_line; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.export_line (
    line_id integer NOT NULL,
    export_id integer NOT NULL,
    auth_user_id integer NOT NULL,
    consent_id integer NOT NULL
);


--
-- Name: export_line_line_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.export_line_line_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: export_line_line_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.export_line_line_id_seq OWNED BY public.export_line.line_id;


--
-- Name: export_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.export_log (
    export_id integer NOT NULL,
    export_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id integer NOT NULL,
    site_id integer,
    export_type public.export_type NOT NULL,
    exported_by integer NOT NULL,
    exported_at timestamp with time zone DEFAULT now() NOT NULL,
    row_count integer NOT NULL,
    file_hash text NOT NULL,
    file_ref text
);


--
-- Name: COLUMN export_log.site_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.export_log.site_id IS 'The site this export covered, on the per-site exports that predate 0010. NULL on a project export, which covers every site the exporter could see - the rows themselves name their site.';


--
-- Name: COLUMN export_log.file_ref; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.export_log.file_ref IS 'Storage reference of the CSV exactly as generated; NULL for exports that predate 0023';


--
-- Name: export_log_export_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.export_log_export_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: export_log_export_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.export_log_export_id_seq OWNED BY public.export_log.export_id;


--
-- Name: import_batch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_batch (
    batch_id integer NOT NULL,
    batch_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    source_id integer NOT NULL,
    project_id integer,
    file_name text NOT NULL,
    file_hash text NOT NULL,
    declared_rows integer NOT NULL,
    accepted_rows integer DEFAULT 0 NOT NULL,
    rejected_rows integer DEFAULT 0 NOT NULL,
    status public.batch_status DEFAULT 'received'::public.batch_status NOT NULL,
    error_report text,
    imported_by integer NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: import_batch_batch_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.import_batch_batch_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: import_batch_batch_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.import_batch_batch_id_seq OWNED BY public.import_batch.batch_id;


--
-- Name: message_template; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.message_template (
    template_id integer NOT NULL,
    key character varying(64) NOT NULL,
    channel character varying(8) NOT NULL,
    subject text,
    body text NOT NULL,
    updated_by integer,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT message_template_body_present CHECK ((length(btrim(body)) > 0)),
    CONSTRAINT message_template_channel CHECK (((channel)::text = ANY ((ARRAY['email'::character varying, 'sms'::character varying])::text[])))
);


--
-- Name: TABLE message_template; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.message_template IS 'Subject and body an administrator or the DPO set for one message junction and channel; absent means the code default';


--
-- Name: message_template_template_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.message_template_template_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: message_template_template_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.message_template_template_id_seq OWNED BY public.message_template.template_id;


--
-- Name: nomination; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.nomination (
    nomination_id integer NOT NULL,
    nomination_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    principal_user_id integer NOT NULL,
    nominee_name text NOT NULL,
    rights public.rights_request_type[] NOT NULL,
    status public.nomination_status DEFAULT 'pending'::public.nomination_status NOT NULL,
    accept_token_hash text,
    accept_expires_at timestamp with time zone,
    accepted_at timestamp with time zone,
    declined_at timestamp with time zone,
    revoked_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    nominee_mobile text,
    nominee_email text,
    invoked_at timestamp with time zone,
    invoked_event public.rights_trigger_event,
    invoked_request_id integer,
    nominee_user_id integer,
    nominee_email_hash text,
    nominee_mobile_hash text,
    nominee_name_ngrams text[],
    CONSTRAINT nomination_email_indexed CHECK (((nominee_email IS NULL) OR (nominee_email_hash IS NOT NULL))),
    CONSTRAINT nomination_mobile_indexed CHECK (((nominee_mobile IS NULL) OR (nominee_mobile_hash IS NOT NULL))),
    CONSTRAINT nomination_rights_not_empty CHECK ((cardinality(rights) >= 1)),
    CONSTRAINT nomination_some_contact CHECK (((nominee_mobile IS NOT NULL) OR (nominee_email IS NOT NULL))),
    CONSTRAINT nomination_status_dates CHECK ((((status = 'active'::public.nomination_status) AND (accepted_at IS NOT NULL)) OR ((status = 'declined'::public.nomination_status) AND (declined_at IS NOT NULL)) OR ((status = 'revoked'::public.nomination_status) AND (revoked_at IS NOT NULL)) OR (status = 'pending'::public.nomination_status)))
);


--
-- Name: COLUMN nomination.nominee_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.nomination.nominee_user_id IS 'The account the nominee accepted with, set at acceptance; NULL for a nomination never accepted, or accepted before this column existed and matching no account';


--
-- Name: nomination_nomination_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.nomination_nomination_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: nomination_nomination_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.nomination_nomination_id_seq OWNED BY public.nomination.nomination_id;


--
-- Name: notice; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notice (
    notice_id integer NOT NULL,
    notice_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    notice_code character varying(80) NOT NULL,
    project_id integer NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    withdraw_url text NOT NULL,
    exercise_rights_url text NOT NULL,
    board_complaint_url text NOT NULL,
    dpo_contact character varying(255) NOT NULL,
    recipients_text text,
    status public.notice_status DEFAULT 'draft'::public.notice_status NOT NULL,
    change_class public.change_class,
    approved_by integer,
    published_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    note text,
    applicable_to public.notice_audience,
    CONSTRAINT publishable CHECK (((status <> 'published'::public.notice_status) OR ((recipients_text IS NOT NULL) AND (published_at IS NOT NULL))))
);


--
-- Name: COLUMN notice.note; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice.note IS 'A note from the author to whoever collects against this notice. Shown to the DCO and never to the data principal - it is an instruction to the collector, not part of the notice they are given.';


--
-- Name: COLUMN notice.applicable_to; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice.applicable_to IS 'Who this notice addresses. Null on notices that predate the column; the publish checklist requires it, so nothing reaches a data principal without it being answered.';


--
-- Name: notice_language; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notice_language (
    notice_language_id integer NOT NULL,
    notice_language_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    notice_id integer NOT NULL,
    language_code public.language_code NOT NULL,
    rendered_text text NOT NULL,
    content_hash text NOT NULL,
    created_by integer NOT NULL,
    approved_by integer,
    approved_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: notice_language_notice_language_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notice_language_notice_language_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notice_language_notice_language_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notice_language_notice_language_id_seq OWNED BY public.notice_language.notice_language_id;


--
-- Name: notice_notice_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notice_notice_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notice_notice_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notice_notice_id_seq OWNED BY public.notice.notice_id;


--
-- Name: notice_purpose; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notice_purpose (
    notice_purpose_id integer NOT NULL,
    notice_id integer NOT NULL,
    purpose_id integer NOT NULL,
    display_order integer DEFAULT 0 NOT NULL,
    is_mandatory boolean DEFAULT false NOT NULL,
    data_categories_override text[],
    uses_override text,
    overridden_by integer,
    overridden_at timestamp with time zone,
    CONSTRAINT override_categories_not_empty CHECK (((data_categories_override IS NULL) OR (cardinality(data_categories_override) >= 1))),
    CONSTRAINT override_is_attributed CHECK ((((data_categories_override IS NULL) AND (uses_override IS NULL)) OR ((overridden_by IS NOT NULL) AND (overridden_at IS NOT NULL))))
);


--
-- Name: COLUMN notice_purpose.data_categories_override; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice_purpose.data_categories_override IS 'Rule 3(b)(i) for this notice only. NULL means the purpose''s own list, which is the default and the common case. A value must be a subset of it - a notice may narrow what is collected, never widen it.';


--
-- Name: COLUMN notice_purpose.uses_override; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice_purpose.uses_override IS 'Rule 3(b)(ii) for this notice only. NULL means the purpose''s own text.';


--
-- Name: notice_purpose_notice_purpose_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notice_purpose_notice_purpose_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notice_purpose_notice_purpose_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notice_purpose_notice_purpose_id_seq OWNED BY public.notice_purpose.notice_purpose_id;


--
-- Name: person_type_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.person_type_history (
    history_id integer NOT NULL,
    history_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    auth_user_id integer NOT NULL,
    from_type public.person_type,
    to_type public.person_type NOT NULL,
    reason text,
    changed_by integer NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: person_type_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.person_type_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: person_type_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.person_type_history_history_id_seq OWNED BY public.person_type_history.history_id;


--
-- Name: processor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processor (
    processor_id integer NOT NULL,
    processor_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    legal_name character varying(255) NOT NULL,
    type public.processor_type NOT NULL,
    contract_ref character varying(120) NOT NULL,
    security_confirmed_at date NOT NULL,
    status public.record_status DEFAULT 'active'::public.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_in_house boolean DEFAULT false NOT NULL
);


--
-- Name: COLUMN processor.is_in_house; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.processor.is_in_house IS 'Whether this is the organisation collecting for itself. It drives routing: a project collected by a third party goes to a DCO Admin to be assigned, one collected in-house goes back to the R&D owner to assign an RCO. Separate from processor_type, which says what kind of thing a processor is (lab, tool) and not whose it is - a lab can be either.';


--
-- Name: processor_processor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.processor_processor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: processor_processor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.processor_processor_id_seq OWNED BY public.processor.processor_id;


--
-- Name: processor_respondent; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processor_respondent (
    respondent_id integer NOT NULL,
    respondent_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    processor_id integer NOT NULL,
    name text NOT NULL,
    contact text NOT NULL,
    user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    removed_at timestamp with time zone
);


--
-- Name: processor_respondent_respondent_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.processor_respondent_respondent_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: processor_respondent_respondent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.processor_respondent_respondent_id_seq OWNED BY public.processor_respondent.respondent_id;


--
-- Name: project; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project (
    project_id integer NOT NULL,
    project_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    project_name character varying(200) NOT NULL,
    internal_project_name character varying(200),
    description text,
    requesting_team character varying(120),
    project_status public.project_status DEFAULT 'in_draft'::public.project_status NOT NULL,
    current_notice_id integer,
    created_by integer NOT NULL,
    dco_user_id integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: project_approval; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_approval (
    approval_id integer NOT NULL,
    approval_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id integer NOT NULL,
    approval_type public.approval_type NOT NULL,
    reference_no character varying(120) NOT NULL,
    approved_on date NOT NULL,
    proof_file_ref text NOT NULL,
    proof_file_hash text NOT NULL,
    uploaded_by integer NOT NULL,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: project_approval_approval_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_approval_approval_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_approval_approval_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_approval_approval_id_seq OWNED BY public.project_approval.approval_id;


--
-- Name: project_processor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_processor (
    project_processor_id integer NOT NULL,
    project_id integer NOT NULL,
    processor_id integer NOT NULL,
    added_by integer NOT NULL,
    added_at timestamp with time zone DEFAULT now() NOT NULL,
    status public.processor_request_status DEFAULT 'approved'::public.processor_request_status NOT NULL,
    decided_by integer,
    decided_at timestamp with time zone,
    decision_reason text,
    CONSTRAINT processor_decision_is_attributed CHECK (((status = 'pending'::public.processor_request_status) OR (decided_at IS NULL) OR (decided_by IS NOT NULL))),
    CONSTRAINT processor_rejection_has_a_reason CHECK (((status <> 'rejected'::public.processor_request_status) OR ((decided_by IS NOT NULL) AND (decided_at IS NOT NULL) AND (COALESCE(length(TRIM(BOTH FROM decision_reason)), 0) > 0))))
);


--
-- Name: TABLE project_processor; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.project_processor IS 'Who will collect for this project. Chosen at creation, before any site exists, because who collects is the first decision and the sites follow from it. Many-to-many: a study running at a partner campus and in-house at once is ordinary, not exceptional.';


--
-- Name: COLUMN project_processor.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project_processor.status IS 'Added while the project was in draft, or approved as an amendment: ''approved''. Requested against an already-approved project and not yet decided: ''pending''. Refused: ''rejected'', with the reason kept.';


--
-- Name: COLUMN project_processor.decision_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project_processor.decision_reason IS 'Why the DPO refused. Required on a rejection - "no" without a reason is a decision the R&D User cannot act on, so they ask again and get it again.';


--
-- Name: project_processor_project_processor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_processor_project_processor_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_processor_project_processor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_processor_project_processor_id_seq OWNED BY public.project_processor.project_processor_id;


--
-- Name: project_project_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_project_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_project_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_project_id_seq OWNED BY public.project.project_id;


--
-- Name: project_site; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_site (
    site_id integer NOT NULL,
    site_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id integer NOT NULL,
    processor_id integer,
    site_label character varying(160) NOT NULL,
    location character varying(200),
    status public.record_status DEFAULT 'active'::public.record_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    source_id integer,
    dco_override_user_id integer,
    dco_override_by integer,
    dco_override_at timestamp with time zone,
    CONSTRAINT site_override_is_attributed CHECK (((dco_override_user_id IS NULL) OR ((dco_override_by IS NOT NULL) AND (dco_override_at IS NOT NULL))))
);


--
-- Name: COLUMN project_site.source_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project_site.source_id IS 'The data source deployed at this site. Ownership is read through it: a site has no owner of its own.';


--
-- Name: COLUMN project_site.dco_override_user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project_site.dco_override_user_id IS 'Who runs this site on this project, when that is not whoever owns its data source. NULL - the usual case - means the source decides. Setting it changes nothing about the source or about other projects deploying the same source.';


--
-- Name: COLUMN project_site.dco_override_by; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.project_site.dco_override_by IS 'Who made the exception. An override with no author is an exception nobody can be asked about, which is the state the audit trail exists to prevent.';


--
-- Name: project_site_site_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_site_site_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_site_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_site_site_id_seq OWNED BY public.project_site.site_id;


--
-- Name: project_status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.project_status_history (
    history_id integer NOT NULL,
    history_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    project_id integer NOT NULL,
    from_status public.project_status,
    to_status public.project_status NOT NULL,
    reason text,
    actor_user_id integer NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: project_status_history_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.project_status_history_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: project_status_history_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.project_status_history_history_id_seq OWNED BY public.project_status_history.history_id;


--
-- Name: purpose; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purpose (
    purpose_id integer NOT NULL,
    purpose_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    purpose_code character varying(80) NOT NULL,
    version integer DEFAULT 1 NOT NULL,
    status public.purpose_status DEFAULT 'draft'::public.purpose_status NOT NULL,
    name character varying(200) NOT NULL,
    description text NOT NULL,
    uses text NOT NULL,
    lawful_basis public.lawful_basis NOT NULL,
    s7_clause public.s7_clause,
    data_categories text[] NOT NULL,
    retention_period interval NOT NULL,
    retention_basis public.retention_basis NOT NULL,
    erasure_trigger public.erasure_trigger NOT NULL,
    consent_validity_period interval,
    cross_border_permitted boolean DEFAULT false NOT NULL,
    permitted_for_minors boolean DEFAULT false NOT NULL,
    lapse_behaviour public.lapse_behaviour DEFAULT 'quarantine'::public.lapse_behaviour NOT NULL,
    created_by integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT categories_not_empty CHECK ((cardinality(data_categories) >= 1)),
    CONSTRAINT s7_clause_required CHECK ((((lawful_basis = 'legitimate_use_s7'::public.lawful_basis) AND (s7_clause IS NOT NULL)) OR ((lawful_basis = 'consent_s6'::public.lawful_basis) AND (s7_clause IS NULL))))
);


--
-- Name: purpose_purpose_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.purpose_purpose_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purpose_purpose_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.purpose_purpose_id_seq OWNED BY public.purpose.purpose_id;


--
-- Name: rights_request; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rights_request (
    request_id integer NOT NULL,
    request_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    reference character varying(24) NOT NULL,
    request_type public.rights_request_type NOT NULL,
    original_type public.rights_request_type,
    status public.rights_request_status DEFAULT 'received'::public.rights_request_status NOT NULL,
    outcome public.rights_request_outcome,
    channel public.rights_request_channel NOT NULL,
    subject_user_id integer,
    submitted_name text,
    submitted_contact text NOT NULL,
    request_text text NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    due_at timestamp with time zone NOT NULL,
    acknowledged_at timestamp with time zone,
    verification_method public.rights_verification_method,
    verification_status public.rights_verification_status DEFAULT 'pending'::public.rights_verification_status NOT NULL,
    verified_at timestamp with time zone,
    verified_by integer,
    verification_note text,
    classified_at timestamp with time zone,
    classified_by integer,
    refusal_reason text,
    intent_confirmed_at timestamp with time zone,
    linked_request_id integer,
    nomination_id integer,
    trigger_event public.rights_trigger_event,
    trigger_evidence_ref text,
    trigger_evidence_hash text,
    trigger_evidenced_at timestamp with time zone,
    about_dpo boolean DEFAULT false NOT NULL,
    reviewer_user_id integer,
    escalated_at timestamp with time zone,
    grievance_upheld boolean,
    remedy_text text,
    response_text text,
    response_file_ref text,
    response_file_hash text,
    responded_at timestamp with time zone,
    responded_by integer,
    download_expires_at timestamp with time zone,
    closed_at timestamp with time zone,
    created_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    consent_id integer,
    submitted_contact_hash text,
    submitted_name_ngrams text[],
    CONSTRAINT rights_closed_has_outcome CHECK (((status <> 'closed'::public.rights_request_status) OR (outcome IS NOT NULL))),
    CONSTRAINT rights_due_after_receipt CHECK ((due_at > received_at)),
    CONSTRAINT rights_nominee_has_nomination CHECK (((channel <> 'nominee'::public.rights_request_channel) OR (nomination_id IS NOT NULL))),
    CONSTRAINT rights_refusal_has_reason CHECK (((outcome <> 'refused'::public.rights_request_outcome) OR (refusal_reason IS NOT NULL))),
    CONSTRAINT rights_request_contact_indexed CHECK (((submitted_contact IS NULL) OR (submitted_contact_hash IS NOT NULL))),
    CONSTRAINT rights_verified_is_attributed CHECK (((verification_status <> 'verified'::public.rights_verification_status) OR ((verified_at IS NOT NULL) AND (verification_method IS NOT NULL))))
);


--
-- Name: TABLE rights_request; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.rights_request IS 'A data principal''s request under ss.11-14 of the DPDP Act, and its clock. The clock starts on receipt, not on verification.';


--
-- Name: COLUMN rights_request.due_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.rights_request.due_at IS 'Copied from the published response period at receipt. A period changed later does not move a request already running.';


--
-- Name: rights_request_holder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rights_request_holder (
    holder_id integer NOT NULL,
    holder_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id integer NOT NULL,
    processor_id integer,
    label character varying(200) NOT NULL,
    derived_from public.rights_holder_source NOT NULL,
    evidence jsonb DEFAULT '{}'::jsonb NOT NULL,
    confirmed_at timestamp with time zone,
    confirmed_by integer,
    ticket_status public.rights_ticket_status DEFAULT 'pending'::public.rights_ticket_status NOT NULL,
    instruction text,
    responder_name text,
    responder_contact text,
    issued_at timestamp with time zone,
    due_at timestamp with time zone,
    escalated_at timestamp with time zone,
    returned_at timestamp with time zone,
    return_summary text,
    return_evidence_ref text,
    return_evidence_hash text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    respondent_id integer,
    responder_user_id integer,
    channel character varying(10) DEFAULT 'email'::character varying NOT NULL,
    contact_log jsonb DEFAULT '[]'::jsonb NOT NULL,
    brief jsonb,
    office_read_at timestamp with time zone,
    holder_read_at timestamp with time zone,
    return_evidence_name character varying(255),
    last_reminded_at timestamp with time zone,
    reminders_sent integer DEFAULT 0 NOT NULL,
    sent_back_at timestamp with time zone,
    sent_back_reason text,
    sent_back_count integer DEFAULT 0 NOT NULL,
    CONSTRAINT holder_channel CHECK (((channel)::text = ANY ((ARRAY['portal'::character varying, 'email'::character varying])::text[]))),
    CONSTRAINT holder_issued_has_date CHECK (((ticket_status = 'pending'::public.rights_ticket_status) OR (issued_at IS NOT NULL))),
    CONSTRAINT holder_portal_has_account CHECK ((((channel)::text <> 'portal'::text) OR (responder_user_id IS NOT NULL))),
    CONSTRAINT holder_returned_has_date CHECK (((ticket_status <> 'returned'::public.rights_ticket_status) OR (returned_at IS NOT NULL)))
);


--
-- Name: rights_request_holder_holder_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_request_holder_holder_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_request_holder_holder_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rights_request_holder_holder_id_seq OWNED BY public.rights_request_holder.holder_id;


--
-- Name: rights_request_item; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rights_request_item (
    item_id integer NOT NULL,
    item_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id integer NOT NULL,
    asset_consent_id integer NOT NULL,
    holder_id integer,
    other_subjects integer DEFAULT 0 NOT NULL,
    state public.rights_item_state DEFAULT 'proposed'::public.rights_item_state NOT NULL,
    decision public.rights_scope_decision,
    basis text,
    retain_until date,
    floor_passed_at timestamp with time zone,
    decided_at timestamp with time zone,
    decided_by integer,
    applied_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT item_decided_is_attributed CHECK (((decision IS NULL) OR (decided_at IS NOT NULL))),
    CONSTRAINT item_decision_has_basis CHECK (((decision IS NULL) OR (basis IS NOT NULL))),
    CONSTRAINT item_retain_has_until CHECK (((decision IS DISTINCT FROM 'retain'::public.rights_scope_decision) OR (retain_until IS NOT NULL)))
);


--
-- Name: TABLE rights_request_item; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.rights_request_item IS 'The erasure scope: one row per appearance of the principal in a collected asset. Disposition is applied to asset_consent, never to data_asset.';


--
-- Name: rights_request_item_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_request_item_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_request_item_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rights_request_item_item_id_seq OWNED BY public.rights_request_item.item_id;


--
-- Name: rights_request_ref_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_request_ref_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_request_request_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_request_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_request_request_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rights_request_request_id_seq OWNED BY public.rights_request.request_id;


--
-- Name: rights_response_file; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rights_response_file (
    file_id integer NOT NULL,
    file_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    request_id integer NOT NULL,
    file_ref text NOT NULL,
    file_hash text NOT NULL,
    file_name text NOT NULL,
    size_bytes integer NOT NULL,
    content_type character varying(120),
    uploaded_by integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: rights_response_file_file_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_response_file_file_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_response_file_file_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rights_response_file_file_id_seq OWNED BY public.rights_response_file.file_id;


--
-- Name: rights_ticket_message; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rights_ticket_message (
    message_id integer NOT NULL,
    message_uuid uuid DEFAULT gen_random_uuid() NOT NULL,
    holder_id integer NOT NULL,
    author_user_id integer,
    author_side character varying(10) NOT NULL,
    kind character varying(20) DEFAULT 'message'::character varying NOT NULL,
    body text NOT NULL,
    evidence_ref text,
    evidence_hash text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    evidence_name text,
    CONSTRAINT ticket_message_kind CHECK (((kind)::text = ANY ((ARRAY['brief'::character varying, 'instruction'::character varying, 'message'::character varying, 'return'::character varying, 'escalation'::character varying, 'status'::character varying])::text[]))),
    CONSTRAINT ticket_message_side CHECK (((author_side)::text = ANY ((ARRAY['office'::character varying, 'holder'::character varying, 'system'::character varying])::text[])))
);


--
-- Name: rights_ticket_message_message_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rights_ticket_message_message_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rights_ticket_message_message_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rights_ticket_message_message_id_seq OWNED BY public.rights_ticket_message.message_id;


--
-- Name: v_current_consent; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_current_consent AS
 SELECT consent_id,
    consent_uuid,
    auth_user_id,
    notice_id,
    notice_language_id,
    notice_content_hash,
    link_id,
    served_at,
    affirmative_action_at,
    action_type,
    ip_address,
    is_withdrawal,
    supersedes_consent_id,
    created_at
   FROM public.consent_artefact ca
  WHERE (NOT (EXISTS ( SELECT 1
           FROM public.consent_artefact s
          WHERE (s.supersedes_consent_id = ca.consent_id))));


--
-- Name: asset_consent asset_consent_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_consent ALTER COLUMN asset_consent_id SET DEFAULT nextval('public.asset_consent_asset_consent_id_seq'::regclass);


--
-- Name: auth_user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user ALTER COLUMN id SET DEFAULT nextval('public.auth_user_id_seq'::regclass);


--
-- Name: collection collection_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection ALTER COLUMN collection_id SET DEFAULT nextval('public.collection_collection_id_seq'::regclass);


--
-- Name: consent_artefact consent_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact ALTER COLUMN consent_id SET DEFAULT nextval('public.consent_artefact_consent_id_seq'::regclass);


--
-- Name: consent_link link_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link ALTER COLUMN link_id SET DEFAULT nextval('public.consent_link_link_id_seq'::regclass);


--
-- Name: consent_purpose_grant grant_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_purpose_grant ALTER COLUMN grant_id SET DEFAULT nextval('public.consent_purpose_grant_grant_id_seq'::regclass);


--
-- Name: data_asset asset_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset ALTER COLUMN asset_id SET DEFAULT nextval('public.data_asset_asset_id_seq'::regclass);


--
-- Name: data_source source_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source ALTER COLUMN source_id SET DEFAULT nextval('public.data_source_source_id_seq'::regclass);


--
-- Name: delegation delegation_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation ALTER COLUMN delegation_id SET DEFAULT nextval('public.delegation_delegation_id_seq'::regclass);


--
-- Name: export_line line_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_line ALTER COLUMN line_id SET DEFAULT nextval('public.export_line_line_id_seq'::regclass);


--
-- Name: export_log export_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log ALTER COLUMN export_id SET DEFAULT nextval('public.export_log_export_id_seq'::regclass);


--
-- Name: import_batch batch_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch ALTER COLUMN batch_id SET DEFAULT nextval('public.import_batch_batch_id_seq'::regclass);


--
-- Name: message_template template_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_template ALTER COLUMN template_id SET DEFAULT nextval('public.message_template_template_id_seq'::regclass);


--
-- Name: nomination nomination_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination ALTER COLUMN nomination_id SET DEFAULT nextval('public.nomination_nomination_id_seq'::regclass);


--
-- Name: notice notice_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice ALTER COLUMN notice_id SET DEFAULT nextval('public.notice_notice_id_seq'::regclass);


--
-- Name: notice_language notice_language_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language ALTER COLUMN notice_language_id SET DEFAULT nextval('public.notice_language_notice_language_id_seq'::regclass);


--
-- Name: notice_purpose notice_purpose_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose ALTER COLUMN notice_purpose_id SET DEFAULT nextval('public.notice_purpose_notice_purpose_id_seq'::regclass);


--
-- Name: person_type_history history_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_type_history ALTER COLUMN history_id SET DEFAULT nextval('public.person_type_history_history_id_seq'::regclass);


--
-- Name: processor processor_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor ALTER COLUMN processor_id SET DEFAULT nextval('public.processor_processor_id_seq'::regclass);


--
-- Name: processor_respondent respondent_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor_respondent ALTER COLUMN respondent_id SET DEFAULT nextval('public.processor_respondent_respondent_id_seq'::regclass);


--
-- Name: project project_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project ALTER COLUMN project_id SET DEFAULT nextval('public.project_project_id_seq'::regclass);


--
-- Name: project_approval approval_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_approval ALTER COLUMN approval_id SET DEFAULT nextval('public.project_approval_approval_id_seq'::regclass);


--
-- Name: project_processor project_processor_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor ALTER COLUMN project_processor_id SET DEFAULT nextval('public.project_processor_project_processor_id_seq'::regclass);


--
-- Name: project_site site_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site ALTER COLUMN site_id SET DEFAULT nextval('public.project_site_site_id_seq'::regclass);


--
-- Name: project_status_history history_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_status_history ALTER COLUMN history_id SET DEFAULT nextval('public.project_status_history_history_id_seq'::regclass);


--
-- Name: purpose purpose_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purpose ALTER COLUMN purpose_id SET DEFAULT nextval('public.purpose_purpose_id_seq'::regclass);


--
-- Name: rights_request request_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request ALTER COLUMN request_id SET DEFAULT nextval('public.rights_request_request_id_seq'::regclass);


--
-- Name: rights_request_holder holder_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder ALTER COLUMN holder_id SET DEFAULT nextval('public.rights_request_holder_holder_id_seq'::regclass);


--
-- Name: rights_request_item item_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item ALTER COLUMN item_id SET DEFAULT nextval('public.rights_request_item_item_id_seq'::regclass);


--
-- Name: rights_response_file file_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_response_file ALTER COLUMN file_id SET DEFAULT nextval('public.rights_response_file_file_id_seq'::regclass);


--
-- Name: rights_ticket_message message_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_ticket_message ALTER COLUMN message_id SET DEFAULT nextval('public.rights_ticket_message_message_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: asset_consent asset_consent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_consent
    ADD CONSTRAINT asset_consent_pkey PRIMARY KEY (asset_consent_id);


--
-- Name: audit_log audit_log_log_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_log_uuid_key UNIQUE (log_uuid);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: auth_user auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user auth_user_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT auth_user_uuid_key UNIQUE (uuid);


--
-- Name: collection collection_collection_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_collection_uuid_key UNIQUE (collection_uuid);


--
-- Name: collection collection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_pkey PRIMARY KEY (collection_id);


--
-- Name: collection collection_source_id_source_collection_ref_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_source_id_source_collection_ref_key UNIQUE (source_id, source_collection_ref);


--
-- Name: consent_artefact consent_artefact_consent_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_consent_uuid_key UNIQUE (consent_uuid);


--
-- Name: consent_artefact consent_artefact_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_pkey PRIMARY KEY (consent_id);


--
-- Name: consent_link consent_link_link_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_link_uuid_key UNIQUE (link_uuid);


--
-- Name: consent_link consent_link_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_pkey PRIMARY KEY (link_id);


--
-- Name: consent_link consent_link_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_token_key UNIQUE (token);


--
-- Name: consent_purpose_grant consent_purpose_grant_consent_id_purpose_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_purpose_grant
    ADD CONSTRAINT consent_purpose_grant_consent_id_purpose_id_key UNIQUE (consent_id, purpose_id);


--
-- Name: consent_purpose_grant consent_purpose_grant_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_purpose_grant
    ADD CONSTRAINT consent_purpose_grant_pkey PRIMARY KEY (grant_id);


--
-- Name: data_asset data_asset_asset_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset
    ADD CONSTRAINT data_asset_asset_uuid_key UNIQUE (asset_uuid);


--
-- Name: data_asset data_asset_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset
    ADD CONSTRAINT data_asset_pkey PRIMARY KEY (asset_id);


--
-- Name: data_asset data_asset_source_id_source_asset_ref_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset
    ADD CONSTRAINT data_asset_source_id_source_asset_ref_key UNIQUE (source_id, source_asset_ref);


--
-- Name: data_source data_source_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT data_source_pkey PRIMARY KEY (source_id);


--
-- Name: data_source data_source_source_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT data_source_source_code_key UNIQUE (source_code);


--
-- Name: data_source data_source_source_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT data_source_source_uuid_key UNIQUE (source_uuid);


--
-- Name: delegation delegation_delegation_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_delegation_uuid_key UNIQUE (delegation_uuid);


--
-- Name: delegation delegation_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_pkey PRIMARY KEY (delegation_id);


--
-- Name: export_line export_line_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_line
    ADD CONSTRAINT export_line_pkey PRIMARY KEY (line_id);


--
-- Name: export_log export_log_export_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log
    ADD CONSTRAINT export_log_export_uuid_key UNIQUE (export_uuid);


--
-- Name: export_log export_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log
    ADD CONSTRAINT export_log_pkey PRIMARY KEY (export_id);


--
-- Name: import_batch import_batch_batch_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch
    ADD CONSTRAINT import_batch_batch_uuid_key UNIQUE (batch_uuid);


--
-- Name: import_batch import_batch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch
    ADD CONSTRAINT import_batch_pkey PRIMARY KEY (batch_id);


--
-- Name: message_template message_template_one_per_channel; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_template
    ADD CONSTRAINT message_template_one_per_channel UNIQUE (key, channel);


--
-- Name: message_template message_template_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_template
    ADD CONSTRAINT message_template_pkey PRIMARY KEY (template_id);


--
-- Name: nomination nomination_nomination_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination
    ADD CONSTRAINT nomination_nomination_uuid_key UNIQUE (nomination_uuid);


--
-- Name: nomination nomination_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination
    ADD CONSTRAINT nomination_pkey PRIMARY KEY (nomination_id);


--
-- Name: notice_language notice_language_notice_id_language_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_notice_id_language_code_key UNIQUE (notice_id, language_code);


--
-- Name: notice_language notice_language_notice_language_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_notice_language_uuid_key UNIQUE (notice_language_uuid);


--
-- Name: notice_language notice_language_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_pkey PRIMARY KEY (notice_language_id);


--
-- Name: notice notice_notice_code_version_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice
    ADD CONSTRAINT notice_notice_code_version_key UNIQUE (notice_code, version);


--
-- Name: notice notice_notice_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice
    ADD CONSTRAINT notice_notice_uuid_key UNIQUE (notice_uuid);


--
-- Name: notice notice_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice
    ADD CONSTRAINT notice_pkey PRIMARY KEY (notice_id);


--
-- Name: notice_purpose notice_purpose_notice_id_purpose_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose
    ADD CONSTRAINT notice_purpose_notice_id_purpose_id_key UNIQUE (notice_id, purpose_id);


--
-- Name: notice_purpose notice_purpose_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose
    ADD CONSTRAINT notice_purpose_pkey PRIMARY KEY (notice_purpose_id);


--
-- Name: person_type_history person_type_history_history_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_type_history
    ADD CONSTRAINT person_type_history_history_uuid_key UNIQUE (history_uuid);


--
-- Name: person_type_history person_type_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_type_history
    ADD CONSTRAINT person_type_history_pkey PRIMARY KEY (history_id);


--
-- Name: processor processor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor
    ADD CONSTRAINT processor_pkey PRIMARY KEY (processor_id);


--
-- Name: processor processor_processor_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor
    ADD CONSTRAINT processor_processor_uuid_key UNIQUE (processor_uuid);


--
-- Name: processor_respondent processor_respondent_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor_respondent
    ADD CONSTRAINT processor_respondent_pkey PRIMARY KEY (respondent_id);


--
-- Name: processor_respondent processor_respondent_respondent_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor_respondent
    ADD CONSTRAINT processor_respondent_respondent_uuid_key UNIQUE (respondent_uuid);


--
-- Name: project_approval project_approval_approval_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_approval
    ADD CONSTRAINT project_approval_approval_uuid_key UNIQUE (approval_uuid);


--
-- Name: project_approval project_approval_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_approval
    ADD CONSTRAINT project_approval_pkey PRIMARY KEY (approval_id);


--
-- Name: project project_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_pkey PRIMARY KEY (project_id);


--
-- Name: project_processor project_processor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_pkey PRIMARY KEY (project_processor_id);


--
-- Name: project_processor project_processor_project_id_processor_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_project_id_processor_id_key UNIQUE (project_id, processor_id);


--
-- Name: project project_project_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_project_uuid_key UNIQUE (project_uuid);


--
-- Name: project_site project_site_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_pkey PRIMARY KEY (site_id);


--
-- Name: project_site project_site_site_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_site_uuid_key UNIQUE (site_uuid);


--
-- Name: project_status_history project_status_history_history_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_status_history
    ADD CONSTRAINT project_status_history_history_uuid_key UNIQUE (history_uuid);


--
-- Name: project_status_history project_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_status_history
    ADD CONSTRAINT project_status_history_pkey PRIMARY KEY (history_id);


--
-- Name: purpose purpose_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purpose
    ADD CONSTRAINT purpose_pkey PRIMARY KEY (purpose_id);


--
-- Name: purpose purpose_purpose_code_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purpose
    ADD CONSTRAINT purpose_purpose_code_key UNIQUE (purpose_code);


--
-- Name: purpose purpose_purpose_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purpose
    ADD CONSTRAINT purpose_purpose_uuid_key UNIQUE (purpose_uuid);


--
-- Name: rights_request_holder rights_request_holder_holder_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_holder_uuid_key UNIQUE (holder_uuid);


--
-- Name: rights_request_holder rights_request_holder_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_pkey PRIMARY KEY (holder_id);


--
-- Name: rights_request_item rights_request_item_item_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_item_uuid_key UNIQUE (item_uuid);


--
-- Name: rights_request_item rights_request_item_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_pkey PRIMARY KEY (item_id);


--
-- Name: rights_request_item rights_request_item_request_id_asset_consent_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_request_id_asset_consent_id_key UNIQUE (request_id, asset_consent_id);


--
-- Name: rights_request rights_request_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_pkey PRIMARY KEY (request_id);


--
-- Name: rights_request rights_request_reference_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_reference_key UNIQUE (reference);


--
-- Name: rights_request rights_request_request_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_request_uuid_key UNIQUE (request_uuid);


--
-- Name: rights_response_file rights_response_file_file_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_response_file
    ADD CONSTRAINT rights_response_file_file_uuid_key UNIQUE (file_uuid);


--
-- Name: rights_response_file rights_response_file_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_response_file
    ADD CONSTRAINT rights_response_file_pkey PRIMARY KEY (file_id);


--
-- Name: rights_ticket_message rights_ticket_message_message_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_ticket_message
    ADD CONSTRAINT rights_ticket_message_message_uuid_key UNIQUE (message_uuid);


--
-- Name: rights_ticket_message rights_ticket_message_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_ticket_message
    ADD CONSTRAINT rights_ticket_message_pkey PRIMARY KEY (message_id);


--
-- Name: auth_user_email_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX auth_user_email_hash_key ON public.auth_user USING btree (email_hash);


--
-- Name: auth_user_mobile_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX auth_user_mobile_hash_key ON public.auth_user USING btree (mobile_hash);


--
-- Name: auth_user_organization_id_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX auth_user_organization_id_hash_key ON public.auth_user USING btree (organization_id_hash);


--
-- Name: auth_user_secondary_email_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX auth_user_secondary_email_hash_key ON public.auth_user USING btree (secondary_email_hash);


--
-- Name: auth_user_username_hash_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX auth_user_username_hash_key ON public.auth_user USING btree (username_hash);


--
-- Name: idx_approval_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_approval_project ON public.project_approval USING btree (project_id, uploaded_at DESC);


--
-- Name: idx_artefact_supersedes; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_artefact_supersedes ON public.consent_artefact USING btree (supersedes_consent_id);


--
-- Name: idx_artefact_user_notice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_artefact_user_notice ON public.consent_artefact USING btree (auth_user_id, notice_id, affirmative_action_at DESC);


--
-- Name: idx_asset_collection; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_collection ON public.data_asset USING btree (collection_id);


--
-- Name: idx_asset_consent_asset; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_consent_asset ON public.asset_consent USING btree (asset_id);


--
-- Name: idx_asset_consent_consent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_consent_consent ON public.asset_consent USING btree (consent_id);


--
-- Name: idx_asset_unmapped; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_asset_unmapped ON public.data_asset USING btree (collection_id) WHERE has_unmapped_subjects;


--
-- Name: idx_audit_actor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_actor ON public.audit_log USING btree (actor_user_id, occurred_at DESC);


--
-- Name: idx_audit_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_entity ON public.audit_log USING btree (entity_type, entity_id);


--
-- Name: idx_audit_event; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_event ON public.audit_log USING btree (event_type, occurred_at DESC);


--
-- Name: idx_audit_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_subject ON public.audit_log USING btree (subject_user_id, occurred_at DESC);


--
-- Name: idx_auth_user_full_name_ngrams; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_auth_user_full_name_ngrams ON public.auth_user USING gin (full_name_ngrams);


--
-- Name: idx_batch_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batch_project ON public.import_batch USING btree (project_id, received_at DESC);


--
-- Name: idx_batch_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_batch_source ON public.import_batch USING btree (source_id, received_at DESC);


--
-- Name: idx_collection_batch; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_batch ON public.collection USING btree (batch_id);


--
-- Name: idx_collection_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_collection_project ON public.collection USING btree (project_id, collected_on DESC);


--
-- Name: idx_delegation_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_delegation_active ON public.delegation USING btree (delegate_user_id, delegator_user_id) WHERE (revoked_at IS NULL);


--
-- Name: idx_delegation_by_delegator; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_delegation_by_delegator ON public.delegation USING btree (delegator_user_id);


--
-- Name: idx_export_line_export; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_export_line_export ON public.export_line USING btree (export_id);


--
-- Name: idx_export_line_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_export_line_user ON public.export_line USING btree (auth_user_id);


--
-- Name: idx_export_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_export_project ON public.export_log USING btree (project_id, exported_at DESC);


--
-- Name: idx_grant_consent; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grant_consent ON public.consent_purpose_grant USING btree (consent_id);


--
-- Name: idx_grant_purpose; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_grant_purpose ON public.consent_purpose_grant USING btree (purpose_id) WHERE granted;


--
-- Name: idx_link_notice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_link_notice ON public.consent_link USING btree (notice_id);


--
-- Name: idx_link_site; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_link_site ON public.consent_link USING btree (site_id) WHERE (status = 'active'::public.link_status);


--
-- Name: idx_nomination_nominee_email_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nomination_nominee_email_hash ON public.nomination USING btree (nominee_email_hash);


--
-- Name: idx_nomination_nominee_mobile_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nomination_nominee_mobile_hash ON public.nomination USING btree (nominee_mobile_hash);


--
-- Name: idx_nomination_nominee_name_ngrams; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nomination_nominee_name_ngrams ON public.nomination USING gin (nominee_name_ngrams);


--
-- Name: idx_nomination_principal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_nomination_principal ON public.nomination USING btree (principal_user_id);


--
-- Name: idx_notice_lang_notice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notice_lang_notice ON public.notice_language USING btree (notice_id);


--
-- Name: idx_notice_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notice_project ON public.notice USING btree (project_id, version DESC);


--
-- Name: idx_notice_purpose_notice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_notice_purpose_notice ON public.notice_purpose USING btree (notice_id, display_order);


--
-- Name: idx_processor_respondent_live; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_processor_respondent_live ON public.processor_respondent USING btree (processor_id) WHERE (removed_at IS NULL);


--
-- Name: idx_project_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_created_by ON public.project USING btree (created_by, created_at DESC);


--
-- Name: idx_project_dco; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_dco ON public.project USING btree (dco_user_id, created_at DESC);


--
-- Name: idx_project_processor_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_processor_pending ON public.project_processor USING btree (project_id) WHERE (status = 'pending'::public.processor_request_status);


--
-- Name: idx_project_processor_processor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_processor_processor ON public.project_processor USING btree (processor_id);


--
-- Name: idx_project_processor_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_processor_project ON public.project_processor USING btree (project_id);


--
-- Name: idx_project_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_project_status ON public.project USING btree (project_status, created_at DESC);


--
-- Name: idx_ptype_hist_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ptype_hist_user ON public.person_type_history USING btree (auth_user_id, changed_at DESC);


--
-- Name: idx_rights_holder_request; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_holder_request ON public.rights_request_holder USING btree (request_id);


--
-- Name: idx_rights_holder_responder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_holder_responder ON public.rights_request_holder USING btree (responder_user_id) WHERE (responder_user_id IS NOT NULL);


--
-- Name: idx_rights_item_floor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_item_floor ON public.rights_request_item USING btree (retain_until) WHERE ((decision = 'retain'::public.rights_scope_decision) AND (floor_passed_at IS NULL));


--
-- Name: idx_rights_item_request; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_item_request ON public.rights_request_item USING btree (request_id);


--
-- Name: idx_rights_request_contact_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_request_contact_hash ON public.rights_request USING btree (submitted_contact_hash);


--
-- Name: idx_rights_request_linked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_request_linked ON public.rights_request USING btree (linked_request_id);


--
-- Name: idx_rights_request_status_due; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_request_status_due ON public.rights_request USING btree (status, due_at);


--
-- Name: idx_rights_request_subject; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_request_subject ON public.rights_request USING btree (subject_user_id);


--
-- Name: idx_rights_request_submitted_name_ngrams; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rights_request_submitted_name_ngrams ON public.rights_request USING gin (submitted_name_ngrams);


--
-- Name: idx_site_dco_override; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_site_dco_override ON public.project_site USING btree (dco_override_user_id) WHERE (dco_override_user_id IS NOT NULL);


--
-- Name: idx_site_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_site_project ON public.project_site USING btree (project_id) WHERE (status = 'active'::public.record_status);


--
-- Name: idx_site_source; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_site_source ON public.project_site USING btree (source_id) WHERE (source_id IS NOT NULL);


--
-- Name: idx_source_owner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_source_owner ON public.data_source USING btree (owner_user_id) WHERE (owner_user_id IS NOT NULL);


--
-- Name: idx_status_hist_project; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_status_hist_project ON public.project_status_history USING btree (project_id, occurred_at DESC);


--
-- Name: idx_ticket_message_holder; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ticket_message_holder ON public.rights_ticket_message USING btree (holder_id, message_id);


--
-- Name: idx_user_role_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_role_status ON public.auth_user USING btree (role, status);


--
-- Name: idx_user_via_link; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_via_link ON public.auth_user USING btree (registered_via_link_id);


--
-- Name: nomination_nominee_user_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX nomination_nominee_user_id_idx ON public.nomination USING btree (nominee_user_id) WHERE (nominee_user_id IS NOT NULL);


--
-- Name: rights_request_consent_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX rights_request_consent_idx ON public.rights_request USING btree (consent_id) WHERE (consent_id IS NOT NULL);


--
-- Name: rights_response_file_request_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX rights_response_file_request_idx ON public.rights_response_file USING btree (request_id);


--
-- Name: uq_artefact_one_root_per_notice; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_artefact_one_root_per_notice ON public.consent_artefact USING btree (auth_user_id, notice_id) WHERE (supersedes_consent_id IS NULL);


--
-- Name: uq_artefact_supersedes_once; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_artefact_supersedes_once ON public.consent_artefact USING btree (supersedes_consent_id) WHERE (supersedes_consent_id IS NOT NULL);


--
-- Name: uq_delegation_live; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_delegation_live ON public.delegation USING btree (delegator_user_id, delegate_user_id) WHERE ((revoked_at IS NULL) AND (ends_at IS NULL));


--
-- Name: uq_nomination_live; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_nomination_live ON public.nomination USING btree (principal_user_id) WHERE (status = ANY (ARRAY['pending'::public.nomination_status, 'active'::public.nomination_status]));


--
-- Name: uq_processor_respondent_user; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_processor_respondent_user ON public.processor_respondent USING btree (processor_id, user_id) WHERE ((user_id IS NOT NULL) AND (removed_at IS NULL));


--
-- Name: uq_rights_holder_processor; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_rights_holder_processor ON public.rights_request_holder USING btree (request_id, processor_id) WHERE (processor_id IS NOT NULL);


--
-- Name: project_approval trg_approval_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_approval_append_only BEFORE DELETE OR UPDATE ON public.project_approval FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: audit_log trg_audit_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_append_only BEFORE DELETE OR UPDATE ON public.audit_log FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: audit_log trg_audit_chain; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_audit_chain BEFORE INSERT ON public.audit_log FOR EACH ROW EXECUTE FUNCTION public.cmp_audit_chain();


--
-- Name: auth_user trg_auth_user_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_auth_user_touch BEFORE UPDATE ON public.auth_user FOR EACH ROW EXECUTE FUNCTION public.cmp_touch_updated_at();


--
-- Name: consent_artefact trg_consent_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_consent_append_only BEFORE DELETE OR UPDATE ON public.consent_artefact FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: consent_artefact trg_consent_coherent; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_consent_coherent BEFORE INSERT ON public.consent_artefact FOR EACH ROW EXECUTE FUNCTION public.cmp_consent_coherent();


--
-- Name: auth_user trg_contact_belongs_to_one_person; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_contact_belongs_to_one_person BEFORE INSERT OR UPDATE OF email_hash, secondary_email_hash ON public.auth_user FOR EACH ROW EXECUTE FUNCTION public.cmp_contact_belongs_to_one_person();


--
-- Name: export_line trg_export_line_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_export_line_append_only BEFORE DELETE OR UPDATE ON public.export_line FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: export_log trg_export_log_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_export_log_append_only BEFORE DELETE OR UPDATE ON public.export_log FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: consent_purpose_grant trg_grant_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_grant_append_only BEFORE DELETE OR UPDATE ON public.consent_purpose_grant FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: consent_purpose_grant trg_grant_in_notice; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_grant_in_notice BEFORE INSERT ON public.consent_purpose_grant FOR EACH ROW EXECUTE FUNCTION public.cmp_grant_in_notice();


--
-- Name: consent_link trg_link_coherent; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_link_coherent BEFORE INSERT ON public.consent_link FOR EACH ROW EXECUTE FUNCTION public.cmp_link_coherent();


--
-- Name: consent_link trg_link_use_count_guard; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_link_use_count_guard BEFORE UPDATE ON public.consent_link FOR EACH ROW EXECUTE FUNCTION public.cmp_link_use_count_guard();


--
-- Name: nomination trg_nominee_needs_mobile; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_nominee_needs_mobile BEFORE INSERT ON public.nomination FOR EACH ROW EXECUTE FUNCTION public.cmp_nominee_needs_mobile();


--
-- Name: notice trg_notice_freeze; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notice_freeze BEFORE UPDATE ON public.notice FOR EACH ROW EXECUTE FUNCTION public.cmp_notice_freeze();


--
-- Name: notice_language trg_notice_language_freeze; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notice_language_freeze BEFORE UPDATE ON public.notice_language FOR EACH ROW EXECUTE FUNCTION public.cmp_notice_language_freeze();


--
-- Name: notice_language trg_notice_language_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notice_language_touch BEFORE UPDATE ON public.notice_language FOR EACH ROW EXECUTE FUNCTION public.cmp_touch_updated_at();


--
-- Name: notice_purpose trg_notice_purpose_freeze; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notice_purpose_freeze BEFORE INSERT OR DELETE OR UPDATE ON public.notice_purpose FOR EACH ROW EXECUTE FUNCTION public.cmp_notice_purpose_freeze();


--
-- Name: notice trg_notice_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_notice_touch BEFORE UPDATE ON public.notice FOR EACH ROW EXECUTE FUNCTION public.cmp_touch_updated_at();


--
-- Name: person_type_history trg_person_type_history_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_person_type_history_append_only BEFORE DELETE OR UPDATE ON public.person_type_history FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: project_status_history trg_project_history_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_project_history_append_only BEFORE DELETE OR UPDATE ON public.project_status_history FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: project trg_project_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_project_touch BEFORE UPDATE ON public.project FOR EACH ROW EXECUTE FUNCTION public.cmp_touch_updated_at();


--
-- Name: purpose trg_purpose_touch; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_purpose_touch BEFORE UPDATE ON public.purpose FOR EACH ROW EXECUTE FUNCTION public.cmp_touch_updated_at();


--
-- Name: project_site trg_site_owner; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_site_owner AFTER INSERT OR DELETE OR UPDATE OF source_id, dco_override_user_id, status, project_id ON public.project_site FOR EACH ROW EXECUTE FUNCTION public.cmp_site_owner_changed();


--
-- Name: data_source trg_source_owner; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_source_owner AFTER UPDATE OF owner_user_id ON public.data_source FOR EACH ROW EXECUTE FUNCTION public.cmp_source_owner_changed();


--
-- Name: auth_user trg_subject_needs_mobile; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_subject_needs_mobile BEFORE INSERT ON public.auth_user FOR EACH ROW EXECUTE FUNCTION public.cmp_subject_needs_mobile();


--
-- Name: rights_ticket_message trg_ticket_message_append_only; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_ticket_message_append_only BEFORE DELETE OR UPDATE ON public.rights_ticket_message FOR EACH STATEMENT EXECUTE FUNCTION public.cmp_append_only();


--
-- Name: asset_consent asset_consent_asset_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_consent
    ADD CONSTRAINT asset_consent_asset_id_fkey FOREIGN KEY (asset_id) REFERENCES public.data_asset(asset_id);


--
-- Name: asset_consent asset_consent_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.asset_consent
    ADD CONSTRAINT asset_consent_consent_id_fkey FOREIGN KEY (consent_id) REFERENCES public.consent_artefact(consent_id);


--
-- Name: audit_log audit_log_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.auth_user(id);


--
-- Name: audit_log audit_log_subject_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_subject_user_id_fkey FOREIGN KEY (subject_user_id) REFERENCES public.auth_user(id);


--
-- Name: collection collection_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_batch_id_fkey FOREIGN KEY (batch_id) REFERENCES public.import_batch(batch_id);


--
-- Name: collection collection_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: collection collection_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.project_site(site_id);


--
-- Name: collection collection_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.collection
    ADD CONSTRAINT collection_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_source(source_id);


--
-- Name: consent_artefact consent_artefact_auth_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_auth_user_id_fkey FOREIGN KEY (auth_user_id) REFERENCES public.auth_user(id);


--
-- Name: consent_artefact consent_artefact_link_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_link_id_fkey FOREIGN KEY (link_id) REFERENCES public.consent_link(link_id);


--
-- Name: consent_artefact consent_artefact_notice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_notice_id_fkey FOREIGN KEY (notice_id) REFERENCES public.notice(notice_id);


--
-- Name: consent_artefact consent_artefact_notice_language_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_notice_language_id_fkey FOREIGN KEY (notice_language_id) REFERENCES public.notice_language(notice_language_id);


--
-- Name: consent_artefact consent_artefact_supersedes_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_artefact
    ADD CONSTRAINT consent_artefact_supersedes_consent_id_fkey FOREIGN KEY (supersedes_consent_id) REFERENCES public.consent_artefact(consent_id);


--
-- Name: consent_link consent_link_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: consent_link consent_link_notice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_notice_id_fkey FOREIGN KEY (notice_id) REFERENCES public.notice(notice_id);


--
-- Name: consent_link consent_link_revoked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_revoked_by_fkey FOREIGN KEY (revoked_by) REFERENCES public.auth_user(id);


--
-- Name: consent_link consent_link_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_link
    ADD CONSTRAINT consent_link_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.project_site(site_id);


--
-- Name: consent_purpose_grant consent_purpose_grant_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_purpose_grant
    ADD CONSTRAINT consent_purpose_grant_consent_id_fkey FOREIGN KEY (consent_id) REFERENCES public.consent_artefact(consent_id);


--
-- Name: consent_purpose_grant consent_purpose_grant_purpose_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consent_purpose_grant
    ADD CONSTRAINT consent_purpose_grant_purpose_id_fkey FOREIGN KEY (purpose_id) REFERENCES public.purpose(purpose_id);


--
-- Name: data_asset data_asset_collection_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset
    ADD CONSTRAINT data_asset_collection_id_fkey FOREIGN KEY (collection_id) REFERENCES public.collection(collection_id);


--
-- Name: data_asset data_asset_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_asset
    ADD CONSTRAINT data_asset_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_source(source_id);


--
-- Name: data_source data_source_owner_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT data_source_owner_user_id_fkey FOREIGN KEY (owner_user_id) REFERENCES public.auth_user(id);


--
-- Name: data_source data_source_processor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT data_source_processor_id_fkey FOREIGN KEY (processor_id) REFERENCES public.processor(processor_id);


--
-- Name: delegation delegation_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: delegation delegation_delegate_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_delegate_user_id_fkey FOREIGN KEY (delegate_user_id) REFERENCES public.auth_user(id);


--
-- Name: delegation delegation_delegator_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_delegator_user_id_fkey FOREIGN KEY (delegator_user_id) REFERENCES public.auth_user(id);


--
-- Name: delegation delegation_revoked_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.delegation
    ADD CONSTRAINT delegation_revoked_by_fkey FOREIGN KEY (revoked_by) REFERENCES public.auth_user(id);


--
-- Name: export_line export_line_auth_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_line
    ADD CONSTRAINT export_line_auth_user_id_fkey FOREIGN KEY (auth_user_id) REFERENCES public.auth_user(id);


--
-- Name: export_line export_line_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_line
    ADD CONSTRAINT export_line_consent_id_fkey FOREIGN KEY (consent_id) REFERENCES public.consent_artefact(consent_id);


--
-- Name: export_line export_line_export_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_line
    ADD CONSTRAINT export_line_export_id_fkey FOREIGN KEY (export_id) REFERENCES public.export_log(export_id);


--
-- Name: export_log export_log_exported_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log
    ADD CONSTRAINT export_log_exported_by_fkey FOREIGN KEY (exported_by) REFERENCES public.auth_user(id);


--
-- Name: export_log export_log_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log
    ADD CONSTRAINT export_log_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: export_log export_log_site_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.export_log
    ADD CONSTRAINT export_log_site_id_fkey FOREIGN KEY (site_id) REFERENCES public.project_site(site_id);


--
-- Name: project fk_project_notice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT fk_project_notice FOREIGN KEY (current_notice_id) REFERENCES public.notice(notice_id);


--
-- Name: data_source fk_source_site; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_source
    ADD CONSTRAINT fk_source_site FOREIGN KEY (site_id) REFERENCES public.project_site(site_id);


--
-- Name: auth_user fk_user_link; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.auth_user
    ADD CONSTRAINT fk_user_link FOREIGN KEY (registered_via_link_id) REFERENCES public.consent_link(link_id);


--
-- Name: import_batch import_batch_imported_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch
    ADD CONSTRAINT import_batch_imported_by_fkey FOREIGN KEY (imported_by) REFERENCES public.auth_user(id);


--
-- Name: import_batch import_batch_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch
    ADD CONSTRAINT import_batch_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: import_batch import_batch_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_batch
    ADD CONSTRAINT import_batch_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_source(source_id);


--
-- Name: message_template message_template_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.message_template
    ADD CONSTRAINT message_template_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.auth_user(id);


--
-- Name: nomination nomination_invoked_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination
    ADD CONSTRAINT nomination_invoked_request_id_fkey FOREIGN KEY (invoked_request_id) REFERENCES public.rights_request(request_id);


--
-- Name: nomination nomination_nominee_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination
    ADD CONSTRAINT nomination_nominee_user_id_fkey FOREIGN KEY (nominee_user_id) REFERENCES public.auth_user(id);


--
-- Name: nomination nomination_principal_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.nomination
    ADD CONSTRAINT nomination_principal_user_id_fkey FOREIGN KEY (principal_user_id) REFERENCES public.auth_user(id);


--
-- Name: notice notice_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice
    ADD CONSTRAINT notice_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.auth_user(id);


--
-- Name: notice_language notice_language_approved_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_approved_by_fkey FOREIGN KEY (approved_by) REFERENCES public.auth_user(id);


--
-- Name: notice_language notice_language_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: notice_language notice_language_notice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_language
    ADD CONSTRAINT notice_language_notice_id_fkey FOREIGN KEY (notice_id) REFERENCES public.notice(notice_id);


--
-- Name: notice notice_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice
    ADD CONSTRAINT notice_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: notice_purpose notice_purpose_notice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose
    ADD CONSTRAINT notice_purpose_notice_id_fkey FOREIGN KEY (notice_id) REFERENCES public.notice(notice_id);


--
-- Name: notice_purpose notice_purpose_overridden_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose
    ADD CONSTRAINT notice_purpose_overridden_by_fkey FOREIGN KEY (overridden_by) REFERENCES public.auth_user(id);


--
-- Name: notice_purpose notice_purpose_purpose_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_purpose
    ADD CONSTRAINT notice_purpose_purpose_id_fkey FOREIGN KEY (purpose_id) REFERENCES public.purpose(purpose_id);


--
-- Name: person_type_history person_type_history_auth_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_type_history
    ADD CONSTRAINT person_type_history_auth_user_id_fkey FOREIGN KEY (auth_user_id) REFERENCES public.auth_user(id);


--
-- Name: person_type_history person_type_history_changed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.person_type_history
    ADD CONSTRAINT person_type_history_changed_by_fkey FOREIGN KEY (changed_by) REFERENCES public.auth_user(id);


--
-- Name: processor_respondent processor_respondent_processor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor_respondent
    ADD CONSTRAINT processor_respondent_processor_id_fkey FOREIGN KEY (processor_id) REFERENCES public.processor(processor_id);


--
-- Name: processor_respondent processor_respondent_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processor_respondent
    ADD CONSTRAINT processor_respondent_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.auth_user(id);


--
-- Name: project_approval project_approval_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_approval
    ADD CONSTRAINT project_approval_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: project_approval project_approval_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_approval
    ADD CONSTRAINT project_approval_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.auth_user(id);


--
-- Name: project project_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: project project_dco_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project
    ADD CONSTRAINT project_dco_user_id_fkey FOREIGN KEY (dco_user_id) REFERENCES public.auth_user(id);


--
-- Name: project_processor project_processor_added_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_added_by_fkey FOREIGN KEY (added_by) REFERENCES public.auth_user(id);


--
-- Name: project_processor project_processor_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.auth_user(id);


--
-- Name: project_processor project_processor_processor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_processor_id_fkey FOREIGN KEY (processor_id) REFERENCES public.processor(processor_id);


--
-- Name: project_processor project_processor_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_processor
    ADD CONSTRAINT project_processor_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: project_site project_site_dco_override_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_dco_override_by_fkey FOREIGN KEY (dco_override_by) REFERENCES public.auth_user(id);


--
-- Name: project_site project_site_dco_override_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_dco_override_user_id_fkey FOREIGN KEY (dco_override_user_id) REFERENCES public.auth_user(id);


--
-- Name: project_site project_site_processor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_processor_id_fkey FOREIGN KEY (processor_id) REFERENCES public.processor(processor_id);


--
-- Name: project_site project_site_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: project_site project_site_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_site
    ADD CONSTRAINT project_site_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.data_source(source_id);


--
-- Name: project_status_history project_status_history_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_status_history
    ADD CONSTRAINT project_status_history_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.auth_user(id);


--
-- Name: project_status_history project_status_history_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.project_status_history
    ADD CONSTRAINT project_status_history_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.project(project_id);


--
-- Name: purpose purpose_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purpose
    ADD CONSTRAINT purpose_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request rights_request_classified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_classified_by_fkey FOREIGN KEY (classified_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request rights_request_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_consent_id_fkey FOREIGN KEY (consent_id) REFERENCES public.consent_artefact(consent_id);


--
-- Name: rights_request rights_request_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request_holder rights_request_holder_confirmed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_confirmed_by_fkey FOREIGN KEY (confirmed_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request_holder rights_request_holder_processor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_processor_id_fkey FOREIGN KEY (processor_id) REFERENCES public.processor(processor_id);


--
-- Name: rights_request_holder rights_request_holder_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.rights_request(request_id);


--
-- Name: rights_request_holder rights_request_holder_respondent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_respondent_id_fkey FOREIGN KEY (respondent_id) REFERENCES public.processor_respondent(respondent_id);


--
-- Name: rights_request_holder rights_request_holder_responder_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_holder
    ADD CONSTRAINT rights_request_holder_responder_user_id_fkey FOREIGN KEY (responder_user_id) REFERENCES public.auth_user(id);


--
-- Name: rights_request_item rights_request_item_asset_consent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_asset_consent_id_fkey FOREIGN KEY (asset_consent_id) REFERENCES public.asset_consent(asset_consent_id);


--
-- Name: rights_request_item rights_request_item_decided_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_decided_by_fkey FOREIGN KEY (decided_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request_item rights_request_item_holder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES public.rights_request_holder(holder_id);


--
-- Name: rights_request_item rights_request_item_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request_item
    ADD CONSTRAINT rights_request_item_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.rights_request(request_id);


--
-- Name: rights_request rights_request_linked_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_linked_request_id_fkey FOREIGN KEY (linked_request_id) REFERENCES public.rights_request(request_id);


--
-- Name: rights_request rights_request_nomination_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_nomination_id_fkey FOREIGN KEY (nomination_id) REFERENCES public.nomination(nomination_id);


--
-- Name: rights_request rights_request_responded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_responded_by_fkey FOREIGN KEY (responded_by) REFERENCES public.auth_user(id);


--
-- Name: rights_request rights_request_reviewer_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_reviewer_user_id_fkey FOREIGN KEY (reviewer_user_id) REFERENCES public.auth_user(id);


--
-- Name: rights_request rights_request_subject_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_subject_user_id_fkey FOREIGN KEY (subject_user_id) REFERENCES public.auth_user(id);


--
-- Name: rights_request rights_request_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_request
    ADD CONSTRAINT rights_request_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.auth_user(id);


--
-- Name: rights_response_file rights_response_file_request_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_response_file
    ADD CONSTRAINT rights_response_file_request_id_fkey FOREIGN KEY (request_id) REFERENCES public.rights_request(request_id);


--
-- Name: rights_response_file rights_response_file_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_response_file
    ADD CONSTRAINT rights_response_file_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.auth_user(id);


--
-- Name: rights_ticket_message rights_ticket_message_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_ticket_message
    ADD CONSTRAINT rights_ticket_message_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES public.auth_user(id);


--
-- Name: rights_ticket_message rights_ticket_message_holder_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rights_ticket_message
    ADD CONSTRAINT rights_ticket_message_holder_id_fkey FOREIGN KEY (holder_id) REFERENCES public.rights_request_holder(holder_id);


--
-- PostgreSQL database dump complete
--

\unrestrict unFgVPf0byVBjujp72hF1EEPO4qjyTYMEFlLYfipX5CiEBNddX1VrRJpaAZ6h2Y

