# IRIS Anvil — contest judge's quickstart

**A synthetic accessibility-routing workflow using InterSystems AI Hub 154.**
The AI agent proposes a route; an independent IRIS ObjectScript policy can
override or block it; an IRIS interoperability production persists a local
demo queue, outbox and receipt. **No physical alert or external notification.**

This project supports two distinct, documented demonstrations. The **portable
Docker Compose path** below is intended for reviewers with their own OpenAI
API key. The **verified Grok golden path** uses a separately authenticated
host CLI and a network-isolated disposable IRIS instance. Their provider
configuration and observed evidence must not be conflated.

## 1. Install the contest's exact AI Hub build

Obtain the official AI Hub Community EAP image, build
`2026.3.0AI.154.0`, from the InterSystems EAP portal:
https://evaluation.intersystems.com/Eval/early-access/AIHub

Do not use build 162, and do not publicly redistribute the EAP image.
On x86-64 Linux, after downloading the gated archive:

```bash
docker image load -i /path/to/iris-community-2026.3.0AI.154.0-docker.tar.gz
docker images
# If Docker loaded the upstream internal name, tag it locally:
docker tag docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2026.3.0AI.154.0 \
  iris-ai-hub-community:2026.3.0AI.154.0
```

The project uses a local-only image tag and Compose `pull_policy: never`.
Your host needs Docker Compose v2 or later, Python 3, Bash and `setfacl`
(the `acl` package on Ubuntu/Debian). Reserve localhost ports 52783 and 1973.
Nothing needs to be pushed to a container registry.

## 2. Docker Compose / standard OpenAI path

From a fresh clone of this repository:

```bash
cd contest/ai-hub
export OPENAI_API_KEY=YOUR_OWN_API_KEY   # never commit this
./scripts/setup.sh
```

The setup calls `docker compose up -d` using `compose.yml`, waits for IRIS
health on **cold starts**, compiles the nine native ObjectScript production
classes and starts `Anvil.Interop.Production`. A second invocation is safe:
it reports an existing production without recompiling active classes. To
load source updates, stop/rebuild the disposable instance intentionally;
setup never silently hot-replaces a running production.

Inspect the native production via the host-local IRIS Management Portal:
http://127.0.0.1:52783/csp/sys/UtilHome.csp

Run the sample synthetic event:

```bash
./scripts/demo.sh
# Copy the printed demo-... event_id, e.g. demo-12345-67890.
docker exec -e ANVIL_GOLDEN_EVENT_ID=YOUR_PRINTED_EVENT_ID \
  -i iris-anvil-aihub iris session iris -U USER < scripts/golden-state.scr
```

Run the read-only query again after the File Inbound Adapter processes the
message (its interval is 2 seconds). Look for `status: COMPLETE`,
`pending_cleared: 1`, `queue_count: 1`, matching policy/receipt/outbox
checks, and an `inbound_header_count` of at least 1. Output begins with
`ANVIL_GOLDEN_STATE|`. A genuine provider call may take longer; never
interpret a pending state as a success.

The Compose route uses the ordinary OpenAI-compatible provider and
`gpt-4o-mini` as configured in `Anvil.Interop.Agent`; this path requires
a valid key and may incur provider charges. When no key is set, the workflow
**deliberately blocks** rather than simulating an AI decision; a missing
receipt is the expected fail-closed outcome in that case. Do not paste keys
into screenshots or commit `.env` files.

Shut down only this optional Compose demonstration:

```bash
docker compose down
```

## 3. One-command evidence-backed Grok golden path

For an authenticated Grok Build CLI on an authorized Linux host, use
[GOLDEN-PATH.md](GOLDEN-PATH.md) and its
`python3 scripts/golden-path.py --lab-dir /new/private/path` command.

It starts an isolated Docker instance with **no network and no published
ports**, invokes a genuine Grok model through the host's private Unix socket,
runs **9 native compile gates and 8 policy cases**, and proves two native
inbound Alert messages for an identical event with **one total model call**
and the same persisted receipt. Credentials never enter the container.

The executed October 19/20, 2026 proof used commit `deef4e4`, proposal
`BOTH`, governed route `BOTH`, one local queue, and a native receipt.
Private raw logs are deliberately **not** distributed with the repository.
See [DEMO-EVIDENCE.md](DEMO-EVIDENCE.md) for a safe summary and reproducibility
boundaries.

## 4. What the entry proves—and what it does not

The synthetic `SMOKE` and `BABY_CRY` policy cases demonstrate that the
independent ObjectScript policy forces `BOTH` even if an agent proposes a
weaker route; they are **policy tests**, not claims that a live model emitted
the weaker proposals. The genuine Grok `DOORBELL` call is a separate actual
model decision routed through native IRIS.

The queue/outbox/receipt are in-IRIS demonstration records, **not** a
tamper-proof signed assurance record, SMS, real haptic output, or emergency
notification. The real worker SIGKILL evidence and operator-assisted recovery
are separate experiments (PRs #3, #6 and draft #7; issue #5). Unattended
recovery, external exactly-once delivery and power-loss resilience are unproven.

For review, inspect the source classes under `src/Anvil/Interop/`,
`scripts/` for native policy and receipt checks, and the isolated runbook
rather than trusting a video or GitHub CI as independent runtime attestation.
