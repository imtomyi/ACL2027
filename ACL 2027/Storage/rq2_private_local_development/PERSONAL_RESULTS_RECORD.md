# RQ2 private development diagnostic — personal record

This note records the latest completed local RQ2 engineering diagnostic for
personal reference. It is **not a manuscript result**, is **not scientifically
interpretable as an RQ2 estimate**, and must not be copied into any manuscript
source, draft, appendix, compiled PDF, or submission export.

## Recorded run

- Review run: `rq2dev_20260826T220315Z_ad29df5a`
- Source run: `rq2dev_20260826T215429Z_53e4a7e1`
- Reviewer model: `llama3.1:8b` (local loopback service)
- Scope: one sealed packet, five controlled variants, three role prompts, one
  repetition
- Observation attempts: 15
- Valid observations: 13
- Terminal failures: 2

## Arithmetic diagnostic

| Role prompt | Exact target flags | Attempted items | Arithmetic recall | Terminal failures |
|---|---:|---:|---:|---:|
| Generalist | 0 | 5 | 0.0% | 1 |
| Methods | 0 | 5 | 0.0% | 1 |
| Domain | 0 | 5 | 0.0% | 0 |

These values reflect the frozen diagnostic scoring rule only. They are not
estimates of role performance and support no comparison between roles.

## Why this cannot support a manuscript claim

- The five target labels were not independently verified.
- The same local model constructed and reviewed the variants.
- The source run preceded a prospective evidence-role binding repair.
- The review transport schema caused two invalid outputs.
- The run did not freeze all required software identifiers.
- One packet and one repetition do not implement the planned RQ2 design.
- No WarrantRoute-versus-fixed-role comparison, held-out CaCHe estimate,
  Dreaddit test audit, clustered confidence interval, or cost analysis exists.

## Authoritative machine-readable records

- `rq2dev_20260826T220315Z_ad29df5a/run_manifest.json`
- `rq2dev_20260826T220315Z_ad29df5a/results.development.json`
- `postrun_audit_rq2dev_20260826T220315Z_ad29df5a.json`

The machine-readable records are authoritative if this note and those files
ever disagree.
