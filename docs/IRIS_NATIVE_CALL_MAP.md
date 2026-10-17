# IRIS native call-path research (2026-10-17)

This is an **observation**, not an attestation, vulnerability report, or claim
of source-code visibility. Work used an immutable, locally obtained InterSystems
IRIS Community AI Hub 2026.3.0AI.154.0 image in a private, network-disabled lab.
No proprietary binaries or disassembly are included.

## Confirmed static edges

| Native path | Evidence type |
| --- | --- |
| IrisGlobalSet → gset → gsetjrn | Direct call followed by tail jump |
| gsetjrn → ginsert4k | Direct call to block-insertion helper |
| gsetjrn → journalset | Direct call to logical journal-record helper |
| IrisTCommit → tcommit → journaltran | Direct calls along a commit-related path |
| journaltran → jrncmtsync → jrnsyncblk_options | Direct calls along a journal-sync path |

Local specimen libirisdb.so SHA-256:
0aee0ad5d27a8903d83bfcb8e2fb9c28d496765c8b7b2d9a6f663cb13e6b68f7

**Interpretation:** Native code exposes control-flow connections between
global updates, block storage, logical journaling, and transaction
commit/journal synchronization. Branches are conditional: not every path
runs for each transaction. This does not prove database flush, fsync, WIJ
write timing, crash safety, or runtime order.

IRIS distinguishes logical journaling from the WIJ that protects physical
database consistency:
- https://irisdocs.intersystems.com/irisforhealthlatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCDI_journal
- https://irisdocs.intersystems.com/irisforhealthlatest/csp/docbook/DocBook.UI.Page.cls?KEY=GCDI_wij

## Reproduction

Supply your own lawfully acquired ELF; do not commit it or the full private
trace. Requires GNU nm and objdump. The script **does not run the target**.

    python3 scripts/map_native_calls.py \
      --binary /private/path/to/libirisdb.so \
      --root IrisGlobalSet --root gset --root gsetjrn \
      --root IrisTCommit --root tcommit --root journaltran \
      --root jrncmtsync --output /private/native-map.json

Output records direct edges, instruction addresses, a SHA-256 identity, and
authority NONE. PLT calls may be interposed; indirect calls are unresolved.
Independent dynamic evidence is needed before describing any path as executed.

Synthetic no-vendor-binary test:

    python3 -m unittest discover -s tests -p 'test_native_call_map.py' -v

Detailed analysis and experimental evidence stay in the private lab; the public
repository contains only the repeatable method and bounded conclusions.

## Executed runtime follow-up (October 17, 2026)

**Native executable matters:** The initial static map above was derived from
libirisdb.so. The running IRIS server actually used the separate irisdb
executable, with distinct symbol addresses. Both were obtained from the
same pinned IRIS AI Hub Community build and are retained only in the lab.
The executed server ELF SHA-256 is:
0b99751cdf6528acea33aa366987013ac4b7d557f04e26e33968a1d54410e854.

A disposable IRIS instance (Docker network none, no published ports) ran
a phase-marked synthetic ObjectScript transaction in USER, read the value
back, and removed its test global. The GDB session attached only to that
unique owned worker process and recorded native hit markers and short stacks.

**Observed executable paths:**

- Write: DISPATCH -> Cgset -> gsetjrn -> journalset
- Write-time journal activity: journalset -> journaltran
- Commit: DISPATCH -> Ctcommit -> journaltran

The last edge explains the difference from the static libirisdb.so
IrisTCommit -> tcommit path. The ObjectScript session executed Ctcommit,
not tcommit, at its breakpoint. The jrncmtsync breakpoint was not
hit by the bounded run. No absence of synchronization or durability is
inferred from missing hits.

The verified local record, retained outside GitHub, reports:
- worker PID 1490; normal debugger-observed exit
- PHASE_VERIFIED (transaction level 0, value phase)
- PHASE_CLEAN (test global absent)
- four required native stack relationships verified
- status OBSERVED_EXECUTION_NOT_DURABILITY_PROOF
- authority NONE

**Reproduction:** scripts/iris_native_trace.gdb contains the
read-only breakpoint commands used in the lab. Use only on your own
disposable, explicitly authorized IRIS worker: debugger attachment
pauses the process, may require additional process-tracing privileges,
and should not target production. Record the phase markers and full
GDB session privately; the verifier requires normal exit, matching
worker ID, ordered phase markers, clean data removal, and the exact
required call-stack relationships.

    python3 scripts/verify_native_execution.py \
      --session /private/phase-session.log \
      --debugger /private/phase-gdb.log \
      --runtime-binary /private/irisdb \
      --output /private/native-execution.json

Unit tests use synthetic logs only:

    python3 -m unittest discover -s tests -p 'test_native_*.py' -v

An LD_AUDIT attempt did not capture the worker. A separate GDB attempt
missed a process that had already exited. Neither is counted as a
successful execution trace; the final run attached to a freshly
started worker and completed normally.

**Limits:** These findings establish executed native functions and
stack relationships for one synthetic workload. They are not
independent attestation, do not prove a crash-consistent commit,
WIJ/fsync behavior, performance, absence of vulnerabilities, or a
complete WindAnvil native assurance record. Proprietary ELF binaries,
memory content, and raw debugger transcripts are excluded from GitHub.

## Journal-sync branch follow-up (October 17, 2026)

A separate clean, disposable, network-disabled IRIS AI Hub Community
instance ran a second synthetic ObjectScript global transaction. We
recorded one Ctcommit and three journaltran breakpoint hits in the
identified worker (PID 780). The session reported a successful commit
readback and test-global removal; GDB observed the same worker exiting
normally.

The original irisdb executable's **static** control-transfer map has
journaltran -> jrnforceblk and journaltran -> jrnsyncblk_options.
The **worker-level dynamic** follow-up recorded zero breakpoint hits
for jrnforceblk, jrnsyncblk_options, jrncmtsync, and jrnflushbuf.
This is a limited observation about one workload and one instrumented
worker: it does **not** imply the helpers never run, that a journal
write was skipped, or that a commit lacked durability. Other
worker/daemon contexts, options, and paths were not traced.

The lab record, preserved outside GitHub, has status
OBSERVATION_NOT_DURABILITY_PROOF and authority NONE.
Its two private transcript SHA-256 digests are:

- Terminal: 1f0fbb1f05c8204b44403aeb804209be9e2da0d27117a64258df2e54e1fb1a0e
- Debugger: 5ddad0e3c8ab31d807d79f3c89dbc164347783bad174928f41733104f5df49e5

The next *bounded* hypothesis is that journal persistence may be
coordinated with a daemon process or an option-dependent path.
Verifying it requires tracing the responsible process in a disposable
instance and correlating supported journal counters with physical I/O;
missing function hits alone must not be treated as negative proof.

The disposable IRIS instance and temporary debugger installation
were deleted after the successful local capture, preserving research
evidence and the original unmodified image.
