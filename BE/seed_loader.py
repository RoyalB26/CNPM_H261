"""Tạo Loader đọc json từ mock_seed.json, nạp vô reset()"""

import json
from pathlib import Path
from typing import Any


DEFAULT_SEED_PATH = (
    Path(__file__).resolve().parent / "data" / "mock_seed.json"
)


SEED_TYPES = {
    "hubs": list,
    "user": dict,
    "bookings": list,
    "staff": list,
    "relocations": list,
    "next_relocation_number": int,
    "maintenance_tickets": list,
    "parking_records": list,
    "incidents": list,
    "simulation_rules": list,
    "simulation_history": list,
    "telemetry_events": list,
    "operator_mock": dict,
}


class SeedLoadError(ValueError):
    """file seed bij thiếu, k0 đọc được hoặc sai cấu trúc"""


def reject_duplicate_keys(
        pairs: list[tuple[str, Any]],
)                   -> dict[str, Any]:

    """Từ chối key trùng, tránh data bị ghi đè"""

    result = {}

    for key, value in pairs:
        if key in result:
            raise SeedLoadError(f"Key bi trung trong json {key}")

        result[key] = value

    return result




def require_type(container: dict[str, Any],
                 key: str,
                 expected_type: type,
                 location: str,
                ) -> None:
    """ Check 1  trường hợp bắt buộc, ktra type của nó"""

    field_path = f"{location}.{key}"

    if key not in container:
        raise SeedLoadError(f"Thiếu trường: {field_path}")

    if type(container[key]) is not expected_type:
        raise SeedLoadError(
            f"{field_path} phải có kiểu {expected_type.__name__}"
            )




def load_seed(
        seed_path: str | Path |None = None,
)   -> dict[str, Any]:

    """Đọc seed mới mỗi lần gọi"""

    path = (
        DEFAULT_SEED_PATH if seed_path is None
        else Path(seed_path)
    ) 

    try:
        text = path.read_text(encoding="utf-8-sig")
    except(OSError, UnicodeError) as exc:
        raise SeedLoadError(
            f"không đọc được file seed {path}: {exc}"
        )


    try:
        seed = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise SeedLoadError(
            f"Json không hợp lệ tại{path}, "
            f"dòng {exc.lineno}, cột {exc.colno}: {exc.msg}"
        ) from exc


    if type(seed) is not dict:
        raise SeedLoadError(f"Gốc của file seed phải là objec Json")

    for key, expected_type in SEED_TYPES.items():
        require_type(seed, key, expected_type, "seed")


    extra_keys = set(seed) - set(SEED_TYPES)

    if extra_keys:
        raise SeedLoadError(
            f"Key gốc not support: {sorted(extra_keys)}"
        )

    if seed["next_relocation_number"] < 1:
        raise SeedLoadError(
            "seed.next_relocation_number phải lớn hơn 0"
        )

    operator_mock = seed["operator_mock"]

    require_type(operator_mock, "auth", dict, "seed.operator_mock")

    require_type(operator_mock, 
                 "simulation_result_template",
                 dict,
                 "seed.operator_mock")

    auth = operator_mock["auth"]

    require_type(auth,
                 "profile",
                 dict,
                 "seed.operator_mock.auth")

    require_type(auth,
                 "token",
                 dict,
                 "seed.operator_mock.auth")

    template = operator_mock["simulation_result_template"]

    for key in ("load_chart_data",
                "power_chart_data",
                "recommendations",
            ):
        require_type(
            template,
            key,
            list,
            "seed.operator_mock.simulation_result_template"
        )


    return seed