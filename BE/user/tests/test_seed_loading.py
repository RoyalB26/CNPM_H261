"""Bảo vệ định dạng seed dùng chung khi chuyển sang json.load()."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.seed_loader import SeedLoadError, load_seed


class SeedLoadingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "seed.json"

    def test_utf8_bom_and_independent_loads(self):
        original = load_seed()
        self.path.write_text(json.dumps(original, ensure_ascii=False), encoding="utf-8-sig")
        loaded = load_seed(self.path)
        self.assertEqual(original, loaded)
        loaded["hubs"].clear()
        self.assertEqual(original, load_seed(self.path))

    def test_duplicate_keys_malformed_or_missing_file_rejected(self):
        for contents in ('{"hubs": [], "hubs": []}', '{', '[]', '{"hubs": []}'):
            with self.subTest(contents=contents):
                self.path.write_text(contents, encoding="utf-8")
                with self.assertRaises(SeedLoadError):
                    load_seed(self.path)
        self.path.unlink()
        with self.assertRaises(SeedLoadError):
            load_seed(self.path)

    def test_wrong_types_and_unknown_root_keys_rejected(self):
        for field, value in (("hubs", {}), ("next_relocation_number", True),
                             ("next_relocation_number", 0), ("unknown", [])):
            with self.subTest(field=field, value=value):
                seed = load_seed()
                seed[field] = value
                self.path.write_text(json.dumps(seed), encoding="utf-8")
                with self.assertRaises(SeedLoadError):
                    load_seed(self.path)


if __name__ == "__main__":
    unittest.main()
