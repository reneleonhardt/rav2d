# AV2 1.0.0 coverage

This suite detects regressions. It does not certify full AV2 conformance.
Its scope is [AV2 v1.0.0](https://av2.aomedia.org/v1.0.0/index.html), sections
4–8 and Annexes A/E. A conformance claim must list supported profiles and levels.

| Requirement | Tests | Remaining gaps |
| --- | --- | --- |
| §5/6 syntax and semantics | `obu::tests` remove every byte suffix from both release sequence headers | Some syntax elements and boundaries lack tests |
| §7 decoding and output order | `avmenc_vectors_bit_exact`, `bit_exact_avm_reference_md5` | Six `pending_*` streams still fail |
| §8 entropy parsing | `getbits::tests`, `msac::tests`, `cdf::tests` and bitstream sweeps | Some symbols and context combinations lack tests |
| Annex A profiles | `sequence_profile_boundaries`, profile 3/4/31 pending tests | Full profile support, interoperability and level/tier limits lack tests |
| Annex E decoder model | Hashes of frames in display order | Timing, buffer limits and display schedules lack tests |

The `avmenc-v1-*` fixtures use the official reference release.
Their [source and generation steps](data/avmenc/AVM-v1.0.0.md) are separate
from the older fixtures. They test 8/10-bit 4:2:0 and LCR/OPS headers with one
layer. They do not test multilayer selection. AV2 1.0.0 reserves twelve-bit
indicators (Table 6.3). The 12-bit unit tests fall outside this scope.

The older `cov-multitile-416x240.obu` fixture has an AVM 1.0.0 hash:
`490eb0b7e4896088d46e74a8fe7e2622`. It covers four 416x240 8-bit 4:2:0 frames.
`avmdec --threads=1` Y4M output and `--threads=2 --i420` raw output agree.
Its pending test uses AVM because dav2d emits partial output that changes with
its thread configuration.

Supported cases block CI. Scheduled and manual CI runs test known failures
separately with `continue-on-error`. These tests still require the correct AVM
output. Untested requirements have no implied pass or failure exemption.
