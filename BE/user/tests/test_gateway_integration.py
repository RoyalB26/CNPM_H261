"""Chạy Gateway trong tiến trình riêng để không đụng runtime demo hiện tại."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class GatewayIntegrationTests(unittest.TestCase):
    def test_lifecycles_concurrency_rollback_and_restart(self):
        """Dữ liệu thanh toán phải tồn tại khi một tiến trình Python mới khởi động."""
        scenario = Path(__file__).with_name("gateway_scenarios.py")
        with tempfile.TemporaryDirectory(prefix="be-user-gateway-") as directory:
            for mode in ("exercise", "verify"):
                with self.subTest(mode=mode):
                    result = subprocess.run(
                        [sys.executable, "-B", str(scenario), mode, directory],
                        capture_output=True, text=True, timeout=45,
                    )
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
