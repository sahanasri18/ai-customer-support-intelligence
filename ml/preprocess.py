"""Inspect and split the Bitext customer-service intent dataset.

Only ``instruction`` is model input and ``category`` is the target. The raw
source CSV is never modified; deterministic, de-duplicated splits are written
under ignored data/processed/.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "bitext" / "Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv"
MANIFEST = ROOT / "data" / "raw" / "bitext" / "dataset_manifest.json"
PROC_DIR = ROOT / "data" / "processed" / "bitext"
REPORT_PATH = ROOT / "docs" / "data_quality_report.md"
SEED = 42
REQUIRED_COLUMNS = {"flags", "instruction", "category", "intent", "response"}


def clean_text(value: object) -> str:
    value = "" if pd.isna(value) else str(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"https?://\S+|www\.\S+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def pii_scan_counts(frame: pd.DataFrame) -> dict[str, dict[str, int]]:
    email = re.compile(r"(?i)(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
    phone = re.compile(r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)")
    ip_address = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
    findings = {}
    for column in ("instruction", "response"):
        values = frame[column].fillna("").astype(str)
        findings[column] = {
            "rows_with_email_like_text": int(values.map(lambda v: bool(email.search(v))).sum()),
            "rows_with_phone_like_text": int(values.map(lambda v: bool(phone.search(v))).sum()),
            "rows_with_ip_like_text": int(values.map(lambda v: bool(ip_address.search(v))).sum()),
            "rows_with_template_placeholders": int(values.str.contains(r"\{\{[^{}]+\}\}", regex=True).sum()),
        }
    return findings


def distribution(series: pd.Series) -> dict[str, int]:
    return {str(label): int(count) for label, count in series.value_counts(dropna=False).items()}


def main() -> None:
    if not RAW_CSV.is_file() or not MANIFEST.is_file():
        raise SystemExit("Raw Bitext CSV/manifest missing. Run ml/download_dataset.py first.")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("license") != "cdla-sharing-1.0":
        raise SystemExit("Unexpected dataset license; refusing to preprocess.")

    source = pd.read_csv(RAW_CSV, low_memory=False)
    missing_columns = REQUIRED_COLUMNS - set(source.columns)
    if missing_columns:
        raise SystemExit(f"Source schema mismatch; missing columns: {sorted(missing_columns)}")

    raw_rows = len(source)
    raw_duplicate_rows = int(source.duplicated().sum())
    missing_by_column = {str(k): int(v) for k, v in source.isna().sum().items()}
    types_by_column = {str(k): str(v) for k, v in source.dtypes.items()}
    source_category_distribution = distribution(source["category"])
    source_intent_distribution = distribution(source["intent"])

    # Standardize labels but preserve their source vocabulary; no category map
    # or labels are synthesized. Drop blank/invalid rows before split creation.
    work = source[["instruction", "category", "intent", "flags"]].copy()
    work["text_clean"] = work["instruction"].map(clean_text)
    work["category"] = work["category"].fillna("").astype(str).str.strip().str.upper()
    work["intent"] = work["intent"].fillna("").astype(str).str.strip().str.lower()
    empty_text = int(work["text_clean"].eq("").sum())
    empty_category = int(work["category"].eq("").sum())
    empty_intent = int(work["intent"].eq("").sum())
    work = work[(work.text_clean != "") & (work.category != "") & (work.intent != "")].copy()

    # An intent should map consistently to one high-level category. Exclude an
    # entire ambiguous intent rather than silently picking or remapping labels.
    categories_per_intent = work.groupby("intent")["category"].nunique()
    conflicting_intents = categories_per_intent[categories_per_intent > 1].index
    conflicting_rows = int(work.intent.isin(conflicting_intents).sum())
    work = work[~work.intent.isin(conflicting_intents)].copy()

    # Normalize exact text variants before deduplication. Conflicting targets
    # for identical input are invalid and all such rows are excluded.
    category_per_text = work.groupby("text_clean")["category"].nunique()
    conflicting_texts = category_per_text[category_per_text > 1].index
    conflicting_text_rows = int(work.text_clean.isin(conflicting_texts).sum())
    work = work[~work.text_clean.isin(conflicting_texts)].copy()
    duplicate_instructions_removed = int(work.duplicated(subset=["text_clean"], keep="first").sum())
    work = work.drop_duplicates(subset=["text_clean"], keep="first").reset_index(drop=True)

    if work.category.nunique() < 2:
        raise SystemExit("Not enough usable category labels after validation.")
    if int(work.category.value_counts().min()) < 3:
        raise SystemExit("Each category needs at least three unique instructions for stratified splits.")

    train, holdout = train_test_split(
        work, test_size=0.30, random_state=SEED, stratify=work["category"]
    )
    validation, test = train_test_split(
        holdout, test_size=0.50, random_state=SEED + 1,
        stratify=holdout["category"],
    )

    split_texts = [set(split["text_clean"]) for split in (train, validation, test)]
    if (split_texts[0] & split_texts[1]) or (split_texts[0] & split_texts[2]) or (split_texts[1] & split_texts[2]):
        raise RuntimeError("Exact normalized text leaked between splits")

    PROC_DIR.mkdir(parents=True, exist_ok=True)
    for name, split in (("train", train), ("validation", validation), ("test", test)):
        split[["text_clean", "category", "intent"]].to_csv(PROC_DIR / f"{name}.csv", index=False)
    config = {
        "source_dataset": manifest["dataset_id"],
        "source_revision": manifest["revision"],
        "license": manifest["license"],
        "text_column": "instruction",
        "label_column": "category",
        "intent_column": "intent",
        "excluded_columns": ["flags", "response"],
        "split_seed": SEED,
        "split_ratios": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "split_rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "exact_normalized_text_overlap": 0,
    }
    (PROC_DIR / "preprocessing_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    report = [
        "# Bitext dataset quality report",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).isoformat()}",
        f"Source: {manifest['dataset_id']} at revision `{manifest['revision']}`",
        f"License: {manifest['license']}",
        f"Raw CSV SHA-256: `{manifest['sha256']}`",
        "Synthetic customer-service requests; not observations of real customer behavior.",
        "",
        "## Source inspection",
        f"- Rows: {raw_rows:,}; columns: {len(source.columns)}",
        f"- Columns and pandas types: `{json.dumps(types_by_column, sort_keys=True)}`",
        f"- Missing values by column: `{json.dumps(missing_by_column, sort_keys=True)}`",
        f"- Exact duplicate full rows: {raw_duplicate_rows:,}",
        f"- Duplicate normalized instructions removed: {duplicate_instructions_removed:,}",
        f"- Empty instruction/category/intent rows removed: {empty_text}/{empty_category}/{empty_intent}",
        f"- Rows excluded for inconsistent intent-to-category labels: {conflicting_rows:,}",
        f"- Rows excluded for identical text with conflicting categories: {conflicting_text_rows:,}",
        f"- Category class counts: `{json.dumps(source_category_distribution, sort_keys=True)}`",
        f"- Intent class count: {len(source_intent_distribution)}",
        f"- PII-like patterns in instruction and response text (counts only; no matched values emitted): `{json.dumps(pii_scan_counts(source), sort_keys=True)}`",
        "- The source uses named placeholder tokens (for example `{{Order Number}}`); these are synthetic slots, not observed customer identifiers.",
        "- Near-duplicate paraphrases across different instructions were not deterministically clustered; held-out scores may still benefit from shared generation templates.",
        "- `flags` and `response` are excluded from model input; only `instruction` is used.",
        "",
        "## Validated modeling data",
        f"- Rows after validation and exact-text deduplication: {len(work):,}",
        f"- Category counts after validation: `{json.dumps(distribution(work['category']), sort_keys=True)}`",
        f"- Stratified split rows: train {len(train):,}, validation {len(validation):,}, test {len(test):,}.",
        "- Exact normalized instruction overlap between splits: 0.",
        "- Text vectorization and model fitting are performed inside the train-only scikit-learn pipeline.",
        "- Priority and sentiment labels are absent from this source; those models are not trained.",
    ]
    REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Inspected {raw_rows:,} raw rows; retained {len(work):,} unique valid instructions.")
    print(f"Split rows: train={len(train):,}, validation={len(validation):,}, test={len(test):,}.")
    print("Category counts:", json.dumps(distribution(work["category"]), sort_keys=True))
    print(f"Saved quality report: {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
