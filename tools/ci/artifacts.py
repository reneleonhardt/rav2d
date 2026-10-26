"""Run the same release files on each CPU model in CI."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from smoke import ROOT, command, smoke

ARTIFACTS = ROOT / "ci-artifacts"


def pack(messages, target):
    ARTIFACTS.mkdir(exist_ok=True)
    names = {"rav2d": "unit-tests", "conformance": "conformance-tests", "fuzz": "fuzz-tests"}
    found = set()
    for line in Path(messages).read_text().splitlines():
        item = json.loads(line)
        if item.get("reason") != "compiler-artifact" or not item.get("executable"):
            continue
        name = item["target"]["name"]
        if item["profile"]["test"] and name in names:
            shutil.copy2(item["executable"], ARTIFACTS / names[name])
            found.add(name)
    assert found == names.keys(), (found, names.keys())
    release = ROOT / "target" / target / "release" if target else ROOT / "target/release"
    shutil.copy2(release / "rav2d", ARTIFACTS / "rav2d")
    shutil.copy2(ROOT / "dav2d/build/tests/checkasm", ARTIFACTS / "checkasm")
    library = ARTIFACTS / "lib"
    library.mkdir(exist_ok=True)
    for path in (ROOT / "dav2d/build/src").glob("libdav2d.so*"):
        shutil.copy2(path, library / path.name)
    assert list(library.iterdir()), "missing C oracle library"
    # Copy the build host's loader and libc.
    # Newer runner versions can require CPU features that older models lack.
    sysroot = ARTIFACTS / "sysroot"
    for binary in [ARTIFACTS / name for name in names.values()] + [ARTIFACTS / "rav2d", ARTIFACTS / "checkasm"]:
        output = subprocess.check_output(["ldd", str(binary)], text=True)
        for name in re.findall(r"(/[^\s]+)", output):
            path = Path(name)
            if path.is_file():
                destination = sysroot / path.relative_to("/")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                if path.is_relative_to(ROOT / "dav2d/build"):
                    shutil.copy2(path, library / path.name)


def run(emulator):
    os.environ["LD_LIBRARY_PATH"] = str(ARTIFACTS / "lib")
    os.environ["QEMU_LD_PREFIX"] = str(ARTIFACTS / "sysroot")
    prefix = [emulator] if emulator else []
    binary = ARTIFACTS / "checkasm"
    binary.chmod(0o755)
    result = subprocess.run(command(prefix + [str(binary), "-v"]),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
    print(result.stdout, end="", flush=True)
    result.check_returncode()
    assert re.search(r"checkasm: all [1-9][0-9]* tests passed", result.stdout), "no assembly tests passed"
    for name, filters in (
        ("unit-tests", []),
        ("conformance-tests", ["bit_exact_keyframe_filtered", "--exact"]),
        ("conformance-tests", ["required_fixtures_are_present", "--exact"]),
        ("fuzz-tests", ["fuzz_regression_corpus_no_panic", "--exact"]),
    ):
        binary = ARTIFACTS / name
        binary.chmod(0o755)
        result = subprocess.run(command(prefix + [str(binary)] + filters + ["--test-threads=1"]),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=600)
        print(result.stdout, end="", flush=True)
        result.check_returncode()
        assert re.search(r"test result: ok\. [1-9][0-9]* passed;", result.stdout), "no tests passed"
    (ARTIFACTS / "rav2d").chmod(0o755)
    smoke(ARTIFACTS / "rav2d", emulator)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--pack", metavar="CARGO_JSON")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--emulator")
    parser.add_argument("--target", default="")
    args = parser.parse_args()
    if args.pack:
        pack(args.pack, args.target)
    else:
        run(args.emulator)
