"""Chạy cục bộ để lấy URI đăng ký Authenticator cho Operator đã được cấp."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shared.authentication import ensure_accounts, accounts, provisioning_uri

if __name__ == "__main__":
    failure = ensure_accounts()
    if failure is not None:
        raise SystemExit("Không lưu được tài khoản")
    account = next(a for a in accounts() if a["role"] == "operator")
    print(provisioning_uri(account))
