# Model status and evaluation

**Category model trained and integrated locally on 2026-11-10.** Artifact: ignored `ml/models/category_pipeline.joblib`. Model version: `bitext-category-20261110T112314Z`. No priority or sentiment model is available.

## Dataset and split

- Source: Bitext customer-service dataset, pinned revision `0e8da3ba739b8b03572f7f058b9de9c90e8a692e`, CDLA-Sharing-1.0. Full license and data-quality analysis: [`dataset_review.md`](dataset_review.md) and [`data_quality_report.md`](data_quality_report.md).
- Model input is `instruction` only; `flags`, `intent`, and `response` are excluded. Target is the source `category` label, preserving all 11 observed classes.
- 24,274 unique usable instructions after removing 2,598 repeated normalized instructions; no exact normalized-text overlap across splits.
- Stratified split with seed 42: train 16,991, validation 3,641, test 3,642. The TF-IDF pipeline is fit on train only. Validation macro F1 selected the algorithm; test scores were computed once on the selected model.

## Candidate comparison on validation

| Model | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| TF-IDF + Logistic Regression | 0.9984 | 0.9989 | 0.9982 | 0.9985 |
| TF-IDF + Linear SVC | 0.9992 | 0.9996 | 0.9989 | 0.9992 |

Linear SVC was selected on validation macro F1.

## Selected model on held-out test

- Accuracy: **0.9989**
- Macro precision: **0.9991**
- Macro recall: **0.9989**
- Macro F1: **0.9990**
- Per-class precision, recall, F1, support, and the 11-by-11 confusion matrix are in [`evaluation_report.md`](evaluation_report.md) and `ml/models/category_metrics.json` (local, ignored).

These high scores are a synthetic benchmark only. Bitext says its instructions are generated using NLP/NLG from source text and automated labeling. The split removes exact normalized duplicate instructions but does not cluster all generated near-duplicate paraphrases; shared templates may make the holdout easier. The dataset is intent/request-focused, not a sample of real ticket traffic. Do not claim these metrics predict production performance.

## Separate template stress test

The original random-split results above are preserved unchanged. A second evaluation groups every row for a source intent together, preventing same-intent paraphrases from crossing train/validation/test. It holds the previously selected Linear SVC fixed and does not use the grouped test for model selection. The intent-held-out test scores **0.6542 accuracy** and **0.5018 macro F1** on 8,144 examples from nine categories. CANCEL and SUBSCRIPTION each have only one source intent, so no unseen-intent test example is possible for those classes while keeping them in training. Per-class results and the split protocol are in [`grouped_evaluation_report.md`](grouped_evaluation_report.md).

The gap from random-split macro F1 0.9990 to intent-held-out macro F1 0.5018 indicates the original result is strongly optimistic for generalizing to unseen request/intent templates. Intent grouping blocks all within-intent template variants but cannot guarantee that semantically related language across different intents has no overlap. This synthetic stress test is still not evidence of real-world customer-ticket performance.

The original split audit found all **27 of 27 intents in each of train, validation, and test**. Exact structural text signatures (lowercased `text_clean` with named placeholders and numeric sequences normalized) were also shared across train/validation (83 signatures), train/test (88), and validation/test (25). This signature check is conservative and does not detect every semantic paraphrase; it does confirm repeated prompt structures crossed the original boundaries. See the grouped report for matching-row counts and method.

## Runtime availability and confidence

- `GET /api/predictions/status` reports which artifacts actually load at runtime and their model version.
- `POST /api/predictions/category` runs the loaded category pipeline. Predictions are stored on ticket creation and returned by ticket read/re-predict APIs.
- Linear SVC has no calibrated probability interface in this artifact, so category confidence is `null` and the UI does not fabricate a confidence percentage.
- **Priority:** unavailable because Bitext has no priority labels. Tobi has source priority labels but is CC BY-NC 4.0, so it was not downloaded or used.
- **Sentiment:** unavailable because no selected dataset sentiment labels exist.
- **Urgency:** existing keyword/rule detector only. It has no calibrated confidence and can miss serious issues or flag non-urgent wording; human review remains necessary.

## Reproduce

With the original CSV already present, run:

```powershell
.\venv\Scripts\python.exe .\ml\preprocess.py
.\venv\Scripts\python.exe .\ml\train_models.py
```

The downloader pins the reviewed source revision, verifies expected byte size and SHA-256, and refuses to overwrite an existing raw copy. Raw data, splits, and trained artifacts remain local and Git-ignored.
