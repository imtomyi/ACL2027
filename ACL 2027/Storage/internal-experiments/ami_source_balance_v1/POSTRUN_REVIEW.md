# Post-run scientific review

Status: internal interpretation note written after the frozen run. It does not
change the protocol or generated metrics.

## Defensible finding

Across 118 officially seen AMI scenario meetings, component-safe out-of-fold
macro-F1 was 0.949 for dominant-role-only TF-IDF and 0.992 for pooled all-role
TF-IDF. The conditional component-bootstrap difference was 0.043 with a 95%
interval of [0.009, 0.079]. Dominant-role-only made six meeting-level errors;
pooled and role-balanced TF-IDF each made one. Pooled and role-balanced
representations had identical aggregate predictions and metrics. All three
learned conditions classified the small 20-meeting, five-component official
unseen set perfectly.

The narrow conclusion is:

> For this elicited AMI meeting-phase task, removing the three less-talkative
> roles reduced predictive performance, while equal weighting of the four
> roles caused no observed loss relative to pooled text.

## Required qualifications

1. The pooled condition uses more text than the dominant-role condition. The
   observed difference therefore combines source breadth and text quantity; it
   is not an isolated causal effect of source balance.
2. Bootstrap intervals resample the fixed out-of-fold predictions by connected
   component. They are conditional on the official folds and fitted pipelines
   and do not include fold-assignment or model-refitting uncertainty.
3. The identical pooled and role-balanced results show no observed loss on this
   task. They are not general noninferiority evidence; the exploratory -0.05
   margin has no independent power or substantive-margin justification.
4. Meeting phase is an easy, elicited proxy label with phase-specific agenda
   cues. Near-perfect phase classification does not demonstrate theme quality,
   provenance quality, voice preservation, serious-error detection, routing,
   or repair.
5. Source concentration differs by phase. The median largest-role word share
   is highest in phase `a` (about 0.492) and approximately 0.339–0.369 in the
   other phases, so concentration is associated with the target label.
6. The official unseen result has only five connected components. Its perfect
   score and degenerate conditional interval are descriptive.
7. The run remains private and separate from WarrantRoute's human study. It
   cannot populate the manuscript's human adequacy, reliability, routing, or
   repair cells.
8. Pooled and role-balanced predictions are identical. Their separately seeded
   marginal bootstrap intervals differ by at most Monte Carlo rounding in one
   endpoint; the paired difference uses shared resamples and is exactly zero.

An independent post-run comparison checked the 554 consumed license, meeting,
and word resources against the immutable source archive. No member was missing,
ambiguous, or mismatched; the path-bound archive and extracted composites both
equal `abf289b77e383fc4e6b1f502270c38c6825d24f5865d772f6464d688dd2cd731`.
This closes the current-run input-integrity check, although a future runner
should enforce the per-file composite before model fitting rather than relying
on a post-run audit.

## Useful next experiment

A prospectively frozen follow-up should compare dominant-role text with an
all-role representation matched to the same token count. That would reduce the
current text-volume confound. A refit bootstrap or repeated component-safe
outer split would better represent model-fitting uncertainty.
