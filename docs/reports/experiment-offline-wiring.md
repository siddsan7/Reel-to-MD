# Experiment record: offline wiring v0.1

Status: synthetic plumbing verification completed; real-video experiment not run.

## Hypothesis

A local content-addressed pipeline can enforce the supplied evidence/target contracts, preserve missing-channel uncertainty, export inert Markdown, and reuse work without any paid inference.

## Configuration

- Date: 18 October 2026; pipeline 0.1.0; Python 3.12.10; dependency graph in `uv.lock`.
- Inputs: `docs/examples/example.json`, generated five-second blue silent video, and test fixtures. No source groups or dataset partitions.
- Extraction: two-second samples, up to 60, 64×64 grayscale thumbnail difference threshold 2.0; first/middle/last subset for optional vision; native versions recorded per attempt.
- Models: none live. Local transport simulated in tests. ASR weights absent. Text fallback is a deterministic extractive draft.
- Prompt/schema: packaged copies of teacher prompt and schema 1.0; hashed in each video job identity.
- Hardware: existing Windows development machine, no rented compute.
- Decoding: subprocess timeouts; local model output cap 4096 tokens; no automatic retry, training, or repair.

## Predefined success and stop rules

Accept valid examples; reject broken timestamps/references and unsupported commands; preserve uncertainty; render injection text inertly; reuse completed work; keep paid cost zero. Preserve failures. Do not count fixtures as real clips. Real milestone completion requires two reviewed videos and source-fact inventories.

## Results

60 tests passed. Synthetic JSON wiring and generated silent-media CLI checks passed with correct separate labels/partial status. Repeat job reused successful caches. USD 0 cash and inference spend, no model calls beyond mocked responses. Source distribution and wheel built offline. Real source fidelity, model quality, p50/p95, human review time, and remaining pilot forecast are unmeasured.

## Interpretation

The independent scaffolding works under tested synthetic conditions. It does not show that chosen OCR/ASR/models can recover technical content from real clips. Keep the milestone partial and obtain clips plus available local inference resources before claiming extraction quality or selecting a teacher. See [full limitations and failed attempts](milestone-1.md).
