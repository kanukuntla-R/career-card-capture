param(
    [string]$HostAddress = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$InstallRoot = Join-Path $ProjectRoot "work\local-ocr"
$Server = Join-Path $InstallRoot "bin\llama-server.exe"
$Model = Join-Path $InstallRoot "models\HunyuanOCR-Q8_0.gguf"
$Projector = Join-Path $InstallRoot "models\mmproj-HunyuanOCR-Q8_0.gguf"

if (-not (Test-Path -LiteralPath $Server -PathType Leaf)) {
    throw "Local OCR runtime is missing. Run: .\.venv\Scripts\python.exe .\scripts\download_local_ocr.py"
}

if (-not (Test-Path -LiteralPath $Model -PathType Leaf) -or -not (Test-Path -LiteralPath $Projector -PathType Leaf)) {
    throw "Local HunyuanOCR model is missing. Run: .\.venv\Scripts\python.exe .\scripts\download_local_ocr.py"
}

$env:HF_HOME = Join-Path $InstallRoot "hf-cache"
$env:HF_HUB_CACHE = Join-Path $env:HF_HOME "hub"

Write-Host "Starting local HunyuanOCR on http://${HostAddress}:8081"
Write-Host "Model files are loaded only from the project's work/local-ocr directory."

& $Server `
    --model $Model `
    --mmproj $Projector `
    --alias "HYVL" `
    --host $HostAddress `
    --port "8081" `
    --ctx-size "4096" `
    --n-gpu-layers "99" `
    --flash-attn "on"
