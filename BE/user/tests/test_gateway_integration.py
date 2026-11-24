"""Chạy Gateway trong tiến trình riêng để không đụng runtime demo hiện tại."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class GatewayIntegrationTests(unittest.TestCase):
    def test_qualified_package_imports_preserve_singleton_paths_and_other_schemas(self):
        """Cấu trúc mới không đổi db, đường dẫn JSON hoặc module schemas khác."""
        scenario = Path(__file__).with_name('package_import_scenario.py')
        with tempfile.TemporaryDirectory(prefix='be-import-cwd-') as directory:
            result = subprocess.run([sys.executable, '-B', str(scenario)], cwd=directory,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_user_candidate_writes_with_gateway_and_versioned_urls(self):
        """Gateway không ghi lại transaction User và không sửa RAM trước JSON."""
        self.run_write_contract('gateway')

    def test_user_candidate_writes_without_gateway_using_legacy_aliases(self):
        """Handler tự lưu và rollback được khi không có middleware Gateway."""
        self.run_write_contract('standalone')

    def run_write_contract(self, mode):
        scenario = Path(__file__).with_name('user_persistence_scenario.py')
        result = subprocess.run([sys.executable, '-B', str(scenario), mode],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_personal_bundle_checkin_charge_checkout_and_restart(self):
        """Gói ghép phải dùng được qua API User/Staff và lưu cả hai hóa đơn."""
        scenario = Path(__file__).with_name('gateway_scenarios.py')
        with tempfile.TemporaryDirectory(prefix='be-user-personal-') as directory:
            for mode in ('personal', 'verify'):
                with self.subTest(mode=mode):
                    result = subprocess.run([sys.executable, '-B', str(scenario), mode, directory],
                                            capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_hub_deactivation_and_maintenance_during_charging_and_swap(self):
        """Operator ngừng Hub và Staff xử lý bảo trì phải tác động đúng luồng User."""
        scenario = Path(__file__).with_name("gateway_scenarios.py")
        with tempfile.TemporaryDirectory(prefix="be-user-resource-change-") as directory:
            result = subprocess.run([sys.executable, "-B", str(scenario), "resource-change", directory],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_operator_incoming_hold_blocks_rental_return_without_partial_changes(self):
        """Lệnh Operator giữ chỗ phải có hiệu lực trên API tra cứu và trả xe User."""
        scenario = Path(__file__).with_name("gateway_scenarios.py")
        with tempfile.TemporaryDirectory(prefix="be-user-capacity-") as directory:
            result = subprocess.run([sys.executable, "-B", str(scenario), "capacity", directory],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_user_routes_do_not_read_or_change_other_owners_records(self):
        """Mã bản ghi được biết trước không cho phép vượt bộ lọc sở hữu."""
        scenario = Path(__file__).with_name("ownership_gateway_scenario.py")
        result = subprocess.run([sys.executable, "-B", str(scenario)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_automatic_expiry_shares_http_lock_and_stops_on_shutdown(self):
        """Gateway phải tự hết hạn booking, lưu JSON và thu hồi tác vụ nền."""
        scenario = Path(__file__).with_name("expiry_gateway_scenario.py")
        result = subprocess.run([sys.executable, "-B", str(scenario)],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

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
