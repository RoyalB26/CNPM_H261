# Backend — Cấu trúc thư mục và luồng xử lý

## 1. Cấu trúc thư mục (Project Structure)

```text
BE/
├── run_all.py                 # Gateway tập hợp API User, Operator và Staff
├── mock_db.py                 # Store chung trong RAM, khởi tạo dữ liệu và xử lý CRUD
├── database.py                # Export lại db và MockDatabaseStore từ mock_db
├── seed_loader.py             # Đọc JSON, kiểm tra cấu trúc và kiểu dữ liệu seed
├── data/
│   └── mock_seed.json          # Dữ liệu mẫu chung và mẫu riêng của Operator
├── operator/					# Backend Operator; main.py, schemas và README riêng
├── user/                      # Backend User; main.py, schemas và README riêng
├── staff/                     # Backend Staff; main.py, schemas và README riêng
└── README.md                  # Cấu trúc BE và luồng xử lý tổng quan
```

## 2. Luồng xử lý (Request Flow)

**Khởi tạo dữ liệu:**

```text
mock_seed.json → seed_loader.load_seed() → MockDatabaseStore.reset() → db
```

**Xử lý API Operator:**

```text
Frontend gửi request → route → handler → schema kiểm tra đầu vào
→ kiểm tra nghiệp vụ, đọc/cập nhật db → schema response → JSONResponse
```

`main.py` tập hợp route; `handlers/` xử lý yêu cầu; `schemas/` định nghĩa và kiểm tra dữ liệu. Handler truy cập `db` qua `operator/store.py`; thao tác dữ liệu có thể nằm trong handler hoặc hàm của `mock_db.py`.

**Ví dụ chạy What-if:**

```text
POST /simulation/run → kiểm tra nguồn và cấu hình → lấy mẫu từ db.operator_mock
→ tính giá trị đỉnh, sinh ID/thời gian → thêm vào db.simulation_history → trả kết quả
```

Hiện kết quả biểu đồ What-if vẫn là dữ liệu mẫu. Dữ liệu phát sinh được lưu trong RAM, chưa ghi ngược xuống JSON; restart hoặc gọi `db.reset()` sẽ nạp lại seed. Khi chạy cùng gateway trong một tiến trình, ba backend dùng chung `db`.
