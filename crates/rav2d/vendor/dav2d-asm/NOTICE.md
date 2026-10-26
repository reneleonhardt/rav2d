# Vendored dav2d aarch64 assembly

This directory links to assembly code, headers and tables from
[dav2d](https://code.videolan.org/videolan/dav2d), the AV2 reference decoder.
Cargo replaces these links with regular files when it packages the crate.
The published crate builds NEON pixel kernels without a dav2d checkout.

The staged submodule commit selects the source version. `REVISION` records
that commit. After you stage a submodule update, run
`python3 tools/vendor_dav2d.py` from the repository root.
CI uses `--check` to check the links and source bytes against that commit.
It also checks that the package contains exact regular files.

Native workspace builds use a configured submodule. Cross-builds and builds
without that configuration use these paths and the portable configuration.
Git checkouts need the initialized submodule and symbolic links for NEON.
On Windows, enable Developer Mode or use an elevated terminal. Set
`core.symlinks=true` before checkout. Published crates need neither setting.
For source checks on Windows, also set `core.autocrlf=false` before checkout.

On Apple targets, `build/config.h` sets `PREFIX` so assembly symbols start
with an underscore. ELF targets use names without that prefix.

## Contents

| Vendored path                         | dav2d source                  |
| ------------------------------------- | ----------------------------- |
| `src/arm/64/mc.S`                     | `src/arm/64/mc.S`             |
| `src/arm/64/mc_common.S`              | `src/arm/64/mc_common.S`      |
| `src/arm/64/mc_dotprod.S`             | `src/arm/64/mc_dotprod.S`     |
| `src/arm/64/ipred.S`                  | `src/arm/64/ipred.S`          |
| `src/arm/64/util.S`                   | `src/arm/64/util.S`           |
| `src/arm/asm.S`                       | `src/arm/asm.S`               |
| `src/tables.c`                        | `src/tables.c`                |
| `include/common/attributes.h`         | `include/common/attributes.h` |
| `include/dav2d/headers.h`             | `include/dav2d/headers.h`     |
| `COPYING`                             | `COPYING`                    |
| `REVISION`                            | staged submodule revision    |
| `build/config.h`                      | maintained portable settings |

`build.rs` extracts only the read-only data tables the kernels reference
(`dav2d_mc_subpel_filters`, `dav2d_mc_warp_filter`, `dav2d_sm_weights`,
`dav2d_dc_ibp_weights`) out of `tables.c`.

## License

dav2d is licensed under the BSD 2-Clause License (see `COPYING`),
which is compatible with rav2d's own BSD-2-Clause license. The original
copyright notices in the vendored files are retained.
