"""Evaluate the selected category model with entire source intents held out.

Bitext generates multiple paraphrase templates within each intent. Holding out
whole intents prevents those intent-specific templates from straddling the
training/evaluation boundary. This is a stress test, not the headline random
split benchmark, and leaves categories with a single source intent unevaluated.
"""
import json
import re
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from train_models import build_pipeline

ROOT = Path(__file__).resolve().parent.parent
PROC_DIR = ROOT / "data" / "processed" / "bitext"
MODEL_DIR = ROOT / "ml" / "models"
OUTPUT_JSON = MODEL_DIR / "intent_heldout_metrics.json"
OUTPUT_MD = ROOT / "docs" / "grouped_evaluation_report.md"


def template_signature(text: str) -> str:
    """Make an exact structural signature by normalizing placeholders/numbers."""
    text = re.sub(r"\{\{[^{}]+\}\}", "<slot>", str(text))
    text = re.sub(r"\b\d+(?:[.,]\d+)*\b", "<num>", text)
    return re.sub(r"\s+", " ", text).strip()


def allocate_intent_groups(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Allocate whole intents within each category, deterministically."""
    intent_category = frame[["intent", "category"]].drop_duplicates()
    if intent_category.intent.duplicated().any():
        raise ValueError("Source intent-to-category labels conflict")

    train_intents, validation_intents, test_intents = set(), set(), set()
    allocations = {}
    for category, part in intent_category.groupby("category", sort=True):
        intents = sorted(part.intent.tolist())
        if len(intents) == 1:
            train_intents.update(intents)
            allocations[category] = {"train": intents, "validation": [], "test": []}
        elif len(intents) == 2:
            # Keep one intent in training and reserve the other for evaluation.
            train_intents.add(intents[0])
            test_intents.add(intents[1])
            allocations[category] = {"train": [intents[0]], "validation": [], "test": [intents[1]]}
        else:
            # Reserve complete groups for validation and final test.
            train_intents.update(intents[:-2])
            validation_intents.add(intents[-2])
            test_intents.add(intents[-1])
            allocations[category] = {
                "train": intents[:-2], "validation": [intents[-2]], "test": [intents[-1]]
            }

    splits = tuple(
        frame[frame.intent.isin(group)].copy().reset_index(drop=True)
        for group in (train_intents, validation_intents, test_intents)
    )
    if not splits[0].category.nunique() == frame.category.nunique():
        raise RuntimeError("Intent grouping removed a category from training")
    if not splits[2].empty and set(splits[0].intent) & set(splits[2].intent):
        raise RuntimeError("Intent leakage across train/test")
    if not splits[1].empty and (set(splits[0].intent) & set(splits[1].intent)):
        raise RuntimeError("Intent leakage across train/validation")
    return (*splits, allocations)


def main() -> None:
    paths = [PROC_DIR / f"{name}.csv" for name in ("train", "validation", "test")]
    if not all(path.is_file() for path in paths):
        raise SystemExit("Processed source splits are missing; run ml/preprocess.py first.")
    # Reconstruct the validated rows from the preserved splits. This evaluation
    # uses intent grouping across the union, never the random split membership.
    random_splits = {
        name: pd.read_csv(path)
        for name, path in zip(("train", "validation", "test"), paths)
    }
    intent_sets = {name: set(part.intent) for name, part in random_splits.items()}
    template_sets = {
        name: set(part.text_clean.map(template_signature))
        for name, part in random_splits.items()
    }
    crossing_audit = {}
    for first, second in (("train", "validation"), ("train", "test"), ("validation", "test")):
        crossing_audit[f"{first}-{second}"] = {
            "shared_template_signatures": len(template_sets[first] & template_sets[second]),
            "first_split_rows_with_signature_in_second": int(
                random_splits[first].text_clean.map(template_signature).isin(template_sets[second]).sum()
            ),
            "second_split_rows_with_signature_in_first": int(
                random_splits[second].text_clean.map(template_signature).isin(template_sets[first]).sum()
            ),
        }
    frame = pd.concat(list(random_splits.values()), ignore_index=True)
    frame = frame.drop_duplicates(subset=["text_clean"]).reset_index(drop=True)
    train, validation, test, allocations = allocate_intent_groups(frame)
    if train.empty or test.empty:
        raise SystemExit("Intent-held-out evaluation did not produce train and test rows")

    # The original benchmark selected LinearSVC; hold the algorithm fixed to
    # evaluate split difficulty independently from another model-selection step.
    model = build_pipeline("LinearSVC")
    model.fit(train.text_clean, train.category)
    predictions = model.predict(test.text_clean)
    labels = sorted(set(train.category) | set(test.category))
    report = classification_report(
        test.category, predictions, labels=labels, output_dict=True, zero_division=0
    )
    evaluated_categories = sorted(set(test.category))
    payload = {
        "protocol": "intent-held-out grouped stress test",
        "grouping_key": "source intent; all normalized paraphrases for an intent remain together",
        "algorithm": "LinearSVC + TF-IDF",
        "selection": "Fixed to the model selected by the preserved random-split validation; grouped test not used for selection.",
        "rows": {"train": len(train), "validation": len(validation), "test": len(test)},
        "intent_counts": {"train": train.intent.nunique(), "validation": validation.intent.nunique(), "test": test.intent.nunique()},
        "categories_evaluated": evaluated_categories,
        "categories_without_heldout_intents": sorted(set(frame.category) - set(evaluated_categories)),
        "accuracy": float(accuracy_score(test.category, predictions)),
        "macro_precision": float(report["macro avg"]["precision"]),
        "macro_recall": float(report["macro avg"]["recall"]),
        "macro_f1": float(report["macro avg"]["f1-score"]),
        "per_class": {label: report.get(label, {"precision": 0.0, "recall": 0.0, "f1-score": 0.0, "support": 0}) for label in labels},
        "confusion_matrix_labels": labels,
        "confusion_matrix": confusion_matrix(test.category, predictions, labels=labels).tolist(),
        "intent_allocation": allocations,
        "original_random_split_audit": {
            "intents_present_in_all_three_splits": len(set.intersection(*intent_sets.values())),
            "total_source_intents": len(set.union(*intent_sets.values())),
            "template_signature_definition": "Exact text_clean after replacing named {{...}} placeholders and numeric sequences.",
            "pairwise_template_crossings": crossing_audit,
        },
        "caveats": [
            "Two categories have only one source intent and therefore have no unseen-intent test examples.",
            "Intent grouping blocks intent-specific templates but does not guarantee grouping of semantically similar prompts across different intents.",
            "The dataset is synthetic; neither this stress test nor the random split estimates real customer-ticket performance.",
        ],
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Intent-held-out grouped evaluation",
        "",
        "This separate stress test preserves the original random-split benchmark and its report.",
        "All examples for a source `intent` are assigned as a unit, so same-intent generated paraphrase templates cannot cross train/validation/test.",
        "The algorithm is fixed to LinearSVC selected on the original random-split validation set; this grouped test was not used to select it.",
        "",
        "## Results",
        "",
        f"- Rows: train {len(train):,}, validation {len(validation):,}, test {len(test):,}.",
        f"- Source intent groups: train {train.intent.nunique()}, validation {validation.intent.nunique()}, test {test.intent.nunique()}.",
        f"- Test categories: {', '.join(evaluated_categories)}.",
        f"- Accuracy: {payload['accuracy']:.4f}",
        f"- Macro precision: {payload['macro_precision']:.4f}",
        f"- Macro recall: {payload['macro_recall']:.4f}",
        f"- Macro F1: {payload['macro_f1']:.4f}",
        "",
        "## Audit of the preserved random split",
        "",
        f"- All {payload['original_random_split_audit']['intents_present_in_all_three_splits']} of {payload['original_random_split_audit']['total_source_intents']} source intents appear in each original partition.",
        "- Template signatures use exact `text_clean` after replacing named `{{...}}` placeholders and numeric sequences. This is a reproducible structural match, not a semantic similarity measure.",
        "| Original split pair | Shared signatures | Rows in first with match in second | Rows in second with match in first |",
        "| --- | ---: | ---: | ---: |",
    ]
    for pair, audit in crossing_audit.items():
        lines.append(
            f"| {pair} | {audit['shared_template_signatures']} | "
            f"{audit['first_split_rows_with_signature_in_second']} | "
            f"{audit['second_split_rows_with_signature_in_first']} |"
        )
    lines += [
        "",
        "## Per-class test metrics",
        "",
        "| Category | Precision | Recall | F1 | Support |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for label in labels:
        row = payload["per_class"][label]
        if row["support"]:
            lines.append(f"| {label} | {row['precision']:.4f} | {row['recall']:.4f} | {row['f1-score']:.4f} | {int(row['support'])} |")
        else:
            lines.append(f"| {label} | n/a | n/a | n/a | 0 |")
    lines += ["", "## Interpretation and limitations", ""]
    lines.extend(f"- {item}" for item in payload["caveats"])
    lines += [
        "- The high random-split score is optimistic relative to this unseen-intent stress test; it benefits from examples drawn across the same source intents/templates.",
        "- Two categories have one intent and cannot contribute a held-out intent without removing that category from training. They are not assigned fabricated scores.",
        "- Some paraphrases may be similar across different intents; intent grouping is a conservative, reproducible grouping rule, not a semantic duplicate detector.",
        "- Full class allocation and confusion matrix are recorded in `ml/models/intent_heldout_metrics.json` (local artifact).",
        "",
    ]
    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Intent-heldout sizes: train={len(train)}, validation={len(validation)}, test={len(test)}")
    print(f"Held-out test: accuracy={payload['accuracy']:.4f}, macro precision={payload['macro_precision']:.4f}, macro recall={payload['macro_recall']:.4f}, macro F1={payload['macro_f1']:.4f}")
    print("Per-class:", json.dumps({k: v for k, v in payload["per_class"].items() if v.get("support")}, sort_keys=True))
    print("Categories lacking held-out intents:", ", ".join(payload["categories_without_heldout_intents"]))


if __name__ == "__main__":
    main()
