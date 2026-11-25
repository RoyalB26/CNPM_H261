"""Phí theo giờ bắt đầu, báo giá có chữ ký và hiệu lực 5 phút."""
import base64
import hashlib
import hmac
import json
import math
import os
import secrets
from datetime import datetime, timedelta, timezone
from starlette.exceptions import HTTPException
from .parking_reservations import plate_key

QUOTE_SECRET = os.environ.get("PARKING_QUOTE_SECRET", "").encode() or secrets.token_bytes(32)


def utc_now():
    return datetime.now(timezone.utc)


def parking_time(value):
    try:
        moment = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        try:
            moment = datetime.strptime(value, "%d/%m/%Y · %H:%M")
        except (ValueError, TypeError):
            raise HTTPException(409, "Mốc thời gian gửi xe không hợp lệ")
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone(timedelta(hours=7)))
    return moment.astimezone(timezone.utc)


def find_ticket(store, identifier):
    matches = [r for r in store.parking_records if r["ticket_code"] == identifier]
    if not matches:
        matches = [r for r in store.parking_records if plate_key(r["plate_number"]) == plate_key(identifier)]
        opened = [r for r in matches if r.get("checkout_time") is None]
        matches = opened or matches
    if not matches:
        raise HTTPException(404, "Vé gửi xe không tồn tại")
    if len(matches) != 1:
        raise HTTPException(409, "Cần mã vé để xác định duy nhất lượt gửi xe")
    return matches[0]


def parking_rate(store, record):
    rate = record.get("parking_hourly_rate")
    if rate is None:
        hub = store.get_hub(record["hub_id"])
        if hub is None:
            raise HTTPException(409, "Hub của vé không tồn tại")
        slot = next((s for s in hub.get("slots", []) if s["id"] == record["slot_id"]), {})
        rate = slot.get("hourly_rate", hub.get("pricing", {}).get("parking_hourly"))
    if type(rate) is not int or rate < 0:
        raise HTTPException(409, "Đơn giá gửi xe không hợp lệ")
    return rate


def calculate_fee(checkin_time, checkout_time, rate):
    seconds = (parking_time(checkout_time) - parking_time(checkin_time)).total_seconds()
    if seconds < 0:
        raise HTTPException(409, "Giờ ra phải sau giờ vào")
    minutes = math.ceil(seconds / 60)
    hours = math.ceil(seconds / 3600)
    return {"elapsed_minutes": minutes, "billable_hours": hours,
            "parking_fee": hours * rate, "duration_display": f"{minutes // 60} giờ {minutes % 60:02d} phút"}


def signature(data):
    return hmac.new(QUOTE_SECRET, data.encode(), hashlib.sha256).hexdigest()


def checkout_quote(store, record, now=None):
    now = now or utc_now()
    if record.get("checkout_time") is not None:
        return {**record, "quote_token": None}
    rate = parking_rate(store, record)
    checkout_at = now.isoformat()
    fee = calculate_fee(record["checkin_time"], checkout_at, rate)
    payload = {"ticket_code": record["ticket_code"], "checkin_time": record["checkin_time"],
               "checkout_time": checkout_at, "parking_hourly_rate": rate, **fee,
               "expires_at": (now + timedelta(minutes=5)).isoformat()}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    return {**record, **payload, "quote_token": encoded + "." + signature(encoded)}


def verified_quote(store, record, token):
    try:
        encoded, supplied = token.split(".")
        if not hmac.compare_digest(signature(encoded), supplied):
            raise ValueError()
        quote = json.loads(base64.urlsafe_b64decode(encoded))
        if (quote["ticket_code"] != record["ticket_code"] or quote["checkin_time"] != record["checkin_time"]
                or parking_time(quote["expires_at"]) < utc_now()
                or parking_time(quote["checkout_time"]) > utc_now()
                or (record.get("parking_hourly_rate") is not None
                    and quote["parking_hourly_rate"] != record["parking_hourly_rate"])):
            raise ValueError()
        expected = calculate_fee(record["checkin_time"], quote["checkout_time"], quote["parking_hourly_rate"])
        if any(quote[k] != v for k, v in expected.items()):
            raise ValueError()
        return quote
    except (ValueError, TypeError, KeyError):
        raise HTTPException(409, "Báo giá không hợp lệ hoặc hết hạn, cần xem trước lại")
