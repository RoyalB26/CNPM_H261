"""Lưu thay đổi User/Staff khi chạy qua gateway chung.

Dành cho các HTTP API JSON hiện tại, một tiến trình phục vụ.
Các thay đổi Operator đã dùng persist_change trong handler.
"""

import asyncio

from .database import db, storage, persist_change


class SharedPersistenceMiddleware:
    def __init__(self, app):
        self.app = app
        self._request_lock = asyncio.Lock()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Cho các request dùng chung db chạy lần lượt.
        async with self._request_lock:
            path = scope.get("path", "")
            method = scope.get("method", "GET")

            should_track = (
                method in {"POST", "PUT", "PATCH", "DELETE"}
                and not path.startswith("/api/v1/operator/")
            )

            if not should_track:
                await self.app(scope, receive, send)
                return

            before = storage.snapshot()
            messages = []

            async def capture(message):
                # Giữ response lại đến khi lưu xong.
                messages.append(message)

            try:
                await self.app(scope, receive, capture)

                response_start = next(
                    message
                    for message in messages
                    if message["type"] == "http.response.start"
                )

                if 200 <= response_start["status"] < 300:
                    after = storage.snapshot()

                    if after != before:
                        # Trả RAM về trạng thái cũ để commit thực hiện
                        # ghi file trước, rồi mới áp dụng trạng thái mới.
                        db.__dict__.update(before)

                        def change(candidate):
                            candidate.__dict__.update(after)

                        failure_response = persist_change(change)

                        if failure_response is not None:
                            await failure_response(scope, receive, send)
                            return
                else:
                    db.__dict__.update(before)

            except BaseException:
                db.__dict__.update(before)
                raise

            for message in messages:
                await send(message)
