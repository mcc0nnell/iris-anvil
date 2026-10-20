# IRIS Anvil — evidence-backed contest demonstration

**Native execution:** October 19, 2026 (US Eastern) / October 20, 2026 (UTC).
This describes a real executed test, not a recording of a production alert.

Execution came from commit deef4e485d5338bb403726f42ed960a8c8cf5dec
on Butcher, using InterSystems AI Hub Community 2026.3.0AI.154.0 in a
disposable container with networking disabled, no published ports, and a
real Grok Build CLI on the host behind a private Unix socket.

## Actual synthetic DOORBELL result

| Observation | Verified result |
| --- | --- |
| Native ObjectScript compiled | 9 / 9 classes |
| Native independent policy tests | 8 / 8 cases |
| Genuine model invocation attempts | 1 |
| Successful model decisions | 1 |
| Model's proposed route | BOTH |
| Independent policy-authorized route | BOTH |
| Native IRIS inbound Alert headers | 2 |
| Failed inbound Alert headers | 0 |
| Local queue entries for the event | 1 |
| Pending decision after completion | Cleared |
| Added model calls after identical replay | 0 |
| Recomputed native receipt | SMv1V8E3vluXqYufFYKCJvzY2Bvp0CUCp+QauDCZotU= |

An actual model generated the DOORBELL proposal; a different run can
produce another allowlisted route. The critical SMOKE and BABY_CRY
override examples are separate deterministic ObjectScript policy cases,
not evidence that a live model produced weaker proposals.

Both input files used the same event ID and payload. Two native
Ens.MessageHeader records attribute both requests to IRIS, while the
persisted proposal, route, outbox, queue and receipt stayed unchanged.
The host bridge recorded one and only one model invocation attempt.

## Evidence and reproducibility

Private native compilation, policy, runtime, model bridge and read-only
state logs, along with the SHA-256 evidence manifest, remain on Butcher:

    /home/commander/lab/iris-contest-golden-20261019-final/evidence/

The Git repository contains no credentials, private Grok session logs,
or gated EAP container image. This summary is not an external or signed
attestation. To reproduce, consult [GOLDEN-PATH.md](GOLDEN-PATH.md)
and [JUDGE-QUICKSTART.md](JUDGE-QUICKSTART.md).

The local queue is not real SMS, lights, or a haptic device. Crash
recovery and actual worker SIGKILL are separately documented in
[CRASH-RECOVERY.md](CRASH-RECOVERY.md); unattended replay, external
exactly-once semantics and power-loss durability remain unproven.

## Accessible demo recording outline

1. Show the synthetic household DOORBELL event and its accessibility use.
2. Show the exact AI Hub build and the nine natively compiled classes.
3. Distinguish the genuine model proposal from the independent eight-case
   native ObjectScript policy results.
4. Show the persisted native receipt, outbox and single local queue entry.
5. Show two IRIS inbound messages and zero new model calls on identical replay.
6. Clearly state the operational limitations and the separate recovery work.

Use open captions (always-visible text), high contrast and avoid
audio-only explanations. This outline is for a **future demonstration
recording**, not a claim that a recording already exists.
