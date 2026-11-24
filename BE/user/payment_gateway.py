"""VNPAY 2.1.0, URL có chữ ký và IPN đối chiếu dữ liệu đã lưu."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import uuid4
from starlette.responses import JSONResponse
from starlette.routing import Route
from shared.database import db, persist_change
from shared.notifications import notify
from .payments import PaymentError, validate_final_invoice
from .schemas.payment import PaymentProcessResult

VN_TIMEZONE = timezone(timedelta(hours=7))


def utc_now():
    return datetime.now(timezone.utc)


def configuration():
    values = {key: os.environ.get("VNPAY_" + key, "") for key in ("TMN_CODE", "HASH_SECRET", "RETURN_URL")}
    if not all(values.values()):
        raise PaymentError("Cần cấu hình VNPAY_TMN_CODE, VNPAY_HASH_SECRET và VNPAY_RETURN_URL", 503)
    values["PAYMENT_URL"] = os.environ.get("VNPAY_PAYMENT_URL", "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html")
    return values


def signed_query(params):
    return urlencode(sorted((key, value) for key, value in params.items()
        if key.startswith("vnp_") and key not in ("vnp_SecureHash", "vnp_SecureHashType") and value != ""))


def sign(params, secret):
    return hmac.new(secret.encode(), signed_query(params).encode(), hashlib.sha512).hexdigest()


def find_invoice(store, invoice_id, owner_id):
    matches = [(booking, key, booking[key]) for booking in store.bookings
        for key in ("rental_invoice", "charging_invoice", "battery_swap_invoice")
        if booking.get("user_id") == owner_id and (booking.get(key) or {}).get("id") == invoice_id
        and (booking.get(key) or {}).get("user_id") == owner_id]
    if not matches:
        raise PaymentError("Không tìm thấy hóa đơn dịch vụ", 404)
    if len(matches) != 1:
        raise PaymentError("Mã hóa đơn không duy nhất", 409)
    return matches[0]


def eligible_invoice(booking, key, invoice):
    personal = (booking.get("personal_bundle") and key == "charging_invoice"
                and booking.get("status") == "Đang sử dụng"
                and (booking.get("charging_session") or {}).get("status") == "Hoàn thành")
    if booking.get("status") != "Hoàn thành" and not personal:
        raise PaymentError("Dịch vụ chưa kết thúc", 409)
    if invoice.get("status") not in ("unpaid", "pending") or invoice.get("payment_channel") != "online":
        raise PaymentError("Hóa đơn đã xử lý hoặc không hỗ trợ thanh toán online", 409)
    validate_final_invoice(booking, key, invoice)


def create_payment(store, payment, ip_address="127.0.0.1"):
    booking, key, invoice = find_invoice(store, payment.invoice_id, store.user["id"])
    eligible_invoice(booking, key, invoice)
    if payment.method == "cash_guard":
        raise PaymentError("Hóa đơn này dùng cổng thanh toán online", 409)
    amount = invoice["total_amount"]
    if payment.amount is not None and payment.amount != amount:
        raise PaymentError("Số tiền không khớp hóa đơn", 409)
    if amount == 0:
        reference = "FREE-" + uuid4().hex
        invoice.update(status="paid", transaction_id=reference, paid_at=utc_now().isoformat(),
                       payment_method=payment.method)
        return PaymentProcessResult(transaction_id=reference, status="completed",
                                    message="Đã tất toán hóa đơn 0 đồng")
    config = configuration()
    intents = store.operator_mock.setdefault("payment_intents", [])
    pending = next((i for i in intents if i["invoice_id"] == invoice["id"] and i["status"] == "PENDING"), None)
    if pending:
        if datetime.fromisoformat(pending["expires_at"]) <= utc_now():
            raise PaymentError("Phiên thanh toán hết hạn, cần đối soát kết quả trước khi tạo lại", 409)
        if pending["amount"] != amount:
            raise PaymentError("Hóa đơn thay đổi trong khi chờ thanh toán", 409)
        return PaymentProcessResult(transaction_id=pending["id"], status="pending",
            payment_url=pending["payment_url"], expires_at=pending["expires_at"],
            message="Tiếp tục phiên thanh toán đang chờ")
    now = utc_now()
    expires = now + timedelta(minutes=15)
    reference = uuid4().hex
    params = {
        "vnp_Version": "2.1.0", "vnp_Command": "pay", "vnp_TmnCode": config["TMN_CODE"],
        "vnp_Amount": str(amount * 100), "vnp_CurrCode": "VND", "vnp_TxnRef": reference,
        "vnp_OrderInfo": "Thanh toan hoa don " + invoice["id"], "vnp_OrderType": "other",
        "vnp_Locale": "vn", "vnp_ReturnUrl": config["RETURN_URL"], "vnp_IpAddr": ip_address,
        "vnp_CreateDate": now.astimezone(VN_TIMEZONE).strftime("%Y%m%d%H%M%S"),
        "vnp_ExpireDate": expires.astimezone(VN_TIMEZONE).strftime("%Y%m%d%H%M%S"),
    }
    url = config["PAYMENT_URL"] + "?" + signed_query(params) + "&vnp_SecureHash=" + sign(params, config["HASH_SECRET"])
    intent = {"id": reference, "invoice_id": invoice["id"], "user_id": store.user["id"],
              "amount": amount, "method": payment.method, "merchant": config["TMN_CODE"],
              "status": "PENDING", "created_at": now.isoformat(), "expires_at": expires.isoformat(),
              "payment_url": url}
    intents.append(intent)
    invoice["status"] = "pending"
    return PaymentProcessResult(transaction_id=reference, status="pending", payment_url=url,
        expires_at=expires.isoformat(), message="Chờ kết quả xác nhận từ VNPAY")


def ipn_result(code, message):
    return JSONResponse({"RspCode": code, "Message": message})


async def vnpay_ipn(request):
    try:
        config = configuration()
    except PaymentError:
        return ipn_result("99", "Merchant not configured")
    pairs = list(request.query_params.multi_items())
    if len({k for k, _ in pairs}) != len(pairs):
        return ipn_result("97", "Duplicate parameter")
    params = dict(pairs)
    supplied = params.get("vnp_SecureHash", "")
    if not supplied or not hmac.compare_digest(sign(params, config["HASH_SECRET"]), supplied.lower()):
        return ipn_result("97", "Invalid signature")
    if params.get("vnp_TmnCode") != config["TMN_CODE"]:
        return ipn_result("97", "Invalid merchant")

    def change(candidate):
        intents = candidate.operator_mock.get("payment_intents", [])
        intent = next((i for i in intents if i["id"] == params.get("vnp_TxnRef")), None)
        if intent is None:
            return ipn_result("01", "Order not found")
        if params.get("vnp_CurrCode", "VND") != "VND":
            return ipn_result("04", "Invalid currency")
        if params.get("vnp_Amount") != str(intent["amount"] * 100):
            return ipn_result("04", "Invalid amount")
        if intent["merchant"] != params["vnp_TmnCode"]:
            return ipn_result("97", "Merchant mismatch")
        try:
            booking, key, invoice = find_invoice(candidate, intent["invoice_id"], intent["user_id"])
        except PaymentError:
            return ipn_result("01", "Invoice not found")
        transaction = params.get("vnp_TransactionNo", "")
        if intent["status"] == "PAID":
            return ipn_result("02", "Order already confirmed") if transaction == intent.get("provider_transaction_id") else ipn_result("99", "Transaction mismatch")
        if intent["status"] != "PENDING":
            return ipn_result("02", "Order already processed")
        try:
            eligible_invoice(booking, key, invoice)
        except PaymentError:
            return ipn_result("99", "Invoice state mismatch")
        if invoice["total_amount"] != intent["amount"]:
            return ipn_result("04", "Invoice amount mismatch")
        successful = params.get("vnp_ResponseCode") == "00" and params.get("vnp_TransactionStatus") == "00"
        if successful:
            if not transaction.isascii() or not transaction.isdigit() or int(transaction) <= 0:
                return ipn_result("99", "Invalid transaction reference")
            if any(i.get("provider_transaction_id") == transaction and i["status"] == "PAID" for i in intents):
                return ipn_result("99", "Transaction already used")
            try:
                paid_at = datetime.strptime(params["vnp_PayDate"], "%Y%m%d%H%M%S").replace(tzinfo=VN_TIMEZONE)
                if not datetime.fromisoformat(intent["created_at"]) - timedelta(seconds=60) <= paid_at <= datetime.fromisoformat(intent["expires_at"]):
                    raise ValueError()
            except (ValueError, KeyError):
                return ipn_result("99", "Invalid payment time")
            intent.update(status="PAID", provider_transaction_id=transaction, paid_at=paid_at.isoformat())
            invoice.update(status="paid", transaction_id=transaction, paid_at=paid_at.isoformat(),
                           payment_method=intent["method"])
            notify(candidate, "paid:" + intent["id"], intent["user_id"], "Thanh toán hóa đơn thành công", invoice["id"])
        else:
            if not params.get("vnp_ResponseCode") or not params.get("vnp_TransactionStatus"):
                return ipn_result("99", "Missing transaction status")
            intent.update(status="FAILED", response_code=params["vnp_ResponseCode"])
            invoice["status"] = "unpaid"
        return ipn_result("00", "Confirm success")
    return persist_change(change)


routes = [Route("/api/v1/payments/vnpay/ipn", vnpay_ipn, methods=["GET"])]
