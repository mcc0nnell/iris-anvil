# Bounded operator replay for interrupted IRIS Anvil messages

**Status:** tested on InterSystems AI Hub `2026.3.0AI.154.0` in an isolated lab. **Operator-triggered**, not unattended worker supervision or automated retry. Does not invoke Grok or another model.

## Why

A real IRIS worker `SIGKILL` left `^Anvil.Interop.Pending`, the local Outbox and route Queue intact, but no Receipt. The initial replay was archived without recovering. After the interoperability production was restarted and a new identical input was submitted, the original Router reconstructed the receipt (see [CRASH-RECOVERY.md](../../CRASH-RECOVERY.md), issue #5).

This optional tool performs the **guarded input re-submission** after an operator has confirmed the failed worker/process is no longer running and restarted the production. It never rewrites the Router, edits the original decision, or bypasses the deterministic policy.

## Safety boundary

The optional `RecoveryReplay.cls` is loaded separately; the nine production classes stay unchanged. It inspects exactly one explicitly supplied event ID. Eligible state requires:

- Valid bounded event ID and **no existing receipt or previous recovery claim**
- Existing Pending with saved input digest, proposal and route
- Matching saved local Queue and Outbox, with exactly one allowed route
- Recalculated **input and outbox SHA-256 hashes** matching the saved records
- Route re-evaluated against current independent `Anvil.Interop.Policy`

The `--apply` mode requires `--ack-restarted` and the exact base64 input digest copied from a prior read-only plan. Under IRIS's per-event lock it re-verifies the candidate, writes a **durable one-shot `^Anvil.Interop.RecoveryClaim(eventId)`**, and only then stages a JSON replay through the existing File Inbound Adapter. Input staging uses an atomic exclusive hard link to a `*.json` file, with a private `.part` source, rather than overwriting an existing file. Only the **original signal/detail** can be staged; no new model proposal is requested.

A failed stage after a successful claim leaves the claim in place. It **does not silently clear/retry**. A human must inspect and reconcile that case. Receipt presence means future `--apply` is rejected. The replayed message still traverses the normal source Router, policy and Business Operation.

## Runbook — isolated or explicitly authorized synthetic data

Do not operate while the worker is still processing a request. Verify the original production is healthy and restart/reconcile failed Ensemble messages as appropriate **before** staging. The CLI cannot prove a restart actually happened; `--ack-restarted` is an explicit operator attestation.

From the repository root, on the authorized Docker host:

```bash
python3 contest/ai-hub/tools/recovery/operator.py \
  --container YOUR_ISOLATED_IRIS --event-id YOUR_SYNTHETIC_EVENT_ID

# After independently checking the plan and restarting the test production:
python3 contest/ai-hub/tools/recovery/operator.py \
  --container YOUR_ISOLATED_IRIS \
  --event-id YOUR_SYNTHETIC_EVENT_ID \
  --apply --ack-restarted \
  --expected-digest EXACT_BASE64_DIGEST_FROM_DRY_RUN

# Then verify the stored receipt and the single expected queue entry with
# the read-only recovery audit:
docker cp contest/ai-hub/tools/recovery/RecoveryAudit.cls \
  YOUR_ISOLATED_IRIS:/tmp/AnvilRecoveryAudit.cls
docker exec -i YOUR_ISOLATED_IRIS iris session iris -U USER \
  < contest/ai-hub/scripts/recovery-audit.scr
```

Only the operator tool is copied to `/tmp` inside IRIS. It requires a mounted `/opt/iris-anvil/inbox` owned by the IRIS process. No OpenAI/xAI keys are sent to the container by the recovery tool, and no model endpoint is needed for pending decisions.

## Native tests executed on Butcher (Oct 17, 2026)

The source `Router`, `Policy` and nine production classes compiled unchanged against build 154, with a **lab-only synthetic agent**. After one successful local DOORBELL / VISUAL delivery, a disposable lab created the precise persisted *post-delivery/pre-receipt* state by retaining its Pending, Queue and Outbox and deleting only the receipt. This operator-tool test **did not SIGKILL a worker**: the separate previous [SIGKILL evidence](../../CRASH-RECOVERY.md) established that state occurs after a real process kill.

- Dry-run returned `READY`, correct route `VISUAL` and matching stored input fingerprint
- Wrong supplied digest rejected **before** claiming or staging
- Correct explicit claim produced exactly one replay JSON file
- Native IRIS consumed it, reconstructed the **identical original receipt** `OaymPztIWH3dekyJgbWkSk+63l8TqEqhihhox5T9DmM=`, and retained the original local Queue and Outbox
- Second `--apply` was rejected as `COMPLETED`
- Saved critical-signal proposal forced into an inconsistent route rejected
- Deliberate incorrect outbox digest rejected; synthetic negative globals cleaned afterward

Private raw evidence (including the disposable source manifest) resides at `/home/commander/lab/iris-supervised-replay-20261017/`. Unit tests for marker parsing, ID/digest validation, exclusive atomic staging, and no re-inference are in `tests/test_supervised_replay.py`.

**Not established:** fully automatic recovery on a worker exit, IRIS process restart orchestration, power-loss durability, external alert delivery, or a signed WindAnvil attestation. This is **operator-assisted, one-shot and fail-closed**, deliberately narrower than issue #5's eventual unattended supervision goal. Pending and claim globals do not have an automated garbage collector or reset operation.
