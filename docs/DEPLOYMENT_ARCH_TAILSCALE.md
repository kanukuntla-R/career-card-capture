# Deployment: Arch Linux + Tailscale

## Known environment

Reference target: a private Arch Linux host.

Known characteristics:

- Arch Linux
- deployment account and paths are environment-specific
- CLI/SSH management
- Tailscale installed/used
- OpenSSH installed/used
- Docker and Docker Compose installed/used
- Avahi present
- Git/SSH workflows
- some Syncthing workflows
- NVIDIA GPU is expected from prior context, but actual GPU/VRAM/driver state must be verified

Do not make destructive host changes automatically.

## Required host preflight

Before deployment:

```bash
hostnamectl
uname -a
df -h
lsblk -f
free -h
lscpu
nvidia-smi || true
docker --version
docker compose version
docker info
docker system df
tailscale status
git status
```

Record relevant outputs in a local deployment note, excluding sensitive Tailnet/device information from commits.

Do not:

- repartition disks,
- change Docker data-root,
- purge images/volumes,
- upgrade NVIDIA drivers,
- modify Tailscale ACLs,
- expose DB ports,
- overwrite unrelated reverse-proxy configs,

without explicit approval.

## Preferred topology

```text
Operator workstation (Mac/Windows)
  webcam
  browser
      |
      | HTTPS over Tailscale
      v
Arch Linux host
  ├── web
  ├── api
  ├── postgres
  └── optional OCR service
```

The webcam remains on the workstation; the browser sends captured still images to the API.

## Tailscale assumptions

Tailscale is the private connectivity layer.

Rules:

- do not hard-code `100.x.x.x` addresses,
- prefer discovered MagicDNS names/config where available,
- database stays on Docker private network,
- only web/API endpoints intended for the user should be reachable,
- do not publicly expose the stack merely for convenience.

## Browser secure context

Browser camera APIs generally require a secure context.

Development options:

- `http://localhost` when running web locally

Private deployed option:

- serve the web app with HTTPS over the Tailnet using the capabilities supported by the installed Tailscale version.

Codex must inspect the installed Tailscale version/current configuration before choosing exact commands. Do not replace existing Tailnet configuration.

## Docker Compose layout

Recommended services:

```text
web
api
postgres
ocr-hunyuan (optional profile)
```

Optional later:

```text
sync-worker
reverse-proxy
```

Use health checks.

Persist PostgreSQL in a named volume or deliberate host path chosen after checking disk capacity.

Never bind PostgreSQL to a public interface. For development, if host DB access is needed, bind deliberately to localhost only.

## GPU OCR

HunyuanOCR should be an optional service/profile so the core app can start even if GPU inference is not configured.

Example operational modes:

```text
OCR_PROVIDER=mock
OCR_PROVIDER=hunyuan
OCR_PROVIDER=extend
```

For GPU setup:

1. verify `nvidia-smi`
2. verify Docker GPU support if containerized
3. verify current HunyuanOCR official runtime requirements
4. test a minimal inference
5. only then enable it in the application

Do not upgrade host NVIDIA/CUDA stack without explicit user approval.

### Windows GPU OCR with the application on the Linux host

When the operator's Windows workstation has the supported NVIDIA GPU and the Linux host does not,
keep web, API, and PostgreSQL on Linux and run llama.cpp on Windows. Bind llama.cpp only to the
workstation's currently discovered Tailscale IPv4 address, not `0.0.0.0`, then configure the API
container with the workstation's MagicDNS name:

```powershell
$TailscaleIp = (tailscale ip -4 | Select-Object -First 1).Trim()
.\scripts\start-local-ocr.ps1 -HostAddress $TailscaleIp
```

```dotenv
OCR_PROVIDER=hunyuan
HUNYUAN_OCR_BASE_URL=http://WINDOWS_MAGICDNS_NAME:8081/v1
HUNYUAN_MODEL_NAME=HYVL
HUNYUAN_REQUEST_TIMEOUT_SECONDS=120
```

Test `/v1/models` from the Linux host before recreating the API container. This endpoint is intentionally
private and unauthenticated, so do not publish it, use Funnel, or bind it to public/LAN interfaces.
The Windows OCR process must remain running while cards are being captured. If a firewall change
is required, review and approve the narrow program/port rule explicitly rather than disabling the
firewall.

## Backups

Minimum production-like backup before relying on the tool:

- PostgreSQL logical dump
- `.env`/secret backup stored securely outside git
- Google Sheet acts as an output copy but is not a DB backup

Document restore procedure.

## Google Sheets on the deployment host

The credential stays under the existing project directory and is mounted read-only into the API.
After creating the service account and sharing the test Sheet with its `client_email`, transfer the
JSON to the deployment host, then place it here:

```bash
cd "$HOME/career-service/app"
mkdir -p config/google
mv "/path/to/the-transferred-key.json" config/google/service-account.json
chmod 700 config/google
chmod 600 config/google/service-account.json
```

Do not display the JSON in the terminal or commit it. Edit `.env` and add:

```dotenv
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEET_ID=PASTE_THE_VALUE_BETWEEN_D_AND_EDIT
GOOGLE_SHEET_TAB_NAME=Responses
GOOGLE_CREDENTIALS_HOST_DIR=./config/google
GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google/service-account.json
```

Then validate configuration, rebuild the two changed services, and verify the connection:

```bash
sudo docker compose -f compose.yaml -f compose.arch.yaml config --quiet
sudo docker compose -f compose.yaml -f compose.arch.yaml up -d --build api web
curl --fail --show-error http://127.0.0.1:3000/backend/ready
curl --fail --show-error -X POST http://127.0.0.1:3000/backend/api/v1/sync/verify
curl --fail --show-error http://127.0.0.1:3000/backend/api/v1/sync/status
```

The API container runs migration `0004_google_sheet_sync` at startup. PostgreSQL remains
authoritative; a Sheets outage leaves captures and approvals usable and records retryable.

## Future VPS

If moved to a VPS:

- keep PostgreSQL private,
- use Tailscale between the VPS and private host if local OCR/data services remain on-premises,
- avoid split-brain ownership of PostgreSQL,
- define one authoritative DB instance,
- migrate with dump/restore and downtime plan rather than running two writers accidentally.

## Exact values intentionally not documented

These must be discovered/configured:

- Tailscale IPs
- Tailnet name
- MagicDNS hostname
- public domain
- port reservations
- Google Sheet ID
- secret paths
