# IRIS Anvil

IRIS Anvil is a proof-first management cockpit for InterSystems IRIS.

Administrative work is modeled as a deterministic reactor:

**Validate → Resolve → Plan → Execute → Verify → Receipt**

Every proposed change gets a canonical SHA-256 digest. Execution is restricted to an explicit allowlist, verification re-derives the proposal digest, and successful runs seal a separate execution receipt. Proposal commands support idempotency keys, and repeat execution returns the original sealed receipt rather than applying the change twice. Verified evidence can be mirrored into Apache Sling / Jackrabbit Oak.

The first real management cartridge is `DEPLOY_WEB_APP`. It is deliberately constrained to `/anvil-demo`, `NameSpace=USER`, `DispatchClass=Anvil.REST`, and `Enabled=1`. The browser authenticates through the official IRIS 2026.2 SysAdmin API at `POST /api/admin/login`, performs the change with `PUT /api/admin/v2/web-app`, and reads it back with `GET /api/admin/v2/web-app`. Anvil then independently rereads the application through ObjectScript, verifies the postconditions, and binds the observed state into the execution receipt.

Management is split into two surfaces. `/anvil/api` is the unauthenticated read/program feed. `/anvil/admin` uses IRIS password authentication and is the producer/mutation surface; the operator must authenticate with an IRIS account authorized for `%Admin_Secure:USE`. The browser asks for those credentials only when a reactor run is requested and retains them only in memory.

## Stack

- **InterSystems IRIS 2026.2** — official `/api/admin` SysAdmin API, authoritative runtime, ObjectScript verifier, ledger, receipt boundary
- **Apache Sling 14** — resource-oriented evidence plane
- **Apache Jackrabbit Oak** — persistent repository behind Sling
- **Apache ECharts 6** — vendored visualization runtime for the Change Reactor cockpit
- **Python standard library** — optional server-side IRIS → Oak receipt mirror helper

The browser never receives Sling credentials.

The cockpit also includes a read-only operational inventory using the official `GET /api/admin/info`, `GET /api/admin/v2/processes`, and `GET /api/admin/v2/tasks` endpoints. This adds authenticated authority discovery, operating-system/process visibility, and task-management visibility without granting the observation control authority to mutate, suspend, terminate, or run anything.

## Safety model

The current demo allowlists only `DEPLOY_WEB_APP` for the exact target `/anvil-demo`. Anything else is rejected by the execution endpoint. The official SysAdmin API performs the mutation; Anvil will seal a receipt only after both the SysAdmin API readback and its independent ObjectScript readback match the declared state. The proposal digest is independent from the execution receipt so both intent and execution can be checked.

The contest container grants unauthenticated CSP requests the built-in `%DB_USER` role so the public demo can execute the REST class in the USER namespace. This is intentionally scoped to the dedicated demo container and should not be copied into a shared production IRIS instance.

## Run

Start the two runtimes:

```bash
docker compose -f docker-compose.anvil.yml up -d
```

Bootstrap the IRIS class and web applications:

```bash
./scripts/bootstrap.sh
```

Open the cockpit:

```text
http://localhost:52773/anvil/index.html
```

Sling runs on host port `8082`. Its Oak repository is persisted by the named volume mounted at `/opt/sling/launcher`.

## API proof

Load the six-phase deterministic plan:

```bash
curl http://localhost:52773/anvil/api/reactor/plan
```

Create a proposal:

```bash
curl -u 'operator:password' -X POST \
  -H 'Content-Type: application/json' \
  --data '{"action":"DEPLOY_WEB_APP","target":"/anvil-demo","payload":"NameSpace=USER|DispatchClass=Anvil.REST|Enabled=1"}' \
  http://localhost:52773/anvil/admin/proposals
```

The cockpit then authenticates at `/api/admin/login`, executes the declared change using the official `PUT /api/admin/v2/web-app`, and confirms it using `GET /api/admin/v2/web-app`. Seal the returned proposal id after that readback:

```bash
curl -u 'operator:password' -X POST http://localhost:52773/anvil/admin/proposals/ID/execute
```

Verify it:

```bash
curl -u 'operator:password' http://localhost:52773/anvil/admin/proposals/ID/verify
```

A successful verification returns `"verified":1` plus the proposal digest and sealed execution receipt.

## Oak mirror

`scripts/sync_oak.py` reads the IRIS ledger and mirrors only receipts that pass the current verifier. Credentials are supplied at runtime:

```bash
SLING_USER=... SLING_PASS=... python3 scripts/sync_oak.py
```

The helper writes `web/oak-status.json` after a successful sync. The cockpit uses that credential-free status file to distinguish `IRIS ONLINE` from `IRIS + OAK`.

Oak evidence is stored under:

```text
/content/iris-anvil/receipts/<id>
```

Each mirrored execution contains the IRIS state, action, target, proposal digest, execution receipt, verification flag, and `source=IRIS`.

## Reproducibility

- ECharts is vendored at `web/echarts.min.js`; the cockpit has no CDN dependency.
- `scripts/bootstrap.sh` is idempotent.
- `docker-compose.anvil.yml` uses the exact IRIS and Sling images exercised by the demo.
- IRIS and Sling communicate over the dedicated `iris-anvil-net` Docker network.
- Oak persists in a named Docker volume.
- The fast `IRIS Anvil contract` workflow pins the required official SysAdmin endpoints, bearer-token boundary, idempotency key, allowlist, independent readback, and receipt construction on every push and pull request.

## Current vertical slice

The implemented path is intentionally narrow but real:

1. Load a deterministic six-phase management plan.
2. Authenticate to the official IRIS SysAdmin API and propose a bounded administrative change.
3. Canonicalize and SHA-256 hash the intent in IRIS.
4. Execute the allowlisted operation through `PUT /api/admin/v2/web-app`.
5. Read back through `GET /api/admin/v2/web-app`, then independently re-derive and verify state and proposal digest in ObjectScript.
6. Seal an execution receipt.
7. Mirror verified evidence into Sling/Oak.
8. Render the live state in the ECharts Change Reactor cockpit.

The **SCAN IRIS** control authenticates through the same in-memory SysAdmin session and reports current live-process and scheduled-task counts. It performs no mutation and stores no credentials.
