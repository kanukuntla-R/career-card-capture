# Security and Privacy

## Data classification posture

Student-written cards may contain arbitrary content even if the intended prompts are simple. Treat card images and transcriptions as potentially sensitive operational data.

Do not assume that every card contains no personal information.

## Default privacy posture

- keep real card processing local/private where possible,
- use Tailscale for remote access,
- do not expose PostgreSQL publicly,
- do not upload real cards to cloud OCR without explicit authorization,
- do not commit captured images,
- do not commit Google/OCR credentials,
- delete temporary images according to configured retention.

## Image retention

Recommended default:

`CARD_IMAGE_RETENTION=delete_after_approval`

Rationale:

- final structured text is the business output,
- long-term image retention increases risk/storage,
- reviewer only requires the image during capture/review unless policy says otherwise.

If the organization decides images should be retained, enable explicit configured storage and document retention duration.

## Logs

Production logs should include:

- request ID
- card/session IDs
- provider name
- status
- latency
- safe error codes

Avoid logging:

- full card transcription by default
- raw image bytes
- API keys/tokens
- Google credentials
- complete OAuth responses

## Secrets

Use `.env` ignored by git for local deployment or a proper secret store later.

Required secret categories may include:

- database password
- Extend API key
- Google service-account/OAuth credentials
- application secret if auth is added

`.env.example` contains names only.

## Authentication

V1 may operate as a single-user private Tailnet application if deployment is accessible only to intended devices/users.

Before wider/team use, add application-level authentication and authorization.

Tailscale network access is not a permanent substitute for application RBAC if multiple unrelated users gain Tailnet access.

## Transport security

- use HTTPS for remote browser access,
- especially because camera APIs require secure context,
- do not disable browser security checks.

## Database

- no public PostgreSQL port,
- strong DB password,
- least-privilege application user,
- backup/restore procedure,
- migrations tracked.

## Cloud OCR

Provider adapter exists for benchmarking and optional use.

Guardrails:

- environment flag required to enable cloud provider,
- docs warning visible,
- no automatic fallback from local OCR to cloud for real data unless explicitly configured,
- a local-provider failure must not silently exfiltrate the image to a cloud provider.

## Google Sheets

Export only fields required by the business workflow.

Do not place OCR provider diagnostics/raw images in the sheet unless explicitly needed.

## Development samples

Use synthetic or explicitly approved sample cards in repository tests.

Do not copy the user's real supplied card photographs into the public repository by default.
