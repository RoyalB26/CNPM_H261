"""Fixture token theo role và IPN có chữ ký cho runtime kiểm thử tạm."""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from urllib.parse import urlencode
from uuid import uuid4

VNPAY_TEST_CONFIG = {
    'VNPAY_TMN_CODE': 'USERTEST',
    'VNPAY_HASH_SECRET': 'test-only-user-integration-secret',
    'VNPAY_RETURN_URL': 'http://localhost:3000/payment-result',
}


def authorize_client(client, db):
    """Cấp session fixture, vẫn đi qua middleware kiểm tra token/quyền thật.

    Kiểm thử login, đăng ký và 2FA riêng nằm trong bộ test Auth của nhóm.
    Fixture không tạo tài khoản hoặc ghi runtime khi chỉ kiểm tra GET.
    """
    from shared.authentication import issue_session
    users = {
        'user': {'id': db.__dict__['user']['id'], 'role': 'user'},
        'operator': {'id': db.operator_mock['auth']['profile']['id'], 'role': 'operator'},
        'staff': {'id': 'STF-02', 'role': 'staff'},
    }
    tokens = {role: issue_session(account) for role, account in users.items()}
    original = client.request

    def request(method, url, **kwargs):
        path = str(url)
        role = 'operator' if '/api/v1/operator/' in path else 'staff' if '/api/v1/staff/' in path else 'user'
        kwargs['headers'] = {'Authorization': 'Bearer ' + tokens[role], **(kwargs.get('headers') or {})}
        return original(method, url, **kwargs)

    client.request = request


def confirm_payment(client, db, invoice_id, result):
    """Hoàn tất bằng IPN ký độc lập; không gọi mạng/cổng VNPAY thực."""
    if result.get('status') == 'completed':
        return
    invoice = next(b[key] for b in db.bookings
                   for key in ('rental_invoice', 'charging_invoice', 'battery_swap_invoice')
                   if (b.get(key) or {}).get('id') == invoice_id)
    params = {
        'vnp_TmnCode': VNPAY_TEST_CONFIG['VNPAY_TMN_CODE'],
        'vnp_TxnRef': result['transaction_id'], 'vnp_Amount': str(invoice['total_amount'] * 100),
        'vnp_ResponseCode': '00', 'vnp_TransactionStatus': '00',
        'vnp_TransactionNo': str(uuid4().int),
        'vnp_PayDate': datetime.now(timezone(timedelta(hours=7))).strftime('%Y%m%d%H%M%S'),
    }
    params['vnp_SecureHash'] = hmac.new(VNPAY_TEST_CONFIG['VNPAY_HASH_SECRET'].encode(),
                                      urlencode(sorted(params.items())).encode(), hashlib.sha512).hexdigest()
    response = client.get('/api/v1/payments/vnpay/ipn', params=params)
    assert response.status_code == 200 and response.json()['RspCode'] == '00', response.text
