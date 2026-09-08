# WarrantRoute cumulative-output v1 working decision

Date: 2026-09-02  
Status: selected working correction, not manuscript eligible

## Decision

Use the public method name `WarrantRoute` for the corrected model. The internal
variant identifier is `cumulative_output_v1`; it is not a second paper-facing
method name. Do not replace the frozen 48-row Table 3 and do not treat this
decision as a prospective study result.

## Semantic correction

WarrantRoute-S already pays for and observes the Generalist output before route
selection. Specialist acquisition therefore adds evidence rather than replacing
evidence. Terminal output composition is:

```text
generalist           = G
qualitative_methods  = G union M
domain               = G union D
both                 = G union M union D
```

The route action, acquired specialists, and total role-call count are inherited
unchanged from the pinned WarrantRoute-S route artifact. This guarantees that
cumulative union recall cannot be lower than Generalist recall on the same valid
outputs.

## Working evidence

| Candidate | TP/1,200 | Recall | Mean role calls | Decision |
| --- | ---: | ---: | ---: | --- |
| Generalist | 654 | 54.5% | 1.0000 | baseline |
| Fixed role | 767 | 63.9% | 1.0000 | exploratory baseline |
| WarrantRoute-S | 770 | 64.2% | 1.3592 | source router |
| WarrantRoute (cumulative_output_v1) | 773 | 64.4% | 1.3592 | selected correction |
| Calibrated breakpoint candidate | 747 | 62.3% | 1.3692 | rejected |
| All roles | 874 | 72.8% | 3.0000 | union upper bound |

The corrected WarrantRoute strictly dominates WarrantRoute-S in this replay: three
additional true positives, identical calls, and no cell regression. The fitted
breakpoint candidate is dominated by the corrected WarrantRoute and is not selected.

## Boundary

The benchmark contains only intended-flaw-positive packets and scores union
recall. It cannot estimate precision or false-positive cost. The source routes
and evaluation outcomes were already opened in earlier working analysis.
Consequently, this evidence may guide implementation and the next protocol but
must not be used as a confirmatory or manuscript result.

The next formal candidate requires a disjoint route-development bank, clean
negative packets, a prospectively fixed call budget, precision/recall/F1 and
false-positive reporting, frozen model digests and prompts, and one untouched
final evaluation bank.
