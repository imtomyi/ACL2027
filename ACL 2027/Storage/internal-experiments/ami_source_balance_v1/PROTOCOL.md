# AMI source-balance experiment protocol

Study ID: `ami-source-balance-internal-v1`

Status: frozen before the first transcript-processing run on 2026-08-26.

## Scope

This is a private, offline exploratory experiment on the real AMI scenario
meeting transcripts. It is separate from the WarrantRoute Dreaddit/CaCHe human
study and cannot fill that study's adequacy, reliability, routing, or repair
result cells.

The run reads only orthographic `<w>` elements and the meeting-to-role mapping
from the selectively extracted AMI source package. It sends no text to a model,
service, browser, or human rater. It writes no transcript text, meeting-level
record, raw meeting ID, raw speaker ID, channel, timing, or participant
metadata. Results are aggregate numeric data only.

## Source snapshot

- Corpus: AMI Meeting Corpus, scenario-meeting subset.
- Official artifact: `ami_public_manual_1.6.2.zip`.
- Artifact SHA-256:
  `b56e5babb2496b8795deeeda7e71178d7fbc9963f94276cf2a3f4b56ebbc9f9d`.
- License: Creative Commons Attribution 4.0 International.
- Local scope: 138 meetings, four role channels per meeting, 35
  meeting-speaker connected components.

Only scenario transcripts and the minimum role/split linkage are processed.
Audio, video, slides, signals, questionnaires, demographics, participant
resources, non-transcript annotations, precise times, and free metadata are
excluded.

## Research question

Does concentrating on a single talkative source discard information that is
useful for recognizing which of the four AMI design phases a meeting belongs
to, and does explicitly balancing the four scenario roles preserve or improve
that information?

The phase labels `a`, `b`, `c`, and `d` are structural scenario labels derived
from the official meeting identifiers. They are not qualitative themes and do
not measure interpretive validity.

## Conditions

1. `majority`: most frequent training phase, with alphabetic tie breaking.
2. `dominant_role_tfidf`: TF-IDF from only the role with the most retained word
   elements in each meeting; ties use the fixed order PM, ID, UI, ME.
3. `pooled_tfidf`: TF-IDF from all four roles concatenated in that fixed order.
4. `role_balanced_tfidf`: each role is transformed with the shared pooled-
   training TF-IDF basis, the four individually L2-normalized role vectors are
   averaged, and the result is L2-normalized.

The three learned conditions use fixed one-versus-rest logistic regression
with `C=1`, balanced class weights, the liblinear solver, and seed `20260826`.
No test-driven model or parameter selection is allowed.

TF-IDF is fixed to lowercase Unicode alphabetic tokens of length at least two,
English stop-word removal, word unigrams, sublinear term frequency, `min_df=2`,
`max_df=0.98`, L2 normalization, and at most 30,000 features. Within each fit,
one vocabulary and IDF are learned from pooled training-meeting text only and
are shared by all three learned conditions. This changes source aggregation
without changing the lexical basis.

## Splits and leakage control

The indivisible unit is the meeting-global-speaker connected component. The
adapter reconstructs these components from `meetings.xml`, verifies that there
are 35, and fails if a component crosses an evaluation split.

Primary evaluation uses the official AMI scenario `k10` designation only among
the 118 officially seen meetings. Every seen meeting receives exactly one
out-of-fold prediction in memory, and vocabulary and model parameters are fit
only on the other nine component-safe folds. The 20 officially unseen meetings
are not read by any primary-fold feature or model fit.

A prespecified sensitivity evaluation trains on the official training and
development components and evaluates once on the official unseen components.

## Outcomes

Primary outcome: macro-averaged F1 across the four phases.

Secondary outcomes:

- accuracy;
- balanced accuracy;
- per-phase F1 and the four-by-four confusion matrix;
- the dominant role's word share and normalized four-role HHI;
- paired macro-F1 and accuracy differences relative to pooled TF-IDF.

Uncertainty uses a percentile bootstrap that resamples connected components,
not individual meetings, with 5,000 replicates and seed `20260826`. The
official-unseen interval has only five components and is descriptive.

Prespecified interpretations:

- H1 is supported if the 95% interval for `pooled - dominant_role` macro-F1 is
  entirely above zero.
- H2 is supported if the 95% interval for `role_balanced - pooled` macro-F1 is
  entirely above the exploratory noninferiority margin of -0.05.

All results are reported regardless of direction.

`FROZEN_RUN.json` records the source, license, protocol, runner, seed, and
bootstrap hashes before any classifier is fit. The runner refuses a full run
when one of those values differs.

## Output and integrity rules

The run may write only:

- a text-free validation record;
- a provenance and environment manifest;
- aggregate metrics and intervals;
- a text-only report containing aggregate results and limitations.

Before success, the runner scans every output for all raw meeting and speaker
identifiers and for AMI identifier or source-file patterns. Any match is a hard
failure. Per-meeting predictions, transcript terms, feature names,
coefficients, and example excerpts are never exported.
