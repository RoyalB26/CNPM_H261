# Backend — Cấu trúc thư mục và luồng xử lý

## 1. Cấu trúc thư mục (Project Structure)

```text
BE/
├── run_all.py                 # Gateway tập hợp API User, Operator và Staff
├── mock_db.py                 # Store chung trong RAM, khởi tạo dữ liệu và xử lý CRUD
├── database.py                # Đầu mối db và bộ lưu JSON chung
├── persistence.py             # Ghi file tạm, kiểm tra rồi thay thế runtime
├── shared_persistence.py      # Lưu thay đổi User/Staff tại gateway
├── seed_loader.py             # Đọc JSON, kiểm tra cấu trúc và kiểu dữ liệu seed
├── data/
│   ├── mock_seed.json          # Dữ liệu mẫu chung và mẫu riêng của Operator
│   └── runtime_db.json         # Trạng thái đã lưu; không đưa vào Git
├── operator/                  # Backend Operator; main.py, schemas và README riêng
├── user/                      # Backend User; main.py, schemas và README riêng
├── staff/                     # Backend Staff; main.py, schemas và README riêng
└── README.md                  # Cấu trúc BE và luồng xử lý tổng quan
```

## 2. Luồng xử lý (Request Flow)

**Khởi tạo dữ liệu:**

```text
database.py → storage.reload() → runtime_db.json nếu có; nếu chưa có dùng mock_seed.json → db
```

**Xử lý API Operator:**

```text
Frontend gửi request → route → handler → schema kiểm tra đầu vào
→ kiểm tra nghiệp vụ → đọc db hoặc persist_change() để lưu cập nhật
→ JSONResponse (chỉ báo cập nhật thành công sau khi ghi JSON)
```

`main.py` tập hợp route; `handlers/` xử lý yêu cầu; `schemas/` định nghĩa và kiểm tra dữ liệu. Handler truy cập `db` qua `operator/store.py`; thao tác dữ liệu có thể nằm trong handler hoặc hàm của `mock_db.py`.

**Ví dụ chạy What-if:**

```text
POST /simulation/run → kiểm tra nguồn và cấu hình → lấy mẫu từ db.operator_mock
→ tính giá trị đỉnh, sinh ID/thời gian → persist_change() thêm lịch sử trên bản sao
→ ghi runtime_db.json thành công → cập nhật db → trả kết quả
```

Hiện kết quả biểu đồ What-if vẫn là dữ liệu mẫu. Khi chạy chung bằng `python -B BE/run_all.py` với một tiến trình phục vụ API, ba backend dùng chung `db` và lưu trạng thái vào `BE/data/runtime_db.json`. Có thể đổi đường dẫn bằng biến môi trường `BE_RUNTIME_PATH`. Khởi động lại sẽ nạp runtime; runtime hỏng sẽ báo lỗi thay vì âm thầm nạp seed.

Runtime được tạo ở lần ghi thành công đầu tiên; các lần sau cập nhật cùng file. Lịch sử What-if nằm trong `simulation_history`, lệnh điều chuyển trong `relocations`; không ghi đè `mock_seed.json`. Để kiểm tra lưu dài hạn: tạo phiên/lệnh qua API, restart gateway rồi đọc lại bằng `GET /api/v1/operator/simulation/history` và `GET /api/v1/operator/relocation/commands`.

Operator ghi qua `persist_change()` trong handler. Middleware tại gateway lưu các thay đổi trong `db` của request User/Staff dùng POST, PUT, PATCH hoặc DELETE trước khi gửi response thành công; nếu ghi thất bại thì trả 503 và phục hồi RAM. Dữ liệu nằm trong biến riêng ngoài `db`, như `staff.DB`, không được lưu bởi cơ chế này. Chạy riêng User/Staff sẽ không có middleware lưu của gateway.

`storage.reload()` nạp lại trạng thái đã lưu; `storage.reset_to_seed()` chủ động ghi seed vào runtime và cập nhật RAM. `db.reset()` cũ chỉ nạp seed vào RAM, nên không dùng để khởi động lại hệ thống trong luồng bình thường. File seed được quản lý bằng Git; runtime và file tạm được bỏ qua.
