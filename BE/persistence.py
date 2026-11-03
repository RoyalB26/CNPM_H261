"""Lưu trạng thái db ra JSON cho backend Operator."""

import copy
import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from seed_loader import DEFAULT_SEED_PATH, SEED_TYPES, load_seed


class PersistenceError(RuntimeError):
    """Không thể lưu trạng thái xuống file."""


class JsonStateStore:
    def __init__(self, db, path):
        self.db = db
        self.path = Path(path).resolve()
        self._lock = RLock()

        if self.path == DEFAULT_SEED_PATH.resolve():
            raise ValueError(
                "File runtime phải khác file dữ liệu mẫu"
            )

    def snapshot(self):
        """Lấy bản sao dữ liệu, không lấy các thuộc tính kỹ thuật."""
        with self._lock:
            return copy.deepcopy({
                key: getattr(self.db, key)
                for key in SEED_TYPES
            })

    def _apply(self, state):
        """Giữ nguyên đối tượng db đang được các backend dùng chung."""
        self.db.__dict__.update(state)

    def reload(self):
        """Nạp trạng thái đã lưu; chỉ dùng seed khi chưa có file runtime."""
        with self._lock:
            try:
                self.path.stat()
            except FileNotFoundError:
                state = load_seed()
            else:
                # File có nhưng hỏng phải báo lỗi, không âm thầm về seed.
                state = load_seed(self.path)

            self._apply(state)

    def _write(self, state):
        """Ghi file tạm cùng thư mục, rồi thay thế file runtime."""
        temporary_path = None

        try:
            text = json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            ) + "\n"

            self.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                temporary_file.write(text)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            # Dùng lại loader hiện có để kiểm tra cấu trúc file đã ghi.
            load_seed(temporary_path)

            os.replace(temporary_path, self.path)
            temporary_path = None

        except (OSError, ValueError, TypeError) as exc:
            raise PersistenceError(
                "Không thể lưu trạng thái JSON"
            ) from exc

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def commit(self, change):
        """
        change chỉ được sửa candidate, không sửa db thật.

        Hàm change phải là hàm đồng bộ, không dùng await.
        """
        with self._lock:
            candidate = copy.copy(self.db)
            candidate.__dict__ = self.snapshot()

            # Lỗi nghiệp vụ/model xảy ra ở đây chưa làm đổi db thật.
            result = change(candidate)

            state = {
                key: getattr(candidate, key)
                for key in SEED_TYPES
            }

            self._write(state)
            self._apply(state)

            return result

    def reset_to_seed(self):
        """Chủ động xóa trạng thái hiện tại và lưu lại dữ liệu mẫu."""
        with self._lock:
            state = load_seed()
            self._write(state)
            self._apply(state)