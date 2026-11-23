"""Kịch bản Gateway trong tiến trình con; chỉ dùng runtime tạm do test truyền vào."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch


def run_scenario(mode: str, directory: str) -> None:
    """Kiểm tra HTTP, lưu JSON và khởi động lại mà không dùng runtime của nhóm."""
    runtime = Path(directory).resolve() / "gateway-test.json"
    # Gán trước mọi import Gateway để shared.database không mở runtime thật.
    os.environ["BE_RUNTIME_PATH"] = str(runtime)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from starlette.testclient import TestClient
    from run_all import app
    from shared.database import db, storage
    from shared.json_store import PersistenceError

    prefix = "/api/v1/user"
    manifest = runtime.with_suffix(".manifest.json")
    with TestClient(app) as client:
        def post(path, payload=None, expected=200):
            response = client.post(prefix + path, **({"json": payload} if payload is not None else {}))
            assert response.status_code == expected, (path, response.status_code, response.text)
            return response.json()

        def invoice(service, **selectors):
            response = client.get(prefix + "/invoices/current", params={"type": service, **selectors})
            assert response.status_code == 200, response.text
            return response.json()

        if mode == "verify":
            identifiers = json.loads(manifest.read_text(encoding="utf-8"))
            for service, invoice_id in identifiers.items():
                result = invoice(service, invoice_id=invoice_id)
                assert result["status"] == "paid", result
                assert result["transaction_id"], result
                post("/invoices/pay", {"invoice_id": invoice_id, "method": "wallet"}, 409)
            assert json.loads(runtime.read_text(encoding="utf-8")) == storage.snapshot()
            return

        # Kiểm chứng các bước đầu của demo trước khi tạo giao dịch.
        before = storage.snapshot()
        login = post("/auth/login", {"email": db.user["email"], "password": "123456"})
        assert login["user"]["id"] == db.user["id"]
        post("/auth/login", {"email": db.user["email"], "password": "wrong"}, 401)
        post("/auth/login", {"email": db.user["email"]}, 422)
        response = client.post(prefix + "/auth/login", content="{", headers={"Content-Type": "application/json"})
        assert response.status_code == 400, response.text
        for path in ("/profile", "/vehicles", "/hubs?keyword=bach%20khoa", "/hubs/hub-02"):
            response = client.get(prefix + path)
            assert response.status_code == 200, (path, response.text)
        response = client.get(prefix + "/hubs/missing")
        assert response.status_code == 404, response.text
        assert before == storage.snapshot()

        # Kết thúc các phiên seed qua API, không sửa singleton bằng tay.
        before = storage.snapshot()
        post("/bookings/EMH-1024/cancel", expected=409)
        assert before == storage.snapshot()
        post("/services/return-vehicle", {"trip_id": "TRIP-8821", "hub_id": "hub-04"})
        post("/services/charging/stop", {"session_id": "CHG-302", "power_consumed_kwh": 2.4})

        rental = {"plan_type": "rental", "hub_id": "hub-02", "resource_name": "XE-052",
                  "destination_hub_id": "hub-04"}
        # Hai request cùng xe: chỉ một booking được giữ tài nguyên.
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: client.post(prefix + "/bookings", json=rental), range(2)))
        assert sorted(result.status_code for result in results) == [200, 409]
        booking = next(result.json() for result in results if result.status_code == 200)
        assert booking["destination_hub_id"] == "hub-04"
        ride = post(f"/bookings/{booking['id']}/start")["ride"]
        post("/services/return-vehicle", {"trip_id": ride["trip_id"], "hub_id": "hub-04"})
        rental_invoice = invoice("rental", trip_id=ride["trip_id"])

        swap = post("/bookings", {"plan_type": "swap", "hub_id": "hub-02", "battery_type": "B48"})
        post(f"/bookings/{swap['id']}/swap")
        swap_invoice = invoice("swap", booking_id=swap["id"])

        charging = post("/bookings", {"plan_type": "charging", "hub_id": "hub-01",
                                      "personal_plate": "59-A1 999.99", "charging_port": "S01"})
        session = post(f"/bookings/{charging['id']}/charging/start")["charging"]
        post("/services/charging/stop", {"session_id": session["session_id"], "power_consumed_kwh": 2.4})
        charging_invoice = invoice("charging", session_id=session["session_id"])
        assert charging_invoice["total_amount"] == 8400

        # Liên thông User -> bảo vệ: giữ chỗ, vào bãi, ra bãi, xem hóa đơn tiền mặt.
        staff_prefix = "/api/v1/staff"
        response = client.post(staff_prefix + "/parking/checkout/confirm",
                               json={"ticket_code": "PRK-901", "payment_method": "TIỀN MẶT"})
        assert response.status_code == 200, response.text
        parking = post("/bookings", {"plan_type": "parking", "hub_id": "hub-02",
                                     "personal_plate": "59-A1 888.88", "parking_slot": "P11"})
        count = db.get_hub("hub-02")["available_parking"]
        response = client.post(staff_prefix + "/parking/checkin", json={
            "license_plate": "59-A1 888.88", "hub_name": "Hub Đại học Bách khoa",
        })
        assert response.status_code == 200, response.text
        ticket = response.json()["ticket_code"]
        assert response.json()["bay_slot"] == "P11"
        assert db.get_hub("hub-02")["available_parking"] == count
        response = client.post(staff_prefix + "/parking/checkout/confirm",
                               json={"ticket_code": ticket, "payment_method": "TIỀN MẶT"})
        assert response.status_code == 200, response.text
        assert db.get_hub("hub-02")["available_parking"] == count + 1
        parking_invoice = invoice("parking", booking_id=parking["id"])
        assert parking_invoice["status"] == "paid"
        post("/invoices/pay", {"invoice_id": parking_invoice["id"], "method": "wallet"}, 404)

        # Phiếu User phải xuất hiện ở Staff và phản ánh kết quả xử lý ngược lại.
        report = post("/incidents", {
            "resource_type": "Phương tiện", "resource_code": "XE-052",
            "hub_name": "Hub Đại học Quốc Tế", "incident_type": "Lỗi khóa",
            "description": "Kiểm thử liên thông báo cáo và bảo trì",
        })
        response = client.get(staff_prefix + "/maintenance/tasks")
        assert response.status_code == 200, response.text
        assert report["maintenance_ticket_code"] in response.text
        response = client.post(staff_prefix + "/maintenance/resolve", json={
            "task_code": report["maintenance_ticket_code"], "technical_notes": "Đã sửa khóa kiểm thử",
        })
        assert response.status_code == 200, response.text
        response = client.get(prefix + "/incidents")
        assert response.status_code == 200, response.text
        resolved = next(item for item in response.json() if item["id"] == report["id"])
        assert resolved["status"] == "Đã giải quyết"
        assert resolved["operator_note"] == "Đã sửa khóa kiểm thử"

        # Operator tạm ngưng Hub phải có hiệu lực ngay với User dùng chung store.
        response = client.post("/api/v1/operator/hubs/hub-02/deactivate", json={
            "reason": "Kiểm thử dùng chung Hub", "lock_chargers": False, "reroute_bookings": False,
        })
        assert response.status_code == 200, response.text
        before = storage.snapshot()
        post("/bookings", {"plan_type": "swap", "hub_id": "hub-02", "battery_type": "B48"}, 409)
        assert before == storage.snapshot()
        # Mở lại bằng API Operator để tiếp tục kiểm tra lỗi ghi trên request hợp lệ.
        response = client.put("/api/v1/operator/hubs/hub-02/config", json={"status": "Hoạt động"})
        assert response.status_code == 200, response.text

        identifiers = {}
        for service, result in (("rental", rental_invoice), ("swap", swap_invoice), ("charging", charging_invoice)):
            payload = {"invoice_id": result["id"], "method": "wallet", "amount": result["total_amount"]}
            post("/invoices/pay", payload)
            before = storage.snapshot()
            post("/invoices/pay", payload, 409)
            assert before == storage.snapshot()
            identifiers[service] = result["id"]

        # GET và request lỗi không làm thay đổi RAM hoặc file JSON.
        before = storage.snapshot()
        disk_before = runtime.read_bytes()
        for path, status in (("/bookings", 200), ("/services/active", 200),
                             ("/invoices/current?type=invalid", 422),
                             ("/invoices/current?type=rental&trip_id=missing", 404)):
            response = client.get(prefix + path)
            assert response.status_code == status, response.text
        assert before == storage.snapshot()
        assert disk_before == runtime.read_bytes()

        # Lỗi lưu file phải trả 503 và hoàn nguyên cả tài nguyên đã giữ trong RAM.
        with patch.object(storage, "_write", side_effect=PersistenceError("Lỗi lưu mô phỏng")):
            post("/bookings", {"plan_type": "swap", "hub_id": "hub-02", "battery_type": "B48"}, 503)
        assert before == storage.snapshot()
        assert disk_before == runtime.read_bytes()
        assert db is storage.db
        manifest.write_text(json.dumps(identifiers), encoding="utf-8")


if __name__ == "__main__":
    run_scenario(sys.argv[1], sys.argv[2])
