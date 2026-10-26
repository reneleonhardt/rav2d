"""Compare CLI output with an independent avmdec hash."""

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def command(args):
    return (["nice", "-n", "10"] if os.name != "nt" else []) + args


def y4m_hash(stream):
    header = stream.readline().split()
    assert header and header[0] == b"YUV4MPEG2", header
    fields = {part[:1]: part[1:] for part in header[1:]}
    assert fields[b"C"] == b"420jpeg", fields
    width, height = int(fields[b"W"]), int(fields[b"H"])
    assert width > 0 and height > 0, fields
    size = width * height + 2 * ((width + 1) // 2) * ((height + 1) // 2)
    digest = hashlib.md5()
    frames = 0
    while marker := stream.readline():
        assert marker == b"FRAME\n", marker
        samples = stream.read(size)
        assert len(samples) == size, "truncated Y4M frame"
        digest.update(samples)
        frames += 1
    assert frames > 0, "CLI produced no frames"
    return frames, digest.hexdigest()


def smoke(binary, emulator=None):
    clip = ROOT / "crates/rav2d/tests/data/media/avm-v14.1.0-bus.64x64.l5.obu"
    expected = Path(str(clip) + ".md5").read_text().strip()
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "decoded.y4m"
        prefix = shlex.split(emulator) if emulator else []
        subprocess.run(command(prefix + [str(Path(binary).resolve()), str(clip), "-t", "1", "-o", str(output)]), check=True, timeout=180,
                       creationflags=subprocess.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 0)
        with output.open("rb") as stream:
            frames, digest = y4m_hash(stream)
            assert digest == expected, (digest, expected)
            print(f"CLI: {frames} displayed frames match avmdec ({expected})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary")
    parser.add_argument("--emulator")
    args = parser.parse_args()
    smoke(args.binary, args.emulator)
