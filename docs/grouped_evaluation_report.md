# Intent-held-out grouped evaluation

This separate stress test preserves the original random-split benchmark and its report.
All examples for a source `intent` are assigned as a unit, so same-intent generated paraphrase templates cannot cross train/validation/test.
The algorithm is fixed to LinearSVC selected on the original random-split validation set; this grouped test was not used to select it.

## Results

- Rows: train 13,235, validation 2,895, test 8,144.
- Source intent groups: train 15, validation 3, test 9.
- Test categories: ACCOUNT, CONTACT, DELIVERY, FEEDBACK, INVOICE, ORDER, PAYMENT, REFUND, SHIPPING.
- Accuracy: 0.6542
- Macro precision: 0.5959
- Macro recall: 0.5427
- Macro F1: 0.5018

## Audit of the preserved random split

- All 27 of 27 source intents appear in each original partition.
- Template signatures use exact `text_clean` after replacing named `{{...}}` placeholders and numeric sequences. This is a reproducible structural match, not a semantic similarity measure.
| Original split pair | Shared signatures | Rows in first with match in second | Rows in second with match in first |
| --- | ---: | ---: | ---: |
| train-validation | 83 | 99 | 85 |
| train-test | 88 | 107 | 93 |
| validation-test | 25 | 26 | 27 |

## Per-class test metrics

| Category | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| ACCOUNT | 0.5858 | 1.0000 | 0.7388 | 836 |
| CANCEL | n/a | n/a | n/a | 0 |
| CONTACT | 0.6964 | 0.8366 | 0.7601 | 979 |
| DELIVERY | 0.9037 | 0.1232 | 0.2169 | 990 |
| FEEDBACK | 0.6744 | 0.0292 | 0.0560 | 993 |
| INVOICE | 0.8997 | 1.0000 | 0.9472 | 888 |
| ORDER | 0.6635 | 0.9949 | 0.7961 | 783 |
| PAYMENT | 0.9919 | 0.6173 | 0.7610 | 993 |
| REFUND | 0.3275 | 0.3772 | 0.3506 | 692 |
| SHIPPING | 0.8121 | 0.9909 | 0.8926 | 990 |
| SUBSCRIPTION | n/a | n/a | n/a | 0 |

## Interpretation and limitations

- Two categories have only one source intent and therefore have no unseen-intent test examples.
- Intent grouping blocks intent-specific templates but does not guarantee grouping of semantically similar prompts across different intents.
- The dataset is synthetic; neither this stress test nor the random split estimates real customer-ticket performance.
- The high random-split score is optimistic relative to this unseen-intent stress test; it benefits from examples drawn across the same source intents/templates.
- Two categories have one intent and cannot contribute a held-out intent without removing that category from training. They are not assigned fabricated scores.
- Some paraphrases may be similar across different intents; intent grouping is a conservative, reproducible grouping rule, not a semantic duplicate detector.
- Full class allocation and confusion matrix are recorded in `ml/models/intent_heldout_metrics.json` (local artifact).
