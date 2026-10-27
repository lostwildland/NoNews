-- Empty IO schema.ensure extraction; no source rows.
CREATE TABLE activity(
 id INTEGER PRIMARY KEY, item_id TEXT, kind TEXT NOT NULL, message TEXT NOT NULL,
 status TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE ai_feed_settings (
  freshrss_feed_id TEXT PRIMARY KEY,
  title TEXT NOT NULL DEFAULT '',
  folders_json TEXT NOT NULL DEFAULT '[]',
  processing_mode TEXT NOT NULL DEFAULT 'disabled'
    CHECK(processing_mode IN ('disabled','normal','important')),
  media_type TEXT CHECK(media_type IS NULL OR
    media_type IN ('news','paper','newsletter','podcast','video')),
  kit_id TEXT,
  scoring_strategy TEXT,
  body_strategy TEXT,
  last_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  subscription_state TEXT NOT NULL DEFAULT 'subscribed',
  contract_origin TEXT NOT NULL DEFAULT 'authored'
);
CREATE TABLE ai_feed_settings_migration (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  completed_at TEXT,
  report_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE ai_folder_profiles (
  folder TEXT PRIMARY KEY,
  profile TEXT,
  enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
  updated_at TEXT NOT NULL
);
CREATE TABLE ai_kits (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  content_type TEXT NOT NULL,
  threshold REAL NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
, content_types_json TEXT);
CREATE TABLE app_settings(
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL);
CREATE TABLE backlog_requests(
 id TEXT PRIMARY KEY, kit TEXT NOT NULL, window TEXT NOT NULL, status TEXT NOT NULL,
 planned INTEGER NOT NULL DEFAULT 0, queued INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 entry_ids_json TEXT, cursor INTEGER NOT NULL DEFAULT 0, error TEXT,
 rescore INTEGER NOT NULL DEFAULT 0, entry_routes_json TEXT);
CREATE TABLE body_texts(
 snapshot_id INTEGER PRIMARY KEY REFERENCES body_versions(snapshot_id),
 text TEXT NOT NULL);
CREATE TABLE body_versions(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 format TEXT NOT NULL DEFAULT 'markdown',
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 source TEXT NOT NULL,
 source_url TEXT NOT NULL DEFAULT '',
 availability TEXT NOT NULL DEFAULT 'usable'
   CHECK(availability IN ('usable','unavailable')),
 availability_reason TEXT NOT NULL DEFAULT '',
 retrieved_at TEXT NOT NULL,
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);
CREATE TABLE command_batches (
  id TEXT PRIMARY KEY, result_json TEXT NOT NULL
);
CREATE TABLE commands (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), command_type TEXT NOT NULL,
  payload TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'pending',
  idempotency_key TEXT NOT NULL UNIQUE, requested_at TEXT NOT NULL, undo_deadline TEXT NOT NULL,
  executed_at TEXT, error TEXT
);
CREATE TABLE curator_runs (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), raw_snapshot_id INTEGER,
  prompt_version_id TEXT, provider TEXT, model TEXT, thinking_effort TEXT, input_hash TEXT,
  score REAL, ai_decision TEXT, reason TEXT, result_json TEXT, status TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT, error TEXT
);
CREATE TABLE deliveries(
 item_id TEXT REFERENCES items(id), target TEXT, destination TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL, external_key TEXT, synced_hash TEXT, error TEXT, updated_at TEXT NOT NULL,
 draft_id TEXT, position INTEGER, issue_id TEXT, issue_date TEXT, section_hash TEXT,
 PRIMARY KEY(item_id,target,destination));
CREATE TABLE draft_bodies(
 draft_id TEXT PRIMARY KEY REFERENCES draft_versions(draft_id),
 text TEXT NOT NULL);
CREATE TABLE draft_versions(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 sha256 TEXT NOT NULL,
 characters INTEGER NOT NULL,
 authority TEXT NOT NULL DEFAULT 'database'
   CHECK(authority IN ('database','imported')),
 stored_at TEXT NOT NULL,
 cleaned_at TEXT, cleanup_request_id TEXT);
CREATE TABLE editor_drafts(
 id TEXT PRIMARY KEY, item_id TEXT REFERENCES items(id), raw_snapshot_id INTEGER,
 prompt_version_id TEXT, provider TEXT, model TEXT, thinking_effort TEXT,
 input_hash TEXT, artifact_hash TEXT, created_at TEXT NOT NULL, model_source_json TEXT, manual_source_id TEXT, manual_revision_id TEXT);
CREATE TABLE entry_observations (
  id INTEGER PRIMARY KEY, freshrss_entry_id TEXT NOT NULL UNIQUE, feed_id TEXT NOT NULL REFERENCES feeds(id),
  item_id TEXT NOT NULL REFERENCES items(id), original_url TEXT, ingested_at TEXT NOT NULL, published_at TEXT
);
CREATE TABLE failure_dismissals(
 kind TEXT NOT NULL, id TEXT NOT NULL, stamp TEXT NOT NULL, dismissed_at TEXT NOT NULL,
 PRIMARY KEY(kind,id));
CREATE TABLE feed_items (
  feed_id TEXT NOT NULL REFERENCES feeds(id), item_id TEXT NOT NULL REFERENCES items(id),
  first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, PRIMARY KEY(feed_id, item_id)
);
CREATE TABLE feeds (
  id TEXT PRIMARY KEY, freshrss_feed_id TEXT NOT NULL UNIQUE, feed_url TEXT,
  title TEXT NOT NULL, current_media_type TEXT, first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL, subscription_status TEXT NOT NULL DEFAULT 'active',
  unsubscribed_at TEXT
);
CREATE TABLE human_reviews (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), curator_run_id TEXT,
  event_type TEXT NOT NULL, decision TEXT, action_source TEXT NOT NULL, created_at TEXT NOT NULL,
  idempotency_key TEXT UNIQUE
);
CREATE TABLE ingestion_failures (
        id TEXT PRIMARY KEY, folder TEXT NOT NULL, entry_id TEXT, artifact_path TEXT NOT NULL,
        error TEXT NOT NULL, updated_at TEXT NOT NULL, resolved INTEGER NOT NULL DEFAULT 0);
CREATE TABLE integrations(
 key TEXT PRIMARY KEY, config_json TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE item_feed_contracts (
  item_id TEXT PRIMARY KEY,
  freshrss_feed_id TEXT,
  media_type TEXT,
  processing_mode TEXT NOT NULL DEFAULT 'disabled',
  kit_id TEXT,
  scoring_strategy TEXT,
  body_strategy TEXT,
  pinned_at TEXT NOT NULL,
  refreshed_at TEXT
);
CREATE TABLE item_identities (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), media_type TEXT NOT NULL,
  identity_type TEXT NOT NULL, identity_value TEXT NOT NULL, created_at TEXT NOT NULL,
  UNIQUE(media_type, identity_type, identity_value)
);
CREATE TABLE item_material_fingerprints (
  item_id TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('scoring','body')),
  media_type TEXT NOT NULL,
  strategy TEXT NOT NULL DEFAULT '',
  source_route TEXT NOT NULL DEFAULT '',
  source_identity TEXT NOT NULL DEFAULT '',
  retrieved_at TEXT NOT NULL,
  sha256 TEXT NOT NULL DEFAULT '',
  characters INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL,
  reason TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,
  PRIMARY KEY(item_id, role)
);
CREATE TABLE item_metadata(
 item_id TEXT PRIMARY KEY REFERENCES items(id), metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE items (
  id TEXT PRIMARY KEY, media_type TEXT NOT NULL CHECK(media_type IN ('news','paper','newsletter','podcast','video')),
  canonical_url TEXT, title TEXT, published_at TEXT, first_ingested_at TEXT NOT NULL,
  review_date TEXT NOT NULL, current_raw_snapshot_id INTEGER,
  human_review_status TEXT NOT NULL DEFAULT 'pending', human_decision TEXT,
  human_curator_run_id TEXT, reviewed_at TEXT, starred INTEGER NOT NULL DEFAULT 0,
  ever_starred INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  review_generation INTEGER NOT NULL DEFAULT 0
, public_id TEXT);
CREATE TABLE legacy_content_imports(
 import_key TEXT PRIMARY KEY,
 batch TEXT NOT NULL DEFAULT '',
 item_id TEXT NOT NULL REFERENCES items(id),
 kind TEXT NOT NULL CHECK(kind IN ('body','draft')),
 path TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 content_sha256 TEXT NOT NULL,
 version INTEGER NOT NULL DEFAULT 0,
 model TEXT NOT NULL DEFAULT '',
 source_system TEXT NOT NULL,
 source_key TEXT NOT NULL,
 source_hash TEXT NOT NULL DEFAULT '',
 target_id TEXT NOT NULL,
 state TEXT NOT NULL,
 verified_at TEXT NOT NULL,
 detail_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE legacy_draft_imports(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id) ON DELETE CASCADE,
 source_system TEXT NOT NULL, source_key TEXT NOT NULL, source_hash TEXT NOT NULL,
 imported_at TEXT NOT NULL, metadata_json TEXT NOT NULL,
 UNIQUE(source_system,source_key,source_hash));
CREATE TABLE literature_assets (
            id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
            kind TEXT NOT NULL, source_path TEXT NOT NULL, archive_path TEXT,
            source_url TEXT, file_hash TEXT NOT NULL,
            identity_verified INTEGER NOT NULL DEFAULT 0,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(item_id,kind,source_path,file_hash)
        );
CREATE TABLE literature_cleanup_audit(
 id INTEGER PRIMARY KEY,
 request_id TEXT NOT NULL,
 item_id TEXT NOT NULL REFERENCES items(id),
 event TEXT NOT NULL,
 detail_json TEXT NOT NULL DEFAULT '{}',
 created_at TEXT NOT NULL);
CREATE TABLE literature_cleanup_backups(
 backup_id TEXT PRIMARY KEY,
 request_id TEXT NOT NULL,
 item_id TEXT NOT NULL REFERENCES items(id),
 path TEXT NOT NULL,
 manifest_sha256 TEXT NOT NULL,
 bytes INTEGER NOT NULL,
 body_count INTEGER NOT NULL,
 draft_count INTEGER NOT NULL,
 verified_at TEXT NOT NULL,
 created_at TEXT NOT NULL);
CREATE TABLE literature_cleanup_media(
        request_id TEXT NOT NULL REFERENCES literature_cleanup_requests(id),
        object_key TEXT NOT NULL, public_url TEXT NOT NULL,
        sha256 TEXT NOT NULL, bytes INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('pending','deleted','shared')),
        PRIMARY KEY(request_id,object_key));
CREATE TABLE literature_cleanup_requests (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
  status TEXT NOT NULL DEFAULT 'hold'
    CHECK(status IN ('hold','pending_review','executing','cancelled','executed')),
  cause TEXT NOT NULL, action_source TEXT, command_id TEXT, review_id INTEGER,
  ai_run_id TEXT, ai_decision TEXT,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  due_at TEXT NOT NULL DEFAULT '', started_at TEXT, completed_at TEXT,
  attempts INTEGER NOT NULL DEFAULT 0, error TEXT, retry_after TEXT,
  backup_id TEXT, execution_token TEXT, tombstone_json TEXT NOT NULL DEFAULT '',
  review_generation INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE literature_drafts(
 draft_id TEXT PRIMARY KEY REFERENCES editor_drafts(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 file_identity TEXT NOT NULL,
 file_draft_id TEXT NOT NULL,
 path TEXT NOT NULL,
 version INTEGER NOT NULL,
 payload_sha256 TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);
CREATE TABLE literature_file_keys(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 file_key TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL,
 source TEXT NOT NULL,
 origin_parent_library_id TEXT NOT NULL,
 origin_parent_item_key TEXT NOT NULL,
 origin_parent_identity TEXT NOT NULL,
 origin_evidence_json TEXT NOT NULL DEFAULT '{}',
 active_parent_library_id TEXT NOT NULL,
 active_parent_item_key TEXT NOT NULL,
 active_parent_identity TEXT NOT NULL,
 active_source TEXT NOT NULL,
 active_evidence_json TEXT NOT NULL DEFAULT '{}',
 initial_citation_key TEXT NOT NULL,
 current_citation_key TEXT NOT NULL,
 drift_state TEXT NOT NULL,
 drift_reason TEXT,
 reserved_at TEXT NOT NULL,
 citation_key_updated_at TEXT NOT NULL,
 parent_updated_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE TABLE literature_files(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 citekey TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL,
 source TEXT NOT NULL,
 evidence_json TEXT NOT NULL DEFAULT '{}',
 conditional_writer TEXT NOT NULL,
 enabled_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE TABLE literature_raws(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 citekey TEXT NOT NULL,
 path TEXT NOT NULL,
 file_sha256 TEXT NOT NULL,
 bound_at TEXT NOT NULL);
CREATE TABLE literature_reading_notes(
 item_id TEXT PRIMARY KEY REFERENCES items(id),
 zotero_key TEXT NOT NULL DEFAULT '',
 citekey TEXT NOT NULL,
 path TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'exported'
   CHECK(status IN ('exported','missing')),
 payload_sha256 TEXT NOT NULL,
 body_version_id INTEGER,
 body_sha256 TEXT NOT NULL,
 fulltext_url TEXT NOT NULL DEFAULT '',
 extra_status TEXT NOT NULL DEFAULT 'pending'
   CHECK(extra_status IN ('pending','written','failed')),
 extra_error TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE TABLE literature_selections (
  item_id TEXT PRIMARY KEY REFERENCES items(id), curator_run_id TEXT NOT NULL,
  score REAL NOT NULL, threshold REAL NOT NULL, selected_at TEXT NOT NULL
);
CREATE TABLE media_derivatives (
        original_key TEXT NOT NULL REFERENCES media_objects(key),
        derived_key TEXT NOT NULL REFERENCES media_objects(key),
        purpose TEXT NOT NULL, detail_json TEXT NOT NULL,
        PRIMARY KEY(original_key,derived_key,purpose));
CREATE TABLE media_document_generations (
        item_id TEXT NOT NULL,
        generation INTEGER NOT NULL,
        document_hash TEXT NOT NULL,
        planned_output_hash TEXT,
        staging_path TEXT NOT NULL,
        staging_device INTEGER NOT NULL,
        staging_inode INTEGER NOT NULL,
        document_bytes INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        provenance_json TEXT NOT NULL,
        expected_current_hash TEXT,
        state TEXT NOT NULL CHECK(state IN ('pending','committed')),
        raw_snapshot_id INTEGER,
        cleanup_state TEXT NOT NULL DEFAULT 'pending',
        cleanup_error TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(item_id, generation)
    );
CREATE TABLE media_document_receipts (
        id INTEGER PRIMARY KEY,
        item_id TEXT NOT NULL,
        generation INTEGER NOT NULL DEFAULT 1,
        document_hash TEXT NOT NULL,
        planned_output_hash TEXT,
        status TEXT NOT NULL,
        raw_snapshot_id INTEGER,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
CREATE TABLE media_objects(
        key TEXT PRIMARY KEY, namespace TEXT NOT NULL,
        sha256 TEXT NOT NULL, stored_sha256 TEXT NOT NULL, ext TEXT NOT NULL,
        bytes INTEGER NOT NULL, width INTEGER NOT NULL DEFAULT 0, height INTEGER NOT NULL DEFAULT 0,
        transcoded_from TEXT NOT NULL DEFAULT '', public_url TEXT NOT NULL,
        verified_at TEXT, created_at TEXT NOT NULL, cleanup_generation INTEGER NOT NULL DEFAULT 0, cleanup_request_id TEXT, deleted_at TEXT,
        UNIQUE(namespace, stored_sha256));
CREATE TABLE media_pending(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, source_ref TEXT NOT NULL,
        staging_path TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        next_attempt_at TEXT, last_error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, namespace TEXT NOT NULL DEFAULT 'literature', payload_sha256 TEXT NOT NULL DEFAULT '', payload_bytes INTEGER NOT NULL DEFAULT 0, staging_owned INTEGER NOT NULL DEFAULT 0, staging_device INTEGER NOT NULL DEFAULT 0, staging_inode INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'pending',
        UNIQUE(owner_kind, owner_id, source_ref));
CREATE TABLE media_raw_activation_intents (
    id TEXT PRIMARY KEY, item_id TEXT NOT NULL, expected_snapshot_id INTEGER,
    old_mapping_json TEXT NOT NULL, old_authority_json TEXT NOT NULL, citekey TEXT NOT NULL,
    candidate_hash TEXT NOT NULL, preimage_json TEXT, quarantine_path TEXT,
    state TEXT NOT NULL, snapshot_id INTEGER, receipt_id TEXT);
CREATE TABLE media_receipts(
        id INTEGER PRIMARY KEY,
        owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL, raw_snapshot_id INTEGER,
        status TEXT NOT NULL, images_total INTEGER NOT NULL DEFAULT 0,
        uploaded INTEGER NOT NULL DEFAULT 0, reused INTEGER NOT NULL DEFAULT 0,
        skipped INTEGER NOT NULL DEFAULT 0, failed INTEGER NOT NULL DEFAULT 0,
        bytes_total INTEGER NOT NULL DEFAULT 0, detail_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL);
CREATE TABLE media_source_current(
        namespace TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, object_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        PRIMARY KEY(namespace, owner_kind, owner_id, source_ref));
CREATE TABLE media_source_revisions(
        namespace TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, source_revision TEXT NOT NULL, object_key TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        PRIMARY KEY(namespace, owner_kind, owner_id, source_ref, source_revision));
CREATE TABLE media_upload_intents(
        object_key TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, object_json TEXT NOT NULL, payload BLOB NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(object_key,owner_kind,owner_id,source_ref));
CREATE TABLE media_usages(
        object_key TEXT NOT NULL, owner_kind TEXT NOT NULL, owner_id TEXT NOT NULL,
        source_ref TEXT NOT NULL, first_seen_at TEXT NOT NULL,
        PRIMARY KEY(object_key, owner_kind, owner_id, source_ref));
CREATE TABLE model_configs(
 kit_id TEXT, role TEXT, config_json TEXT NOT NULL, updated_at TEXT,
 PRIMARY KEY(kit_id,role));
CREATE TABLE news_notes(
 item_id TEXT PRIMARY KEY REFERENCES items(id), vault TEXT NOT NULL, path TEXT NOT NULL,
 updated_at TEXT NOT NULL);
CREATE TABLE newsletter_outbox (
        command_id TEXT PRIMARY KEY REFERENCES commands(id), item_id TEXT NOT NULL REFERENCES items(id),
        target_date TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        available_at TEXT NOT NULL, draft_id TEXT, expected_file_hash TEXT, error TEXT, revision_id TEXT);
CREATE TABLE observation_news_labels (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        draft_id TEXT NOT NULL, label TEXT, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT);
CREATE TABLE observation_paper_labels (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        curator_run_id TEXT NOT NULL, label TEXT, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT, projection_version INTEGER NOT NULL DEFAULT 0);
CREATE TABLE observation_projection (
        observation_id INTEGER PRIMARY KEY REFERENCES entry_observations(id),
        desired_read INTEGER NOT NULL, desired_starred INTEGER NOT NULL, status TEXT NOT NULL,
        attempts INTEGER NOT NULL, available_at TEXT NOT NULL, error TEXT, desired_published INTEGER NOT NULL DEFAULT 0, decision_value TEXT, decision_status TEXT, decision_attempts INTEGER NOT NULL DEFAULT 0, decision_available_at TEXT, decision_error TEXT);
CREATE TABLE pipeline_stage_runs(
            job_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            result_json TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(job_id, item_id, stage)
        );
CREATE TABLE private_raw_sources(
 snapshot_id INTEGER PRIMARY KEY REFERENCES raw_snapshots(id),
 item_id TEXT NOT NULL REFERENCES items(id),
 relative_path TEXT NOT NULL, sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL);
CREATE TABLE processing_jobs (
          id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
          stage TEXT NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
          status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
          available_at TEXT NOT NULL, created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, error TEXT, result_json TEXT,
          intent_json TEXT
        , magpie_block_reason TEXT, editor_target TEXT, batch_id TEXT, decision_generation INTEGER, origin TEXT);
CREATE TABLE prompt_versions(
 id TEXT PRIMARY KEY, kit_id TEXT NOT NULL, role TEXT NOT NULL,
 content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE raw_snapshots (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), path TEXT NOT NULL,
  source_hash TEXT NOT NULL, retrieved_at TEXT NOT NULL, created_at TEXT NOT NULL,
  provenance TEXT NOT NULL DEFAULT '', vault_exported_at TEXT,
  UNIQUE(item_id, source_hash)
);
CREATE TABLE reconciliation_bootstrap (
        feed_id TEXT PRIMARY KEY REFERENCES feeds(id),
        started_at TEXT NOT NULL,
        completed_at TEXT
    );
CREATE TABLE reconciliation_cursors (
        folder TEXT PRIMARY KEY, cursor TEXT, completed_at TEXT);
CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE stage_state(
 item_id TEXT REFERENCES items(id), stage TEXT, status TEXT NOT NULL,
 error TEXT, link TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(item_id,stage));
CREATE TABLE star_events (
  id INTEGER PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id), starred INTEGER NOT NULL,
  action_source TEXT NOT NULL, created_at TEXT NOT NULL, idempotency_key TEXT UNIQUE
);
CREATE TABLE unstar_cleanup (
  id TEXT PRIMARY KEY, item_id TEXT NOT NULL REFERENCES items(id),
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  available_at TEXT NOT NULL, error TEXT
);
CREATE TABLE zotero_links(
 item_id TEXT PRIMARY KEY REFERENCES items(id), item_key TEXT NOT NULL UNIQUE,
 note_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
 available_at TEXT NOT NULL, synced_hash TEXT, error TEXT,
 adoption_source TEXT, adoption_status TEXT, sync_scope TEXT NOT NULL DEFAULT 'parent-and-note');
CREATE TABLE zotero_resolution(
 item_id TEXT PRIMARY KEY REFERENCES items(id), attempts INTEGER NOT NULL,
 status TEXT NOT NULL, available_at TEXT NOT NULL);
CREATE INDEX body_versions_item ON body_versions(item_id, snapshot_id);
CREATE INDEX commands_item ON commands(item_id);
CREATE INDEX commands_pending ON commands(status, undo_deadline);
CREATE INDEX curator_runs_latest ON curator_runs(item_id, finished_at DESC, id DESC);
CREATE INDEX draft_versions_item ON draft_versions(item_id, draft_id);
CREATE INDEX editor_drafts_item ON editor_drafts(item_id, created_at);
CREATE UNIQUE INDEX editor_drafts_manual_revision ON editor_drafts(manual_revision_id) WHERE manual_revision_id IS NOT NULL;
CREATE INDEX entry_observations_item ON entry_observations(item_id);
CREATE INDEX entry_observations_recent ON entry_observations(ingested_at DESC, id DESC);
CREATE INDEX feeds_title ON feeds(title);
CREATE INDEX item_identities_item ON item_identities(item_id);
CREATE INDEX items_decision ON items(human_review_status, human_decision);
CREATE UNIQUE INDEX items_public_id ON items(public_id);
CREATE INDEX items_review ON items(human_review_status, first_ingested_at, id);
CREATE INDEX items_starred ON items(starred);
CREATE INDEX legacy_content_imports_item
 ON legacy_content_imports(item_id, kind);
CREATE INDEX legacy_content_imports_target
 ON legacy_content_imports(target_id);
CREATE INDEX literature_assets_item ON literature_assets(item_id,kind);
CREATE INDEX literature_cleanup_audit_request
 ON literature_cleanup_audit(request_id, id);
CREATE INDEX literature_cleanup_backups_request
 ON literature_cleanup_backups(request_id);
CREATE INDEX literature_cleanup_requests_due
        ON literature_cleanup_requests(status, due_at);
CREATE INDEX literature_cleanup_requests_item
  ON literature_cleanup_requests(item_id, status);
CREATE UNIQUE INDEX literature_cleanup_requests_review
  ON literature_cleanup_requests(review_id);
CREATE UNIQUE INDEX literature_drafts_file
 ON literature_drafts(citekey, file_draft_id);
CREATE UNIQUE INDEX literature_drafts_identity
 ON literature_drafts(item_id, file_identity);
CREATE INDEX literature_drafts_item ON literature_drafts(item_id);
CREATE UNIQUE INDEX literature_file_keys_current
 ON literature_file_keys(current_citation_key);
CREATE UNIQUE INDEX literature_raws_item ON literature_raws(item_id);
CREATE UNIQUE INDEX media_document_one_pending
        ON media_document_generations(item_id) WHERE state='pending';
CREATE INDEX media_upload_intents_owner ON media_upload_intents(owner_kind,owner_id);
CREATE INDEX media_usages_owner ON media_usages(owner_kind, owner_id);
CREATE INDEX pipeline_stage_runs_item_stage ON pipeline_stage_runs(item_id,stage,status);
CREATE INDEX processing_jobs_batch ON processing_jobs(batch_id,status);
CREATE INDEX processing_jobs_item ON processing_jobs(item_id,status);
CREATE INDEX processing_jobs_pending ON processing_jobs(status,available_at);
