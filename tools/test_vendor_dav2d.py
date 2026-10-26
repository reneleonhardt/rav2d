import io
from pathlib import Path
import subprocess
import tarfile
from tempfile import TemporaryDirectory
import unittest

from vendor_dav2d import FILES, sync, verify_package


class VendorTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "dav2d"
        self.upstream.mkdir()
        self.git(self.root, "init")
        self.git(self.upstream, "init")
        for name in FILES:
            path = self.upstream / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"upstream\n")
        self.commit_upstream()
        self.pin()

    def git(self, directory, *args):
        return subprocess.check_output(["git", "-C", str(directory), "-c", "commit.gpgsign=false",
                                       "-c", "core.hooksPath=/dev/null", "-c", "user.name=Test",
                                       "-c", "user.email=test@example.invalid", *args], stderr=subprocess.PIPE)

    def commit_upstream(self):
        self.git(self.upstream, "add", ".")
        self.git(self.upstream, "commit", "-m", "Update source")

    def pin(self):
        revision = self.git(self.upstream, "rev-parse", "HEAD").decode().strip()
        self.git(self.root, "update-index", "--add", "--cacheinfo", f"160000,{revision},dav2d")

    def test_refresh_links_pinned_sources_and_preserves_config(self):
        vendor = self.root / "crates/rav2d/vendor/dav2d-asm"
        config = vendor / "build/config.h"
        config.parent.mkdir(parents=True)
        config.write_bytes(b"portable settings\n")
        sync(self.root)
        self.assertEqual(config.read_bytes(), b"portable settings\n")
        self.assertEqual((vendor / "REVISION").read_bytes(), self.git(self.upstream, "rev-parse", "HEAD"))
        for name in FILES:
            self.assertTrue((vendor / name).is_symlink())
            self.assertFalse((vendor / name).readlink().is_absolute())
            self.assertEqual((vendor / name).resolve(), (self.upstream / name).resolve())
        for kind in ["copy", "missing", "wrong link", "broken link"]:
            with self.subTest(kind=kind):
                path = vendor / "COPYING"
                path.unlink()
                if kind == "copy":
                    path.write_bytes(b"upstream\n")
                elif kind != "missing":
                    path.symlink_to(self.upstream / ("src/tables.c" if kind == "wrong link" else "missing"))
                with self.assertRaisesRegex(SystemExit, "COPYING"):
                    sync(self.root, check=True)
                sync(self.root)
                sync(self.root, check=True)

    def test_dirty_or_missing_sources_are_rejected_without_modifying_them(self):
        sync(self.root)
        source = self.upstream / "COPYING"
        for content in [b"uncommitted\n", None]:
            source.unlink() if content is None else source.write_bytes(content)
            for check in [False, True]:
                with self.assertRaisesRegex(SystemExit, "staged pin: COPYING"):
                    sync(self.root, check=check)
            self.assertEqual(source.read_bytes() if source.exists() else None, content)

    def test_linked_directories_cannot_redirect_source_updates(self):
        vendor = self.root / "crates/rav2d/vendor/dav2d-asm"
        for directory in [vendor, vendor / "include/common"]:
            with self.subTest(directory=directory):
                directory.parent.mkdir(parents=True, exist_ok=True)
                directory.symlink_to(self.upstream, target_is_directory=True)
                for check in [False, True]:
                    with self.assertRaisesRegex(SystemExit, "directories"):
                        sync(self.root, check=check)
                directory.unlink()
        for name in FILES:
            self.assertFalse((self.upstream / name).is_symlink())
            self.assertEqual((self.upstream / name).read_bytes(), b"upstream\n")

    def test_revision_links_are_replaced_without_writing_their_targets(self):
        sync(self.root)
        target = self.root / "source"
        target.write_bytes(b"unrelated\n")
        path = self.root / "crates/rav2d/vendor/dav2d-asm/REVISION"
        path.unlink()
        path.symlink_to(target)
        with self.assertRaisesRegex(SystemExit, "REVISION"):
            sync(self.root, check=True)
        sync(self.root)
        self.assertFalse(path.is_symlink())
        self.assertEqual(path.read_bytes(), self.git(self.upstream, "rev-parse", "HEAD"))
        self.assertEqual(target.read_bytes(), b"unrelated\n")

    def test_package_requires_exact_regular_files(self):
        sync(self.root)
        vendor = self.root / "crates/rav2d/vendor/dav2d-asm"
        (vendor / "NOTICE.md").write_bytes(b"notice\n")
        (vendor / "build").mkdir()
        (vendor / "build/config.h").write_bytes(b"portable settings\n")
        archive = self.root / "rav2d-0.1.0.crate"
        for broken in [None, "missing", "changed", "symlink", "hardlink", "config"]:
            with self.subTest(broken=broken):
                with tarfile.open(archive, "w:gz") as package:
                    for name in (*FILES, "REVISION", "NOTICE.md", "build/config.h"):
                        if name == "COPYING" and broken == "missing":
                            continue
                        content = (vendor / name).read_bytes()
                        entry = tarfile.TarInfo(f"{archive.stem}/vendor/dav2d-asm/{name}")
                        if name == "COPYING" and broken in ("symlink", "hardlink"):
                            entry.type = tarfile.SYMTYPE if broken == "symlink" else tarfile.LNKTYPE
                            entry.linkname = str(self.upstream / name)
                        elif (name == "COPYING" and broken == "changed") or (name == "build/config.h" and broken == "config"):
                            content = b"wrong bytes\n"
                        entry.size = len(content) if entry.isfile() else 0
                        package.addfile(entry, io.BytesIO(content))
                if broken:
                    with self.assertRaisesRegex(SystemExit, "packaged assembly|Packaged assembly"):
                        verify_package(archive, self.root)
                else:
                    verify_package(archive, self.root)

    def test_submodule_updates_require_an_explicit_pin_and_refresh(self):
        sync(self.root)
        (self.upstream / "COPYING").write_bytes(b"new upstream\n")
        self.commit_upstream()
        with self.assertRaisesRegex(SystemExit, "staged pin"):
            sync(self.root)
        self.pin()
        with self.assertRaisesRegex(SystemExit, "REVISION"):
            sync(self.root, check=True)
        sync(self.root)
        sync(self.root, check=True)
        self.assertEqual((self.root / "crates/rav2d/vendor/dav2d-asm/COPYING").read_bytes(), b"new upstream\n")

if __name__ == "__main__":
    unittest.main()
