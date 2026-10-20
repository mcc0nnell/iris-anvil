# Contest golden path — genuine AI Hub 154 agent, independent gate, one receipt

**Scope:** one reproducible, synthetic, operator-run native InterSystems interoperability demonstration. This is not an alert service, recovery daemon, externally signed attestation, or production assurance claim.

## Exact environment

- InterSystems AI Hub Community Docker image **2026.3.0AI.154.0**, installed locally from the gated EAP package; **do not redistribute the image**
- Docker daemon and Python 3.12+ on an authorized Linux host
- An already authenticated **Grok Build CLI** at ~/.local/bin/grok (host network access may be necessary)
- No OpenAI key, EAP credentials, or Grok session files committed or passed into IRIS; a dummy API key is used only for native provider setup

The host's genuine Grok CLI is invoked through an explicitly tool-disabled,
one-turn bridge. The disposable IRIS container has **no network**, no published
ports, and no real notification connector; it reaches the host bridge only
over a private Unix socket through a container-local HTTP proxy.

From a checkout of the PR #3 based golden-path branch:

    cd /path/to/iris-anvil
    python3 contest/ai-hub/scripts/golden-path.py \
      --lab-dir "$HOME/lab/iris-contest-golden-$(date +%Y%m%d-%H%M%S)"

Choose a **new** lab path outside Git. The script refuses to reuse a directory.
It creates private evidence, starts a disposable container and bridge, validates
the proof, and removes both on success or failure. It does not stop or alter
other IRIS containers or restart any production. Input/archive directories are
writable by the IRIS container user within a private host-operated lab folder.

## What the single execution must prove

1. Compile **9 production ObjectScript classes** on native AI Hub 154.
   Fail on compiler errors, missing markers or incomplete counts.
2. Execute **8 native deterministic policy cases**. In particular
   SMOKE + VISUAL => BOTH and BABY_CRY + HAPTIC => BOTH prove the policy
   can override *hypothetical* weaker proposals, not that the model made them.
3. Start Anvil.Interop.Production, submit one synthetic DOORBELL input, and
   invoke an actual native %AI.Agent.Chat() call routed through the authenticated
   host Grok CLI. The bridge must report **one successful model decision**.
4. Read native Receipt, Queue, Outbox, Pending and Ens.MessageHeader for the
   selected event. Check allowlisted proposal, independent Policy.Resolve(),
   recomputed hashes, pending cleared and exactly one local queue entry.
5. Submit an **identical event ID and payload** in a second JSON file.
   Require at least two corresponding **native inbound Alert headers**,
   unchanged persisted decision/route/receipt/outbox/queue, and **zero**
   additional model calls. The IRIS adapter may retain original input files:
   file movement or presence is *not* replay-completion evidence.
6. Report **PASS only after all gates pass**. A provider failure, timeout,
   malformed transcript, missing header, changed receipt, duplicate inference
   or absent IRIS state remains INCOMPLETE.

This is the attribution boundary: **the model proposes**, **native policy
authorizes**, **native interoperability persists**, and **replay does not
re-infer**. The DOORBELL result may vary. Critical signal overrides are proven
in separate native policy cases within the same run.

## Evidence and boundaries

The private evidence directory contains native compile/policy/start logs,
a bridge log showing the canonical decision and hashed model output (no
credentials), native first/replay record snapshots, and a manifest with image
digest, source commit, proposal, policy route, receipt, call count, and SHA-256
for every other evidence file. Raw logs remain private pending review.

Never commit provider credentials, gated EAP images, proprietary Grok logs or
runtime tokens.

**Not proven:** unattended recovery after SIGKILL; a native positive replay
through the final experimental recovery watcher; SMS, lights, haptics or
external notifications; power-loss durability; external exactly-once delivery;
signed WindAnvil assurance. The distinct worker-kill and operator-recovery
evidence belongs in PRs #3, #6, #7 and issue #5, and is not a prerequisite
for this golden path.

The final Open Exchange submission still requires English setup instructions,
a public repository, and an accessible captioned/silent demo of one successful
run with a redacted IRIS trace. This runner does **not** submit a contest entry.
