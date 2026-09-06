# External References for Codex

Re-check these during implementation because model/tool documentation can change.

## HunyuanOCR

Official repository:
`https://github.com/Tencent-Hunyuan/HunyuanOCR`

Inference guide:
`https://github.com/Tencent-Hunyuan/HunyuanOCR/blob/main/docs/inference/inference.md`

Important: validate current CUDA/runtime requirements against the target host's GPU driver before
installation.

## Extend

Documentation:
`https://docs.extend.ai/`

Extraction configuration:
`https://docs.extend.ai/extraction/configuration`

Extend supports schema-based structured extraction and has higher-accuracy processing options aimed at complex/handwritten content. Use only when authorized for the data.

## PaddleOCR

Official repository:
`https://github.com/PaddlePaddle/PaddleOCR`

Treat as an optional benchmark/fallback candidate rather than a mandatory dependency.

## Tailscale

Use current installed-version documentation and CLI output on the target host. Do not copy stale
Serve/certificate commands blindly into production.
