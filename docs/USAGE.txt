# ReTurn preview

A small, runnable preview of conversation-dependent failures in multimodal models: read frozen tasks, generate **native model histories**, run matched single-turn controls, score, and inspect paired results.

The preview contains **80 base tasks / 40 complete pairs**, sampled from the frozen Development pool. The prepared companion media package covers the **8-task / 4-pair Short quick start** and all **127 clips and WAVs needed by the 80-task preview**; it is [available on Hugging Face](https://huggingface.co/datasets/Link-world/ReTurn) after accepting the upstream terms. Results from this subset are **preview subset results**, not a leaderboard submission or a reproduction of the full benchmark scores. Full data and further model adapters are **coming soon**.

## Install

Download `return-preview-media.zip` from [Hugging Face](https://huggingface.co/datasets/Link-world/ReTurn) after signing in and accepting the upstream terms. Install it using the command below. Cached examples can still run without media or API credentials.

Run the commands below from the repository root (the directory containing `return_eval/`). Cached scoring and reporting need only Python 3.10+. New inference also requires the Python dependencies below and FFmpeg/ffprobe; API inference needs no GPU.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/install_media.py /path/to/return-preview-media.zip --accept-terms
python -m return_eval.check --manifest data/quickstart_manifest.json --media
```

Local model environments are separate: install a compatible CUDA PyTorch build and `requirements-local.txt`; Qwen3-Omni also requires FlashAttention 2. The tested environment used Python 3.10.20, PyTorch 2.12.1, Transformers 5.12.1, and one 96 GiB H20 per model. These are observed settings, not minimum hardware requirements. Model weights are obtained under each model's own license; they are not bundled.

## Run the quick start

Copy `.env.example` to `.env` and fill in credentials and the base URL for your account. Bases end at `/v1` (or the provider's compatible-mode prefix). The runner appends `/chat/completions`. Omni/visual gateways and the judge service are configured by you; no private gateway or personal credentials are included. Availability of a model ID depends on the provider and account.

```bash
cp .env.example .env
# Edit .env, then load it in this shell:
set -a
. ./.env
set +a

python -m return_eval.run --config configs/qwen38_api.json \
  --manifest data/quickstart_manifest.json --out runs/qwen38_quick
python -m return_eval.score --run runs/qwen38_quick --judge
python -m return_eval.report --run runs/qwen38_quick
```

Read `runs/qwen38_quick/report/summary.json` and `groups.csv`. `predictions.jsonl` retains final replies, native history references and generated replies, request status, time, attempts, and generation settings. `scoring/scored_records.jsonl` includes strict and content scores, format compliance, and blind-review reasons. `report/paired_items.jsonl` links the shared valid Single/Multi denominator; excluded items and reasons are separate.

The API and GPT judge require your own accounts and may incur charges. `--judge` sends only anonymous question/gold/options/candidate records to your configured judge, never media or model/condition/task identifiers. Inference sends the selected media, questions and that same model's generated history to your configured model service. No telemetry or automatic publishing is implemented.

To inspect rule scores without making judge calls, omit `--judge`. Non-rule matches then remain **review_pending**, not incorrect. Complete content scores require either an exact-identity review cache or the judge. The formal judge is `gpt-5.6-sol` with explicit `reasoning_effort="medium"`; the exact prompt is in `return_eval/formal.py`. A different judge is an alternative evaluation, not the paper scorer.

## Backends

The supplied CLI validation records report that all six adapters completed end-to-end inference and scoring on a fixed validation subset on **2026-09-30 UTC**. Both interfaces, Single/Multi, and Short/Long were tested. Omni was tested on V and A. Exact counts and recovery notes are in `examples/validation_status.json`; these are small compatibility checks, not full-preview results.

| Config | Exact model ID / weights | Task modalities |
|---|---|---|
| `qwen38_api` | `qwen3.8-omni-flash` | V, A |
| `qwen37_api` | `qwen3.7-plus` | V |
| `stepaudio_api` | `stepaudio-3-chat-preview` | A |
| `qwen3_omni` | `Qwen/Qwen3-Omni-30B-A3B-Instruct` | V, A |
| `qwen3_vl` | `Qwen/Qwen3-VL-30B-A3B-Instruct` | V |
| `audio_flamingo3` | `nvidia/audio-flamingo-3-hf` | A |

Use any config from `configs/`, for example:

```bash
python -m return_eval.run --config configs/stepaudio_api.json \
  --manifest data/quickstart_manifest.json --out runs/stepaudio_quick

CUDA_VISIBLE_DEVICES=0 python -m return_eval.run --config configs/qwen3_vl.json \
  --manifest data/quickstart_manifest.json --out runs/qwen3vl_quick
```

Set `LOCAL_OMNI_MODEL`, `LOCAL_VISUAL_MODEL`, or `LOCAL_AUDIO_MODEL` to an existing local weight directory; otherwise the public model ID is used. Set only variables you use: empty local paths are not valid directories. A unimodal backend selects only its supported task modality. Omni receives the frozen companion audio and video, including on single-modality-required tasks; V/A labels describe necessary evidence, not which channels exist.

Native history is generated recursively from the same model and configuration. No gold or other model's reply is inserted. Controls are the frozen necessary-evidence requests, including historical evidence where required, not a generic current-only approximation. Questions, options, media order, and turn boundaries are preserved. No system description or caption is added.

API video is made silent, constrained to 768 pixels, encoded H.264 CRF20, and sent at 2 fps. Qwen3-VL uses that video with 2 fps frame indices and native video metadata. Qwen3-Omni uses the established native processor, separate audio and video, and disables the talker. Audio Flamingo uses the native processor with the formal multi-turn audio-placeholder correction. StepAudio retains text-then-audio order. Exact caps and retries are in each config; generation is greedy/temperature zero. Truncated, empty, failed or blocked requests do not receive an ordinary wrong-answer score.

## Resume and failure handling

Re-run the same command to reuse successful request IDs. Use `--retry-errors` for transient failures. Provider policy refusals are retained and not retried; their dependent requests remain blocked. Changing the model, endpoint, interfaces, selected tasks, generation settings or frozen input snapshots requires a new output directory. Media are checked against the published SHA256 manifest before any inference or cache reuse. Missing or altered inputs stop the run before model loading. Successful IDs are not rerun. Each process owns one run directory; concurrent writers to the same directory are unsupported.

`state.json` is the progress entry point. An incomplete inference run exits with code 2. Scoring also exits with code 2 when inference has failed or review is pending. Reporting writes the available results and exclusion reasons, then exits with code 2 if any requested views or operation pairs are excluded; an empty result produces a header-only CSV, never stale scores. Authentication failures, HTTP statuses, rate limits, transport exceptions, length retries and dependency failures are explicit. If your proxy blocks an authorized endpoint, configure your network/`NO_PROXY`; TLS verification is never disabled. Logs and run contracts can contain your endpoint and local model location, so review your own outputs before sharing them.

## Cached examples: no model account needed

```bash
python -m return_eval.score --run examples/recorded_outputs/qwen38_api \
  --cache examples/recorded_outputs/qwen38_api/review_cache.jsonl
python -m return_eval.report --run examples/recorded_outputs/qwen38_api
```

`examples/recorded_outputs/` holds historical formal-cache examples, selected for interface/length/modality coverage before looking at predictions. Missing historical dates remain null. `examples/current_validation/` holds the separate live 2026-09-30 checks. Neither directory is a set of hand-picked failure demonstrations. Replaying a cache validates parsing/scoring/reporting; it does not make a current API call.

The upstream CLI parity check compared the exported scorer against **480 physical formal-cache records**, comparing strict, rule, content, uncertainty and format fields: **zero mismatches**. Shared control requests are expanded into logical task views only for reporting, never counted as additional base tasks. See `examples/scoring_parity.json`.

## Full preview

The companion media archive contains the exact frozen media for all 80 tasks: **112 FineVideo clips + 15 LLaVA-Video-178K clips**, each with its companion WAV (254 media files). Install the companion archive once with `scripts/install_media.py`; no original source-dataset download or restoration step is needed.

```bash
python -m return_eval.check --media
python -m return_eval.run --config configs/qwen38_api.json \
  --manifest data/preview_manifest.json --out runs/qwen38_preview
python -m return_eval.score --run runs/qwen38_preview --judge
python -m return_eval.report --run runs/qwen38_preview
```

`data/media_manifest.json` records source IDs, intervals and original preprocessing. `data/ATTRIBUTION.json` retains source credit and license declarations. FineVideo declares CC BY source videos; LLaVA-Video-178K declares Apache License 2.0 and restricts use to academic research and education. The Apache license text is included in `licenses/Apache-2.0.txt`. ReTurn's CC BY 4.0 annotation license does not replace these upstream licenses. See [THIRD_PARTY_MEDIA.md](THIRD_PARTY_MEDIA.md), including FineVideo's terms that users must agree to when accessing its materials.

The optional `scripts/prepare_media.py` can reconstruct missing LLaVA files from an existing upstream copy. That restoration path was validated against every decoded frame and audio sample of all 15 clips, and the separate companion media archive contains the original frozen files. The quick-start and backend-validation selections are unchanged.

## Protocol and results

See [DATA_CARD.md](DATA_CARD.md) for sampling, splits, exposure and pairing. OpenQA and MCQ are reported separately. Each group uses matched, valid Single/Multi responses; missing inference or unresolved review excludes the view with a reason. Accuracy is the unweighted mean across valid logical task views, expressed as a percent. `delta_conv_pp = single_accuracy - multi_accuracy`; harm is Single-correct/Multi-wrong, rescue is the reverse. Pair four-cell summaries require both reference and conflict operations to have valid Single and Multi scores. Empty groups are absent, not zero accuracy.

The preview is small and source-correlated; interfaces, shared controls, short/long descendants and pairs are not independent samples. Do not infer full-benchmark performance or a pure causal effect of history length from these results.

Code: MIT. Original ReTurn task annotations: CC BY 4.0. Source media retain their original rights and attribution; these licenses do not grant rights to third-party media or model outputs. See `LICENSE`, `LICENSE-DATA`, and [THIRD_PARTY_MEDIA.md](THIRD_PARTY_MEDIA.md).
