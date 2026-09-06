"""Install the pinned Windows CUDA llama.cpp runtime into the ignored work directory."""

from __future__ import annotations

import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

ASSETS = (
    (
        "llama-b10587-bin-win-cuda-12.4-x64.zip",
        (
            "https://github.com/ggml-org/llama.cpp/releases/download/b10587/"
            "llama-b10587-bin-win-cuda-12.4-x64.zip"
        ),
        "dbdec1b2cc958b69d3efa9db7184b2760a3690425ba1035c1fc34217a4a43de4",
    ),
    (
        "cudart-llama-bin-win-cuda-12.4-x64.zip",
        (
            "https://github.com/ggml-org/llama.cpp/releases/download/b10587/"
            "cudart-llama-bin-win-cuda-12.4-x64.zip"
        ),
        "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6",
    ),
)

MODEL_ASSETS = (
    (
        "HunyuanOCR-Q8_0.gguf",
        (
            "https://huggingface.co/ggml-org/HunyuanOCR-GGUF/resolve/main/"
            "HunyuanOCR-Q8_0.gguf?download=true"
        ),
        "cdafc794cafeae377868d7a40a70e282a737e39abe77c0d8b73614447b364a21",
    ),
    (
        "mmproj-HunyuanOCR-Q8_0.gguf",
        (
            "https://huggingface.co/ggml-org/HunyuanOCR-GGUF/resolve/main/"
            "mmproj-HunyuanOCR-Q8_0.gguf?download=true"
        ),
        "b77913164ff73d4c0dc4d994e236ed72bacbbe5c5db1ec9b2828627b46c32804",
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, target: Path) -> None:
    partial = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(
        url, headers={"User-Agent": "career-card-local-setup"}
    )
    with urllib.request.urlopen(request) as response, partial.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0"))
        received = 0
        next_report = 0
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            received += len(chunk)
            percent = int(received * 100 / total) if total else 0
            if total and percent >= next_report:
                print(f"  {target.name}: {percent}%", flush=True)
                next_report += 5
    partial.replace(target)


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            member_path = (destination / member.filename).resolve()
            if destination not in member_path.parents and member_path != destination:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        bundle.extractall(destination)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    install_root = project_root / "work" / "local-ocr"
    downloads = install_root / "downloads"
    binary_dir = install_root / "bin"
    model_dir = install_root / "models"
    downloads.mkdir(parents=True, exist_ok=True)
    binary_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    for name, url, expected_digest in ASSETS:
        archive = downloads / name
        if not archive.is_file() or sha256(archive) != expected_digest:
            print(f"Downloading {name}...")
            download(url, archive)
        if sha256(archive) != expected_digest:
            raise RuntimeError(f"Checksum verification failed for {name}")
        print(f"Extracting {name}...")
        safe_extract(archive, binary_dir)

    for name, url, expected_digest in MODEL_ASSETS:
        model_file = model_dir / name
        if not model_file.is_file() or sha256(model_file) != expected_digest:
            print(f"Downloading {name}...")
            download(url, model_file)
        if sha256(model_file) != expected_digest:
            raise RuntimeError(f"Checksum verification failed for {name}")

    executable = binary_dir / "llama-server.exe"
    if not executable.is_file():
        raise RuntimeError("llama-server.exe was not found after extraction")
    print(f"Local OCR runtime ready: {executable}")
    print(f"Local HunyuanOCR model ready: {model_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
