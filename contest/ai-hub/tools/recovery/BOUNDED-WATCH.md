# Opt-in, bounded recovery watch — IRIS AI Hub 154

**Status:** isolated **synthetic** native test; no unattended daemon installed. This feature is stacked on the [human-gated one-shot replay](OPERATOR-REPLAY.md) and does not call Grok or another model.

## Purpose and scope

The opt-in `watch.py` polls **one explicitly chosen event ID** a fixed number of times. It defaults to read-only. `--arm` allows **one** claim-and-stage attempt, through the existing `operator.py`, only if the following evidence agrees:

- `Anvil.Interop.Production` is running, verified by native `Ens.Director.IsProductionRunning()`
- `RecoveryReplay.Inspect()` has validated the original pending decision, independent deterministic policy, input digest, queue and outbox
- The local queue timestamp is at least `--min-age` seconds old (**minimum 60 seconds; default 120**)
- A corresponding **failed** (`Status = 5`) `Anvil.Interop.Alert` is present in the most recent 250 IRIS message headers
- The event has no existing receipt or durable `^Anvil.Interop.RecoveryClaim`

The watch does not discover unknown events, restart IRIS or recover any real external notification. It **never** force-unlocks a stuck event, changes a prior agent proposal, or retries automatically after an attempted claim fails. It is a bounded foreground operator command, not a background service.

### Operator usage

The current host must be explicitly authorized for this disposable IRIS demo, with the failed worker terminated and `Anvil.Interop.Production` independently restarted/verified. Inspect the event ID and relevant failed IRIS message in the Management Portal or the read-only RecoveryAudit before arming.

```bash
# Read-only by default. 12 polls max; each poll separated by 10 seconds.
python3 contest/ai-hub/tools/recovery/watch.py \
  --container YOUR_ISOLATED_IRIS --event-id SYNTHETIC_EVENT_ID

# A specifically authorized, bounded replay after verifying production recovery.
python3 contest/ai-hub/tools/recovery/watch.py \
  --container YOUR_ISOLATED_IRIS --event-id SYNTHETIC_EVENT_ID \
  --min-age 120 --poll-seconds 10 --max-cycles 12 \
  --arm --ack-production-restarted
```

On eligibility, the **existing** one-shot operator re-verifies the state under the IRIS event lock, writes the durable claim, then stages a single original JSON payload through the File Inbound Adapter. The CLI's `WATCH_STAGED_ONCE` means **a replay file was staged**, not that a receipt was completed. Verify the receipt and absence of pending state afterwards through `RecoveryAudit`.

If the watch reports `Event lock busy` or `Expected IRIS production is not running`, stop. Do not manually clear locks or erase recovery claims. Reconcile with IRIS system status and the original failed message before any new attempt. A claim left behind after staging failure deliberately blocks a second automatic attempt.

## Executed native test — October 17, 2026

A private lab used InterSystems IRIS `2026.3.0AI.154.0`, `--network none`, no published ports, and a lab-only deterministic proposal; it **did not call Grok**. The same nine production classes compiled, and a fault-injection-only Router copy paused after a synthetic `DOORBELL` delivery acknowledgement. The targeted IRIS worker (PID **732**) was terminated by **real SIGKILL**. Pending, local outbox and VISUAL queue survived; receipt was absent.

The first watch correctly refused to stage because the queue was younger than 60 seconds. `Ens.MessageHeader` later showed the original inbound `Anvil.Interop.Alert` at status **5**. After a **production restart**, the watch found the failed message and old enough queue, but the one-shot operator refused the claim because the event lock still existed. A separate IRIS session confirmed `LOCK_ACQUIRED=0`. The watch **did not force-unlock**.

Only a **full restart of that disposable IRIS container** cleared the lock (`LOCK_ACQUIRED=1` afterwards), preserving the pending/queue/outbox. The container's production had not auto-started; an initial armed watch version staged the one replay file while production was down. This exposed a **real missing production-health guard**, now added to `RecoveryWatch.Probe` and to the existing `RecoveryReplay.Claim`. The updated read-only native watch was tested with production stopped and returned `BLOCKED / Expected IRIS production is not running`; `Ens.Director.IsProductionRunning` returned false.

After manually starting `Anvil.Interop.Production`, the **already-staged** one-shot replay was consumed. IRIS persisted receipt `J0vX1ZoYkujwTZTsoO8eMjm5npXcV6FiBx2G75WFyjg=`, retained one VISUAL queue/outbox and the durable claim, and cleared Pending. A subsequent watch refused the completed event. **The updated claim production-health check has only been structurally tested, not yet separately compiled in IRIS after that final edit; obtain that native proof before considering this ready for operational use.**

### Boundaries and follow-up

This establishes real worker-kill eligibility detection, fail-closed behavior under age/lock/offline-production conditions, and one-shot local replay completion **with operator interventions**. It does **not** establish full unattended crash recovery: manual full container restart and production restart were needed, event IDs must be preselected, retries are disabled after a claim, there is no auto-discovery or timer service, and no external notification, power-loss guarantee, or signed WindAnvil assurance is claimed.

The private logs and evidence are on Butcher at `/home/commander/lab/iris-supervisor-native-20261017/`. [Issue #5](https://github.com/mcc0nnell/iris-anvil/issues/5) remains open for production-grade supervision, failed-message reconciliation, and safe recovery of held locks through supported vendor controls.
