# Training and experiments

## Candidate and method

Start with Qwen/Qwen3-4B-Instruct-2507, an instruction-tuned text checkpoint. Use QLoRA: freeze quantized base weights and train small adapters. This trains evidence synthesis, not speech recognition or visual perception.

The [official model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507) documents the checkpoint and non-thinking behavior. [PEFT quantization guidance](https://huggingface.co/docs/peft/developer_guides/quantization) describes the adapter approach. Recheck supported library versions and hardware compatibility when implementing.

## Initial configuration to profile

These are starting settings, not validated hyperparameters:

| Setting | Initial candidate |
| --- | --- |
| Base weights | 4-bit NF4 with double quantization |
| Compute dtype | BF16 when supported; otherwise a compatible tested configuration |
| Adapter | Rank 16, alpha 32, dropout 0.05 on attention and MLP linear projections |
| Learning rate | 0.0001 |
| Schedule | Cosine, 3 percent warmup |
| Epoch cap | 2, with validation-based checkpoint selection |
| Batch | Microbatch 1, gradient accumulation 8 |
| Sequence budget | Start at 4096 total tokens; profile actual lengths before fixing |
| Memory | Gradient checkpointing; no unverified GPU fit assumption |
| Loss | Target completion tokens only |
| Seed | 42 for first run; record subsequent seeds |
| Decoding comparison | Same prompt, greedy decoding, output limit, and repair policy |

Do not silently truncate overlength records. Measure lengths first and either segment with preserved evidence references, increase the budget after profiling, or report exclusions. Make sure the complete target and end-of-sequence token survive serialization.

Use the model's chat template and verify completion-token masking on actual tokenized examples. Follow [TRL SFT guidance](https://huggingface.co/docs/trl/v0.29.0/en/sft_trainer); supported flags depend on the pinned version and dataset form.

## Sanity checks

Before a paid run, validate all examples and manually inspect tokenized inputs and labels. Run a tiny overfit/debug test on two to four development examples to verify nonempty loss masks, loss movement, adapter saving/loading, and generation termination. This proves plumbing only, not generalization.

Time a short representative training run. Project complete training, validation, checkpoint I/O, storage, and shutdown costs before continuing. A small model does not guarantee that arbitrary sequence lengths fit the budget.

## Controlled comparisons

| ID | Comparison | Purpose |
| --- | --- | --- |
| B0 | Prompted original model, transcript only | Audio baseline |
| B1 | Prompted original model, full evidence | Main training baseline |
| T0 | Teacher, full evidence | Reference behavior, not ground truth |
| S1 | SFT model, same evidence and prompt as B1 | Training effect |
| A1 | Remove OCR on predefined visual subset | OCR contribution |
| A2 | Remove descriptions on same subset | Description contribution |

Use the strongest development-selected prompt for B1, and apply that prompt consistently to S1. Record any few-shot examples, their token cost, and source groups. Equalize input, output budget, preprocessing, and repair logic.

A cost-limited first full study prioritizes B1 versus S1. Run ablations on a declared subset, and repeat promising runs with another seed only if budget permits. Report single-seed limitations.

## Data scale and checkpoint selection

The 20-clip pilot does not train a credible generalizing model. An optional adapter smoke test is a plumbing test on development examples. Scale toward 200 reviewed training clips only after the pilot finds an addressable synthesis failure.

Use the 25 validation clips for a small, recorded set of choices. A small validation set cannot support unlimited searches. Select checkpoints using recall and unsupported-claim behavior, not training loss alone. Record every tried configuration, including failures.

## Preference optimization

DPO is conditional on persistent, clearly rankable errors after SFT. Collect preferred/rejected answers to the same evidence packet, control for length/style, and have humans verify the preference. It is outside the initial cash allocation unless another planned experiment is replaced explicitly.

No RL is planned. Reconsider only after establishing a trustworthy reward and a failure simpler methods cannot solve.

## Reproducibility record

Save exact model/tokenizer revisions, dataset and split hashes, prompts, labeler settings, dependency lockfile, hardware, training arguments, random seed, loss-mask checks, length distributions, optimizer/scheduler state when resumable, adapter artifacts, validation selection, wall time, memory, tokens, costs, and known failures.

Use the [experiment record](templates/experiment-record.md). Distinguish measured costs from estimates and write negative results with the same detail as positive results.
