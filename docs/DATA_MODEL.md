# Data Model

PostgreSQL is the system of record.

Use UUID primary keys unless implementation evidence strongly favors another strategy.

All timestamps should be timezone-aware and stored in UTC.

## 1. Enumerations

```text
event_type:
  TABLING
  CLASSROOM_PRESENTATION
  OTHER

session_status:
  IN_PROGRESS
  COMPLETED
  ARCHIVED

card_type:
  EMPLOYER
  QUESTION
  UNKNOWN

card_status:
  CAPTURED
  PROCESSING
  NEEDS_REVIEW
  APPROVED
  SKIPPED
  OCR_FAILED
  REMOVED

sync_status:
  NOT_REQUIRED
  PENDING
  SYNCED
  ERROR
```

Prefer database-safe enum handling that can be migrated without painful PostgreSQL enum alterations; string check constraints or application enums are acceptable.

## 2. `events`

Fields:

- `id` UUID PK
- `title` text not null
- `event_type` text not null
- `event_date` date nullable
- `location` text nullable
- `course` text nullable
- `topic` text nullable
- `notes` text nullable
- `is_archived` boolean default false
- `created_at`
- `updated_at`

Indexes:

- event date
- archived flag
- event type

## 3. `capture_sessions`

Fields:

- `id` UUID PK
- `event_id` FK -> events
- `name` text nullable; generate human-readable default if omitted
- `status` text not null default `IN_PROGRESS`
- `started_at`
- `completed_at` nullable
- `archived_at` nullable
- `last_activity_at`
- `created_at`
- `updated_at`

Rules:

- a completed session can be reopened; clearing/recording completion state must be explicit.
- archiving does not cascade-delete cards.
- `last_activity_at` updates when cards are captured/edited/approved.

## 4. `cards`

Fields:

- `id` UUID PK
- `event_id` FK -> events
- `session_id` FK -> capture_sessions
- `sequence_number` integer scoped to session
- `status`
- `suggested_type` nullable
- `final_type` nullable
- `raw_ocr` text nullable
- `final_text` text nullable
- `ocr_confidence` numeric nullable
- `ocr_provider` text nullable
- `ocr_model` text nullable
- `was_edited` boolean default false
- `image_storage_key` text nullable
- `normalized_image_storage_key` text nullable
- `captured_at`
- `approved_at` nullable
- `removed_at` nullable
- `removed_reason` text nullable
- `status_before_removal` nullable
- `created_at`
- `updated_at`

Constraints:

- unique `(session_id, sequence_number)`
- approved card requires non-empty `final_text`
- approved card requires `final_type` in Employer/Question/Unknown; optionally require non-Unknown later only if product decides

Never overwrite `raw_ocr` when an operator edits final text.

## 5. `card_revisions`

Created for edits after an approved/current value exists.

Fields:

- `id` UUID PK
- `card_id` FK
- `revision_number` integer
- `previous_final_type`
- `previous_final_text`
- `new_final_type`
- `new_final_text`
- `reason` text nullable
- `changed_at`
- `changed_by` text/nullable actor identifier for future auth

Unique `(card_id, revision_number)`.

This table is append-only under normal application behavior.

## 6. `ocr_attempts`

Useful for retries and benchmarking.

Fields:

- `id` UUID PK
- `card_id` FK
- `attempt_number`
- `provider`
- `model`
- `raw_text` nullable
- `suggested_type` nullable
- `confidence` nullable
- `latency_ms` nullable
- `provider_metadata` JSONB
- `error_code` nullable
- `error_message_safe` nullable
- `created_at`

Do not store secrets/provider tokens in metadata.

## 7. `sheet_sync_records`

One logical current mapping per card + optional attempt history.

Fields:

- `id` UUID PK
- `card_id` FK unique
- `sheet_id_hash_or_alias` text
- `record_id` UUID/text equal to stable card ID exported to sheet
- `sheet_row_number` integer nullable
- `last_synced_payload_hash` text nullable
- `status`
- `attempt_count`
- `last_error_safe` nullable
- `last_attempt_at` nullable
- `synced_at` nullable
- `created_at`
- `updated_at`

Do not depend solely on `sheet_row_number`; rows may be sorted/moved. Verify the stable `record_id` before updating.

## 8. Optional `settings`

V1 may use environment variables instead. If runtime-editable settings become necessary, add:

- OCR provider selection
- image retention mode
- Google Sheet mapping alias
- auto-capture threshold

Do not store secrets in a plaintext settings table.

## 9. Deletion strategy

Prefer soft/archive behavior for events/sessions.

Approved or skipped cards can be soft-removed by setting `status=REMOVED`, recording the prior
status and removal metadata, and excluding them from active history and counts. The operator can
restore them to the recorded prior status. Raw OCR, final text, attempts, and revisions are never
deleted by this workflow; retained image files are deleted for privacy.

Hard deletion remains outside the normal operator UI and would require an explicit future admin
operation.

## 10. Migration policy

All schema changes use Alembic.

Never modify production schema manually without a matching migration.
