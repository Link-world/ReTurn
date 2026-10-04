# Third-party media and restoration

## FineVideo media in the companion download

The companion package contains 112 clip/WAV pairs from 110 FineVideo parent videos. The [FineVideo dataset card](https://huggingface.co/datasets/HuggingFaceFV/finevideo) identifies the original videos as Creative Commons Attribution (CC BY) material. Per-clip title, creator/channel, source URL, excerpt interval and modifications are recorded in `data/ATTRIBUTION.json` and `data/media_manifest.json`. These are source-license attributions, not a new CC BY 4.0 grant from ReTurn over the videos. Original license version is not recorded in the local source metadata; consult the original source if your use requires that distinction.

Frozen video/WAV bytes are retained. Changes made when constructing those frozen inputs include excerpting, resizing/frame sampling or silent video encoding, and mono 16 kHz companion-audio extraction. The source's removal-update thread was checked on 2026-09-30: it showed the curator's initial announcement and no posted version-removal update. Future redistributors should check the [curator updates](https://huggingface.co/datasets/HuggingFaceFV/finevideo/discussions/2) again; this check is not a perpetual availability guarantee.

Users of the included FineVideo material must agree to its [upstream access terms](https://huggingface.co/datasets/HuggingFaceFV/finevideo), including the original-license, attribution and removal-update requirements. Its dataset-card terms are reproduced below:

> FineVideo dataset is a collection of over 43.000 YouTube videos. We ask that you read and acknowledge the following points before using the dataset:
>   1. FineVideo is a collection of Creative Commons videos. Any use of all or part of the videos must abide by the terms of the original licenses, including attribution clauses when relevant. We facilitate this by providing provenance information for each data point.
>   2. FineVideo is regularly updated to enact validated data removal requests. By clicking on "Access repository", you agree to update your own version of FineVideo to the most recent usable version specified by the maintainers in [the following thread](https://huggingface.co/datasets/HuggingFaceFV/finevideo/discussions/2). If you have questions about dataset versions and allowed uses, please also ask them in the dataset's [community discussions](https://huggingface.co/datasets/HuggingFaceFV/finevideo/discussions/3). We will also notify users via email when the latest usable version changes.
>   3. To host, share, or otherwise provide access to FineVideo, you must include these Terms of Use and require users to agree to it.

## LLaVA media in the companion download

All 15 selected LLaVA clip/WAV pairs are included as exact copies of the frozen evaluation inputs. The [official dataset card](https://huggingface.co/datasets/lmms-lab/LLaVA-Video-178K) declares **Apache License 2.0** and states: “We only allow the use of this dataset for academic research and education purpose.” Both declarations are retained here; this package does not offer unrestricted commercial use. A copy is included at `licenses/Apache-2.0.txt`; retain it and the source/attribution notices when redistributing these materials. Modified media are identified as excerpts with their processing and original time intervals in the manifest. ReTurn's annotation license does not replace the upstream Apache terms.

Dataset curators: Yuanhan Zhang, Jinming Wu and Wei Li. Dataset paper: *Video Instruction Tuning With Synthetic Data* (2024), Yuanhan Zhang, Jinming Wu, Wei Li, Bo Li, Zejun Ma, Ziwei Liu and Chunyuan Li; https://arxiv.org/abs/2410.02713. Each clip's original source URL and exact upstream member path are recorded in `data/ATTRIBUTION.json` and `data/media_manifest.json`. The upstream repository root exposed a README and no separate LICENSE/NOTICE file in the checked listing, so its explicit dataset-card license declaration is retained alongside the standard Apache text.

This package records the two datasets' own published license statements and preserves their terms. It does not claim an independent video-by-video rights audit. That evidence scope applies to both FineVideo and LLaVA.

## Media installation and optional restoration

The separate companion download covers the entire 80-task preview: **127 videos + 127 companion WAVs**. Users do not need to download either source dataset to run it. API accounts or local model weights are still needed for new inference.

For provenance and recovery only, `scripts/prepare_media.py` can recreate missing LLaVA clips from an existing extracted source tree. The exact parent IDs, original intervals and encoding recipes are retained. The previous restoration check matched the geometry and every decoded RGB frame for all 15 clips, and every decoded PCM sample for all 15 companion WAVs (`examples/media_restoration_validation.json`). The distributed files are copied directly from the frozen inputs, not replaced by reconstructed encodes.

## Distribution scope

The public Git repository contains task files, code and provenance, not the raw media archive. The companion download must require agreement to the FineVideo terms and the LLaVA academic-research/education restriction before access. A README notice alone is not our access mechanism.

All 15 LLaVA source paths belong to its declared `XXX_youtube_v0_1` dataset directories: five in `0_30_s`, two in `1_2_m`, and eight in `2_3_m`. This records the upstream declaration and source membership; it is not an independent certification of every original video's copyright. Do not relabel these media under ReTurn's annotation license.
