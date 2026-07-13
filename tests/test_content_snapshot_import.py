from pathlib import Path
from unittest import TestCase


class ContentSnapshotImportTests(TestCase):
    def test_upserts_are_mariadb_compatible(self):
        script = (
            Path(__file__).resolve().parents[1] / "scripts" / "import_content_snapshot.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("AS incoming", script)
        self.assertIn("ON DUPLICATE KEY UPDATE title=VALUES(title)", script)
