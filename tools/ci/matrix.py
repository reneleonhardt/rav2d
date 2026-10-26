"""Choose CPU models for pull requests and scheduled runs."""

import json
import sys

# Expected masks come from CPU detection in the decoder.
AMD64 = [
    ("SSE2 baseline", "qemu64", 1),
    ("Core 2", "Conroe", 3),
    ("Penryn", "Penryn", 7),
    ("Nehalem", "Nehalem", 7),
    ("Westmere", "Westmere", 7),
    ("Sandy Bridge (AVX)", "SandyBridge", 7),
    ("Ivy Bridge", "IvyBridge", 7),
    ("Haswell (AVX2)", "Haswell", 15),
    ("Broadwell", "Broadwell", 15),
    ("Skylake", "Skylake-Client", 15),
    ("Skylake AVX-512", "Skylake-Server", 31),
    ("Cascade Lake", "Cascadelake-Server", 31),
    ("Cooper Lake", "Cooperlake", 31),
    ("Ice Lake AVX-512", "Icelake-Server", 31),
    ("Sapphire Rapids", "SapphireRapids", 31),
    ("Granite Rapids", "GraniteRapids", 31),
    ("Sierra Forest", "SierraForest", 15),
    ("Clearwater Forest", "ClearwaterForest", 15),
    ("Atom Goldmont", "Denverton", 7),
    ("Atom Tremont", "Snowridge", 7),
    ("Xeon Phi", "KnightsMill", 15),
    ("AMD K8", "Opteron_G1", 1),
    ("AMD K8 revision F", "Opteron_G2", 1),
    ("AMD K10", "Opteron_G3", 1),
    ("AMD Bulldozer", "Opteron_G4", 7),
    ("AMD Piledriver", "Opteron_G5", 7),
    ("AMD Zen", "EPYC", 15),
    ("AMD Zen 2", "EPYC-Rome", 15),
    ("AMD Zen 3", "EPYC-Milan", 15),
    ("AMD Zen 4", "EPYC-Genoa", 31),
    ("AMD Zen 5", "EPYC-Turin", 31),
    ("Hygon Dhyana", "Dhyana", 15),
    ("Zhaoxin YongFeng", "YongFeng", 15),
]
ARM64 = [
    ("NEON", "cortex-a53", 1),
    ("dotprod", "cortex-a55", 3),
    ("i8mm", "max,sve=off", 7),
]


def matrix(extended):
    representative = {"qemu64", "SandyBridge", "Haswell", "Icelake-Server", "EPYC"}
    selected = AMD64 if extended else [entry for entry in AMD64 if entry[1] in representative]
    result = []
    for arch, cpus in (("amd64", selected), ("arm64", ARM64)):
        for name, cpu, flags in cpus:
            result.append({"name": name, "cpu": cpu, "flags": flags, "arch": arch,
                           "runner": "ubuntu-26.04" if arch == "amd64" else "ubuntu-26.04-arm",
                           "emulator": "qemu-x86_64" if arch == "amd64" else "qemu-aarch64"})
    return {"include": result}


if __name__ == "__main__":
    print(json.dumps(matrix(sys.argv[1] == "true")))
