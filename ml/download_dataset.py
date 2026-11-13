"""Download the pinned, public Bitext CSV without transforming its raw file."""
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "bitext"
DATASET_ID = "bitext/Bitext-customer-support-llm-chatbot-training-dataset"
REVISION = "0e8da3ba739b8b03572f7f058b9de9c90e8a692e"
FILENAME = "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
LICENSE = "cdla-sharing-1.0"
EXPECTED_SIZE = 19_202_474
EXPECTED_SHA256 = "6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434"
SOURCE_URL = (
    f"https://huggingface.co/datasets/{DATASET_ID}/resolve/{REVISION}/{FILENAME}?download=true"
)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DIR / FILENAME
    manifest_path = RAW_DIR / "dataset_manifest.json"
    if raw_path.exists() or manifest_path.exists():
        raise SystemExit(
            f"Refusing to overwrite existing raw dataset files in {RAW_DIR}. "
            "Inspect or move them manually before retrying."
        )

    request = Request(SOURCE_URL, headers={"User-Agent": "ai-customer-support-intelligence/1.0"})
    digest = hashlib.sha256()
    downloaded = 0
    temporary_path = None
    try:
        with urlopen(request, timeout=60) as response:
            if response.status != 200:
                raise RuntimeError(f"Unexpected HTTP status {response.status}")
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) != EXPECTED_SIZE:
                raise RuntimeError("Source file size differs from the pinned repository metadata")
            with tempfile.NamedTemporaryFile(
                mode="wb", prefix="bitext-", suffix=".part", dir=RAW_DIR, delete=False
            ) as output:
                temporary_path = Path(output.name)
                while chunk := response.read(1024 * 1024):
                    downloaded += len(chunk)
                    if downloaded > EXPECTED_SIZE:
                        raise RuntimeError("Download exceeded the pinned file size")
                    digest.update(chunk)
                    output.write(chunk)

        if downloaded != EXPECTED_SIZE or digest.hexdigest() != EXPECTED_SHA256:
            raise RuntimeError("Downloaded CSV size or SHA-256 does not match the pinned source")
        temporary_path.replace(raw_path)
        manifest = {
            "dataset_id": DATASET_ID,
            "source_url": SOURCE_URL,
            "revision": REVISION,
            "filename": FILENAME,
            "license": LICENSE,
            "rows_reported_by_source": 26872,
            "file_size_bytes": downloaded,
            "sha256": digest.hexdigest(),
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "raw_data_modified": False,
            "attribution": "Bitext Innovations (2024), via Hugging Face Datasets",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    except Exception as exc:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
        raise SystemExit(f"Dataset download failed: {type(exc).__name__}: {exc}") from exc

    print(f"Downloaded pinned source CSV: {raw_path.relative_to(ROOT)}")
    print(f"Rows reported by source: {manifest['rows_reported_by_source']:,}")
    print(f"Size: {downloaded:,} bytes; SHA-256 verified")
    print(f"License: {LICENSE}; raw file and manifest are under ignored data/raw/")


if __name__ == "__main__":
    main()
