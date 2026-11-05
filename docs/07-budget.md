# Budget and resource plan

## Cash ceiling

Aim to complete the first experiment within USD 30, with an absolute initial ceiling of USD 40. This replaces the earlier speculative USD 500 project cap. It is a spending envelope, not a guaranteed full-project cost.

The ceiling covers pilot inference, teacher labeling, one small text-model training experiment, evaluation, and limited storage. It excludes the user's time, existing computer/internet, Android device, and ongoing public hosting. It does not authorize purchasing credits or paid resources.

| Allocation | USD 30 plan | USD 40 maximum plan |
| --- | ---: | ---: |
| Pilot extraction, teacher, and baseline inference | 3 | 5 |
| Remaining dataset extraction and labeling | 4 | 5 |
| QLoRA training and validation | 16 | 20 |
| Final evaluation | 3 | 4 |
| Storage and contingency | 4 | 6 |
| Total | 30 | 40 |

These are allocation targets. If a component cannot fit, reduce scope or stop for an explicit budget decision; do not silently expand the total. Do not use the contingency to hide repeated failed experiments.

## Pilot spending

Reserve at most USD 5 for the 20-clip pilot. Plan 60 selected images per candidate vision model, plus full OCR/transcription and text synthesis. First process two clips, measure actual billed usage, and project the remainder with a 25 percent retry reserve.

Prefer a metered API for this small vision comparison. A local OCR/ASR engine avoids API charges if existing hardware and runtime permit. Local compute still consumes time and resources; record wall-clock time.

Do not assume free-tier access, provider credits, or a particular GPU. Provider minimum top-ups, fees, and taxes count toward cash spending even when token usage is low.

## Cost formulas

API cost = billed input tokens × input rate / 1,000,000 + billed output/reasoning tokens × output rate / 1,000,000 + fixed charges.

GPU cost = billable hours including setup and idle time × hourly rate + storage/transfer charges.

Projected dataset cost = measured cost per eligible clip × expected clip count + retries, rejected examples, and labeling repairs.

Track paid cash, consumed credits, and remaining credits separately. Record both cost per attempted clip and per accepted training example.

## Rate verification

Earlier conversation examples were illustrative, not measured invoices. Verify the chosen endpoint, deployment region, model version, image tokenization, reasoning billing, and prices immediately before running. Preserve a dated rate snapshot in the cost ledger.

- [Google pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Alibaba model pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)
- [Google batch API](https://ai.google.dev/gemini-api/docs/batch-api)

Batch pricing may reduce cost where supported; it does not justify unbounded generation. Cache image outputs and teacher drafts.

## Resource requirements

Required now: Android phone with Instagram, access to candidate source clips, a development computer with disk space for private media, a review tool capable of showing video and text, and credentials for whichever paid endpoints are explicitly enabled.

Required later: a compatible GPU environment for the profiled QLoRA configuration, dependency lockfile, private artifact storage, and automatic shutdown. Do not rent an idle GPU while collecting data.

Human effort estimate for planning: 20 clips may need 2 to 4 hours of collection/source review and 1 to 3 hours of target review, plus engineering setup. Measure actual time on the first two clips. A 200-example review averaging three minutes each is ten hours, excluding difficult repairs and collection.

## Stop conditions

Stop paid work when projected remaining work exceeds the unreserved balance, when validation failures create repeated regeneration, or when the pilot shows extraction is the primary bottleneck. Preserve useful artifacts and report the decision instead of spending through the cap.
