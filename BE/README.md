# Backend — Hướng dẫn làm việc chung

Backend dùng Starlette, Pydantic và store RAM có lưu JSON. User, Operator và Staff dùng chung dữ liệu khi chạy trong cùng gateway; chưa dùng database thật.

## 1. Chạy hệ thống

Mở terminal tại `CNPM_H261/` (thư mục chứa `requirements.txt`):

```powershell
pip install -r requirements.txt
python -B BE/run_all.py
```

Gateway: `http://127.0.0.1:8000`. API chính có tiền tố `/api/v1/user`, `/api/v1/operator`, `/api/v1/staff`. Xem endpoint cụ thể trong README và biến `routes` ở `main.py` của từng phần.

**Dùng gateway để test liên thông.** Chạy riêng từng backend tạo store RAM độc lập; User/Staff chạy riêng không có middleware lưu JSON của gateway. Cơ chế hiện tại dành cho một tiến trình phục vụ API, không chạy nhiều worker cùng ghi runtime.

## 2. Cấu trúc và nơi sửa

```text
BE/
├── run_all.py              # Ghép route và middleware của ba backend
├── mock_db.py              # Export lại store, giữ import cũ của User/Staff
├── shared/
│   ├── __init__.py
│   ├── database.py         # Đầu mối db, storage, persist_change
│   ├── memory_store.py     # Store RAM, singleton db và CRUD chung
│   ├── json_store.py       # Commit, reload, ghi file an toàn
│   ├── seed_loader.py      # Đọc và kiểm tra cấu trúc JSON
│   └── middleware.py       # Lưu thay đổi User/Staff tại gateway
├── data/
│   ├── mock_seed.json      # Dữ liệu mẫu, quản lý bằng Git
│   └── runtime_db.json     # Trạng thái phát sinh, không đưa vào Git
├── operator/              # main.py, handlers/, schemas/, store.py
├── user/                  # Hiện handler nằm trong main.py; schemas/ riêng
├── staff/                 # Hiện handler nằm trong main.py; schemas/ riêng
└── README.md
```

User/Staff có thể tách handler theo cách tổ chức của Operator. Giữ biến `routes` ở `main.py` để gateway ghép API, giữ hợp đồng request/response với FE. Thay đổi `shared/` và cấu trúc dữ liệu cần thống nhất với cả nhóm.

## 3. Quy tắc đọc và lưu dữ liệu

```text
Khởi động → shared/database.py → nạp runtime nếu có, nếu chưa có thì nạp seed → db

Request → route/handler → kiểm tra schema và nghiệp vụ → đọc/cập nhật store → response
```

- **User/Staff hiện tại:** `from mock_db import db` vẫn dùng store chung. Qua gateway, middleware lưu thay đổi trong `db` của request POST/PUT/PATCH/DELETE có HTTP 2xx trước khi gửi response. Request lỗi được phục hồi RAM; ghi file thất bại trả HTTP 503.
- **Operator:** handler dùng `operator/store.py`, ghi qua `persist_change(change)`. Hàm `change(candidate)` phải đồng bộ, chỉ sửa `candidate`; ghi JSON thành công rồi mới cập nhật `db`. Nếu áp dụng mẫu này cho luồng mới, phải trả nguyên response lỗi từ `persist_change` khi lưu thất bại.
- Chỉ tạo singleton `db` tại `shared/memory_store.py`. Không tạo store riêng hoặc gán lại `db`. Import bên ngoài package dùng `shared.*`, bên trong dùng import tương đối; không trộn với `BE.shared.*`.
- GET chỉ đọc. Lỗi nghiệp vụ phải trả HTTP 4xx/5xx; middleware xét HTTP status, không xét cờ lỗi trong body. Không giữ lâu tham chiếu list/dict bên trong `db`, vì commit/reload có thể thay chúng.

Runtime mặc định: `BE/data/runtime_db.json`, đổi được qua biến môi trường `BE_RUNTIME_PATH`. File được tạo ở lần ghi thành công đầu tiên; restart nạp lại runtime. Runtime hỏng sẽ báo lỗi, không tự quay về seed. Không ghi dữ liệu phát sinh vào seed.

`storage.reload()` đọc lại từ đĩa. `storage.reset_to_seed()` ghi đè runtime bằng seed và cập nhật RAM, chỉ dùng khi chủ động reset demo. `db.reset()` chỉ reset RAM.


## 4. Kiểm tra trước khi bàn giao

- Chạy gateway, gọi API cả ba vai trò; kiểm tra ca hợp lệ và ca lỗi, đúng HTTP status.
- Operator tạo điều chuyển → Staff đọc đúng ID và xử lý → Operator đọc lại đúng tiến độ/trạng thái.
- User báo sự cố → Operator thấy phiếu và phân công → Staff xử lý → Operator đọc lại kết quả.
- Kiểm tra đặt/trả xe và bãi đỗ có cập nhật tài nguyên chung đúng nghiệp vụ.
- Restart gateway rồi đọc lại dữ liệu vừa thay đổi; request lỗi không để lại thay đổi dở dang. Test lỗi lưu bằng runtime thử qua `BE_RUNTIME_PATH`.

Đây là tiêu chí kiểm chứng tích hợp, không phải cam kết mọi luồng hiện tại đã hoàn thiện. Xem thêm README của [Operator](operator/README.md), [User](user/README.md) và [Staff](staff/README.md).
