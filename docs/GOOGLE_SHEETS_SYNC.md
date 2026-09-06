# Google Sheets Synchronization

## Principle

PostgreSQL is authoritative. Google Sheets is a synchronized destination for operational sharing/reporting.

The application must remain usable if Google Sheets is temporarily unavailable.

## Suggested sheet columns

Minimum human-facing columns:

- Timestamp
- Event
- Event Type
- Session
- Response Type
- Response

Operational columns:

- Record ID
- Last Updated

`Record ID` should be a stable card UUID and may be hidden in the Sheet UI.

Optional later columns:

- Course
- Topic
- Location

Avoid exporting raw OCR/confidence unless Career Services actually wants it.

## New approval

On first approval:

1. DB transaction commits card.
2. sync record becomes `PENDING`.
3. worker obtains current final payload.
4. append row including stable `Record ID`.
5. record returned row position if available.
6. mark `SYNCED`.

## Historical edit

When approved card changes:

1. create revision.
2. update final DB values.
3. mark sync `PENDING`.
4. worker verifies mapping.
5. update row matching stable `Record ID`.
6. mark synced.

Never append a second row merely because the row number changed or an update retry occurred.

## Row identity strategy

Do not trust row number alone because humans may sort the spreadsheet.

Use:

- stable `Record ID` column,
- cached row number as optimization only,
- verify ID before updating,
- if mismatch, search/scan ID column and update correct row.

For moderate event card volume, this is sufficient. Optimize/batch later if needed.

## Idempotency

Before writing, compute a payload hash from fields that should be in Sheets.

If:

- status is `SYNCED`, and
- payload hash equals last synced hash,

then no write is required.

On retry, use existing Record ID.

## Credential options

The final method depends on what ASU Google Workspace policies permit.

Possible implementations:

### Service account

Operationally simple if the target sheet can be shared with the service-account email.

### OAuth

Use if ASU tenant rules require a user account/delegated authorization.

Do not assume one is allowed until tested with the actual account.

The Google integration code should be separated so credential strategy does not affect card/session business logic.

V1 implements the service-account strategy. OAuth remains a replaceable credential strategy if
the ASU tenant does not permit sharing a Sheet with a service account.

## Implemented operator flow

- approval commits to PostgreSQL and marks the record `PENDING`
- connected browsers trigger a non-blocking sync after approval or an edit
- the dashboard can sync/retry all approved records
- a failed card exposes a one-record retry in card history
- the dashboard links to the configured Sheet and always offers CSV download
- event-title/type edits mark every affected approved card `PENDING`
- removing a previously synced approved card clears its exported values while retaining Record ID;
  restoring it repopulates that same row

The CSV endpoint uses the same columns and works without Google credentials.

## Service-account setup

1. Create a test spreadsheet and a tab named `Responses` (or configure a different tab name).
2. In a Google Cloud project, enable the Google Sheets API and create a service account JSON key.
3. Share the spreadsheet with the service account's `client_email` as an editor.
4. Store the JSON outside git as `config/google/service-account.json` on the application host.
5. Configure `GOOGLE_SHEETS_ENABLED`, `GOOGLE_SHEET_ID`, `GOOGLE_SHEET_TAB_NAME`, and the credential
   paths documented in `.env.example`.
6. Recreate the API, call `POST /api/v1/sync/verify`, then use **Sync approved cards** in the UI.

The Sheet ID is the value between `/d/` and `/edit` in a normal Google Sheets URL. The sync service
creates the exact eight-column header only when row 1 is empty; it will not silently overwrite a
different schema.

## Secrets

Never commit:

- service-account JSON
- OAuth client secret
- refresh token
- Sheet ID if the user considers it sensitive

Recommended environment variables are documented in `.env.example`.

## Failure handling

Classify failures:

- transient/network/rate limit -> retry with backoff
- auth/permission -> error requiring operator/admin action
- sheet/column mismatch -> error requiring configuration review
- row not found -> search stable ID; if truly absent, repair deliberately, not blind duplicate append

## Manual sync controls

Dashboard should expose:

- pending count
- error count
- retry all failed
- retry one record

Do not make the operator wait for sync before processing the next card.
