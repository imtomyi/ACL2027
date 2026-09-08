# Portkey Backend Setup

Status: adapter, USD 100 budget guard, and offline preflight implemented;
credentials and current token prices not configured; no Portkey request has been
made.

This setup is for a future, separately frozen experiment. It does not alter the
completed local Ollama runs or their results.

## Required Portkey Configuration

1. Create a Portkey API key in the Portkey dashboard Settings page.
2. Use a dedicated API key for this experiment. In the Portkey dashboard, set a
   cost budget of exactly USD 100, no periodic reset, and a USD 80 alert
   limit. The key must not be shared with unrelated workloads.
3. Configure provider authentication in Portkey's Model Catalog and obtain its
   provider slug, or create a Portkey config and obtain its config slug.
4. Choose the exact model identifier exposed by that provider or config. The
   supplied setup guide identifies these currently intended pairs:
   `@info-yd4956-ope-01316b/gpt-5.4-mini` and
   `@info-yd4956-anthropic/claude-sonnet-4-5-20250929`.
5. Copy `config/portkey.env.example` to `config/portkey.local.env` and fill in:
   `PORTKEY_API_KEY`, `PORTKEY_MODEL`, and exactly one of `PORTKEY_PROVIDER` or
   `PORTKEY_CONFIG`.
6. Freeze the provider's current input and output USD-per-million-token rates,
   their HTTPS source URL, and the date verified. Pricing must be rechecked
   within seven days of every run.
7. Review Portkey's logging, retention, access, and provider data handling before
   changing `PORTKEY_ALLOW_EXTERNAL_DATA` to the exact acknowledgement required
   by the preflight. Source text may be logged by the gateway and provider.

The local credential file is ignored by Git. The adapter never places the API
key in a manifest, output, exception, trace ID, command argument, or redacted
configuration snapshot. Prefer an ephemeral shell environment or an approved
secret manager over a persistent plaintext file.

## Mandatory USD 100 Budget Control

The experiment has an absolute USD 100 ceiling. The full run is authorized only
when both controls below are active:

1. **Remote enforcement:** a dedicated Portkey API key has a dashboard cost
   budget of USD 100 with no periodic reset. Set `PORTKEY_REMOTE_BUDGET_ACK` to
   the exact value shown by preflight only after confirming this in Portkey.
2. **Local enforcement:** every request first reserves its conservative maximum
   token cost in one shared, file-locked ledger. Committed spend plus all pending
   reservations may never exceed USD 100. Successful responses settle against
   reported input/output usage; failures or responses without usable token
   counts commit the entire reservation.

Portkey documents API-key budget controls as an Enterprise and selected-Pro
feature. If this workspace cannot set and visibly confirm the dedicated key's
USD 100 non-resetting budget, leave the acknowledgement unset and do not run the
experiment. The local ledger alone is not accepted as an invoice-level hard cap.

The reservation is based on UTF-8 prompt bytes plus 2,048 input-overhead tokens,
the requested output limit plus 256 output-overhead tokens, frozen input/output
prices, and a default 1.10 safety multiplier. Parallel workers share the same
ledger, so each worker must use the identical absolute `PORTKEY_BUDGET_LEDGER`
path. Crashed workers leave their reservations pending by design; do not delete
or edit the ledger to recover capacity. Reconcile them against Portkey logs and
document any correction through a separate audited recovery procedure.

The local ledger records token-based estimates, not a provider invoice. Pricing
changes, cached-token pricing, tool charges, taxes, or unsupported custom models
can differ. Therefore the Portkey-side USD 100 key budget is mandatory, not
optional. If Portkey shows a zero cost for the selected model, the run remains
blocked even if the local preflight passes because Portkey documents that such a
model may not count toward its remote budget.

## Preflight

Load the local environment in the current shell:

```bash
set -a
source "experiments/rq2_role_prompted_llm/config/portkey.local.env"
set +a
```

Validate configuration without making a network request:

```bash
python3 experiments/rq2_role_prompted_llm/scripts/check_portkey_setup.py
```

After credentials, provider/config, model, and external-transmission approval
are final, make one minimal probe that contains no research data:

```bash
python3 experiments/rq2_role_prompted_llm/scripts/check_portkey_setup.py --probe
```

The probe incurs one provider request and is charged to the same local USD 100
ledger. It does not certify that the target model
supports the complete experiment prompt or output constraints. A frozen canary
is still required before any full run.

## Experiment Integration Contract

Import `portkey_gateway.PortkeySettings` and `chat_completion` from a future
runner. The adapter uses Portkey's OpenAI-compatible
`POST /v1/chat/completions` endpoint and sends `x-portkey-api-key` plus either
`x-portkey-provider` or `x-portkey-config`. It maps the experiment's
temperature, top-p, output-token limit, response format, model, and timeout
without silent fallback.

Before inference, freeze a new run ID and record the redacted settings, provider
or config slug, exact model ID, prompt and schema hashes, generation settings,
Portkey response-format mode, selection rules, source hashes, and package/runtime
versions. Never reuse a local Ollama manifest for a Portkey run. Never compare or
combine backends under one row unless the experimental design explicitly defines
that comparison in advance.

For every response, retain the response ID, request ID when supplied, reported
model, finish reason, token usage, request hash, validation outcome, and timing.
Reject empty content, malformed JSON, unexpected finish reasons, schema errors,
model mismatch, and missing unit identity. Preserve all failed attempts and use
the same bounded retry rules as the applicable frozen experiment.

No full experiment should start until:

- offline preflight passes;
- the minimal network probe passes;
- the exact target model and provider/config are frozen;
- source-data transmission is explicitly approved;
- a representative canary passes without truncation or schema failures;
- estimated call count and provider cost are reviewed;
- the dedicated Portkey key has a non-resetting USD 100 remote budget;
- current model prices and their source are frozen and at most seven days old;
- the shared local ledger reports enough available reserved budget for the run;
- the run remains Storage-only unless the workspace manuscript policy is later
  satisfied by independently authorized real-corpus evidence.

## Official References

- [Portkey authentication](https://portkey.ai/docs/api-reference/inference-api/authentication)
- [Portkey request headers](https://portkey.ai/docs/api-reference/inference-api/headers)
- [Portkey Chat Completions](https://portkey.ai/docs/product/ai-gateway/chat-completions)
- [Portkey Python SDK and environment setup](https://portkey.ai/docs/api-reference/sdk/python)
- [Portkey API-key budget limits](https://portkey.ai/docs/product/administration/enforce-budget-and-rate-limit)
- [Portkey model pricing and cost management](https://portkey.ai/docs/product/observability/cost-management)
