# Native worker-crash recovery — InterSystems IRIS AI Hub 154

**Evidence date:** October 17, 2026 (UTC). **Scope:** disposable, network-isolated local IRIS lab on Butcher. Not a production availability guarantee.

## Executed test and result

This test goes beyond editing globals to *simulate* a crash: the router's actual IRIS worker OS process was terminated with **SIGKILL**, immediately after the `Anvil.VISUAL` Business Operation acknowledged a queued synthetic event, but **before** the router wrote its final receipt.

A lab-only copy of `Anvil.Interop.Router` inserted a pause at precisely that boundary and published its PID in `^Anvil.Interop.LabCrashJob`. The operator verified the PID corresponded to `irisdb ... StartEnsembleJob^STU`, then killed **only that worker** inside the disposable container. The official source repository and its Grok agent were **not** modified by the fault injection. A lab-only deterministic agent provided the route for this crash test; genuine Grok inference is independently demonstrated in [the Grok bridge runbook](tools/grok/README.md).

| Checkpoint | Pending | Outbox | VISUAL queue | Receipt |
|---|---:|---:|---:|---:|
| After delivery acknowledgment, before kill | Present | Present | Present | Absent |
| After worker SIGKILL (PID 725) | Present | Present | Present | Absent |
| First duplicate file after kill | Present | Present | Present | Absent |
| After controlled production restart and **fresh** duplicate input | Cleared | Present | Present | Present |

An initial replay input was archived without recovering the receipt. After a controlled `Ens.Director.StopProduction()` and `StartProduction("Anvil.Interop.Production")`, a *new replay input* correctly used the previously stored `VISUAL` proposal and existing outbox, reconstructed its receipt, and cleared the pending journal.

Recovered receipt SHA-256 digest (base64):
`rASnZbA4ORPDkYKX9uBvCmE/XH7XssKNqIREBfnl6uU=`

The original and first-replay `Ens.MessageHeader` entries had status `5` after the restart. We must not claim automatic worker recovery, automatic retry or exactly-once delivery. The actual business operation only records a local demo queue, not a real-world visual/haptic notification.

## Read-only operational triage

`tools/recovery/RecoveryAudit.cls` is an **optional operator diagnostic**. It is not part of the automatic production class list or a repair routine. With the checkout's `src/` mounted read-only at `/opt/iris-anvil/src` on an authorized lab IRIS instance:

```bash
docker cp contest/ai-hub/tools/recovery/RecoveryAudit.cls \
  <your-isolated-iris-container>:/tmp/AnvilRecoveryAudit.cls
docker exec -i <your-isolated-iris-container> iris session iris -U USER \
  < contest/ai-hub/scripts/recovery-audit.scr
```

The script compiles the read-only audit class and prints:

- `PENDING_WITH_OUTBOX`: persisted proposal with a queued outbox, receipt not yet present; operator should investigate whether the worker is live before resubmitting
- `PENDING_BEFORE_DELIVERY`: persisted proposal but no outbox, requiring operator triage
- `ORPHAN_OUTBOX`: outbox without pending proposal or receipt; **do not fabricate** an agent proposal to reconcile
- `RECEIPT_WITHOUT_QUEUE`, `RECEIPT_WITHOUT_OUTBOX`, or `PENDING_WITH_RECEIPT`: inconsistent state requiring review
- `COMPLETED`: receipt, matching route queue and outbox are present

The scanner never sends a request, calls a model, deletes globals, or changes queue contents. It is a best-effort **nontransactional snapshot**; concurrent writers can change state during enumeration. Event IDs are included in terminal output and should remain private in real deployments.

Native negative controls created *synthetic only* orphan/pending records. The audit reported `pending=1|orphan=1|broken=0|completed=1` with the expected labels; after cleanup it reported `pending=0|orphan=0|broken=0|completed=1`. The restored source Router compiled successfully and handled the final replay. The test-only paused/router and agent copies remained outside Git.

## Evidence provenance and limitations

Private logs, the seed-and-cleanup negative controls, source digests, and checksums are retained at:

`/home/commander/lab/iris-anvil-sigkill-20261017/`

Executed image: `iris-ai-hub-community:2026.3.0AI.154.0`, `sha256:8fc1e5c64ed790aa263af05089d003a49bba272fb9c714e4823dd868aebff2a6`.

This test **does establish** real SIGKILL of one IRIS interoperability worker and a durable pending/outbox state recovered by the source router after operator restart and explicit replay. It **does not establish** power-loss durability, restartless recovery, background replay automation, end-to-end external notification, externally signed receipts, or long-term uptime. A production-quality implementation needs supervised worker recovery and a safe, auditable reconciliation/replay loop, not silent automatic re-inference.
