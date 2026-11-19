"""Fixtures cho lớp kiểm thử E2E & NFR Nhóm 1 (Playwright).

Tự động khởi chạy Unified Backend (cổng 8000) và Frontend Static Server (cổng 3000),
chặn tài nguyên CDN/bản đồ bên ngoài để tránh treo `networkidle` hoặc sập WebGL,
và cung cấp helper an toàn cho window.alert / chuyển tab.
"""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
from pathlib import Path
import re
import socket
import threading
import time
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Dialog, Page, Route
import pytest
import uvicorn

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
FE_DIR = ROOT_DIR / "FE"
RUN_ALL_PATH = ROOT_DIR / "BE" / "run_all.py"

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000

BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
USER_URL = f"{FRONTEND_URL}/user/"
OPERATOR_URL = f"{FRONTEND_URL}/operator/"
STAFF_URL = f"{FRONTEND_URL}/staff/"

ACTIVE_CLASS_RE = re.compile(r"\bactive\b")
SHOW_CLASS_RE = re.compile(r"\bshow\b")


def _is_port_open(host: str, port: int) -> bool:
    """Kiểm tra cổng TCP đã có tiến trình lắng nghe hay chưa."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    """Đợi máy chủ lắng nghe sẵn sàng trước khi mở trình duyệt Playwright."""
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if _is_port_open(host, port):
            return
        time.sleep(0.1)
    raise RuntimeError(f"Máy chủ tại {host}:{port} không phản hồi sau {timeout}s")


def _load_gateway_app():
    """Nạp Starlette Gateway app từ BE/run_all.py."""
    spec = importlib.util.spec_from_file_location("be_run_all_e2e", RUN_ALL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Không thể nạp Backend Gateway từ {RUN_ALL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


class _QuietHandler(SimpleHTTPRequestHandler):
    """Tắt log HTTP tĩnh để giữ đầu ra Pytest gọn gàng."""

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


@pytest.fixture(scope="session", autouse=True)
def live_servers() -> Iterator[None]:
    """Khởi động Backend (8000) và Frontend (3000) cho toàn bộ phiên E2E."""
    uvicorn_server: uvicorn.Server | None = None
    http_server: ThreadingHTTPServer | None = None

    if not _is_port_open(BACKEND_HOST, BACKEND_PORT):
        app = _load_gateway_app()
        config = uvicorn.Config(
            app,
            host=BACKEND_HOST,
            port=BACKEND_PORT,
            log_level="error",
        )
        uvicorn_server = uvicorn.Server(config)
        be_thread = threading.Thread(target=uvicorn_server.run, daemon=True)
        be_thread.start()
        _wait_for_port(BACKEND_HOST, BACKEND_PORT)

    if not _is_port_open(FRONTEND_HOST, FRONTEND_PORT):
        handler_cls = partial(_QuietHandler, directory=str(FE_DIR))
        http_server = ThreadingHTTPServer((FRONTEND_HOST, FRONTEND_PORT), handler_cls)
        fe_thread = threading.Thread(target=http_server.serve_forever, daemon=True)
        fe_thread.start()
        _wait_for_port(FRONTEND_HOST, FRONTEND_PORT)

    yield

    if http_server is not None:
        http_server.shutdown()
        http_server.server_close()
    if uvicorn_server is not None:
        uvicorn_server.should_exit = True


def block_external_requests(target: Page | BrowserContext) -> None:
    """Chặn các request ngoài localhost/127.0.0.1 (CDN/tiles bản đồ) để test nhanh và không crash."""

    def _route_handler(route: Route) -> None:
        url = route.request.url
        if url.startswith("http://127.0.0.1") or url.startswith("http://localhost") or url.startswith("data:"):
            route.continue_()
        else:
            route.abort()

    target.route("**/*", _route_handler)


def attach_dialog_collector(page: Page) -> list[str]:
    """Tự động chấp nhận window.alert/confirm và lưu thông điệp để assert."""
    messages: list[str] = []

    def _handle_dialog(dialog: Dialog) -> None:
        messages.append(dialog.message)
        dialog.accept()

    page.on("dialog", _handle_dialog)
    return messages


def wait_for_new_dialog(page: Page, dialogs: list[str], previous_count: int, timeout_ms: int = 5000) -> str:
    """Đợi cho tới khi xuất hiện hộp thoại alert mới thay vì sleep cố định."""
    deadline = time.perf_counter() + (timeout_ms / 1000.0)
    while time.perf_counter() < deadline:
        if len(dialogs) > previous_count:
            return dialogs[-1]
        page.wait_for_timeout(100)
    raise AssertionError(f"Không nhận được hộp thoại alert sau {timeout_ms}ms. Hiện có: {dialogs}")


def switch_operator_tab(page: Page, keyword: str) -> None:
    """Chuyển tab Operator an toàn theo nút `.menu-item` chứa từ khóa trong thuộc tính onclick."""
    menu_btn = page.locator(f".menu-item[onclick*='{keyword}']").first
    if menu_btn.count():
        menu_btn.click()
        return

    # Fallback: gọi trực tiếp switchTab với ID có tiền tố `tab-`
    tab_id = keyword if keyword.startswith("tab-") else f"tab-{keyword}"
    page.evaluate(f"() => {{ OperatorApp.switchTab('{tab_id}'); }}")


def login_end_user(page: Page) -> None:
    """Đăng nhập End-User bằng tài khoản seed hợp lệ và đợi vào màn hình chính."""
    block_external_requests(page)
    page.goto(USER_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#screen-login.active", timeout=10000)

    if page.locator("#loginPhone").count():
        page.fill("#loginPhone", "0123456789")
    if page.locator("#loginPassword").count():
        page.fill("#loginPassword", "123456")

    page.evaluate("() => { void App.handleLogin(); }")
    page.wait_for_selector("#screen-map-home.active", timeout=10000)


def open_operator_dashboard(page: Page) -> list[str]:
    """Mở Dashboard Operator, chặn CDN ngoài và vượt qua lớp 2FA (nếu hiển thị)."""
    block_external_requests(page)
    dialogs = attach_dialog_collector(page)
    page.goto(OPERATOR_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#kpiTotalHubs", state="attached", timeout=10000)

    login_overlay = page.locator("#operatorLoginView.show")
    if login_overlay.count() and login_overlay.is_visible():
        prev = len(dialogs)
        page.evaluate("() => { void OperatorApp.completeLogin(); }")
        wait_for_new_dialog(page, dialogs, prev, timeout_ms=5000)
        page.wait_for_selector("#operatorLoginView.show", state="detached", timeout=5000)

    return dialogs


@pytest.fixture()
def incognito_context(browser: Browser) -> Iterator[BrowserContext]:
    """Tạo context ẩn danh sạch (không cookie, không cache) cho TC-U01."""
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    block_external_requests(context)
    yield context
    context.close()