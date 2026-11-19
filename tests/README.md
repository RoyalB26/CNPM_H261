# Test Setup Guide

## 1. Yêu cầu môi trường

- Windows 10/11
- Python 3.10+ (khuyến nghị Python 3.11)
- Git

## 2. Clone project

```bash
git clone https://github.com/RoyalB26/CNPM_H261.git
cd CNPM_H261
```

## 3. Tạo môi trường ảo

```bash
python -m venv .venv
```

Kích hoạt môi trường ảo:

**Windows PowerShell:**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD:**

```cmd
.venv\Scripts\activate.bat
```

## 4. Cài đặt dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Cài đặt thêm các thư viện phục vụ kiểm thử:

```bash
pip install -r requirements-test.txt
```

Cài đặt trình duyệt Chromium cho Playwright:

```bash
playwright install chromium
```

## 5. Chạy kiểm thử

Chạy toàn bộ test:

```bash
pytest tests -v -s
```

Chạy riêng Unit/API Test:

```bash
pytest tests/unit -v -s
```

Chạy riêng E2E Test:

```bash
pytest tests/e2e -v -s
```

**Chạy E2E Test và mở giao diện Chromium:**

```bash
pytest tests/e2e -v -s --headed --browser chromium
```

Ở chế độ này, Playwright sẽ tự động mở cửa sổ trình duyệt Chromium và thực hiện các thao tác kiểm thử trên giao diện. Có thể quan sát trực tiếp quá trình chuyển trang, đăng nhập và tương tác của hệ thống.

Chạy một test cụ thể và mở giao diện:

```bash
pytest tests/e2e/test_user_flow.py -v -s --headed --browser chromium
```

Chạy test với 20 lượt kiểm tra NFR11 (PowerShell):

```powershell
$env:NFR11_RUNS="20"
pytest tests -v -s
```

## 6. Lưu ý

- E2E test tự động khởi chạy Backend (`127.0.0.1:8000`) và Frontend (`127.0.0.1:3000`) thông qua fixture trong `tests/e2e/conftest.py`.
- Không cần khởi chạy server thủ công trước khi chạy test.
- Đảm bảo hai port `8000` và `3000` không bị chương trình khác sử dụng.
- Dữ liệu Mock Database được reset trước và sau mỗi test thông qua fixture trong `tests/conftest.py`.
- Kết quả test được hiển thị trực tiếp trên terminal.
- Mặc định, Playwright chạy trình duyệt ở chế độ ẩn (`headless`). Sử dụng `--headed` nếu muốn quan sát giao diện trong quá trình kiểm thử.
