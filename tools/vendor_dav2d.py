"""Link assembly files to the staged dav2d commit and check packaged copies."""

import argparse
import os
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "COPYING",
    "include/common/attributes.h",
    "include/dav2d/headers.h",
    "src/arm/asm.S",
    "src/arm/64/ipred.S",
    "src/arm/64/mc.S",
    "src/arm/64/mc_common.S",
    "src/arm/64/mc_dotprod.S",
    "src/arm/64/util.S",
    "src/tables.c",
)


def sync(root=ROOT, check=False):
    def git(directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), *args])

    root = root.resolve()
    vendor = root / "crates/rav2d/vendor/dav2d-asm"
    parents = {(vendor / name).parent for name in FILES}
    if any(parent.resolve() != parent for parent in parents):
        raise SystemExit("Assembly directories must not be symbolic links")
    upstream = root / "dav2d"
    revision = git(root, "rev-parse", ":dav2d").strip()
    if git(upstream, "rev-parse", "HEAD").strip() != revision:
        raise SystemExit("dav2d checkout differs from its staged pin; initialize or stage the intended submodule revision first")
    for name in FILES:
        source = upstream / name
        if not source.is_file() or source.read_bytes() != git(upstream, "show", f"{revision.decode()}:{name}"):
            raise SystemExit(f"dav2d source differs from its staged pin: {name}")
    stale = []
    for name in (*FILES, "REVISION"):
        path = vendor / name
        target = Path(os.path.relpath(upstream / name, path.parent)).as_posix()
        if name == "REVISION":
            matches = not path.is_symlink() and path.is_file() and path.read_bytes() == revision + b"\n"
        else:
            matches = path.is_symlink() and path.readlink().as_posix() == target
        if matches:
            continue
        if check:
            stale.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.is_symlink() or path.exists():
                path.unlink()
            if name == "REVISION":
                path.write_bytes(revision + b"\n")
            else:
                path.symlink_to(target)
    if stale:
        raise SystemExit("Stale dav2d assembly subset: " + ", ".join(stale) + "; run python3 tools/vendor_dav2d.py")


def verify_package(archive, root=ROOT):
    sync(root, check=True)
    vendor = root / "crates/rav2d/vendor/dav2d-asm"
    with tarfile.open(archive) as package:
        for name in (*FILES, "REVISION", "NOTICE.md", "build/config.h"):
            try:
                member = package.getmember(f"{archive.stem}/vendor/dav2d-asm/{name}")
            except KeyError:
                raise SystemExit(f"Missing packaged assembly file: {name}") from None
            if not member.isfile() or package.extractfile(member).read() != (vendor / name).read_bytes():
                raise SystemExit(f"Packaged assembly must contain exact regular files: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="reject drift without modifying files")
    mode.add_argument("--package", type=Path, help="check the assembly files in a .crate archive")
    args = parser.parse_args()
    if args.package:
        verify_package(args.package)
    else:
        sync(check=args.check)
