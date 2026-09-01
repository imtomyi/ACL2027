# RQ2 personal-local prompt-limit contract v5

Status: active only for the source-free v2.3 transport diagnostic. The frozen
v2.2 qualification runner, configuration, protocol, requests, call counts, and
artifacts remain unchanged. V2.3 is not a real-corpus execution freeze and has
no `run` or `resume` command.

Every v2.3 outcome is private engineering evidence labeled
`diagnostic_not_manuscript_evidence`. It is ineligible for manuscript,
submission, publication, release, redistribution, or human-review use.

## Prompt-limit invariant

Every Ollama chat request sets top-level `truncate` and `shift` to `false`.
Ollama must reject an input that exceeds the loaded context before generation.
The diagnostic never accepts an automatically truncated request or a response
that lacks prompt-token accounting. A successful response must leave the
frozen output-token reserve and safety margin inside the requested context.

The diagnostic verifies that the local verifier advertises at least the frozen
required native context capacity. This metadata check does not authorize an
unbounded context size or change any predecessor decoding contract.

## Deterministic chunk planning

Chunking operates only on an explicitly declared chunkable payload. The full
task instruction remains in a fixed prefix that is repeated for every chunk.
Chunks preserve all UTF-8 bytes exactly, in order, without duplication or
loss. Boundaries prefer paragraphs, lines, sentences, punctuation, and spaces.
A single code point is never split.

The initial chunk plan is deterministic and hash-bound. If Ollama returns only
its exact pre-generation context-overflow error for a planned chunk, the
diagnostic bisects that payload chunk deterministically and retries the two
children. No model output exists for the rejected request. Other transport
errors are terminal. Chunk count and overflow-rejection limits are enforced
before further calls.

## Canary reducer

The v2.3 live diagnostic reuses the three source-free v2.2 fixture meanings.
Only the inert padding is chunkable. The complete source-free instruction is
repeated for every physical chunk. Each chunk response must independently pass
the frozen flat schema, deterministic cross-field adapter, canonical schema,
and exact fixture comparison.

Every canonical response for one logical fixture must be byte-identical. The
only reducer is exact consensus. Majority vote, last-result selection, JSON
concatenation, manual repair, retry after a generated response, and semantic
adaptation are forbidden. Evidence records only source-free counts and hashes,
never prompt or model content.

## Research-prompt boundary

Generic chunking of a real WarrantRoute packet is not authorized by this
transport diagnostic. The six excerpts must be judged jointly for support,
counterevidence, boundary conditions, and source independence. A future
source-bearing version must freeze task-specific chunk schemas and a
deterministic reducer before it can split such a semantic unit. Until then, an
oversized research prompt must stop before generation rather than use a generic
reducer.

The preferred first response to a prompt that exceeds a configured window but
fits the model's verified native capacity is a separately frozen context
increase. Chunking is reserved for content with an explicit reducer.

## Source and write boundary

Both v2.3 commands are source-free. They do not open dataset files,
predecessor selections, or `Storage/`, and they write no artifacts. The static
command contacts no service. The live preflight contacts only the numeric
loopback Ollama endpoint and prints a sanitized summary.
