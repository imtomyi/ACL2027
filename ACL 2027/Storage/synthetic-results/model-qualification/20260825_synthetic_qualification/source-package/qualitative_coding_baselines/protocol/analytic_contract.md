# Analytic contract: bounded codebook-oriented thematic coding

Version: `qc-analytic-contract-v1`  
Frozen for synthetic qualification: 2026-08-25 (America/Chicago)

## Purpose and scope

The task is a bounded, codebook-oriented thematic coding exercise. It asks a
model to construct useful codes and evidence-linked cross-case themes for one
explicit research question. It is not reflexive thematic analysis, grounded
theory, diagnosis, prevalence estimation, or an autonomous substitute for an
accountable qualitative analyst.

The synthetic qualification uses fictional packets shaped like the four target
corpora. It checks the analysis interface and failure controls without processing
restricted source text. Results cannot establish validity on the real corpora.

## Unit and context

- The atomic evidence unit is an excerpt with a stable `excerpt_id` and
  `source_id`.
- Several excerpts may share one source. Sources, speakers, or turns are not
  treated as statistically independent people.
- The model receives the research question, corpus-neutral context note, and all
  excerpts in a fixed recorded order.
- Only packet text may support a claim. No web, retrieval, tools, memory, dataset
  labels, published themes, or external domain facts are allowed.

## Required products

Each independent run returns:

1. five to eight local codes with definitions, inclusion and exclusion rules,
   analytic level, and exact exemplars;
2. a code assignment for every excerpt, including an explicit `not_coded`
   option and a short source-linked rationale;
3. two to four themes with a bounded claim, code links, exact evidence,
   counterevidence, boundary conditions, and source coverage;
4. negative or contradictory cases; and
5. a short reflexive memo naming uncertainties, plausible alternative readings,
   and limitations.

## Non-negotiable validity rules

- Quotes must be exact contiguous substrings of the cited excerpt.
- Every cited excerpt and source must exist and match each other.
- A cross-source theme needs evidence from at least two distinct sources.
- Counts may describe only the supplied packet. Wording such as “most,”
  “typical,” or “participants generally” must be justified by explicit packet
  coverage and cannot be generalized to a population.
- Disagreement, resolution, temporal change, and counterexamples must not be
  silently averaged away.
- Interactional data are analyzed as interactional processes, not as stable
  personality or cultural traits.
- The model must abstain or state uncertainty when the packet does not warrant a
  claim. Hidden reasoning is neither requested nor stored; only concise warrants
  tied to evidence are required.

## Repetition and blinding

- Five recent Codex runtime models are screened under the same prompt and schema.
- Each model produces three independent runs per packet.
- Model identities are replaced by deterministic blind labels before judgment.
- No “best run” is selected. Metrics are retained for all repeats and aggregated
  with the run as a repeated factor.
- The synthetic evaluation guide is withheld from generators and supplied only
  to evaluators after generation is complete.

## Measurement portfolio

Automatic checks report:

- parse/schema success and missing required products;
- exact quote and source-attribution validity;
- assignment completeness and code-reference validity;
- source coverage and per-theme source concentration;
- presence of counterevidence, boundary conditions, uncertainty, and negative
  cases; and
- cross-run structural stability as a diagnostic.

Blinded evaluation reports evidential support, voice/context preservation,
negative-case preservation, analytic-contract fit, codebook usability,
parsimony, and serious-error flags. Agreement and stability are diagnostics;
neither is treated as qualitative truth.

## Selection rule

Selection is lexicographic rather than a post-hoc weighted score:

1. exclude any model that fails schema, exact-evidence, attribution, governance,
   or serious-error gates at the preregistered tolerance;
2. identify models non-inferior to the best blinded human support/voice result
   under a margin fixed from a pilot;
3. among that set, minimize total cost including expert verification and repair;
4. use repeat stability as a tie-breaker, never as proof of validity.

The synthetic qualification may nominate an engineering candidate using the same
ordering, but cannot freeze the paper's primary model. The primary and backup
must be selected on approved Dreaddit development packets only. Dreaddit test and
AGYW remain untouched until that freeze.

## Real-data stop conditions

Stop without inference if any of the following is unresolved: institutional and
platform authorization; model/provider processing and retention terms; excerpt
privacy review; exact received dataset version; approved fields; cluster-aware
sampling; or a frozen manifest. KODIS and CANDOR additionally require authorized
real distributions and validated adapters.

