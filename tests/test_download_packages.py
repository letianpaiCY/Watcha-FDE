from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_download_packages.py"

EXPECTED = {
    "fde-meeting-data.zip": {
        "fde-meeting-data/README.md",
        "fde-meeting-data/01-product-planning.md",
        "fde-meeting-data/02-client-delivery-risk.md",
        "fde-meeting-data/03-sales-handoff.md",
        "fde-meeting-data/04-incident-review.md",
        "fde-meeting-data/05-cross-team-weekly.md",
    },
    "fde-expense-data.zip": {
        "fde-expense-data/README.md",
        "fde-expense-data/expense-policy.md",
        "fde-expense-data/expense_tickets.csv",
    },
    "fde-cha-cup-marketing-data.zip": {
        "fde-cha-cup-marketing-data/README.md",
        "fde-cha-cup-marketing-data/cha-cup-vi-rules.md",
        "fde-cha-cup-marketing-data/product.csv",
        "fde-cha-cup-marketing-data/marketing_tasks.csv",
        "fde-cha-cup-marketing-data/images/cha-cup-product.png",
        "fde-cha-cup-marketing-data/images/cha-cup-logo.png",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class DownloadPackagesTest(unittest.TestCase):
    def build(self, output_dir: Path) -> None:
        completed = subprocess.run(
            [sys.executable, str(BUILDER), "--output-dir", str(output_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_builds_exact_packages_with_utf8_markdown_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            self.build(output_dir)
            self.assertEqual({path.name for path in output_dir.glob("*.zip")}, set(EXPECTED))
            for filename, expected_entries in EXPECTED.items():
                with zipfile.ZipFile(output_dir / filename) as archive:
                    self.assertIsNone(archive.testzip(), filename)
                    self.assertEqual(set(archive.namelist()), expected_entries)
                    self.assertFalse(any(entry.endswith(".docx") for entry in archive.namelist()))
                    for entry in expected_entries:
                        if entry.endswith(".md"):
                            content = archive.read(entry).decode("utf-8")
                            self.assertTrue(content.startswith("# "), entry)

    def test_repeated_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.build(Path(first))
            self.build(Path(second))
            self.assertEqual(
                {name: sha256(Path(first) / name) for name in EXPECTED},
                {name: sha256(Path(second) / name) for name in EXPECTED},
            )

    @unittest.skipUnless(Path("/usr/bin/python3").exists(), "system Python unavailable")
    def test_builder_runs_with_system_python(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run(
                ["/usr/bin/python3", str(BUILDER), "--output-dir", temp],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
                env=os.environ.copy(),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

if __name__ == "__main__":
    unittest.main()
