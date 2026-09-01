# Qwen3 Generalist external score promotion contract v1

## Boundary

`promote_qwen3_generalist_score.py` is the only component covered by this
contract. It does not score observations and does not open corpus, packet,
truth, observation, raw-execution, or manuscript files. It reads only one
source-free internal aggregate from `Storage/`, one external-authority
promotion record, one detached signature, and one trusted public key from
`governance/local/`. It also reads the fixed system trust registry described
below. It never generates a key or signature.

The internal aggregate must be the exact Qwen3 8B Generalist export for the
Dreaddit test row. Its status must be `complete_internal_only`, its existing
external-authority blocker must remain intact, and all 21 evidence-chain hashes
must be present. The tool rejects extra fields, inconsistent scores, changed
hashes, item-level content, and any different dataset, split, method, model,
actor, or metric.

## Trust registry and signature

Trust cannot be established with command-line parameters. The only production
trust registry path is fixed in code as
`/etc/warrantroute/qwen3_generalist_score_promotion_authorities_v1.json`.
There is no command-line registry override. The resolved registry file must be
root-owned with no write bit, and every resolved ancestor must be root-owned
and not group- or world-writable. A missing, user-owned, writable, inactive, or
malformed registry blocks promotion.

The registry identifies each trusted authority, pins the SHA-256 fingerprint
of its canonical DER SubjectPublicKeyInfo, defines its activation interval,
and repeats the one exact reporting scope it may approve. Authority identifiers
must be unique. The default repository and workstation state contain no such
registry and therefore cannot promote a score.

The caller supplies an authority identifier to select an already trusted
entry, a PEM SubjectPublicKeyInfo file containing the corresponding Ed25519
public key, and a raw 64-byte detached Ed25519 signature. The computed key
fingerprint, registry fingerprint, and fingerprint in the signed record must
be identical. A locally generated key and arbitrary authority identifier have
no standing without a preinstalled registry entry. The
signature covers the canonical UTF-8 JSON representation of the entire
promotion record: keys sorted lexicographically, no insignificant whitespace,
no non-finite numbers, and one trailing newline. Duplicate JSON keys are
rejected before verification.

No registry, public key, authority identifier, promotion record, or signature
is bundled with this repository. A locally invented key or self-signed record
is not an external authorization and must not be installed as a trust anchor.

## Signed promotion record

The promotion record has exactly these top-level fields:

```text
document_type, promotion_version, authority, decision, validity, scope,
aggregate_binding, evidence_chain, attestations
```

`authority` names the externally trusted authority and its public-key
fingerprint. `decision` must state `approved` and set
`manuscript_reporting_authorized` to true. `validity` supplies an approval
time, a not-before time, and an expiry time in UTC. The approval must postdate
the internal aggregate, and the promotion must occur inside the signed
validity interval.

`scope` is exact, not wildcarded. It is limited to project
`warrant-route-acl2027`, study `warrantroute-rq2`, row
`table3_dreaddit_generalist_qwen3_8b`, purpose `manuscript_reporting`, the
Dreaddit test split, the Generalist method, reviewer actor
`qwen3_8b_generalist_reviewer_v1`, the exact Qwen3 model identifier and digest,
and error-detection recall.

`aggregate_binding` contains the exact internal-export file hash, hashes of
the dataset, method, candidate-generation, and complete metric objects, plus
the explicit `TP`, `FN`, `N`, recall, percentage, and confidence interval.
`evidence_chain` repeats the complete 21-entry input-hash map and binds its
canonical hash. The signed values must equal the supplied internal aggregate.

The three attestations must state that only the aggregate was reviewed, source
text is absent from the promotion record, and approval is limited to the bound
score. These attestations supplement rather than replace cryptographic and
scope checks.

## File handling and output

All inputs must be absolute, nonsymlinked, mode-0600 regular files. Their
immediate parent directories must be nonsymlinked mode-0700 directories. The
aggregate must be under `Storage/`; authority material must be under
`governance/local/`. The output must be a new path under a mode-0700 `Storage/`
directory. The system trust registry is the sole exception to these private
input roots and is governed by the ownership and write-protection checks
above. The tool creates the output mode 0600 and refuses overwrite.

Only a successfully verified record produces an output. That output copies
the aggregate score and hashes, records the authority decision and signature
provenance, and sets `manuscript_eligible=true`. It contains no item identifier,
excerpt, prompt, rationale, truth label, observation, or source text. Signature,
fingerprint, authority, scope, date, or binding failure leaves no output.

The source-free `dry-run` confirms only that the promotion component and this
contract are readable. It always reports `manuscript_eligible=false` and may
report whether the fixed registry path exists, but it does not treat existence
as authorization.
