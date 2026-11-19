import importlib.util
from pathlib import Path
from typing import Any, Iterator

import pytest
from starlette.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
RUN_ALL_PATH = ROOT_DIR / "BE" / "run_all.py"

USER_API = "/api/v1/user"
OPERATOR_API = "/api/v1/operator"
STAFF_API = "/api/v1/staff"


def _load_unified_app():
    # Load app from run_all.py 
    spec = importlib.util.spec_from_file_location("be_run_all", RUN_ALL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Can not push Gateway from {RUN_ALL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


@pytest.fixture(scope="session")
def unified_app():
    """Active only one time for all unit tests"""
    return _load_unified_app()


@pytest.fixture()
def api_client(unified_app) -> Iterator[TestClient]:
    """Clear step to test"""
    with TestClient(unified_app) as client:
        yield client


def find_hub_in_db(store: Any, hub_id: str) -> dict[str, Any]:
    """Helper to fine hub """
    candidates = [hub_id, hub_id.lower(), hub_id.upper()]
    if "-" in hub_id:
        suffix = hub_id.split("-")[-1]
        candidates.extend([f"hub-{suffix}", f"HUB-{suffix}"])

    for candidate in candidates:
        if hasattr(store, "get_hub"):
            hub = store.get_hub(candidate)
            if hub is not None:
                return hub

    hubs = getattr(store, "hubs", [])
    items = hubs.values() if isinstance(hubs, dict) else hubs
    for hub in items:
        if str(hub.get("id", "")).lower() == hub_id.lower():
            return hub
    raise AssertionError(f"Can't find Hub '{hub_id}' in mock_db")


def read_first_key(data: dict[str, Any], keys: tuple[str, ...]) -> Any:
    """Read first key to cancel fast"""
    for key in keys:
        if key in data:
            return data[key]
    raise KeyError(f"Can't find key name: {keys} in data: {list(data.keys())}")