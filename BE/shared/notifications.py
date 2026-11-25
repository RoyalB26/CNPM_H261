"""Thông báo lưu bền vững, truy vấn theo tài khoản hoặc vai trò."""
from datetime import datetime, timezone
from uuid import uuid4


def notify(store, key, recipient, message, reference_id):
    rows = store.operator_mock.setdefault("notifications", [])
    if any(row["key"] == key for row in rows):
        return
    rows.append({
        "id": "NTF-" + uuid4().hex, "key": key, "recipient": recipient,
        "message": message, "reference_id": reference_id,
        "created_at": datetime.now(timezone.utc).isoformat(), "read": False,
    })
