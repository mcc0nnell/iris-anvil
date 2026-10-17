# Build 154: controlled execution and evidence capture

**This is the repeatable operator runbook.** On October 17, 2026 UTC, an isolated build-154 lab compiled all nine classes, passed all eight actual ObjectScript policy cases, and started the interoperability production. Local no-key and unknown-signal inbound events returned `BLOCKED` without queued delivery. This evidence does **not** establish an external model call, successful delivery, or immutable assurance. Use only an authorized, isolated IRIS AI Hub **2026.3.0AI.154.0** container. Never redistribute the EAP image or commit provider keys.

## Stage 1: Compile only, without starting production

Use the project's documented Docker Compose setup on a local lab host. The source must be mounted read-only at `/opt/iris-anvil/src`. Keep `OPENAI_API_KEY` **unset** for this stage; do not enable external delivery connectors. If a separate IRIS container is already working, use its actual container name instead of starting another copy. These commands should be run by an operator through an approved IRIS terminal/session, not via a blocked automation channel.

```bash
cd contest/ai-hub
# After IRIS is healthy and the source mount exists:
docker exec -i iris-anvil-aihub iris session iris -U USER < scripts/compile-only.scr | tee compile-154.log
python3 scripts/verify-runtime-log.py compile compile-154.log
```

The compiler script attempts the nine classes in dependency order and prints **one PASS/FAIL line per class plus a summary**. The verifier **fails closed** on missing records, duplicate markers, failures, or partial output. The command's shell exit status alone does not prove compilation succeeded; check the verifier's exit status. Keep raw compile logs in a local private evidence directory (they may contain class details). Do not publish the EAP image or private configuration.

## Stage 2: Deterministic policy tests without a model call

Only after all nine classes compile:

```bash
docker exec -i iris-anvil-aihub iris session iris -U USER < scripts/policy-only.scr | tee policy-154.log
python3 scripts/verify-runtime-log.py policy policy-154.log
```

These tests exercise actual ObjectScript: critical `SMOKE` and `BABY_CRY` routing remains `BOTH`, allowlisted benign routes are preserved, and unknown signals or invalid agent proposals are `BLOCKED`. No provider, network call, fake AI reply, or real notification is involved.

## Stage 3: Production startup, only after preflight passes

In the already isolated demonstration environment, run the existing `scripts/install.scr` (which includes the production start) through an approved operator session. Prove the `ANVIL INTEROP PRODUCTION STARTED` sentinel and inspect IRIS Management Portal message traces. For negative controls, keep credentials absent and verify that synthetic events do **not** create `QUEUED` receipts. Test noncritical and critical synthetic cases separately. A completed local receipt is only an IRIS database digest, **not** an immutable external WindAnvil attestation.

When valid API credentials are explicitly supplied in a separate authorized run, record whether `%AI.Agent.Chat` genuinely returned a proposal and whether the deterministic policy prevented downgrades. This optional step can incur real API cost. Do not claim an agent decision from policy-only tests.

## Evidence ledger

For each run, preserve the image digest and Build 154 identity, source commit, container name/identity, command line, full compiler and policy logs, verification exit codes, timestamp, and actual outcomes. Treat any missing element as **BLOCKED / NOT ESTABLISHED**. The Python verifier proves only that a supplied transcript has the expected structure; it does not authenticate the runtime that produced it.

October 17 native lab update: a normal approved `docker exec -i ... iris session ... < scripts/compile-only.scr` invocation ran directly on build 154. The first attempt compiled 8/9 classes and reported ObjectScript compiler error #1043 in `Inbox.OnProcessInput` (returning a value directly from `CATCH`). After the targeted repair, all 9/9 classes compiled, all 8/8 policy assertions passed, and the production started. Two synthetic inbound events were archived with persisted `Anvil.Interop.Result` records: `DOORBELL` without a provider key returned `BLOCKED` (`OPENAI_API_KEY missing`), and an `UNKNOWN` signal returned `BLOCKED` (`Signal outside allowlist`). Replaying the no-key event remained blocked. `^Anvil.Interop.Queue`, `^Anvil.Interop.Outbox`, and `^Anvil.Interop.Receipts` were empty when queried. A malformed JSON file was retained in the input directory for error handling, so malformed-file quarantine and replay recovery remain separate checks. Raw local runtime evidence is under `/home/commander/lab/iris-anvil-runtime-20261016/` on Butcher. Do not confuse this with live AI inference or a successful delivery.

## October 17: externally authored ChatGPT fixture and pending-decision recovery

A **lab-only replacement** of `Anvil.Interop.Agent.Propose` returned four fixed, manually authored proposals: `DOORBELL → VISUAL`, `LAUNDRY → HAPTIC`, `SMOKE → VISUAL`, and `BABY_CRY → REVIEW`. This fixture lived **outside the Git repository**, under `/home/commander/lab/iris-anvil-chatgpt-fixture-20261016/src/`. It did **not** call OpenAI, IRIS `%AI.Agent.Chat`, or a network endpoint. The Git repository retains the genuine AI Hub provider implementation.

The build-154 IRIS interoperability production processed all four fixture events through the File Inbound Service, Router, deterministic Policy and local Delivery Operation. It persisted **4 receipts, 4 outbox entries and 4 queue entries**, all `QUEUED`. Independent policy forced `SMOKE` from proposed `VISUAL` to `BOTH`, and `BABY_CRY` from `REVIEW` to `BOTH`. A normal replay returned the existing original receipt even when the lab-only provider's available proposal changed.

The original router could not recover if delivery was queued but its receipt was absent: a manually created orphan (receipt deleted in the disposable lab while outbox remained) followed by a changed proposal produced `BLOCKED / Conflicting event-id replay`. The revised Router writes `^Anvil.Interop.Pending(eventId)` with the input digest, proposal and policy route **before** sending to the delivery operation. On replay, it validates that pending decision against the same input/policy, resends the **original route**, and only removes the pending record after a receipt is stored. An outbox without a pending journal, or a mismatching event payload, fails closed for reconciliation.

In an isolated native build-154 test of the revised router, a controlled simulated interruption (restoring pending from an original receipt and removing only that receipt) recovered the **exact original receipt digest and proposal** despite an altered lab fixture. The original `VISUAL` queue/outbox remained; no `HAPTIC` queue was created; `Pending` was cleared. Further tests confirmed that an orphan with no journal and a same-ID/different-payload replay are `BLOCKED`.

A **separate clean container** with the *unchanged, real* `Anvil.Interop.Agent` and the revised Router compiled **9/9** classes, passed **8/8** native policy checks, started the production, and rejected a synthetic doorbell event without API credentials, leaving receipt, pending and outbox empty. The fixture was never copied into the GitHub PR.

**Limits:** These are local, manually orchestrated state-interruption tests; they do not establish actual process-kill/power-loss atomicity, IRIS transaction guarantees, provider liveness, or signed tamper-evident receipts. A successful decision made by a live API-backed AI Hub agent remains unverified. Preserve the private lab evidence at `/home/commander/lab/iris-anvil-chatgpt-fixture-20261016/evidence/`.

## October 17: real AI Hub Chat transport with a local protocol fixture

The native AI Hub build 154 `%AI.Agent.Chat()` method was exercised against a **local OpenAI-compatible HTTP test server**, not a language model. A real AI Hub agent created a session, POSTed to `/v1/chat/completions`, parsed the synthetic `VISUAL` response and retained a two-message session. The receiving server independently logged the HTTP request, model name and two-message request count. No provider credentials, production endpoints, or internet access were involved.

For reproducible provider selection, the repository now supports **optional** `AI_HUB_OPENAI_BASE_URL`. When unset, AI Hub retains its normal OpenAI provider endpoint. When set, the value must use `https://` or the IRIS container's `http://127.0.0.1:` loopback and end in `/` (build 154 appends API paths relative to this URL). `OPENAI_API_KEY` remains required, including when the test endpoint ignores the key; a **disposable dummy key** is sufficient for a local test endpoint. Never direct a genuine API key to a test service or untrusted endpoint. Local loopback means *inside the IRIS container/network namespace*, not the Docker host.

An additional isolated production run, using the **actual repository's `Anvil.Interop.Agent`** and the optional endpoint setting, compiled 9/9 classes, passed 8/8 ObjectScript policy cases, started the interoperability production, and routed four synthetic events through native `agent.Chat()` HTTP requests into the actual IRIS queue/outbox/receipt path. It produced **4 queued operations and 4 receipts**. The policy independently upgraded `SMOKE VISUAL → BOTH` and `BABY_CRY REVIEW → BOTH`. The mock server independently recorded four HTTP requests. These are **protocol fixture responses**, not model-generated decisions.

Negative tests against the real Agent returned `UNAVAILABLE` when: an external cleartext HTTP base URL was configured, the required trailing slash was missing, the key was unset, or an actual HTTP response contained a disallowed token (`NOT_A_VALID_ROUTE`). The last case was tested against a second local protocol stub and its HTTP request was independently recorded.

Private runtime transcript and protocol-observation files: `/home/commander/lab/iris-aihub-chat-transport-20261016/evidence/` on Butcher. The local test server and synthetic keys are deliberately excluded from this public repository. **Still unverified:** a genuine LLM-generated response through a configured provider, a real process kill/power loss recovery, and independently signed assurance.

## October 17: authenticated Grok → native AI Hub Chat → IRIS receipt

The actual Grok Build CLI 1.0.50 on Butcher successfully authenticated through
the operator's official xAI device login. A tool-disabled, no-web, one-turn
`grok --single ... --output-format json` invocation returned a genuine model
response; its `modelUsage` identified `grok-4.7-build` for that direct
test. The live Grok bridge then executed another successful CLI invocation
for a synthetic `DOORBELL` alert. The bridge accepted the canonical
model-generated token `BOTH` and logged the SHA-256 of CLI JSON stdout.

Using **the actual repository's AI Hub Agent and Router classes**, the
isolated IRIS **2026.3.0AI.154.0** container ran with `--network none`
and no published ports. `AI_HUB_OPENAI_BASE_URL` pointed to a container
loopback proxy connected to the host's private Unix socket. The dummy
`OPENAI_API_KEY` value was a local compatibility placeholder; **Grok
authentication remained on the host**. The actual `%AI.Agent.Chat()`
received the OpenAI-compatible bridge response, the independent
`Anvil.Interop.Policy` governed it and `Anvil.Interop.Deliver` queued it.

**Verified outcomes:**
- 9/9 native ObjectScript classes compiled; 8/8 deterministic policy assertions passed
- `Anvil.Interop.Production` started, File Inbound Adapter consumed the synthetic event
- `DOORBELL` proposed `BOTH`, governed to `BOTH`, persisted as `QUEUED`
- `^Anvil.Interop.Receipts`, `^Anvil.Interop.Queue`, `^Anvil.Interop.Outbox` and `Anvil.Interop.Result` all contained the event
- Receipt digest: `J/mqzaMgi76G2L7RI5N8gH3uWtZ+9uqVXM9QDgqaSks=`
- Identical-payload replay returned the **same digest** with `Idempotent replay; no second agent call or delivery`
- The private bridge's successful Grok invocation count remained **1** before and after replay

Private proof directory: `/home/commander/lab/iris-grok-live-20261017/`,
including compiler, policy, production startup, bridge log, initial and
replay result records, source/identity manifest and checksums.

This **closes the genuine-model integration demonstration gap**, but does not
establish external notification delivery, general model safety, IRIS process
kill/power-loss atomicity, or an externally signed WindAnvil Assurance Record.
The Grok bridge is optional, not the default OpenAI provider implementation.
See [the repeatable bridge runbook](tools/grok/README.md).
