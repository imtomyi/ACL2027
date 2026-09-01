# Who Should Be in the Loop? Allocating Expert Review for Qualitative Coding with Language Models

**Anonymous ACL 2027 submission draft**  
**Version:** 0.1 — 25 August 2026  
**Status:** Pre-data manuscript. The abstract, methods, hypotheses, and analysis plan are prospective. No empirical result is claimed in this draft. Bracketed fields must be resolved before submission.

## Abstract

Large language models can propose, organize, and apply qualitative codes at a scale that makes exhaustive expert review difficult. Existing human-in-the-loop systems show that researchers can revise model suggestions, provide persistent feedback, or evaluate outputs after generation. They do not yet establish which judgments require qualitative-method expertise, which require domain expertise, and which can be made reliably by trained non-specialists. We introduce **WarrantRoute**, a source-grounded evaluation protocol and expertise-aware review policy for LLM-generated codes and themes. The study crosses three rater groups—qualitative-method experts, domain experts, and trained researchers—with natural model outputs and controlled “failure twins” that isolate unsupported evidence, source or linkage-supported speaker concentration, removed counterevidence, culturally flattened meaning, and over-broad abstraction. Raters judge evidential support, preservation of participant voice, confidence, and inability to judge, with rationales and review time retained. We will compare all-expert, all-nonexpert, random, uncertainty-only, and learned expertise-aware routing under matched expert-time budgets, freezing the routing rule before evaluation on a held-out domain and model family. A compact downstream test will then measure whether routed feedback repairs the targeted defect without introducing a new unsupported claim. The design treats expert judgment as situated rather than as universal ground truth and preserves disagreement before adjudication. The intended contribution is not another thematic-analysis generator, but evidence about when scarce human expertise changes source-grounded evaluation and how to allocate it without hiding less frequent or negative cases.

> **Drafting note for the research team.** Replace the prospective abstract with a conventional results-bearing abstract only after confirmatory analysis. Do not add predicted numbers as if they were observations.

## 1 Introduction

Qualitative coding is increasingly supported by large language models (LLMs). Recent systems suggest codes, construct hierarchical codebooks, apply categories at scale, refine outputs through multi-agent pipelines, and retain human edits as persistent instructions [@dai2023llm; @spinoso2023qualitative; @zhong2025hicode; @wang2026centaurta; @matveyenko2026muse]. This work makes human feedback technically easy to collect. It does not make all feedback epistemically interchangeable.

A rating can answer several different questions. A qualitative-method expert may recognize that a purported theme is only a topic label or that a reliability criterion conflicts with the declared analytic approach. A domain expert may notice that an apparently plausible interpretation erases a culturally specific meaning, reverses a clinical implication, or overlooks a consequential negative case. A trained researcher may be fully capable of detecting a fabricated quotation, a polarity mismatch, or an unsupported generalization. Treating these judgments as one undifferentiated “human score” obscures when expertise matters and makes expert-only evaluation unnecessarily expensive.

The distinction matters because conventional automatic metrics can appear reassuring while substantively important failures remain. Open-code similarity must accommodate multiple defensible code spaces [@chen2026opencodes]. Human–LLM agreement can be lower than human–human agreement without the LLM’s coding being less preferred in a blind comparison [@liu2026agreement]. High lexical or embedding similarity can coexist with weak conceptual adequacy [@perez2026icr] or can be inflated by style-preserving perturbations [@nam2025idealign]. In sensitive interviews, models have omitted participant evidence, replaced quotations with summaries, refused trauma-related material, or shifted representations with demographic conditioning [@parkington2025human; @zhu2026trauma; @subbiah2026story]. These are not merely label-matching errors: they concern the warrant connecting an interpretation to source evidence and to the distribution of voices in a corpus.

Current human-in-the-loop work also entangles several roles. The same person may help construct a reference, expose preferences to the model, and later evaluate the model’s output. Small panels are common, expertise is reported inconsistently, and feedback is often evaluated on the same task or domain in which it was elicited. This makes it difficult to answer a practical question faced by research teams: **which items can be reviewed by trained team members, and which should be escalated to scarce qualitative or domain experts?**

We study this question through source-grounded evidence packets. Each packet pairs a proposed code or theme-level claim with exact source excerpts, project-pseudonymous source and, where supported, speaker identifiers, and relevant context. Alongside naturally occurring model outputs, we construct controlled failure twins that alter one validity-relevant property while holding surface form as constant as possible. Three rater groups judge support, voice preservation, confidence, and inability to judge. A simple routing policy then decides which items should receive expert review. Its value is assessed under fixed expert-time budgets and on a domain and model family excluded from policy development.

The paper is positioned deliberately. It does **not** claim to automate reflexive thematic analysis, to discover the single correct set of themes, or to replace expert interpretation. It asks a narrower NLP and human-evaluation question: when evaluating source-grounded LLM qualitative outputs, which observable signals predict that specialized human expertise will materially change the judgment?

The planned contributions are:

1. a role-stratified, source-grounded human-evaluation protocol that distinguishes qualitative-method expertise, domain expertise, and trained non-specialist review;
2. a controlled suite of natural outputs and validity-focused failure twins, including unsupported evidence, source concentration, counterevidence loss, cultural flattening, and over-broad abstraction;
3. a held-out, budget-matched evaluation of simple and learned expert-routing policies, with expert time, calibration, false-negative severity, and less-frequent/negative-case preservation as outcomes; and
4. a downstream repair test that distinguishes useful feedback from ratings that merely detect a problem; and
5. an auditable data-collection instrument, annotation guide, and reporting template that retain disagreement, rationales, abstention, source lineage, and publication status.

## 2 Status Quo and Research Gap

The positioning below is bounded to the project’s structured review of 237 unique, full-text-grounded publication identities available by 24 August 2026. Absence statements mean “not found among the inspected full texts,” not that no unpublished or inaccessible study exists.

### 2.1 Manual feedback in peer-reviewed ACL/EMNLP-family work

Manual feedback is already a viable strategy in archival NLP research. The important variation is what the human does and whether that role is independent of system development.

Dai et al. let a human coder provide examples, revise and rationalize model outputs, and decide when to stop; an independent third coder then evaluated the result [@dai2023llm]. Spinoso-Di Piano et al. studied code recommendation against two sequential human codebooks and asked two additional qualitative researchers to judge sampled suggestions [@spinoso2023qualitative]. Parfenova et al. compared inductive annotations from experts and LLMs, with three researchers rating a small selected set and low human agreement illustrating the plurality of the task [@parfenova2025inductive]. HICode constructed hierarchical code spaces across large corpora and showed that human and cosine-based mappings can diverge [@zhong2025hicode]. These papers establish that manual judgments, edits, and small expert panels are acceptable forms of evidence at ACL/EMNLP venues when their role is explicit.

Adjacent peer-reviewed HCI work makes the intervention richer. CollabCoder supports independent pair coding, optional suggestions, disagreement discussion, and source-linked decisions, but primarily evaluates workflow experience and warns that generated groupings can dominate discussion [@gao2024collabcoder]. Reflexis makes drift, disagreement, positionality, and code histories visible while retaining human authority; its single-condition study does not establish downstream validity [@ye2026reflexis]. MindCoder retains source chunks, rationales, edits, memos, and analytic trajectories, but its external assessment used only two raters with different qualitative experience and the inspected version was a preprint [@gao2025mindcoder]. These systems establish editable and reflexive feedback loops, not which reviewer should inspect which potential failure.

More recent work turns feedback into a persistent system input. CentaurTA converts feedback from six participants into reusable instructions and reports that quality can peak and then decline across iterations [@wang2026centaurta]. Muse supports researcher steering and codebook editing, draws design feedback from more than 100 qualitative researchers, and uses two experienced qualitative researchers to inspect sampled errors [@matveyenko2026muse]. Aggregate Code Space evaluates multiple human codebooks without assuming a single correct code set and explicitly stress-tests code flooding and hallucination [@chen2026opencodes]. Zhu et al. combine qualitative researchers, member checking, and large-scale machine experiments to expose refusal-driven and culturally consequential failures in trauma interviews [@zhu2026trauma].

This literature supports the feasibility of collecting ratings, rationales, revisions, surveys, and expert judgments. However, it usually evaluates a particular system or metric; it does not compare evaluator roles under the same evidence, error types, and review budget. “Human” is therefore often a sample description rather than an experimentally studied factor.

### 2.2 Agreement, source support, and situated judgment

Three developments narrow the remaining gap. First, agreement is no longer defensible as a universal proxy for quality. A blind source-symmetric comparison found that a single education expert preferred human and LLM code assignments at nearly equal rates even though human–LLM Jaccard agreement was much lower than human–human agreement [@liu2026agreement]. The study is an important no-single-gold baseline, but one verifier cannot reveal how domain and methodological expertise interact. A specialist-versus-lay clinical comparison likewise reports materially different assessments when clinical/phenomenology experts read the raw corpus and public raters see isolated themes [@moskalewicz2026phenomenology].

Second, expert evaluation can validate automatic measures without making expert judgment infallible. IDEAlign uses triplet judgments from educators and perturbation tests to compare open-ended annotations, but its target is expert-perceived idea similarity rather than source warrant or voice preservation [@nam2025idealign]. ICR shows that conceptual ratings can diverge sharply from lexical metrics, while leaving evaluator assignment and open-world concept handling incompletely specified [@perez2026icr]. LLM-as-a-judge work suggests automated scores may recover coarse model ordering but not nuanced interpretive quality [@han2026judge]. Human judgment must therefore be treated as measured data with its own reliability, calibration, and sampling design.

Third, source links do not by themselves establish validity. Parkington et al. found that two LLM workflows each missed 190 of 428 human excerpts and that many purported quotations were interpretive summaries [@parkington2025human]. Bang et al. distinguish verbatim quotation from paraphrase, truncation, partial hallucination, and full hallucination in a human-led hybrid workflow [@bang2026hybrid]. Hill et al. demonstrate the value of blinding, exact source identifiers, prevalence-aware reliability statistics, and explicit quotation-error definitions, but their inductive comparison is limited to one focus group and one qualitative rater [@hill2026healthcare]. Subbiah et al. show that demographic conditioning can alter semantic, affective, and thematic portraits and that trained evaluators themselves reach only moderate agreement [@subbiah2026story]. Reflexis and related interfaces preserve disagreement, drift history, and analyst authority, but independent outcome validation remains open [@ye2026reflexis].

Existing review-allocation work mostly routes attention from model-side uncertainty rather than demonstrated human expertise. A confidence–diversity framework assigns review tiers in comparatively accessible fixed-code tasks [@zhao2025confidence], while rationale disagreement has been proposed as triage for ambiguous codebook decisions rather than proof of correctness [@tajik2026disagreement]. Confidence is especially fragile: a calibration study reports high stated confidence despite low coding accuracy and strong adoption of a supplied high-confidence anchor [@li2026confidence]. These results motivate confidence, disagreement, and abstention as candidate routing signals, but not as validated substitutes for source-grounded human review.

**Publication-status boundary.** Dai, Spinoso-Di Piano, Parfenova, HICode, CentaurTA, Muse, Chen, Zhu, CollabCoder, Reflexis, Hill, and Bang are cited as peer-reviewed archival work. Liu et al., IDEAlign, ICR, Han et al., Parkington et al., Subbiah et al., MindCoder, and Zhao–Liu were preprints or lacked a verified archival version at the review cutoff; they are used as adjacent evidence, not presented as peer-reviewed ACL/EMNLP publications.

### 2.3 The missing comparison

The status quo can be summarized as follows:

| Established by prior work | Still unresolved |
|---|---|
| Humans can edit codes, rate suggestions, supply preferences, and stop iterative systems. | Which judgments require qualitative-method expertise, domain expertise, or neither? |
| Multiple defensible code sets make a single reference inadequate. | How should role-specific disagreement be retained rather than averaged away? |
| Source links, quote checks, and provenance interfaces are implementable. | Which source-grounded failures are detectable by each role, and at what cost? |
| Expert and LLM-judge scores can be compared and calibrated. | Can a routing policy transfer to an unseen domain/model without sacrificing subtle or less-frequent cases? |
| Small expert panels are accepted in ACL/EMNLP evaluation. | How can a mixed research team use experts selectively while reporting reliability and uncertainty honestly? |

Our positioning is therefore not “human feedback improves LLM qualitative analysis.” That claim is already occupied and too broad. We test the more specific claim that **expertise has error-type-dependent marginal value, and observable first-stage signals can route review while preserving source-grounded validity under a limited expert budget**.

## 3 Analytic Scope and Definitions

### 3.1 Declared analytic contract

“Thematic analysis” covers incompatible analytic contracts. Coding-reliability approaches, codebook approaches, and reflexive thematic analysis assign different roles to consensus, subjectivity, and reliability [@braun2021can; @braun2021quality]. Inter-rater reliability is meaningful only when the method and decision process make shared application of categories an intended construct [@mcdonald2019reliability].

The confirmatory study will therefore evaluate a **bounded codebook-oriented source-warrant task**, not the total quality of reflexive thematic analysis. Raters judge whether a proposed code or theme-level statement is adequately supported by the supplied evidence, preserves relevant differences and counterevidence, and is appropriate under a stated analytic brief. They do not judge whether one final thematic account is universally correct.

### 3.2 Evidence packet

An evidence packet contains:

- the analytic question and declared contract;
- one proposed code or theme-level claim and a short definition;
- the exact excerpt or excerpts offered as evidence, with stable project source identifiers and, where corpus linkage supports it, pseudonymous speaker identifiers;
- a bounded context window around each excerpt;
- corpus-level counts needed to inspect source spread and, only where linkage supports it, speaker concentration;
- relevant counterevidence when sampled by the audit procedure; and
- provenance fields for model, prompt, run, transformation, and human revision.

The main presentation omits model identity and experimental condition. A no-source ablation removes excerpts while preserving the proposed interpretation; this tests the value of source evidence rather than creating the main task.

### 3.3 Human roles

We distinguish roles by task-relevant qualifications rather than seniority or job title.

| Role | Minimum operational definition | Primary expected contribution |
|---|---|---|
| Qualitative-method expert (QME) | Has led or independently conducted qualitative coding/analysis and can explain the declared analytic contract. | Method congruence, claim granularity, treatment of contradiction and alternative readings. |
| Domain expert (DE) | Has substantive research, practice, or lived-context expertise in the source domain. | Contextual meaning, cultural/clinical significance, harmful omission, consequence severity. |
| Trained researcher (TR) | Has research literacy and completes the study tutorial, but lacks specialist expertise for the assigned domain and method. | Scalable first-stage checks of direct support, contradiction, attribution, and obvious overclaiming. |

Role is not treated as a proxy for inherent competence. We record relevant experience, self-assessed familiarity, and task-specific training, and we report within-role variation.

### 3.4 What counts as “expert-needed”

An item is expert-needed for the routing evaluation when, under the preregistered analytic contract, the independent expert panel identifies a material support or voice-preservation problem that the first-stage nonexpert decision would otherwise pass, or when the panel judges that multiple defensible readings must be retained. This target is explicitly **panel- and contract-relative**. It is not a claim that experts reveal an objective latent truth.

## 4 Research Questions and Hypotheses

**RQ1: Role sensitivity.** How do qualitative-method experts, domain experts, and trained researchers differ in their judgments, confidence, abstention, rationales, and review time across validity failure types?

**RQ2: Complementarity.** Which failures are uniquely or jointly detected by methodological and domain expertise, and which can be handled reliably by trained researchers?

**RQ3: Routing.** At a fixed expert-time budget, can expertise-aware routing preserve expert-panel decisions and high-severity error recall better than all-nonexpert, random, or uncertainty-only review?

**RQ4: Transfer.** Does a routing rule frozen on development domains and model outputs retain performance on an unseen domain and model family?

**RQ5: Feedback utility.** When a defect is identified, does expertise-aware routed feedback repair it without introducing collateral unsupported claims?

We preregister the following directional hypotheses:

- **H1:** Role differences will be small for exact quotation and obvious contradiction failures, but larger for cultural/contextual flattening, method-contract violations, source or linkage-supported speaker concentration, and removed counterevidence.
- **H2:** A combination of trained-rater disagreement, “cannot judge,” calibrated confidence, rationale features, and automatic provenance checks will predict expert-needed items better than model confidence or an LLM judge alone.
- **H3:** Under matched expert minutes, expertise-aware routing will recover more high-severity failures than random routing and an uncertainty-only rule while remaining within a preregistered noninferiority margin of all-expert review on the primary accept/escalate decision.
- **H4:** Performance will decline under domain/model shift, but a routing policy based on role-agnostic audit signals will retain an advantage over in-domain-tuned scalar confidence.
- **H5:** Feedback selected by expertise-aware routing will yield more successful repairs than trained-researcher feedback alone and approach full-expert feedback at lower expert cost.

H3’s noninferiority margin and the confirmatory sample size will be fixed after a separate pilot and before held-out evaluation.

## 5 Materials

### 5.1 Corpora

The manuscript documents four candidate corpus lanes. Two currently have
provisional experimental roles: Dreaddit's training partition is planned for
development and its test partition for an in-domain audit, while all 11 Cache2
focus groups (project alias: CaCHe) are planned for the held-out cross-domain
confirmatory evaluation. CaSiNo and the AMI scenario-meeting subset are
acquired but unassigned source-only dialogue candidates.

| Corpus | Context | Current verified inventory | Experimental status |
|---|---|---|---|
| Dreaddit | English Reddit stress segments | 3,553 source segments from 2,929 posts; 3,532 structurally eligible segments and 302,509 eligible words | Processed; development and in-domain audit roles planned; privacy and governance review pending |
| Cache2 AGYW/community-men (CaCHe) | 11 western Kenya focus groups translated into English | 3,944 retained participant/collective turns; 3,076 structurally eligible participant turns and 98,735 eligible words | Processed; held-out confirmatory role planned; privacy and governance review pending |
| CaSiNo [@chawla2021casino] | English dyadic campsite negotiation | 1,030 dialogues, 11,919 ordinary messages, and 228,675 whitespace-delimited ordinary-message words | Restricted source only; no stable cross-dialogue participant token, adopted split, or sampling eligibility |
| AMI scenario meetings [@carletta2006ami] | Elicited four-party English product-design meetings | 138 meetings, 69,258 source segment elements, 793,764 orthographic word elements, and 35 meeting-speaker components | Restricted source only; transcript adaptation, privacy review, experimental role, and component-aware split remain pending |

At least one adopted corpus must contain multiple speakers or sources,
meaningful less-frequent or negative cases, and enough context to distinguish
topical similarity from evidential support. Before real-text model or rater
processing, we will document consent and secondary-use scope, model-processing
authorization, pseudonymization, data minimization, contextual privacy review,
licensing, and whether exact excerpts may be shown to raters or released.
CaSiNo's public 900/30/100 random split is rejected because participant
isolation cannot be verified without stable cross-dialogue linkage. Any AMI
split must preserve all meetings connected through the same global source
speaker.

### 5.2 Model outputs

We will generate candidate codes and theme-level claims using two model families and two workflows:

- a direct single-pass prompt with exact-source citation requirements; and
- an iterative or agentic workflow that proposes, critiques, and revises outputs while retaining provenance.

One model family and one domain are used only after the routing policy, prompt, thresholds, and feature set are frozen. We will record provider/model snapshot, prompt, system instructions, chunking, context order, temperature and sampling settings, retries, run identifier, and all human edits. Each generation condition is repeated at least three times to expose substantive instability. Model outputs are sampled before human ratings using a preregistered scheme stratified by model, workflow, run, source or speaker concentration where supported by the corpus linkage, and automatic confidence; no “best run” is selected on test data.

### 5.3 Natural items and controlled failure twins

Natural model outputs offer ecological validity but can leave the true failure mechanism ambiguous. We therefore pair them with controlled twins. Each twin begins from an expert-vetted supported packet and changes one property while preserving wording, length, and topical plausibility as closely as possible.

| Failure family | Controlled manipulation | Why it matters | Primary expert role hypothesized |
|---|---|---|---|
| Unsupported evidence | Replace a supporting excerpt with a topically similar passage that does not warrant the claim. | Tests whether plausibility is mistaken for support. | TR/QME |
| Misquotation or attribution | Paraphrase, truncate, splice, or assign an excerpt to the wrong source. | Separates exactness from interpretive adequacy. | TR |
| Source or speaker concentration | Preserve the claim but draw its evidence from one source, or one linked speaker where supported, while wording suggests broad prevalence. | Detects the erasure of distribution and voice without inventing unavailable participant linkage. | QME/DE |
| Removed counterevidence | Delete a contradictory or boundary case from an otherwise supported packet. | Tests negative-case survival and conclusion stability. | QME/DE |
| Cultural or contextual flattening | Replace a context-sensitive interpretation with a fluent generic abstraction. | Tests loss of situated meaning without obvious factual error. | DE |
| Method-contract mismatch | Present a topic/category as a pattern-of-meaning theme, or impose consensus language under a reflexive brief. | Tests whether evaluation fits the declared analytic method. | QME |
| Unsupported abstraction | Broaden a local observation into a corpus- or group-level conclusion. | Tests scope and warrant. | QME/DE |

Item constructors will not rate their own items in the confirmatory panel. A second team member verifies that each manipulation changes only the intended factor; failures that cannot be isolated are retained as natural-error items rather than mislabeled as controlled twins.

### 5.4 Data-collection interface

We developed a lightweight web prototype, **Warrant Study**, to make distributed team review practical. The demo presents one evidence packet at a time, collects the rater’s role, 1–5 judgments of evidential support and voice preservation, 1–5 confidence, a “cannot judge” option, and an optional rationale. Responses are stored durably and can be summarized or exported by the organizer.

The demo is not yet the confirmatory instrument. Before data collection, we will add item randomization, blinded condition labels, role-verification questions, per-item timing, repeat-item reliability checks, a study-specific consent sheet, accessibility testing, and a frozen item manifest. The deployed study will not expose organizer views or raw responses through a participant link.

## 6 Human Evaluation

### 6.1 Recruitment and independence

We will recruit from the research team and, where needed, external collaborators to fill the three role strata. Participation by students or employees will be optional, unrelated to performance evaluation, and separated from supervisory decisions. Compensation or workload credit will be uniform within role strata and reported.

Reference construction, first-stage rating, and confirmatory expert evaluation are separated wherever the available team permits. No rater sees the model identity, routing condition, another rater’s score, or whether an item is natural or controlled. Raters disclose prior familiarity with each corpus and whether they helped create the source analysis; those observations are excluded from the primary independence analysis and reported separately.

### 6.2 Incomplete-block assignment

Exhaustive rating would waste expert time and induce fatigue. We use a crossed incomplete-block design in which each rater receives a balanced subset and each item receives at least three independent ratings per role in the confirmatory set. Assignment balances domain, model, workflow, failure family, severity, and natural/twin status. Twin pairs are separated in order and, when feasible, assigned to different raters to reduce recognition.

The pilot will contain no held-out test items. We will use pilot variance components and completion-time distributions to simulate power for the smallest scientifically important role-by-failure interaction and for H3’s noninferiority contrast. The final number of raters and items will be preregistered from that simulation; this draft intentionally does not invent a final sample size.

### 6.3 Rating instrument

For each packet, raters answer:

1. **Evidential support:** How completely does the cited evidence support the proposed interpretation? (1 = not at all, 5 = completely)
2. **Voice preservation:** How well does the interpretation preserve important differences, dissent, and context in the evidence? (1 = not at all, 5 = completely)
3. **Escalation:** Should this output be accepted, revised, rejected, or sent to another kind of expert?
4. **Confidence:** How confident are you in this judgment? (1 = very uncertain, 5 = very confident)
5. **Cannot judge:** Is information or expertise missing?
6. **Rationale:** What evidence, omission, ambiguity, or methodological issue most influenced your judgment?

Domain and qualitative experts additionally assign an error family and severity (minor, material, or high-consequence). Raters can mark more than one defensible interpretation and explain the difference. The analysis retains individual responses before any adjudication.

### 6.4 Training

All raters complete a short tutorial using examples excluded from analysis. Training defines support, voice preservation, counterevidence, source or linkage-supported speaker concentration, and the declared analytic contract without teaching the confirmatory answers. A comprehension check requires raters to identify an obvious unsupported quote and to distinguish “I disagree with the interpretation” from “the evidence cannot support it.” Failed checks trigger one retraining attempt; the exclusion rule is preregistered.

### 6.5 Expert panel and adjudication

The confirmatory target is built from independent judgments by qualitative-method and domain experts. We report each expert’s rating, role-specific distributions, and reliability before adjudication. Adjudication produces an operational accept/escalate label and severity only after independent ratings are locked. Items with persistent, reasoned expert disagreement are labeled **plural/ambiguous**, not forced into a false gold label. Primary routing metrics count successful escalation of such items rather than treating one side as error.

## 7 Expertise-Aware Routing

### 7.1 Routing inputs

The router may use only signals available before specialist review:

- trained-researcher rating distribution and disagreement;
- mean and dispersion of trained-researcher confidence;
- rate of “cannot judge” and requested expert type;
- response time and whether a rationale cites an exact source span;
- automatic quote-exactness, source-count, linkage-supported speaker-concentration, and counterevidence-retrieval checks; and
- model/workflow uncertainty signals that were fixed before the held-out test.

Protected participant attributes, rater identity, the held-out expert label, and free-text content that would reveal the controlled condition are excluded from the primary router. A secondary text-feature analysis may be reported only if it is prespecified and privacy-compatible.

### 7.2 Policies

We compare five policies at matched expert-time budgets:

1. **All trained researchers:** no specialist escalation.
2. **All experts:** every item receives the relevant QME and DE review; this is an expensive reference ceiling, not an assumed objective truth.
3. **Random routing:** items are escalated at the same budget as the proposed method.
4. **Uncertainty-only routing:** escalate on low mean confidence, high confidence dispersion, or “cannot judge.”
5. **Expertise-aware routing:** a development-trained risk model predicts both whether expert review will materially change the first-stage decision and which expert role is most relevant.

The primary implementation will be intentionally simple—a regularized logistic or ordinal model with a documented threshold. A tree-based model is a secondary ablation, not the headline. Thresholds are chosen on development data to maximize high-severity recall subject to a fixed expert-minute budget, then frozen.

### 7.3 Budget and utility

Expertise is costed in observed review minutes, not item counts. At budget (B), a policy’s primary utility is the number of high-severity failures correctly escalated before acceptance, with separate penalties for missed negative cases, missed source- or linkage-supported speaker-concentration failures, and unnecessary expert review. We report the full risk–coverage and quality–time curves rather than selecting one favorable budget after seeing test results.

The main comparison is held-out. Development-domain data may be used to fit coefficients and thresholds. The test domain, test model family, controlled-twin assignments, and expert labels remain inaccessible until the analysis pipeline is frozen.

### 7.4 Downstream feedback-to-revision test

Detection is useful only if the resulting feedback can improve an output. For each defective packet, we will freeze one revision model, prompt, decoding configuration, and feedback formatter before confirmatory evaluation. The model receives one of four inputs: no feedback, trained-researcher feedback, full-expert feedback, or expertise-aware routed feedback. It is not told that the defect was planted.

A separate blinded panel judges whether the revision repairs the targeted defect, preserves accurate and relevant material, and introduces any new unsupported claim, omission, or distortion. The secondary confirmatory endpoint is **successful repair without collateral error**. This is an offline extension of the same collected feedback and requires no additional complexity in the participant-facing interface.

## 8 Analysis Plan

### 8.1 Primary outcomes

The confirmatory primary outcomes are:

- **high-severity failure recall** under matched expert minutes;
- **false acceptance rate** for unsupported, voice-erasing, or plural/ambiguous items;
- **agreement with the independent panel’s accept/escalate decision**, reported with uncertainty and without calling the panel universal ground truth; and
- **expert minutes per correctly escalated high-severity item**.

The key confirmatory contrast is expertise-aware routing versus uncertainty-only and random routing on the held-out domain/model. All-expert and all-trained-researcher policies bound the trade-off.

### 8.2 Secondary outcomes

Secondary outcomes include ordinal support and voice scores, error-family recall, source and negative-case survival, linkage-supported speaker coverage, rationale usefulness, abstention, review time, calibration (Brier score, expected calibration error, and reliability plots), selective risk–coverage, and the fraction of specialist decisions that change a first-stage judgment. We also report how often QME and DE review contribute distinct rather than redundant changes.

The downstream secondary outcome is successful repair without collateral error. We analyze it with a logistic mixed model containing feedback condition and failure family, with random intercepts for base packet and adjudicator. If revised outputs are evaluated pairwise, a Bradley–Terry model with packet effects replaces independent-vote analysis.

### 8.3 Statistical models

Role effects on ordinal ratings will be estimated with cumulative-link mixed models containing fixed effects for role, failure family, natural versus controlled status, domain, model family, workflow, and prespecified role-by-failure interactions. Crossed random intercepts for rater and item account for repeated measures; source/document and generation run are added where identifiable. Binary accept/escalate and high-severity detection outcomes use logistic mixed models with the same structure. Review time uses a log-linked model after preregistered treatment of inactive-browser outliers.

We report effect sizes, 95% confidence intervals, predicted probabilities, and multiplicity-adjusted confirmatory contrasts. The primary interpretation rests on intervals and held-out performance, not on isolated (p)-values. If convergence fails, the fallback model and any collapsed random effects will be disclosed.

### 8.4 Reliability and disagreement

Within-role reliability is reported using ordinal Krippendorff’s alpha and a prevalence-robust coefficient such as Gwet’s AC2, each with cluster-bootstrap intervals. Pairwise percent agreement is included for interpretability. Reliability is not treated as quality: low agreement may reveal genuine ambiguity, and high agreement may reflect shared bias. We therefore audit high-agreement errors and qualitatively analyze persistent cross-role disagreement.

### 8.5 Calibration and routing evaluation

We evaluate rater confidence and router probabilities with reliability diagrams, Brier scores, and risk–coverage curves. A routing policy must not appear successful by deferring almost everything; every result is shown against expert minutes and escalation coverage. We report performance at preregistered budget points and the area under the quality–time curve.

Routing comparisons use item-level paired bootstrap intervals and, where appropriate, permutation tests that preserve item and rater blocks. Noninferiority to all-expert review is claimed only if the lower confidence bound exceeds the preregistered margin. We will not define that margin after inspecting held-out results.

### 8.6 Generalization and ablations

The minimum ablations are:

- remove role information from routing;
- use confidence alone;
- use disagreement alone;
- use automatic provenance checks alone;
- remove rationales and timing;
- omit source excerpts from the rating interface;
- replace human first-stage signals with an LLM judge; and
- evaluate in-domain versus held-out domain/model performance.

Results are stratified by failure family and severity. A pooled average cannot support the paper’s central claim if subtle, culturally situated, or negative-case failures are sacrificed.

### 8.7 Qualitative analysis of rationales

Two analysts will conduct a bounded framework analysis of rationales using the preregistered failure families plus an “other” category. The purpose is diagnostic: to explain why roles disagree and to identify missing router signals, not to create a new ground-truth theme set. Analysts first code independently, discuss differences, retain meaningful dissent, and link every reported pattern to privacy-reviewed, pseudonymized examples. Confirmatory quantitative outcomes will not be changed in response to this post-hoc analysis.

## 9 Ethics, Data Governance, and Researcher Positionality

The study involves both source participants and research-team raters. Their risks differ.

For source data, we will verify that consent and secondary-use terms permit model processing and human review. Sensitive material will use local processing or institutionally approved endpoints whose exact training, retention, access, and deletion settings satisfy the recorded governance decision, plus encryption in transit and at rest, role-based access, and minimal retention. Evidence packets will expose the smallest context needed for judgment; identifying quotations will be suppressed or paraphrased only when the task does not require exactness. Any paraphrase is labeled as such and is not used in quotation-integrity trials.

For raters, participation will be voluntary and separable from employment, coursework, authorship, or supervision. The organizer will not use individual scores for performance assessment. We will collect only task-relevant expertise and positionality fields, publish aggregate role-level results, and use a withdrawal code rather than a public identity. Free-text rationales will be screened for identifying information before release.

Controlled failures involving cultural loss, trauma, or discriminatory language will be co-designed or reviewed by relevant domain/community advisers. We will avoid treating demographic identity as a defect predictor or assuming a single community voice. The primary harm criterion is whether a workflow hides, distorts, or overstates participant evidence; the final interpretive authority remains human and internally accountable under the study protocol.

The project will obtain [IRB/ethics determination] before confirmatory recruitment. We will preregister the hypotheses, exclusions, role definitions, item construction, power analysis, routing thresholds, and primary outcomes. Data and code release will follow source consent, licensing, and privacy constraints; when raw text cannot be released, we will release synthetic twins, derived labels, full prompts, analysis code, and a reproducibility datasheet. Text-derived hashes or keyed commitments will be released only when source terms permit and a linkage-risk review finds them safe.

## 10 Results (Reporting Shell — No Results Yet)

This section is deliberately a shell. It should be populated from a frozen analysis export, with all denominators and exclusions reconciled before prose is written.

### 10.1 Participants and material

Report recruited and analyzed raters by role, exclusions, experience, domain familiarity, completion time, items per rater, ratings per item, corpus sizes, model runs, and natural/twin balance. Distinguish item constructors, first-stage raters, and panel experts.

| Quantity | Development | Held-out test | Total |
|---|---:|---:|---:|
| Source groups or documents | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Verified linked speakers (where supported) | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Sampling-eligible records | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Natural evidence packets | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Controlled twins | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| QME / DE / TR raters | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Independent ratings | [TO REPORT] | [TO REPORT] | [TO REPORT] |

### 10.2 Where expertise changes judgments

Report role-by-failure predicted probabilities and intervals, not only mean Likert ratings. Highlight whether the hypothesized split between obvious source errors and contextual/methodological errors is supported. Include within-role variation and persistent expert disagreement.

| Failure family | TR detection | QME detection | DE detection | Role contrast | Interpretation |
|---|---:|---:|---:|---:|---|
| Unsupported evidence | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Misquotation/attribution | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Source or linked-speaker concentration | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Removed counterevidence | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Cultural/contextual flattening | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Method-contract mismatch | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |

### 10.3 Routing under matched expert time

Report every policy at the preregistered expert-minute budgets. The headline result should be held-out high-severity recall and false acceptance, not development AUC.

| Policy | Expert minutes | High-severity recall | False acceptance | Panel alignment | Calibration |
|---|---:|---:|---:|---:|---:|
| All trained researchers | 0 | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Random | [BUDGET] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Uncertainty-only | [BUDGET] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| Expertise-aware | [BUDGET] | [TO REPORT] | [TO REPORT] | [TO REPORT] | [TO REPORT] |
| All experts | [TO REPORT] | [TO REPORT] | [TO REPORT] | Reference ceiling | [TO REPORT] |

### 10.4 Reliability, calibration, and disagreement

Report alpha/AC2 with intervals for each role and construct, confidence calibration by role, the number of plural/ambiguous items, and a taxonomy of rationales. Include at least one high-agreement shared error and one productive expert disagreement so that reliability is not equated with validity.

### 10.5 Ablations and transfer

Report the full in-domain/held-out matrix, feature ablations, and no-source interface ablation. If the routing advantage disappears under transfer, say so directly and narrow the claim to a measurement study.

### 10.6 Does routed feedback repair the output?

Report successful repair, collateral-error rate, and expert minutes for no-feedback, trained-researcher, expertise-aware, and full-expert conditions. Do not call a fluent rewrite a repair unless the blinded panel verifies the targeted warrant or voice defect.

## 11 Discussion

The paper’s interpretation will depend on which of four patterns the data support.

1. **Complementary expertise.** If QMEs and DEs detect different failures, routing should be multi-destination rather than a single “send to expert” gate. The contribution would be evidence that expertise is task-specific and compositional.
2. **Broad nonexpert competence with narrow escalation.** If trained researchers reliably catch direct support failures while experts add value on a small set of contextual or methodological items, the practical result would be a lightweight first-pass audit with principled escalation.
3. **Persistent plural disagreement.** If experts disagree for articulated, source-grounded reasons, the correct output may be a flag for deliberation rather than a binary verdict. Routing would then identify where plurality should be preserved.
4. **No transferable routing advantage.** If policies fail on the held-out domain/model, the honest contribution would be a negative result: expertise needs cannot be inferred reliably from generic uncertainty signals, and domain-specific review remains necessary.

Any positive routing result must be interpreted narrowly. It would show that, for the declared codebook-oriented warrant task and sampled domains, first-stage signals can allocate review. It would not establish that nonexperts can conduct reflexive thematic analysis, that experts are interchangeable, or that an LLM-generated interpretation becomes valid after a score threshold.

### 11.1 Implications for NLP evaluation

NLP human evaluation often treats annotator expertise as a recruitment detail and inter-rater agreement as a single quality check [@vanderlee2019best; @howcroft2020confusion]. Our design instead makes role an explanatory variable, measures abstention and confidence, and tests value under a resource constraint. This follows a construct-first view of evaluation: the intended construct and its measurement conditions must be explicit before optimization [@jacobs2021measurement].

The approach also changes what “human-in-the-loop” means. A person who supplied the reference, a user who clicked accept/reject, and an independent domain expert do not provide equivalent evidence. Reporting their roles separately should be standard when model preferences, codebooks, or prompts can leak into later evaluation.

### 11.2 Practical use by mixed research teams

The intended workflow is deliberately modest. Team members receive a link, complete a short role-appropriate tutorial, and rate a balanced subset of evidence packets. Obvious unsupported outputs can be rejected immediately; uncertain or high-risk items are routed to the relevant specialist; disagreements and rationales remain visible to the analysis lead. The interface reduces coordination cost, while the scientific design—not the interface—determines whether this allocation is trustworthy.

## 12 Limitations

First, expert judgment is situated. Credentials do not guarantee correctness, and an adjudicated panel can reproduce disciplinary or institutional bias. We mitigate this by defining task-relevant expertise, retaining individual rationales, reporting disagreement, and treating the reference as contract-relative.

Second, controlled twins improve causal attribution but may be easier or less natural than real model errors. We therefore report natural and controlled items separately and require independent plausibility checks.

Third, a small research team may limit the number and diversity of experts. Crossed incomplete blocks improve efficiency but do not replace broader stakeholder representation. Claims will be limited to the recruited domains, languages, and positionalities.

The source-only dialogue candidates add corpus-specific constraints. CaSiNo's public release cannot support distinct-person counts, participant-disjoint splits, or cross-dialogue participant concentration because it lacks a stable participant token. AMI scenario meetings are elicited role play rather than natural conversation, and the planned transcript-only lane omits prosodic, timing, overlap, and multimodal evidence. Neither source contributes experimental evidence unless its pending preprocessing, privacy, split, and governance gates are completed and its role is preregistered.

Fourth, routing can create automation bias: non-routed items may appear safe merely because the policy did not escalate them. The interface will avoid “approved by AI” language, preserve random audit, and keep final authority with the research lead.

Fifth, review-time savings measured in a study may not transfer to real longitudinal qualitative analysis, where familiarization, memoing, team discussion, and responsibility dominate. We measure bounded evidence-packet review, not end-to-end analytic labor.

Finally, proprietary model behavior changes over time. Exact versions, prompts, run metadata, and held-out dates will be reported; a model-specific routing advantage will not be generalized to future systems without replication.

## 13 Conclusion

Manual feedback is already established in ACL/EMNLP research on qualitative coding, but “human feedback” combines different kinds of judgment. This paper asks who should review what. By crossing rater expertise with source-grounded natural outputs and controlled validity failures, then testing review allocation under a fixed expert-time budget and held-out transfer, WarrantRoute aims to turn a mixed research team into a measurable evaluation design rather than an undifferentiated panel. The central standard is conservative: route uncertainty without concealing dissent, and never let fluency, agreement, or provenance stand in for a warranted interpretation.

## A. Planned Reproducibility Package

Subject to consent and licensing, the artifact will include:

- frozen prompts, model/version settings, and generation manifests;
- item-construction guide and controlled-twin transformations;
- blinded evidence-packet schema and stable source offsets;
- rater tutorial, consent text, role definitions, and full questionnaire;
- privacy-reviewed pseudonymous item-level ratings, or aggregate and coded rationale features, and permitted rater-response timing data;
- preregistration, power-simulation code, analysis scripts, and environment lockfiles;
- routing policies and all thresholds fixed before held-out evaluation;
- datasheets describing corpora, rater recruitment, exclusions, privacy restrictions, and known dependencies; and
- a statement of which artifacts are peer reviewed, preprints, or unpublished study materials.

## B. Decisions Required Before Data Collection

- [ ] Preserve the provisional planned Dreaddit and CaCHe roles; decide whether CaSiNo and AMI advance from source-only candidates, resolve the CaSiNo linkage blocker, and validate AMI component-aware preprocessing and splitting.
- [ ] Confirm source-data permissions and obtain the ethics/IRB determination.
- [ ] Freeze the analytic contract and terminology: code, category, theme, warrant, negative case, and voice preservation.
- [ ] Name item constructors, first-stage raters, independent QMEs, independent DEs, and adjudicator(s).
- [ ] Pilot timing and variance on items excluded from confirmation.
- [ ] Run simulation-based power analysis and preregister the final design.
- [ ] Freeze model families, prompts, runs, routing features, thresholds, and expert-minute budgets.
- [ ] Upgrade the demo with randomization, blinding, timing, accessibility, repeat checks, and a production consent flow.
- [ ] Decide what can be released without exposing participants or sensitive quotations.
- [ ] Replace the Results shell and prospective abstract only from a frozen analysis export.

## References

This Markdown draft uses Pandoc citation keys. Full publication metadata and peer-review-status notes are in [`references.bib`](references.bib). Archival ACL/EMNLP-family papers and peer-reviewed journal/conference work are distinguished from preprints in that file and in the project evidence inventory.
