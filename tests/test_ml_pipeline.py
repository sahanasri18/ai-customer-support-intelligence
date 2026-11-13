"""Local dataset/model invariants; data and model artifacts remain git-ignored."""
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "bitext"
PROC_DIR = ROOT / "data" / "processed" / "bitext"
MODEL_PATH = ROOT / "ml" / "models" / "category_pipeline.joblib"
sys.path.insert(0, str(ROOT / "ml"))
from evaluate_intent_heldout import allocate_intent_groups


def test_downloaded_dataset_integrity_and_metadata():
    raw_path = next(RAW_DIR.glob("*.csv"), None) if RAW_DIR.is_dir() else None
    if raw_path is None:
        pytest.skip("Bitext raw data is not present in this checkout")
    manifest = json.loads((RAW_DIR / "dataset_manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert digest == manifest["sha256"]
    assert manifest["license"] == "cdla-sharing-1.0"
    source = pd.read_csv(raw_path, low_memory=False)
    assert len(source) == manifest["rows_reported_by_source"] == 26872
    assert set(source.columns) == {"flags", "instruction", "category", "intent", "response"}
    assert source.isna().sum().sum() == 0
    assert source["category"].nunique() == 11
    assert source["intent"].nunique() == 27


def test_processed_splits_are_stratified_and_have_no_exact_text_overlap():
    split_paths = [PROC_DIR / f"{name}.csv" for name in ("train", "validation", "test")]
    if not all(path.is_file() for path in split_paths):
        pytest.skip("Bitext processed splits are not present in this checkout")
    splits = [pd.read_csv(path) for path in split_paths]
    assert all(not split.empty for split in splits)
    assert all(set(split.category) == set(splits[0].category) for split in splits[1:])
    texts = [set(split.text_clean) for split in splits]
    assert not (texts[0] & texts[1] or texts[0] & texts[2] or texts[1] & texts[2])
    assert all(not split.text_clean.duplicated().any() for split in splits)


def test_saved_classifier_produces_only_source_category_labels():
    if not MODEL_PATH.is_file():
        pytest.skip("Trained category artifact is not present in this checkout")
    import joblib

    model = joblib.load(MODEL_PATH)
    classes = set(model.named_steps["classifier"].classes_)
    prediction = str(model.predict(["I need help with my order delivery"])[0])
    assert prediction in classes
    assert classes == set(pd.read_csv(PROC_DIR / "train.csv").category.unique())


def test_intent_heldout_evaluation_keeps_each_intent_in_one_split():
    names = ("train", "validation", "test")
    splits = [pd.read_csv(PROC_DIR / f"{name}.csv") for name in names]
    grouped_train, grouped_validation, grouped_test, allocations = allocate_intent_groups(
        pd.concat(splits, ignore_index=True).drop_duplicates(subset=["text_clean"])
    )
    intent_sets = [set(part.intent) for part in (grouped_train, grouped_validation, grouped_test)]
    assert not (intent_sets[0] & intent_sets[1])
    assert not (intent_sets[0] & intent_sets[2])
    assert not (intent_sets[1] & intent_sets[2])
    assert set(grouped_train.category) == set(splits[0].category)
    metrics = json.loads((ROOT / "ml" / "models" / "intent_heldout_metrics.json").read_text(encoding="utf-8"))
    assert metrics["protocol"] == "intent-held-out grouped stress test"
    assert metrics["rows"]["test"] == len(grouped_test)
    assert metrics["accuracy"] == pytest.approx(0.6542, abs=0.0001)
    assert metrics["macro_f1"] == pytest.approx(0.5018, abs=0.0001)
    assert metrics["categories_without_heldout_intents"] == ["CANCEL", "SUBSCRIPTION"]
    audit = metrics["original_random_split_audit"]
    assert audit["intents_present_in_all_three_splits"] == audit["total_source_intents"] == 27
    assert audit["pairwise_template_crossings"]["train-test"]["shared_template_signatures"] == 88
    assert len(allocations) == 11
