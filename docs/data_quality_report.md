# Bitext dataset quality report

Generated UTC: 2026-11-10T11:23:08.848069+00:00
Source: bitext/Bitext-customer-support-llm-chatbot-training-dataset at revision `0e8da3ba739b8b03572f7f058b9de9c90e8a692e`
License: cdla-sharing-1.0
Raw CSV SHA-256: `6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434`
Synthetic customer-service requests; not observations of real customer behavior.

## Source inspection
- Rows: 26,872; columns: 5
- Columns and pandas types: `{"category": "object", "flags": "object", "instruction": "object", "intent": "object", "response": "object"}`
- Missing values by column: `{"category": 0, "flags": 0, "instruction": 0, "intent": 0, "response": 0}`
- Exact duplicate full rows: 0
- Duplicate normalized instructions removed: 2,598
- Empty instruction/category/intent rows removed: 0/0/0
- Rows excluded for inconsistent intent-to-category labels: 0
- Rows excluded for identical text with conflicting categories: 0
- Category class counts: `{"ACCOUNT": 5986, "CANCEL": 950, "CONTACT": 1999, "DELIVERY": 1994, "FEEDBACK": 1997, "INVOICE": 1999, "ORDER": 3988, "PAYMENT": 1998, "REFUND": 2992, "SHIPPING": 1970, "SUBSCRIPTION": 999}`
- Intent class count: 27
- PII-like patterns in instruction and response text (counts only; no matched values emitted): `{"instruction": {"rows_with_email_like_text": 0, "rows_with_ip_like_text": 0, "rows_with_phone_like_text": 0, "rows_with_template_placeholders": 6670}, "response": {"rows_with_email_like_text": 55, "rows_with_ip_like_text": 0, "rows_with_phone_like_text": 1, "rows_with_template_placeholders": 13006}}`
- The source uses named placeholder tokens (for example `{{Order Number}}`); these are synthetic slots, not observed customer identifiers.
- Near-duplicate paraphrases across different instructions were not deterministically clustered; held-out scores may still benefit from shared generation templates.
- `flags` and `response` are excluded from model input; only `instruction` is used.

## Validated modeling data
- Rows after validation and exact-text deduplication: 24,274
- Category counts after validation: `{"ACCOUNT": 5358, "CANCEL": 941, "CONTACT": 1966, "DELIVERY": 1645, "FEEDBACK": 1990, "INVOICE": 1801, "ORDER": 3067, "PAYMENT": 1986, "REFUND": 2577, "SHIPPING": 1951, "SUBSCRIPTION": 992}`
- Stratified split rows: train 16,991, validation 3,641, test 3,642.
- Exact normalized instruction overlap between splits: 0.
- Text vectorization and model fitting are performed inside the train-only scikit-learn pipeline.
- Priority and sentiment labels are absent from this source; those models are not trained.
