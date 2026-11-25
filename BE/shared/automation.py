"""Phiên ứng phó tải cao và vòng quét nền dùng chung khóa Gateway."""
import asyncio
import copy
import logging
from datetime import datetime, timezone
from uuid import uuid4
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from .notifications import notify
from .memory_store import RelocationError
from .charging_schedule import reconcile_schedule

logger = logging.getLogger(__name__)


def validate_rule(store, hub_ids, actions):
    if len(set(hub_ids)) != len(hub_ids) or not set(hub_ids).issubset({h["id"] for h in store.hubs}):
        raise ValueError("Hub trong quy tắc không hợp lệ")
    from BE.operator.schemas.relocation import RelocationCommandCreate
    for action in actions:
        if action.get("type") == "relocation":
            try:
                RelocationCommandCreate.model_validate(action.get("payload"))
            except ValidationError:
                raise ValueError("Hành động điều chuyển không đúng cấu trúc")
        elif action.get("type") == "notify":
            if not isinstance(action.get("message"), str) or not action["message"].strip():
                raise ValueError("Thông báo cần nội dung")
        else:
            raise ValueError("Chỉ hỗ trợ hành động relocation hoặc notify")


def hub_load(hub):
    parking = 100 * (hub["parking_capacity"] - hub.get("available_parking", 0)) / hub["parking_capacity"]
    power = 100 * hub.get("power_demand_kw", 0) / hub["max_power_kw"]
    return max(parking, power)


def scan_automation(store):
    runs = store.operator_mock.setdefault("automation_runs", [])
    episodes = store.operator_mock.setdefault("load_episodes", {})
    if store.operator_mock.get("emergency_halt", False):
        return runs
    for hub in store.hubs:
        load = hub_load(hub)
        current_id = episodes.get(hub["id"])
        if hub["status"] != "ACTIVE" or load < hub.get("load_warning_threshold_pct", 85):
            if current_id:
                run = next(r for r in runs if r["id"] == current_id)
                run["load_cleared_at"] = datetime.now(timezone.utc).isoformat()
                episodes.pop(hub["id"])
            continue
        if current_id:
            continue
        rule = next((r for r in store.simulation_rules if r.get("active")
                     and (not r.get("hub_ids") or hub["id"] in r["hub_ids"])
                     and load >= r.get("threshold_pct", 85) and r.get("actions")), None)
        run = {"id": "AUTO-" + uuid4().hex, "hub_id": hub["id"],
               "load_pct": load, "rule_id": rule["id"] if rule else None,
               "status": "RUNNING", "progress": [], "created_at": datetime.now(timezone.utc).isoformat()}
        runs.append(run)
        episodes[hub["id"]] = run["id"]
        if rule is None:
            run.update(status="WAITING_OPERATOR", error="Chưa có quy tắc thực thi phù hợp")
        else:
            execute_actions(store, run, rule)
        notify(store, run["id"], "operator", "Phiên tải cao: " + run["status"], run["id"])
    return runs


def execute_actions(store, run, rule):
    from BE.operator.schemas.relocation import RelocationCommandCreate
    try:
        validate_rule(store, rule.get("hub_ids", []), rule["actions"])
        for index, action in enumerate(rule["actions"]):
            if any(p["index"] == index and p["status"] == "COMPLETED" for p in run["progress"]):
                continue
            if action["type"] == "relocation":
                payload = RelocationCommandCreate.model_validate(action["payload"]).model_dump(mode="json")
                task = store.create_relocation_command(payload)
                reference = task["task_id"]
            else:
                reference = run["id"]
                notify(store, run["id"] + ":action:" + str(index), "operator", action["message"], reference)
            run["progress"].append({"index": index, "status": "COMPLETED", "reference_id": reference})
        run["status"] = "COMPLETED"
        run.pop("error", None)
    except (ValueError, HTTPException, RelocationError) as exc:
        run.update(status="WAITING_OPERATOR", error=getattr(exc, "detail", str(exc)))


async def sweep_operations(storage, request_lock):
    async with request_lock:
        before = storage.snapshot()
        candidate = copy.copy(storage.db)
        candidate.__dict__ = copy.deepcopy(before)
        reconcile_schedule(candidate)
        scan_automation(candidate)
        if candidate.__dict__ != before:
            def change(next_state):
                next_state.__dict__.update(candidate.__dict__)
            storage.commit(change)


async def run_operations_worker(storage, request_lock, interval=5):
    while True:
        try:
            await sweep_operations(storage, request_lock)
        except Exception:
            logger.exception("Quét lịch sạc/tải cao thất bại, thử lại ở lượt kế tiếp")
        await asyncio.sleep(interval)
