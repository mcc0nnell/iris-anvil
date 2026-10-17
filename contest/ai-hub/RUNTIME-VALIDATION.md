# Build 154: controlled execution and evidence capture

**This document is an operator runbook, not a claim that the IRIS Anvil production has already compiled or run.** Use only an authorized, isolated IRIS AI Hub **2026.3.0AI.154.0** container. Never distribute the proprietary EAP image or check in provider keys.

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

Current remote chat execution status (October 16): runtime boot and source mount confirmed; class compilation was denied by the remote command service before IRIS could process it. No compilation or production-start evidence has been established from that attempt.
