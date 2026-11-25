"""B1–B2/C1–C5 qua Gateway ASGI, runtime tạm và OSRM giả lập."""
import asyncio
import copy
import io
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import httpx
from PIL import Image
import test_auth
import test_operator
from shared.database import db, storage
from shared.automation import sweep_operations


class FeatureTests(unittest.TestCase):
    tearDown = test_auth.AuthTests.tearDown
    operator_login = test_auth.AuthTests.operator_login
    register = test_auth.AuthTests.register
    user_login = test_auth.AuthTests.user_login

    def setUp(self):
        test_auth.AuthTests.setUp(self)
        self.operator = test_operator.OperatorCases.headers(self)
        response = self.client.post("/api/v1/operator/hubs", headers=self.operator, json={
            "hub_code": "TEST-HUB", "name": "Test Hub", "address": "Test address",
            "lat": 10.87, "lng": 106.80, "parking_capacity": 10,
            "charger_capacity": 2, "max_power_kw": 100,
        })
        self.assertEqual(response.status_code, 201, response.text)
        self.hub_id = response.json()["hub"]["id"]
        self.add_port("TEST-S01")
        self.assertEqual(self.register().status_code, 201)
        self.user = self.user_login()
        staff = self.client.post("/api/v1/staff/auth/login", json={
            "username_or_phone": "staff_b", "password": "staff123",
        })
        self.staff = {"Authorization": "Bearer " + staff.json()["access_token"]}

    def add_port(self, code):
        response = self.client.post(f"/api/v1/operator/hubs/{self.hub_id}/devices",
            headers=self.operator, json={"kind": "port", "id": code, "name": code, "power_kw": 10})
        self.assertEqual(response.status_code, 201, response.text)

    def window(self, **updates):
        start = datetime.now(timezone.utc) + timedelta(days=1)
        data = {"hub_id": self.hub_id, "port_id": "TEST-S01", "plate_number": "59TEST1",
                "starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=1)).isoformat(),
                "battery_pct": 50}
        return {**data, **updates}

    def reserve(self, body, headers=None):
        return self.client.post("/api/v1/user/charging/schedules",
            headers=headers or self.user, json=body)

    def device_state(self, enabled):
        return self.client.put(f"/api/v1/operator/hubs/{self.hub_id}/devices/port/TEST-S01",
            headers=self.operator, json={"enabled": enabled})

    def simulation(self, **changes):
        payload = {"source_type": "LIVE_A", "config": {
            "scenario_name": "Demand", "demand_increase_pct": 50, "target_hub_ids": [self.hub_id]}}
        return self.client.post("/api/v1/operator/simulation/run",
            headers=self.operator, json={**payload, **changes})

    def new_ticket(self):
        response = self.client.post("/api/v1/operator/maintenance/tickets",
            headers=self.operator, json={"device_code": "TEST-S01", "hub_name": "Test Hub",
                "source": "Operator", "fault_category": "Broken", "description": "Repair",
                "assigned_staff_id": "STF-02"})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()["ticket"]["ticket_code"]

    def test_B1_road_geometry_and_unavailable_provider(self):
        payload = {"origin_lat": 10.86, "origin_lng": 106.80,
                   "dest_lat": 10.87, "dest_lng": 106.81, "vehicle_type": "personal"}
        async def road(*args, **kwargs):
            return httpx.Response(200, request=httpx.Request("GET", "https://osrm.test/route"), json={
                "code": "Ok", "routes": [{"distance": 3200, "duration": 540,
                "geometry": {"type": "LineString", "coordinates": [[106.8, 10.86], [106.81, 10.87]]}}]})
        with patch("httpx.AsyncClient.get", side_effect=road):
            response = self.client.post("/api/hubs/suggest-route", headers=self.user, json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["distance_km"], 3.2)
        self.assertIsNone(response.json()["recommended_bike"])
        with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("offline")):
            response = self.client.post("/api/hubs/suggest-route", headers=self.user, json=payload)
        self.assertEqual(response.status_code, 503, response.text)

    def test_B2_overlap_adjacent_and_cancel(self):
        first = self.window()
        booked = self.reserve(first)
        self.assertEqual(booked.status_code, 201, booked.text)
        self.register("2")
        other = self.user_login("2")
        overlap = {**first, "plate_number": "59TEST2"}
        self.assertEqual(self.reserve(overlap, other).status_code, 409)
        second = {**overlap, "starts_at": first["ends_at"],
                  "ends_at": (datetime.fromisoformat(first["ends_at"]) + timedelta(hours=1)).isoformat()}
        self.assertEqual(self.reserve(second, other).status_code, 201)
        response = self.client.post(f"/api/v1/user/charging/schedules/{booked.json()['id']}/cancel", headers=self.user)
        self.assertEqual(response.status_code, 200)
        storage.reload()
        listing = self.client.get("/api/v1/user/charging/schedules", headers=self.user).json()["items"]
        self.assertEqual(listing[0]["status"], "CANCELLED")

    def test_B2_priority_port_change_and_notifications(self):
        self.assertEqual(self.device_state(False).status_code, 200)
        body = self.window(join_queue=True, battery_pct=80)
        self.assertEqual(self.reserve(body).json()["status"], "WAITING")
        self.register("2")
        other = self.user_login("2")
        self.assertEqual(self.reserve({**body, "battery_pct": 5, "plate_number": "59TEST2"}, other).status_code, 201)
        self.assertEqual(self.device_state(True).status_code, 200)
        def status(headers):
            return self.client.get("/api/v1/user/charging/schedules", headers=headers).json()["items"][0]["status"]
        self.assertEqual(status(other), "RESERVED")
        self.assertEqual(status(self.user), "WAITING")
        messages = self.client.get("/api/v1/user/notifications", headers=other).json()["items"]
        self.assertEqual(len(messages), 1)
        self.device_state(False)
        self.assertEqual(status(other), "WAITING")
        self.device_state(True)
        self.assertEqual(status(other), "RESERVED")

    def test_B2_invalid_window_and_access(self):
        first = self.window()
        self.assertEqual(self.reserve({**first, "ends_at": first["starts_at"]}).status_code, 422)
        booked = self.reserve(first).json()
        self.assertEqual(self.client.post(f"/api/v1/user/charging/schedules/{booked['id']}/start", headers=self.user).status_code, 409)
        self.register("2")
        other = self.user_login("2")
        self.assertEqual(self.client.post(f"/api/v1/user/charging/schedules/{booked['id']}/cancel", headers=other).status_code, 404)

    def test_C1_counts_duplicate_and_hub_restore(self):
        self.device_state(False)
        self.device_state(False)
        self.assertEqual(db.get_hub(self.hub_id)["available_chargers"], 0)
        self.device_state(True)
        self.device_state(True)
        self.assertEqual(db.get_hub(self.hub_id)["available_chargers"], 1)
        response = self.client.post(f"/api/v1/operator/hubs/{self.hub_id}/devices",
            headers=self.operator, json={"kind": "port", "id": "TEST-S01", "name": "Port"})
        self.assertEqual(response.status_code, 409)
        path = f"/api/v1/operator/hubs/{self.hub_id}/config"
        for status in ("Tạm ngưng", "Hoạt động"):
            self.assertEqual(self.client.put(path, headers=self.operator, json={"status": status}).status_code, 200)

    def test_C2_rule_executes_once_across_reload(self):
        def prepare(candidate):
            candidate.get_hub(self.hub_id)["power_demand_kw"] = 120
            candidate.simulation_rules.append({"id": "RULE-TEST", "active": True,
                "hub_ids": [self.hub_id], "threshold_pct": 85,
                "actions": [{"type": "notify", "message": "High demand"}]})
        storage.commit(prepare)
        for _ in range(2):
            self.assertEqual(self.client.post("/api/v1/operator/automation/scan", headers=self.operator).status_code, 200)
            storage.reload()
        runs = [r for r in db.operator_mock["automation_runs"] if r["hub_id"] == self.hub_id]
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "COMPLETED")
        self.assertEqual(len(runs[0]["progress"]), 1)

    def test_C2_missing_rule_and_intervention(self):
        response = self.client.post("/api/v1/operator/automation/scan", headers=self.operator)
        run = next(r for r in response.json()["items"] if r["hub_id"] == self.hub_id)
        self.assertEqual(run["status"], "WAITING_OPERATOR")
        path = "/api/v1/operator/automation/runs/" + run["id"]
        self.assertEqual(self.client.put(path, headers=self.operator, json={"action": "pause"}).json()["status"], "PAUSED")
        self.assertEqual(self.client.put(path, headers=self.operator, json={"action": "resolve"}).json()["status"], "HANDLED")

    def test_TC_O01_computation_and_live_unchanged(self):
        before = copy.deepcopy(db.hubs)
        one = self.simulation()
        self.assertEqual(one.status_code, 200, one.text)
        two = self.simulation(config={"scenario_name": "Demand", "demand_increase_pct": 300,
                                      "target_hub_ids": [self.hub_id]})
        self.assertEqual(two.status_code, 200, two.text)
        first = next(h for h in one.json()["hub_results"] if h["hub_id"] == self.hub_id)
        second = next(h for h in two.json()["hub_results"] if h["hub_id"] == self.hub_id)
        self.assertEqual(first["peak_requested_power_kw"], 7.5)
        self.assertEqual(second["peak_requested_power_kw"], 20)
        self.assertEqual(second["peak_unmet_power_kw"], 10)
        self.assertEqual(db.hubs, before)

    def test_C3_snapshot_timeout_retry_save(self):
        payload = {"source_type": "LIVE_A", "config": {"scenario_name": "Freeze"}}
        capture = self.client.post("/api/v1/operator/simulation/snapshots", headers=self.operator, json=payload)
        self.assertEqual(capture.status_code, 201, capture.text)
        self.device_state(False)
        failed = self.simulation(snapshot_id=capture.json()["snapshot_id"], trigger_timeout_error=True)
        self.assertEqual(failed.status_code, 504, failed.text)
        simulation_id = failed.json()["simulation_id"]
        self.assertEqual(next(r for r in db.simulation_history if r.get("id") == simulation_id)["status"], "FAILED")
        result = self.client.post(f"/api/v1/operator/simulation/{simulation_id}/retry", headers=self.operator)
        self.assertEqual(result.status_code, 200, result.text)
        hub = next(h for h in result.json()["hub_results"] if h["hub_id"] == self.hub_id)
        self.assertEqual(hub["capacity_kw"], 10)
        saved = self.client.post(f"/api/v1/operator/simulation/{simulation_id}/save", headers=self.operator,
            json={"operation_plan": "Queue excess demand"})
        self.assertEqual(saved.status_code, 200)
        storage.reload()
        detail = self.client.get(f"/api/v1/operator/simulation/history/{simulation_id}", headers=self.operator).json()
        self.assertEqual(detail["attempts"], 2)
        self.assertEqual(detail["operation_plan"], "Queue excess demand")

    def test_C3_manual_invalid_and_structured_rule(self):
        snapshot = self.client.get("/api/v1/operator/simulation/source-state", headers=self.operator).json()["hub_snapshots"]
        snapshot[0]["current_bikes"] = snapshot[0]["total_parking_capacity"] + 1
        self.assertEqual(self.simulation(source_type="MANUAL_A_PRIME", hub_snapshots=snapshot).status_code, 422)
        result = self.simulation().json()
        response = self.client.post("/api/v1/operator/simulation/save-rule", headers=self.operator, json={
            "simulation_id": result["simulation_id"], "rule_name": "Response",
            "operation_instructions": "Notify", "hub_ids": [self.hub_id],
            "actions": [{"type": "notify", "message": "Load high"}]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(db.simulation_rules[0]["actions"])

    def test_C4_user_image_persist_and_access(self):
        response = self.client.post("/api/v1/user/incidents", headers=self.user, json={
            "hub_name": "Test Hub", "resource_type": "Cổng sạc", "resource_code": "TEST-S01",
            "incident_type": "Damage", "description": "Broken"})
        self.assertEqual(response.status_code, 200, response.text)
        image = io.BytesIO()
        Image.new("RGB", (4, 4), "red").save(image, format="PNG")
        endpoint = f"/api/v1/user/incidents/{response.json()['id']}/photos"
        uploaded = self.client.post(endpoint, headers=self.user, files={"file": ("damage.png", image.getvalue(), "image/png")})
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        url = uploaded.json()["photo_url"]
        storage.reload()
        self.assertEqual(self.client.get(url, headers=self.user).content, image.getvalue())
        self.register("2")
        self.assertEqual(self.client.get(url, headers=self.user_login("2")).status_code, 403)
        self.assertEqual(self.client.post(endpoint, headers=self.user, content=b"fake").status_code, 422)

    def test_C4_staff_upload_C5_workshop_exact_device_and_replay(self):
        code = self.new_ticket()
        self.add_port("TEST-S02")
        image = io.BytesIO()
        Image.new("RGB", (2, 2)).save(image, "JPEG")
        upload = self.client.post(f"/api/v1/staff/maintenance/{code}/photos",
            headers={**self.staff, "Content-Type": "image/jpeg"}, content=image.getvalue())
        self.assertEqual(upload.status_code, 201, upload.text)
        payload = {"task_code": code, "outcome": "TRANSFER_TO_WORKSHOP", "technical_notes": "Workshop"}
        for _ in range(2):
            response = self.client.post("/api/v1/staff/maintenance/resolve", headers=self.staff, json=payload)
            self.assertEqual(response.status_code, 200, response.text)
        hub = db.get_hub(self.hub_id)
        self.assertEqual(hub["available_chargers"], 1)
        self.assertTrue(hub["ports"][0]["workshop"])
        self.assertTrue(hub["ports"][1]["is_available"])
        messages = self.client.get("/api/v1/staff/notifications", headers=self.staff).json()["items"]
        self.assertTrue(any(n["reference_id"] == code for n in messages))

    def test_C5_fixed_on_site_and_invalid_body(self):
        code = self.new_ticket()
        self.device_state(False)
        response = self.client.post("/api/v1/staff/maintenance/resolve", headers=self.staff, json={
            "task_code": code, "outcome": "FIXED_ON_SITE", "technical_notes": "Repaired"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(db.get_hub(self.hub_id)["ports"][0]["is_available"])
        self.assertEqual(self.client.post("/api/v1/staff/maintenance/resolve", headers=self.staff, json={}).status_code, 422)

    def test_worker_sweep_commits_only_changes(self):
        loop = test_auth.InProcessLoop()
        try:
            loop.run_until_complete(sweep_operations(storage, asyncio.Lock()))
            with patch.object(storage, "_write", wraps=storage._write) as write:
                loop.run_until_complete(sweep_operations(storage, asyncio.Lock()))
                write.assert_not_called()
        finally:
            loop.close()

    def test_B2_start_stop_scheduled_session(self):
        body = self.window()
        response = self.reserve(body)
        self.assertEqual(response.status_code, 201, response.text)
        schedule_id = response.json()["id"]
        due = datetime.fromisoformat(body["starts_at"]) + timedelta(minutes=1)
        with patch("shared.charging_schedule.utc_now", return_value=due), patch("shared.operations_api.utc_now", return_value=due):
            response = self.client.post(f"/api/v1/user/charging/schedules/{schedule_id}/start", headers=self.user)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "IN_SERVICE")
        profile = self.client.get("/api/v1/user/profile", headers=self.user).json()
        session = profile["active_services"]["charging"]
        stopped = self.client.post("/api/v1/user/services/charging/stop", headers=self.user, json={
            "session_id": session["session_id"], "power_consumed_kwh": 2.0, "final_charge": 80,
        })
        self.assertEqual(stopped.status_code, 200, stopped.text)
        def change(candidate):
            from shared.charging_schedule import reconcile_schedule
            reconcile_schedule(candidate)
        storage.commit(change)
        row = next(r for r in db.operator_mock["charging_schedule"] if r["id"] == schedule_id)
        self.assertEqual(row["status"], "COMPLETED")
        self.assertTrue(db.get_hub(self.hub_id)["ports"][0]["is_available"])

    def test_B2_immediate_booking_respects_schedule(self):
        from shared.charging_reservations import select_charging_port
        from shared.identity import current_user_id
        body = self.window()
        self.reserve(body)
        due = datetime.fromisoformat(body["starts_at"])
        with patch("shared.charging_schedule.utc_now", return_value=due):
            with self.assertRaises(ValueError):
                select_charging_port(db, db.get_hub(self.hub_id), {
                    "personal_plate": "59OTHER", "charging_port": "TEST-S01",
                })

    def test_C2_relocation_action_and_failure_progress(self):
        def prepare(candidate):
            candidate.simulation_rules.append({"id": "RULE-DISPATCH", "active": True,
                "hub_ids": [self.hub_id], "threshold_pct": 85, "actions": [
                    {"type": "notify", "message": "Dispatch required"},
                    {"type": "relocation", "payload": {"source_hub_id": "missing",
                        "target_hub_id": self.hub_id, "bike_count": 1, "assigned_staff_id": "STF-01"}},
                ]})
        storage.commit(prepare)
        response = self.client.post("/api/v1/operator/automation/scan", headers=self.operator)
        self.assertEqual(response.status_code, 200, response.text)
        run = next(r for r in response.json()["items"] if r["hub_id"] == self.hub_id)
        self.assertEqual(run["status"], "WAITING_OPERATOR")
        self.assertEqual(len(run["progress"]), 1)
        self.client.put("/api/v1/operator/automation/runs/" + run["id"],
                        headers=self.operator, json={"action": "resume"})
        run = next(r for r in db.operator_mock["automation_runs"] if r["id"] == run["id"])
        self.assertEqual(len(run["progress"]), 1)

    def test_C3_manual_valid_and_reproducible(self):
        hub = {
            "hub_id": self.hub_id, "hub_code": "TEST-HUB", "name": "Test Hub",
            "total_parking_capacity": 10, "current_bikes": 0, "free_parking_slots": 1,
            "total_chargers": 2, "active_chargers": 1, "base_power_kw": 6.0,
            "available_power_kw": 10.0, "max_power_kw": 100.0,
        }
        one = self.simulation(source_type="MANUAL_A_PRIME", hub_snapshots=[hub])
        two = self.simulation(source_type="MANUAL_A_PRIME", hub_snapshots=[hub])
        self.assertEqual(one.status_code, 200, one.text)
        self.assertEqual(one.json()["hub_results"], two.json()["hub_results"])
        self.assertEqual(one.json()["hub_results"][0]["peak_requested_power_kw"], 9)

    def test_C4_upload_too_large_and_no_cross_account_mutation(self):
        before = copy.deepcopy(db.incidents)
        response = self.client.post("/api/v1/user/incidents/missing/photos",
            headers=self.user, content=b"x" * (2 * 1024 * 1024 + 65537))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(db.incidents, before)

    def test_TC_O03_backend_dispatch_and_staff_notification(self):
        response = self.client.post("/api/v1/operator/relocation/commands", headers=self.operator, json={
            "source_hub_id": "hub-02", "target_hub_id": "hub-04",
            "bike_count": 1, "assigned_staff_id": "STF-01",
        })
        self.assertEqual(response.status_code, 201, response.text)
        task_id = response.json()["id"]
        login = self.client.post("/api/v1/staff/auth/login", json={
            "username_or_phone": "staff_01", "password": "staff123"})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertEqual(login.json()["staff"]["id"], "STF-01")
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        messages = self.client.get("/api/v1/staff/notifications", headers=headers).json()["items"]
        self.assertTrue(any(n["reference_id"] == task_id for n in messages))
        listing = self.client.get("/api/v1/operator/relocation/commands", headers=self.operator).json()
        self.assertTrue(any(t["id"] == task_id for t in listing["items"]))

    def test_C1_battery_group_toggle(self):
        endpoint = f"/api/v1/operator/hubs/{self.hub_id}/devices"
        response = self.client.post(endpoint, headers=self.operator, json={
            "kind": "battery", "id": "TEST-B48", "name": "48V", "available_count": 3,
        })
        self.assertEqual(response.status_code, 201, response.text)
        for enabled, expected in ((False, 0), (False, 0), (True, 3)):
            response = self.client.put(endpoint + "/battery/TEST-B48",
                headers=self.operator, json={"enabled": enabled})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(db.get_hub(self.hub_id)["available_batteries"], expected)

    def test_B1_shared_bike_route_returns_available_bike(self):
        async def road(*args, **kwargs):
            return httpx.Response(200, request=httpx.Request("GET", "https://osrm.test/route"),
                json={"code": "Ok", "routes": [{"distance": 1000, "duration": 300,
                    "geometry": {"type": "LineString", "coordinates": [[106.8, 10.86], [106.81, 10.87]]}}]})
        with patch("httpx.AsyncClient.get", side_effect=road):
            response = self.client.post("/api/hubs/suggest-route", headers=self.user, json={
                "origin_lat": 10.86, "origin_lng": 106.80,
                "dest_lat": 10.87, "dest_lng": 106.81, "vehicle_type": "bike",
            })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNotNone(response.json()["recommended_bike"])
        self.assertNotEqual(response.json()["origin_hub"]["id"], response.json()["destination_hub"]["id"])

    def test_C2_actual_auto_dispatch_notification(self):
        def prepare(candidate):
            candidate.simulation_rules.append({"id": "RULE-DISPATCH", "active": True,
                "hub_ids": [self.hub_id], "threshold_pct": 85, "actions": [
                    {"type": "relocation", "payload": {"source_hub_id": "hub-02",
                        "target_hub_id": "hub-04", "bike_count": 1, "assigned_staff_id": "STF-01"}},
                ]})
        storage.commit(prepare)
        response = self.client.post("/api/v1/operator/automation/scan", headers=self.operator)
        run = next(r for r in response.json()["items"] if r["hub_id"] == self.hub_id)
        self.assertEqual(run["status"], "COMPLETED", run)
        task_id = run["progress"][0]["reference_id"]
        self.assertTrue(any(t["task_id"] == task_id for t in db.relocations))
        self.client.post("/api/v1/operator/automation/scan", headers=self.operator)
        self.assertEqual(sum(t["task_id"] == task_id for t in db.relocations), 1)
