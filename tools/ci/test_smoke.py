import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import artifacts
from smoke import y4m_hash


class Y4mTests(unittest.TestCase):
    def test_independent_sample_hash(self):
        frames, digest = y4m_hash(io.BytesIO(b"YUV4MPEG2 W2 H2 C420jpeg\nFRAME\nabcdef"))
        self.assertEqual((frames, digest), (1, "e80b5017098950fc58aad83c8c14978e"))

    def test_missing_or_truncated_output_fails(self):
        for data in (b"", b"YUV4MPEG2 W2 H2 C420jpeg\n",
                     b"YUV4MPEG2 W2 H2 C420jpeg\nFRAME\nabcde",
                     b"YUV4MPEG2 W2 H2 C420jpeg\nBROKEN\nabcdef"):
            with self.subTest(data=data), self.assertRaises(AssertionError):
                y4m_hash(io.BytesIO(data))


class ArtifactTests(unittest.TestCase):
    def test_pack_preserves_executables_and_dynamic_dependencies(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "artifacts"
            for name in ("target/aarch64-unknown-linux-gnu/release/rav2d",
                         "dav2d/build/tests/checkasm", "dav2d/build/src/libdav2d.so.0",
                         "loader.so", "unit", "conformance", "fuzz"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(name.encode())
                path.chmod(0o755)
            messages = root / "cargo.json"
            items = [{"reason": "build-script-executed"}]
            for name, executable in [("rav2d", "unit"), ("conformance", "conformance"), ("fuzz", "fuzz")]:
                items.append({"reason": "compiler-artifact", "target": {"name": name},
                              "profile": {"test": True}, "executable": str(root / executable)})
            messages.write_text("\n".join(map(json.dumps, items)))
            dependencies = f"libdav2d.so.0 => {root}/dav2d/build/src/libdav2d.so.0 (0x1)\n{root}/loader.so (0x2)"
            with patch.object(artifacts, "ROOT", root), patch.object(artifacts, "ARTIFACTS", output), \
                 patch.object(artifacts.subprocess, "check_output", return_value=dependencies) as ldd:
                artifacts.pack(messages, "aarch64-unknown-linux-gnu")
                self.assertEqual(ldd.call_count, 5)
                for source, destination in [("unit", "unit-tests"), ("conformance", "conformance-tests"),
                                            ("fuzz", "fuzz-tests"), ("loader.so", "sysroot" + str(root / "loader.so")),
                                            ("dav2d/build/src/libdav2d.so.0", "lib/libdav2d.so.0")]:
                    self.assertEqual((root / source).read_bytes(), (output / destination).read_bytes())
                    self.assertTrue((output / destination).stat().st_mode & 0o111)
                messages.write_text(json.dumps(items[0]))
                with self.assertRaises(AssertionError):
                    artifacts.pack(messages, "aarch64-unknown-linux-gnu")

    def test_rust_suite_cannot_succeed_without_passing_tests(self):
        for output, code in [("test result: ok. 0 passed;", 0),
                             ("test result: FAILED. 1 passed;", 1)]:
            with self.subTest(output=output), TemporaryDirectory() as directory:
                root = Path(directory)
                for name in ("checkasm", "unit-tests"):
                    (root / name).touch()
                results = [subprocess.CompletedProcess([], 0, "checkasm: all 3 tests passed"),
                           subprocess.CompletedProcess([], code, output)]
                with patch.object(artifacts, "ARTIFACTS", root), patch.dict(artifacts.os.environ), \
                     patch.object(artifacts.subprocess, "run", side_effect=results), \
                     patch.object(artifacts, "smoke") as smoke, redirect_stdout(io.StringIO()):
                    with self.assertRaises((AssertionError, subprocess.CalledProcessError)):
                        artifacts.run("qemu-aarch64")
                    smoke.assert_not_called()

    def test_assembly_suite_cannot_succeed_without_tests(self):
        for output, code in [("reference functions unavailable", 0),
                             ("checkasm: all 0 tests passed", 0),
                             ("checkasm: all 3 tests passed", 1)]:
            with self.subTest(output=output), TemporaryDirectory() as directory:
                binary = Path(directory) / "checkasm"
                binary.touch()
                result = subprocess.CompletedProcess([], code, output)
                with patch.object(artifacts, "ARTIFACTS", Path(directory)), \
                     patch.dict(artifacts.os.environ), \
                     patch.object(artifacts.subprocess, "run", return_value=result), \
                     patch.object(artifacts, "smoke") as smoke, redirect_stdout(io.StringIO()):
                    with self.assertRaises((AssertionError, subprocess.CalledProcessError)):
                        artifacts.run("qemu-aarch64")
                    smoke.assert_not_called()

    def test_assembly_and_rust_suites_use_the_same_emulator(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("checkasm", "unit-tests", "conformance-tests", "fuzz-tests", "rav2d"):
                (root / name).touch()
            results = [subprocess.CompletedProcess([], 0, "checkasm: all 3 tests passed")] + [
                subprocess.CompletedProcess([], 0, "test result: ok. 1 passed;") for _ in range(4)]
            with patch.object(artifacts, "ARTIFACTS", root), patch.dict(artifacts.os.environ), \
                 patch.object(artifacts.subprocess, "run", side_effect=results) as run, \
                 patch.object(artifacts, "smoke") as smoke, redirect_stdout(io.StringIO()):
                artifacts.run("qemu-aarch64")
                self.assertEqual(len(run.call_args_list), 5)
                for call in run.call_args_list:
                    self.assertIn("qemu-aarch64", call.args[0])
                smoke.assert_called_once_with(root / "rav2d", "qemu-aarch64")


if __name__ == "__main__":
    unittest.main()
