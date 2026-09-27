# IRIS Anvil release notes

## 2026-09-27 — Verified IRIS 2026.2 reactor

This release turns the contest vertical slice into a reproducible, live-tested
IRIS 2026.2 workflow. The supported mutation remains deliberately narrow:
`DEPLOY_WEB_APP` may change only `/anvil-demo` to the declared USER namespace,
`Anvil.REST` dispatch class, and enabled state.

### Added

- Live IRIS 2026.2 integration coverage in GitHub Actions.
- `scripts/smoke_iris.py`, which exercises SysAdmin login, web-app PUT and GET,
  independent ObjectScript verification, sealed receipt replay, and read-only
  process and scheduled-task inventory.
- `scripts/create_demo_operator.py` for a randomly credentialed operator in a
  fresh, disposable local demo container.
- Authenticated read-only observation through `/api/admin/info`,
  `/api/admin/v2/processes`, and `/api/admin/v2/tasks`.
- A contract gate covering the official SysAdmin endpoints, bearer boundary,
  allowlist, receipt construction, and both REST bootstrap surfaces.

### Fixed

- Parse the IRIS 2026.2 `/api/admin/login` access token from the actual
  top-level response field.
- Compile both `Anvil.Public` and `Anvil.REST` during bootstrap; previously a
  fresh 2026.2 container could return 404 from the public API.
- Wait for the IRIS instance to report `running` before bootstrapping, avoiding
  a container-start race.
- Treat an independent receipt-verification mismatch as a visible reactor
  failure.

### Hardened

- Reject proposals whose action, target, or complete payload falls outside the
  demo allowlist before they enter the ledger.
- Refuse execution when the stored proposal digest or payload no longer matches
  the canonical declared intent.
- Verify the sealed receipt again from current IRIS state; a merely planned
  proposal can no longer report as verified.
- Bind IRIS, superserver, and Sling demo ports to localhost by default.
- Pin the contest runtime to `intersystems/iris-community:2026.2`.

### Verified

The live smoke path passed on IRIS Community 2026.2 (Build 221U):

1. Reject an out-of-allowlist proposal.
2. Confirm that a planned proposal does not verify as executed.
3. Authenticate through `POST /api/admin/login`.
4. Apply the bounded change through `PUT /api/admin/v2/web-app`.
5. Read it back through `GET /api/admin/v2/web-app`.
6. Independently reread the application in ObjectScript and seal a receipt.
7. Replay execution without producing a different receipt.
8. Read live process and scheduled-task inventories.

### Upgrade notes

- Pull the new IRIS 2026.2 image and recreate the demo container before
  bootstrapping.
- The generated `AnvilDemo` account holds `%All` and is intended only for the
  dedicated local demo container. Use an appropriately authorized operator in
  any shared or production environment.
- Existing external clients must now connect through localhost unless the
  Compose port bindings are deliberately changed.

### Current scope

- The only mutation cartridge is the bounded `/anvil-demo` web-app operation.
- Process and task functions are observation-only.
- Sling/Oak mirroring remains optional and is not part of the mutation trust
  boundary.
