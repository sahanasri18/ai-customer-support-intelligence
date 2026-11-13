"""Compare and train local TF-IDF category classifiers without split leakage."""
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC


ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed" / "bitext"
MODELS_DIR = ROOT / "ml" / "models"
EVALUATION_PATH = ROOT / "docs" / "evaluation_report.md"
SEED = 42


def build_pipeline(algorithm: str) -> Pipeline:
    if algorithm == "LogisticRegression":
        classifier = LogisticRegression(
            C=3.0, max_iter=1500, class_weight="balanced", random_state=SEED
        )
    elif algorithm == "LinearSVC":
        classifier = LinearSVC(C=1.0, class_weight="balanced", random_state=SEED)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2), max_features=50000, min_df=2,
            sublinear_tf=True, strip_accents="unicode",
        )),
        ("classifier", classifier),
    ])


def score_model(model: Pipeline, features: pd.Series, labels: pd.Series) -> dict:
    predictions = model.predict(features)
    label_order = sorted(set(labels) | set(predictions))
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision_macro": float(precision_score(labels, predictions, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(labels, predictions, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(labels, predictions, average="macro", zero_division=0)),
        "labels": label_order,
        "confusion_matrix": confusion_matrix(labels, predictions, labels=label_order).tolist(),
        "per_class": classification_report(
            labels, predictions, labels=label_order, output_dict=True, zero_division=0
        ),
    }


def main() -> None:
    split_paths = {name: PROC_DIR / f"{name}.csv" for name in ("train", "validation", "test")}
    if not all(path.is_file() for path in split_paths.values()):
        raise SystemExit("Processed train/validation/test splits missing. Run ml/preprocess.py first.")
    splits = {name: pd.read_csv(path) for name, path in split_paths.items()}
    for name, data in splits.items():
        if not {"text_clean", "category"}.issubset(data.columns) or data.empty:
            raise SystemExit(f"Invalid or empty {name} split")
    train, validation, test = (splits[name] for name in ("train", "validation", "test"))
    train_labels = set(train.category)
    if set(validation.category) - train_labels or set(test.category) - train_labels:
        raise SystemExit("Validation/test contains category classes absent from training")

    comparisons = {}
    candidates = {}
    for algorithm in ("LogisticRegression", "LinearSVC"):
        pipeline = build_pipeline(algorithm)
        # Pipeline.fit learns TF-IDF vocabulary/weights from train only.
        pipeline.fit(train.text_clean, train.category)
        candidates[algorithm] = pipeline
        comparisons[algorithm] = score_model(
            pipeline, validation.text_clean, validation.category
        )

    selected_algorithm = max(
        ("LogisticRegression", "LinearSVC"),
        key=lambda name: comparisons[name]["f1_macro"],
    )
    selected = candidates[selected_algorithm]
    test_metrics = score_model(selected, test.text_clean, test.category)

    # The LinearSVC has no calibrated probability output. Do not turn its
    # decision margins into a made-up probability or confidence score.
    confidence_supported = hasattr(selected, "predict_proba")
    source_manifest_path = ROOT / "data" / "raw" / "bitext" / "dataset_manifest.json"
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    trained_at = datetime.now(timezone.utc)
    model_version = f"bitext-category-{trained_at.strftime('%Y%m%dT%H%M%SZ')}"

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(selected, MODELS_DIR / "category_pipeline.joblib")
    metrics_document = {
        "task": "category_classification",
        "dataset_id": source_manifest["dataset_id"],
        "dataset_revision": source_manifest["revision"],
        "dataset_license": source_manifest["license"],
        "dataset_sha256": source_manifest["sha256"],
        "model_version": model_version,
        "trained_at_utc": trained_at.isoformat(),
        "selected_algorithm": selected_algorithm,
        "candidate_selection_metric": "validation macro F1",
        "validation_metrics_by_candidate": comparisons,
        "held_out_test_metrics": test_metrics,
        "rows": {name: len(data) for name, data in splits.items()},
        "classes": sorted(train_labels),
        "random_seed": SEED,
        "split": {"train": 0.70, "validation": 0.15, "test": 0.15},
        "training_policy": "TF-IDF is fit on train only; validation selects algorithm; test is final evaluation.",
        "confidence_available": confidence_supported,
        "dependencies": {"python": platform.python_version(), "scikit_learn": sklearn.__version__},
        "limitations": [
            "Bitext describes a synthetic customer-service intent dataset, not real ticket traffic.",
            "Target labels are the dataset's category labels, not the application's manually entered ticket category taxonomy.",
            "Near-duplicate paraphrases generated from shared templates may occur across splits.",
        ],
    }
    (MODELS_DIR / "category_metrics.json").write_text(
        json.dumps(metrics_document, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (MODELS_DIR / "model_version.txt").write_text(model_version, encoding="utf-8")
    availability = {
        "model_version": model_version,
        "trained_at_utc": trained_at.isoformat(),
        "source_dataset": source_manifest["dataset_id"],
        "source_revision": source_manifest["revision"],
        "models": {
            "category": {"available": True, "artifact": "category_pipeline.joblib", "confidence": confidence_supported},
            "priority": {"available": False, "reason": "The selected dataset has no priority labels."},
            "sentiment": {"available": False, "reason": "The selected dataset has no sentiment labels."},
        },
    }
    (MODELS_DIR / "model_manifest.json").write_text(
        json.dumps(availability, indent=2), encoding="utf-8"
    )

    lines = [
        "# Category model evaluation",
        "",
        f"- Generated UTC: {trained_at.isoformat()}",
        f"- Dataset: `{source_manifest['dataset_id']}` at `{source_manifest['revision']}` ({source_manifest['license']})",
        "- Synthetic requests only; these results do not establish performance on real customer tickets.",
        "- Feature: `instruction` only. `flags`, `intent`, and `response` are excluded from model inputs.",
        "- Split: stratified 70/15/15 train/validation/test, seed 42. TF-IDF fitted on train only.",
        f"- Rows: train {len(train):,}, validation {len(validation):,}, test {len(test):,}.",
        "",
        "## Validation comparison (algorithm selection)",
        "",
        "| Algorithm | Accuracy | Macro precision | Macro recall | Macro F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for algorithm, metrics in comparisons.items():
        lines.append(
            f"| {algorithm} + TF-IDF | {metrics['accuracy']:.4f} | "
            f"{metrics['precision_macro']:.4f} | {metrics['recall_macro']:.4f} | {metrics['f1_macro']:.4f} |"
        )
    lines.extend([
        "",
        f"Selected on validation macro F1: **{selected_algorithm} + TF-IDF**.",
        "",
        "## Held-out test results (selected model)",
        "",
        f"- Accuracy: {test_metrics['accuracy']:.4f}",
        f"- Macro precision: {test_metrics['precision_macro']:.4f}",
        f"- Macro recall: {test_metrics['recall_macro']:.4f}",
        f"- Macro F1: {test_metrics['f1_macro']:.4f}",
        "- Confusion matrix label order: " + ", ".join(test_metrics["labels"]),
        "- Confusion matrix (rows=true, columns=predicted):",
        "```text",
        json.dumps(test_metrics["confusion_matrix"]),
        "```",
        "",
        "## Per-class held-out test metrics",
        "",
        "| Category | Precision | Recall | F1 | Support |",
        "| --- | ---: | ---: | ---: | ---: |",
    ])
    for label in test_metrics["labels"]:
        row = test_metrics["per_class"][label]
        lines.append(
            f"| {label} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1-score']:.4f} | {int(row['support'])} |"
        )
    lines.extend([
        "",
        "## Other tasks",
        "",
        "- Priority: not trained; this dataset has no priority label.",
        "- Sentiment: not trained; this dataset has no sentiment label.",
        "- Urgency remains the existing transparent keyword rule, not a learned label.",
        "- Near-duplicate template paraphrases may still cross the split boundary; interpret scores as a synthetic benchmark.",
        "",
    ])
    EVALUATION_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Selected validation model: {selected_algorithm}")
    print(f"Held-out test: accuracy={test_metrics['accuracy']:.4f}, "
          f"macro precision={test_metrics['precision_macro']:.4f}, "
          f"macro recall={test_metrics['recall_macro']:.4f}, "
          f"macro F1={test_metrics['f1_macro']:.4f}")
    print(f"Saved model version {model_version} and evaluation report.")


if __name__ == "__main__":
    main()
