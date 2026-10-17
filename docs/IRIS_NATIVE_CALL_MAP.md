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
