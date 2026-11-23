"""Bổ sung chủ sở hữu cho dữ liệu một tài khoản cũ, không ghi đè chủ đã lưu."""


def assign_owner(record: dict, user_id: str) -> None:
    """Gắn chủ nếu thiếu; từ chối chủ rỗng hoặc không khớp quan hệ cha/con."""
    if 'user_id' not in record:
        record['user_id'] = user_id
    if not isinstance(record['user_id'], str) or not record['user_id'].strip():
        raise ValueError('user_id phải là chuỗi không rỗng')
    if record['user_id'] != user_id:
        raise ValueError('Chủ sở hữu của bản ghi liên kết không khớp')


def normalize_user_ownership(seed: dict) -> None:
    """Gắn dữ liệu legacy của bản demo một người cho tài khoản seed khi nạp.

    Không sửa file trên đĩa, không tạo tài khoản mới và không gán vé walk-in
    không rõ chủ cho User. Các chủ tường minh đã lưu được giữ nguyên.
    """
    seed_user_id = seed['user'].get('id')
    if not isinstance(seed_user_id, str) or not seed_user_id.strip():
        raise ValueError('Tài khoản seed thiếu id hợp lệ')
    bookings = seed['bookings']
    for booking in bookings:
        owner = booking.get('user_id', seed_user_id)
        assign_owner(booking, owner)
        for key in ('rental_trip', 'rental_invoice', 'charging_session', 'charging_invoice', 'battery_swap_invoice'):
            if booking.get(key) is not None:
                assign_owner(booking[key], owner)
    for report in seed['incidents']:
        assign_owner(report, report.get('user_id', seed_user_id))
    for session in seed['user'].get('active_services', {}).values():
        if session is not None:
            assign_owner(session, seed_user_id)
    for record in seed['parking_records']:
        linked = [b for b in bookings if record.get('booking_id') and b['id'] == record['booking_id']]
        if len(linked) == 1:
            assign_owner(record, linked[0]['user_id'])
        elif 'user_id' in record:
            assign_owner(record, record['user_id'])
