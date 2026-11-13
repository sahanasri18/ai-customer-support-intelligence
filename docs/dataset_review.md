# Dataset research and inspection

Reviewed 2026-11-10 against the official Hugging Face dataset repositories and license texts. The Bitext CSV below was downloaded to ignored local storage and inspected. The Tobi ticket dataset was not downloaded because its license is non-commercial and Bitext is a better fit for a public portfolio experiment. Neither source is real production customer traffic.

## Candidate comparison

| Dataset | Official source and size | License and redistribution | Fields and labels | Decision |
| --- | --- | --- | --- | --- |
| [`Tobi-Bueck/customer-support-tickets`](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets) | Official Hub viewer currently reports 61,765 rows and 53.1 MB; CSV repository. | CC BY-NC 4.0. Requires attribution, license link, and modification notice; prohibits commercial use. Do not redistribute raw data in this project. | Viewer displays `subject`, `body`, `answer`, `type`, `queue`, `priority`, `language`, `version`, and `tag_1` through `tag_8`; 4 types, 52 queues, 5 priorities, and 2 languages (English/German). Card text says 10 tag columns, while the viewer lists 8. No sentiment column. The dataset card describes its generated IT tickets as synthetic and claims no PII; this was not independently tested because the file was not downloaded. | Not used: non-commercial license does not fit the preferred public portfolio path. It would support a separate queue/priority experiment only after data review. |
| [`bitext/Bitext-customer-support-llm-chatbot-training-dataset`](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset) | Official Hub lists 26,872 rows, one train split, CSV, and 19.2 MB. Downloaded immutable revision [`0e8da3ba739b8b03572f7f058b9de9c90e8a692e`](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/commit/0e8da3ba739b8b03572f7f058b9de9c90e8a692e); file size 19,202,474 bytes. | CDLA-Sharing-1.0. Use and publication are granted. If received or enhanced data is published, it must remain under the agreement, preserve attribution/notices, and identify changes. The agreement says publication/use of Results has no restrictions. Raw data is kept local and ignored. This is not a legal determination about whether model weights always qualify as Results; do not redistribute artifacts without review. | `flags`, `instruction`, `category`, `intent`, `response`; English. The card says 27 intents / 10 categories; Hub viewer says 27 / 11. Local source has 26,872 rows, 27 intents, and 11 categories. No priority or sentiment labels. The card describes a hybrid synthetic dataset built with NLP/NLG and automated labeling, with roughly 1,000 examples per intent. | Used for a local category-classification benchmark only. `instruction` is input and `category` is target. No fields are combined with the Tobi dataset. |

## License notes

- [CC BY-NC 4.0 deed](https://creativecommons.org/licenses/by-nc/4.0/deed.en): permits sharing/adaptation with attribution and modification notices, but does not permit commercial use. This restriction is why Tobi was not downloaded or used.
- [CDLA-Sharing-1.0 agreement](https://cdla.dev/sharing-1-0/): permits use and publication; publication of Data or Enhanced Data must preserve the agreement and attribution/credit, and mark changes. Section 3.5 says the agreement places no restrictions on use/publication of Results. Dataset use still has privacy-law obligations. The raw dataset and derived splits remain under ignored `data/` paths and are not included in this source tree.
- Bitext attribution: Bitext Innovations (2024), [official dataset](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset), CDLA-Sharing-1.0. The exact downloaded file and revision/hash are recorded in `data/raw/bitext/dataset_manifest.json` (local, ignored).

## Local inspection: Bitext

The original 19,202,474-byte CSV is preserved unchanged at `data/raw/bitext/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv`. Its SHA-256 is `6f81102b0100b97b8468eb04368033a23206bf1fde9d53500d5806ec1001a434`. Raw data, processed splits, and model artifacts are ignored by `.gitignore`.

Observed on 2026-11-10:

- 26,872 rows and 5 object/string columns; no missing values and no exact duplicate full rows.
- Categories: ACCOUNT 5,986; CANCEL 950; CONTACT 1,999; DELIVERY 1,994; FEEDBACK 1,997; INVOICE 1,999; ORDER 3,988; PAYMENT 1,998; REFUND 2,992; SHIPPING 1,970; SUBSCRIPTION 999.
- 27 intent labels; no intent-to-category conflicts and no identical normalized instruction assigned to conflicting categories.
- 2,598 repeated normalized instructions were removed. The remaining 24,274 distinct normalized instructions were stratified 70/15/15 into train (16,991), validation (3,641), and test (3,642), seed 42. Exact normalized instruction overlap across splits is zero.
- A regex scan of `instruction` and `response` found zero email/phone/IP-like rows in model input `instruction`; in unused `response`, it flagged 55 email-like rows and 1 phone-like row. Matches were counted but never printed. Named `{{...}}` template slots appeared in 6,670 instructions and 13,006 responses; these are source-provided synthetic placeholders. The response field is excluded from training. Raw source is not uploaded.
- All categories and intents are preserved as source labels. The UI/product taxonomy is not mapped onto these labels.
- Shared generator templates may create near-duplicate paraphrases across splits even though exact normalized overlap is zero. Metrics therefore measure this synthetic source distribution and may overstate generalization.

Detailed data types, missingness, exact distributions, scan counts, and split information are in [`data_quality_report.md`](data_quality_report.md). The actual source file is excluded from Git.

## Label/task decision

- **Category:** train only the Bitext `instruction` to `category` classifier. This is synthetic customer-service intent/category data, not real ticket-routing evidence.
- **Priority:** not trained. Bitext has no priority label. Tobi has priority labels but is CC BY-NC and was not downloaded; no labels are borrowed from another source.
- **Sentiment:** not trained. Neither selected Bitext column nor current training input provides sentiment labels.
- **Urgency:** retain the existing transparent keyword rule. It is a triage hint, not a calibrated model or a claim that unflagged tickets are safe.

## Official source references

- Bitext dataset card, file/size/count metadata, and actual schema: [Hugging Face dataset page](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset).
- Pinned original CSV: [file at reviewed repository revision](https://huggingface.co/datasets/bitext/Bitext-customer-support-llm-chatbot-training-dataset/blob/0e8da3ba739b8b03572f7f058b9de9c90e8a692e/Bitext_Sample_Customer_Support_Training_Dataset_27K_responses-v11.csv).
- Tobi candidate card, viewer, and metadata: [Hugging Face dataset page](https://huggingface.co/datasets/Tobi-Bueck/customer-support-tickets).
- License texts: [CDLA-Sharing-1.0](https://cdla.dev/sharing-1-0/) and [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/legalcode.en).
