# Category model evaluation

- Generated UTC: 2026-11-10T11:23:14.193326+00:00
- Dataset: `bitext/Bitext-customer-support-llm-chatbot-training-dataset` at `0e8da3ba739b8b03572f7f058b9de9c90e8a692e` (cdla-sharing-1.0)
- Synthetic requests only; these results do not establish performance on real customer tickets.
- Feature: `instruction` only. `flags`, `intent`, and `response` are excluded from model inputs.
- Split: stratified 70/15/15 train/validation/test, seed 42. TF-IDF fitted on train only.
- Rows: train 16,991, validation 3,641, test 3,642.

## Validation comparison (algorithm selection)

| Algorithm | Accuracy | Macro precision | Macro recall | Macro F1 |
| --- | ---: | ---: | ---: | ---: |
| LogisticRegression + TF-IDF | 0.9984 | 0.9989 | 0.9982 | 0.9985 |
| LinearSVC + TF-IDF | 0.9992 | 0.9996 | 0.9989 | 0.9992 |

Selected on validation macro F1: **LinearSVC + TF-IDF**.

## Held-out test results (selected model)

- Accuracy: 0.9989
- Macro precision: 0.9991
- Macro recall: 0.9989
- Macro F1: 0.9990
- Reliability follow-up: see the separate [intent-held-out grouped stress test](grouped_evaluation_report.md); the random-split result remains preserved but is not considered a reliable estimate for unseen intents.
- Confusion matrix label order: ACCOUNT, CANCEL, CONTACT, DELIVERY, FEEDBACK, INVOICE, ORDER, PAYMENT, REFUND, SHIPPING, SUBSCRIPTION
- Confusion matrix (rows=true, columns=predicted):
```text
[[804, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 141, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 295, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 247, 0, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 299, 0, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 270, 0, 0, 0, 0, 0], [0, 0, 0, 0, 0, 0, 459, 0, 0, 1, 0], [2, 0, 0, 1, 0, 0, 0, 295, 0, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 387, 0, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 292, 0], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 149]]
```

## Per-class held-out test metrics

| Category | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| ACCOUNT | 0.9975 | 1.0000 | 0.9988 | 804 |
| CANCEL | 1.0000 | 1.0000 | 1.0000 | 141 |
| CONTACT | 1.0000 | 1.0000 | 1.0000 | 295 |
| DELIVERY | 0.9960 | 1.0000 | 0.9980 | 247 |
| FEEDBACK | 1.0000 | 1.0000 | 1.0000 | 299 |
| INVOICE | 1.0000 | 1.0000 | 1.0000 | 270 |
| ORDER | 1.0000 | 0.9978 | 0.9989 | 460 |
| PAYMENT | 1.0000 | 0.9899 | 0.9949 | 298 |
| REFUND | 1.0000 | 1.0000 | 1.0000 | 387 |
| SHIPPING | 0.9966 | 1.0000 | 0.9983 | 292 |
| SUBSCRIPTION | 1.0000 | 1.0000 | 1.0000 | 149 |

## Other tasks

- Priority: not trained; this dataset has no priority label.
- Sentiment: not trained; this dataset has no sentiment label.
- Urgency remains the existing transparent keyword rule, not a learned label.
- Near-duplicate template paraphrases may still cross the split boundary; interpret scores as a synthetic benchmark.
