-- SpecID schema v0.6 (PostgreSQL 16). v0.5 consolidated PRD v0.4 Appendix E + TRD + App Flow;
-- v0.6 adds multi-CPSE consent (review_consent, AWAITING_CONSENT) and change notices (change_notice).
-- gen_random_uuid() is built in since PG 13. No extensions required.

-- ===== Organisations and access =====
CREATE TABLE cpse (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code text NOT NULL UNIQUE,
  name text NOT NULL,
  sector text,
  vendor_salt text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_user (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  username text NOT NULL UNIQUE,
  display_name text,
  password_hash text NOT NULL,
  role text NOT NULL CHECK (role IN ('MAKER','CHECKER','ADMIN','AUDITOR','INTEGRATOR')),
  cpse_id uuid REFERENCES cpse(id),
  is_active boolean NOT NULL DEFAULT true,
  must_change_password boolean NOT NULL DEFAULT true,
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE api_key (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES app_user(id),
  key_hash text NOT NULL UNIQUE,
  label text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);

-- ===== Ingestion =====
CREATE TABLE upload_batch (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cpse_id uuid NOT NULL REFERENCES cpse(id),
  filename text NOT NULL,
  file_sha256 text NOT NULL,
  status text NOT NULL CHECK (status IN ('UPLOADED','MAPPED','INGESTING','INGESTED','FAILED')),
  column_mapping jsonb,
  row_count integer,
  quality jsonb,
  is_synthetic boolean NOT NULL DEFAULT false,
  created_by uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX upload_batch_cpse_idx ON upload_batch (cpse_id);

CREATE TABLE material_record (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id uuid NOT NULL REFERENCES upload_batch(id) ON DELETE CASCADE,
  cpse_id uuid NOT NULL REFERENCES cpse(id),
  legacy_code text NOT NULL,
  short_text text NOT NULL,
  long_text text,
  uom text,
  uom_canonical text,
  mat_group text,
  manufacturer text,
  mpn text,
  plant text,
  criticality text,
  annual_value numeric CHECK (annual_value IS NULL OR annual_value >= 0),
  annual_qty numeric CHECK (annual_qty IS NULL OR annual_qty >= 0),
  content_hash text NOT NULL,
  raw jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (cpse_id, legacy_code, batch_id)
);
CREATE INDEX material_record_cpse_idx ON material_record (cpse_id, legacy_code);
CREATE INDEX material_record_batch_idx ON material_record (batch_id);
CREATE UNIQUE INDEX material_record_idem_uq ON material_record (cpse_id, legacy_code, content_hash);
CREATE INDEX material_record_mpn_idx ON material_record (upper(manufacturer), upper(mpn)) WHERE mpn IS NOT NULL;

CREATE TABLE procurement_line (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  record_id uuid NOT NULL REFERENCES material_record(id) ON DELETE CASCADE,
  po_date date NOT NULL,
  qty numeric NOT NULL CHECK (qty >= 0),
  uom text,
  unit_price numeric CHECK (unit_price IS NULL OR unit_price >= 0),
  currency text NOT NULL DEFAULT 'INR',
  vendor_hash text,
  plant text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX procurement_line_record_idx ON procurement_line (record_id, po_date);

-- ===== Rulebook =====
CREATE TABLE template (
  id text NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  category text NOT NULL,
  definition jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('DRAFT','ACTIVE','RETIRED')),
  golden_passed integer,
  golden_failed integer,
  created_by uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  activated_by uuid REFERENCES app_user(id),
  activated_at timestamptz,
  PRIMARY KEY (id, version)
);
CREATE UNIQUE INDEX template_one_active_uq ON template (id) WHERE status = 'ACTIVE';

CREATE TABLE dictionary (
  kind text NOT NULL CHECK (kind IN ('ABBREVIATION','UOM','HEADER_SYNONYM','UNSPSC_MAP')),
  version integer NOT NULL CHECK (version >= 1),
  content jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('DRAFT','ACTIVE','RETIRED')),
  created_by uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, version)
);
CREATE UNIQUE INDEX dictionary_one_active_uq ON dictionary (kind) WHERE status = 'ACTIVE';

-- ===== Specifications =====
CREATE TABLE spec_record (
  record_id uuid PRIMARY KEY REFERENCES material_record(id) ON DELETE CASCADE,
  template_id text,
  template_version integer,
  category text,
  class_source text NOT NULL DEFAULT 'NONE' CHECK (class_source IN ('RULE','ML','NONE')),
  class_prob numeric CHECK (class_prob IS NULL OR (class_prob >= 0 AND class_prob <= 1)),
  class_path text[],
  norm_text text NOT NULL,
  attrs jsonb NOT NULL DEFAULT '{}',
  attr_meta jsonb NOT NULL DEFAULT '{}',
  residual text[] NOT NULL DEFAULT '{}',
  spec_completeness numeric,
  embedding real[],
  dictionary_version integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX spec_record_category_idx ON spec_record (category);
CREATE INDEX spec_record_block_idx ON spec_record (category, ((attrs->>'size_dn')));

CREATE TABLE attribute_supply (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  record_id uuid NOT NULL REFERENCES material_record(id) ON DELETE CASCADE,
  attr text NOT NULL,
  value text NOT NULL,
  source_note text NOT NULL CHECK (char_length(source_note) >= 5),
  supplied_by uuid NOT NULL REFERENCES app_user(id),
  supplied_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX attribute_supply_record_idx ON attribute_supply (record_id);

-- ===== Runs and decisions =====
CREATE TABLE run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_ids uuid[] NOT NULL,
  mode text NOT NULL CHECK (mode IN ('CROSS_CPSE','WITHIN_CPSE','BOTH')),
  config jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL CHECK (status IN ('QUEUED','RUNNING','CANCELLING','CANCELLED','DONE','FAILED')),
  stats jsonb,
  error text,
  started_by uuid REFERENCES app_user(id),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz
);
CREATE INDEX run_status_idx ON run (status, started_at DESC);

CREATE TABLE pair_decision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  rec_a uuid NOT NULL REFERENCES material_record(id),
  rec_b uuid NOT NULL REFERENCES material_record(id),
  verdict text NOT NULL CHECK (verdict IN ('IDENTICAL','EQUIVALENT','NOT_EQUIVALENT','INSUFFICIENT_DATA')),
  route text NOT NULL CHECK (route IN ('AUTO_ELIGIBLE','REVIEW','NONE')),
  p_equiv numeric,
  text_sim numeric CHECK (text_sim IS NULL OR (text_sim >= 0 AND text_sim <= 1)),
  baseline jsonb,
  lookalike text CHECK (lookalike IN ('LOOKALIKE_VETOED','HIDDEN_TWIN')),
  channels smallint NOT NULL DEFAULT 0,
  reasons text[] NOT NULL DEFAULT '{}',
  evidence jsonb NOT NULL,
  model_version text,
  template_version integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (rec_a < rec_b),
  UNIQUE (run_id, rec_a, rec_b)
);
CREATE INDEX pair_decision_run_verdict_idx ON pair_decision (run_id, verdict);
CREATE INDEX pair_decision_lookalike_idx ON pair_decision (run_id, lookalike) WHERE lookalike IS NOT NULL;
CREATE INDEX pair_decision_rec_b_idx ON pair_decision (run_id, rec_b);

CREATE TABLE cannot_link (
  rec_a uuid NOT NULL REFERENCES material_record(id) ON DELETE CASCADE,
  rec_b uuid NOT NULL REFERENCES material_record(id) ON DELETE CASCADE,
  reason text NOT NULL,
  created_by uuid NOT NULL REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (rec_a < rec_b),
  PRIMARY KEY (rec_a, rec_b)
);

CREATE TABLE substitution (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid REFERENCES run(id) ON DELETE SET NULL,
  from_record uuid NOT NULL REFERENCES material_record(id),
  to_record uuid NOT NULL REFERENCES material_record(id),
  rule text NOT NULL,
  status text NOT NULL CHECK (status IN ('PROPOSED','APPROVED','REJECTED')),
  approver_id uuid REFERENCES app_user(id),
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (from_record <> to_record),
  UNIQUE (from_record, to_record, rule)
);

-- ===== Clusters and review =====
CREATE TABLE cluster (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  category text,
  status text NOT NULL CHECK (status IN ('PROPOSED','APPROVED','REJECTED','SPLIT')),
  cohesion numeric,
  needs_review boolean NOT NULL DEFAULT true,
  is_critical boolean NOT NULL DEFAULT false,
  flags_count integer NOT NULL DEFAULT 0,
  priority numeric,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cluster_run_status_idx ON cluster (run_id, status, priority DESC);

CREATE TABLE cluster_member (
  cluster_id uuid NOT NULL REFERENCES cluster(id) ON DELETE CASCADE,
  record_id uuid NOT NULL REFERENCES material_record(id),
  PRIMARY KEY (cluster_id, record_id)
);
CREATE INDEX cluster_member_record_idx ON cluster_member (record_id);

CREATE TABLE blocked_edge (
  id bigserial PRIMARY KEY,
  run_id uuid NOT NULL REFERENCES run(id) ON DELETE CASCADE,
  rec_a uuid NOT NULL REFERENCES material_record(id),
  rec_b uuid NOT NULL REFERENCES material_record(id),
  blocking_a uuid NOT NULL REFERENCES material_record(id),
  blocking_b uuid NOT NULL REFERENCES material_record(id),
  reason text NOT NULL
);
CREATE INDEX blocked_edge_run_idx ON blocked_edge (run_id);

CREATE TABLE review_task (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cluster_id uuid NOT NULL UNIQUE REFERENCES cluster(id) ON DELETE CASCADE,
  state text NOT NULL CHECK (state IN ('OPEN','MADE','AWAITING_CONSENT','DONE')),
  made_by uuid REFERENCES app_user(id),
  proposed_decision text CHECK (proposed_decision IN ('APPROVE','REJECT','SPLIT','NEEDS_INFO')),
  checked_by uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (checked_by IS NULL OR made_by IS NULL OR checked_by <> made_by)
);
CREATE INDEX review_task_state_idx ON review_task (state);

CREATE TABLE review_decision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id uuid NOT NULL REFERENCES review_task(id) ON DELETE CASCADE,
  actor_id uuid NOT NULL REFERENCES app_user(id),
  actor_role text NOT NULL CHECK (actor_role IN ('MAKER','CHECKER')),
  decision text NOT NULL CHECK (decision IN ('APPROVE','REJECT','SPLIT','NEEDS_INFO','CONFIRM','OVERTURN')),
  comment text,
  split_groups jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX review_decision_task_idx ON review_decision (task_id);

-- Multi-CPSE consent (SF-11): one row per participating CPSE per task
CREATE TABLE review_consent (
  task_id uuid NOT NULL REFERENCES review_task(id) ON DELETE CASCADE,
  cpse_id uuid NOT NULL REFERENCES cpse(id),
  user_id uuid NOT NULL REFERENCES app_user(id),
  decision text NOT NULL CHECK (decision IN ('CONSENT','DECLINE')),
  via text NOT NULL CHECK (via IN ('MAKER_PROPOSAL','CHECKER_CONFIRMATION','STEWARD')),
  reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (task_id, cpse_id),
  CHECK (decision = 'CONSENT' OR char_length(coalesce(reason, '')) >= 5)
);
CREATE INDEX review_consent_cpse_idx ON review_consent (cpse_id, decision);

-- ===== Registry =====
CREATE SEQUENCE cnmc_seq START 1;

CREATE TABLE cnmc (
  cnmc text PRIMARY KEY CHECK (cnmc ~ '^NMC-[0-9]{11}$'),
  template_id text,
  template_version integer,
  category text NOT NULL,
  class_path text[],
  unspsc text,
  canonical_spec jsonb NOT NULL,
  spec_completeness numeric,
  variants jsonb NOT NULL DEFAULT '[]',
  base_uom text,
  short_desc_40 text CHECK (char_length(short_desc_40) <= 40),
  long_desc text,
  status text NOT NULL CHECK (status IN ('ACTIVE','MERGED','DEPRECATED')),
  merged_into text REFERENCES cnmc(cnmc),
  source_cluster uuid REFERENCES cluster(id),
  version integer NOT NULL DEFAULT 1,
  issued_by uuid REFERENCES app_user(id),
  issued_at timestamptz NOT NULL DEFAULT now(),
  CHECK (status <> 'MERGED' OR merged_into IS NOT NULL)
);
CREATE INDEX cnmc_category_idx ON cnmc (category, status);

CREATE TABLE crosswalk (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cnmc text NOT NULL REFERENCES cnmc(cnmc),
  record_id uuid NOT NULL REFERENCES material_record(id),
  cpse_id uuid NOT NULL REFERENCES cpse(id),
  legacy_code text NOT NULL,
  relation text NOT NULL CHECK (relation IN ('IDENTICAL','EQUIVALENT')),
  status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REMOVED')),
  uom text,
  uom_factor numeric CHECK (uom_factor IS NULL OR uom_factor > 0),
  migration_action text CHECK (migration_action IN ('RETAIN','BLOCK_FOR_NEW_PROCUREMENT','PHASE_OUT_WHEN_STOCK_ZERO')),
  cluster_id uuid REFERENCES cluster(id),
  approver_id uuid REFERENCES app_user(id),
  approved_at timestamptz NOT NULL DEFAULT now(),
  removed_by uuid REFERENCES app_user(id),
  removed_at timestamptz,
  remove_reason text,
  CHECK (status = 'ACTIVE' OR (removed_by IS NOT NULL AND removed_at IS NOT NULL AND remove_reason IS NOT NULL))
);
CREATE UNIQUE INDEX crosswalk_active_uq ON crosswalk (cpse_id, legacy_code) WHERE status = 'ACTIVE';
CREATE INDEX crosswalk_cnmc_idx ON crosswalk (cnmc);
CREATE INDEX crosswalk_record_idx ON crosswalk (record_id);

-- ===== Change notices per CPSE (SF-12, P1) =====
CREATE TABLE change_notice (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cpse_id uuid NOT NULL REFERENCES cpse(id),
  kind text NOT NULL CHECK (kind IN ('CNMC_ISSUED','CNMC_MERGED','CROSSWALK_REMOVED','CONSENT_DECLINED','TEMPLATE_ACTIVATED')),
  object_type text NOT NULL,
  object_id text NOT NULL,
  summary text NOT NULL,
  delta jsonb NOT NULL DEFAULT '[]',
  audit_event_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  acknowledged_by uuid REFERENCES app_user(id),
  acknowledged_at timestamptz,
  CHECK ((acknowledged_by IS NULL) = (acknowledged_at IS NULL))
);
CREATE INDEX change_notice_inbox_idx ON change_notice (cpse_id, acknowledged_at, created_at DESC);

-- ===== Evaluation =====
CREATE TABLE eval_run (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind text NOT NULL CHECK (kind IN ('SYNTHETIC','PUBLIC','PILOT')),
  run_id uuid REFERENCES run(id) ON DELETE SET NULL,
  seed integer,
  config jsonb NOT NULL DEFAULT '{}',
  status text NOT NULL CHECK (status IN ('QUEUED','RUNNING','DONE','FAILED')),
  metrics jsonb,
  git_commit text,
  report_path text,
  created_by uuid REFERENCES app_user(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ===== Audit (append-only) =====
CREATE TABLE audit_event (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL,
  actor_id uuid REFERENCES app_user(id),
  action text NOT NULL,
  object_type text NOT NULL,
  object_id text NOT NULL,
  before jsonb,
  after jsonb,
  prev_hash text,
  hash text NOT NULL UNIQUE
);
CREATE INDEX audit_event_object_idx ON audit_event (object_type, object_id);
CREATE INDEX audit_event_actor_idx ON audit_event (actor_id, ts);

CREATE FUNCTION audit_event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_event is append-only';
END;
$$;
CREATE TRIGGER audit_event_no_update_delete BEFORE UPDATE OR DELETE ON audit_event
  FOR EACH ROW EXECUTE FUNCTION audit_event_append_only();
CREATE TRIGGER audit_event_no_truncate BEFORE TRUNCATE ON audit_event
  FOR EACH STATEMENT EXECUTE FUNCTION audit_event_append_only();

-- ===== API idempotency (P1) =====
CREATE TABLE idempotency_key (
  key text NOT NULL,
  user_id uuid NOT NULL REFERENCES app_user(id),
  endpoint text NOT NULL,
  response jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (key, user_id, endpoint)
);
