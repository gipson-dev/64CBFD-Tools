"""The split retains pinned dependencies and executable Linux wrappers."""

import configparser
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "CBFD_rabbitizer": "724a49a5b4dbfb99f1a9e6992e63964fd29c90c8",
    "asm-differ": "fdf9c6c1c8a85d44cfe0f9f755fe39c81b4f2331",
    "asm-processor": "b29ff12bf1d7cd1f49bf9a47b03e3ff3972ed973",
    "mips_to_c": "554de36df60762fdd7d18b7b61b5f0d3c31f4a05",
    "n64splat": "d6ae99292fe07539a87ce696df24ae3d12ff4702",
    "texture2c": "8ff9babfd9a3d5d07a9ab177bcb1b75bbaf9a9e7",
    "ultralib": "e24c836796df4bf520ff8b11a5c9d2cea3a66cbd",
}


class RepositorySetupTests(unittest.TestCase):
    def tree(self):
        output = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "--stage"], text=True
        )
        return {
            path: tuple(metadata.split()[:2])
            for metadata, path in (line.split("\t", 1) for line in output.splitlines())
        }

    def test_upstream_pins_and_paths_are_preserved(self):
        config = configparser.ConfigParser()
        config.read(ROOT / ".gitmodules")
        paths = {config[section]["path"] for section in config.sections()}
        self.assertEqual(paths, set(PINS))
        tree = self.tree()
        for path, expected in PINS.items():
            self.assertEqual(tree[path], ("160000", expected))
            self.assertTrue(config[f'submodule "{path}"']["url"].startswith("https://github.com/"))

    def test_wrappers_are_executable_and_lf(self):
        tree = self.tree()
        for name in ("mkrawobject", "mksimpleelf"):
            self.assertEqual(tree[name][0], "100755")
            data = (ROOT / name).read_bytes()
            self.assertTrue(data.startswith(b"#!/usr/bin/env bash\n"))
            self.assertNotIn(b"\r\n", data)

    def test_private_inputs_are_not_tracked(self):
        for path in self.tree():
            self.assertNotIn("__pycache__", Path(path).parts)
            self.assertNotIn(".codex", Path(path).parts)
            self.assertNotIn("build", Path(path).parts)
            self.assertNotIn(Path(path).suffix.lower(), {".z64", ".n64", ".v64", ".o", ".elf", ".bin"})


if __name__ == "__main__":
    unittest.main()
