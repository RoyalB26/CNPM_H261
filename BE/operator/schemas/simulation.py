"""Model dữ liệu cho các API mô phỏng What-if của Operator."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScenarioType(str, Enum):
    """Các tình huống mô phỏng được mô tả trong hệ thống."""

    DEMAND_SURGE = "Nhu cầu sạc tăng đột biến"
    PARKING_FULL = "Bãi đỗ đầy"
    CHARGER_FAILURE = "Trạm sạc gặp sự cố"
    FLEET_CONCENTRATION = "Phương tiện tập trung tại một khu vực"
    HUB_EXPANSION = "Mở rộng Hub"


class SourceStateType(str, Enum):
    """Nguồn dữ liệu dùng làm đầu vào mô phỏng."""

    LIVE_STATE_A = "LIVE_A"
    MANUAL_STATE_A_PRIME = "MANUAL_A_PRIME"


class HubStateSnapshot(BaseModel):
    """Ảnh chụp trạng thái một Hub tại thời điểm mô phỏng."""

    hub_id: str = Field(..., min_length=1, examples=["hub-01"])
    hub_code: str = Field(..., min_length=1, examples=["HUB-01"])
    name: str = Field(..., min_length=1, examples=["Hub Ga Metro ĐHQG"])

    total_parking_capacity: int = Field(
        ..., strict=True, gt=0, examples=[20]
    )
    current_bikes: int = Field(
        ..., strict=True, ge=0, examples=[3]
    )
    free_parking_slots: int = Field(
        ..., strict=True, ge=0, examples=[6]
    )
    total_chargers: int = Field(
        ..., strict=True, ge=0, examples=[4]
    )
    active_chargers: int = Field(
        ..., strict=True, ge=0, examples=[3]
    )
    base_power_kw: float = Field(
        ..., strict=True, ge=0, allow_inf_nan=False, examples=[10.85]
    )
    max_power_kw: float = Field(
        ..., strict=True, gt=0, allow_inf_nan=False, examples=[100.0]
    )


class SimulationSourceState(BaseModel):
    """Nguồn dữ liệu và thông tin thời điểm chụp trạng thái."""

    source_type: SourceStateType
    source_label: str = Field(
        ..., examples=["Snapshot từ store; công suất nền ước tính"]
    )
    captured_at: str = Field(
        ..., examples=["2026-11-03T10:00:00+00:00"]
    )
    power_basis: str = Field(
        ..., examples=["Ước tính 50% tổng công suất cổng sẵn sàng"]
    )
    hub_snapshots: List[HubStateSnapshot]


class SimulationScenarioConfig(BaseModel):
    """Cấu hình tình huống; bản cơ bản hỗ trợ tăng nhu cầu sạc."""

    model_config = ConfigDict(extra="forbid")

    scenario_name: str = Field(
        ..., min_length=1, pattern=r"\S",
        examples=["Nhu cầu sạc tăng 50%"]
    )
    scenario_type: ScenarioType = ScenarioType.DEMAND_SURGE
    demand_increase_pct: int = Field(
        default=50, ge=-50, le=300, examples=[50]
    )
    duration_minutes: int = Field(
        default=60, ge=10, le=360, examples=[60]
    )
    start_time: str = Field(default="18:00", examples=["18:00"])

    # Các tham số này phải bằng 0 với tình huống tăng nhu cầu thuần túy.
    affected_chargers_count: int = Field(default=0, ge=0, examples=[0])
    lost_power_kw: float = Field(
        default=0.0, ge=0, allow_inf_nan=False, examples=[0.0]
    )
    target_fill_rate_pct: int = Field(default=95, ge=0, le=100)
    additional_bikes_count: int = Field(default=0, ge=0, examples=[0])

    # Giữ tương thích dữ liệu cũ; BE tự kiểm tra thay vì tin hai cờ này.
    is_input_valid: bool = True
    is_grid_state_loaded: bool = True


class SimulationRunRequest(BaseModel):
    """Đầu vào chung cho kiểm tra tham số và chạy mô phỏng."""

    model_config = ConfigDict(extra="forbid")

    source_type: SourceStateType = SourceStateType.LIVE_STATE_A
    hub_snapshots: Optional[List[HubStateSnapshot]] = None
    config: SimulationScenarioConfig

    # Cờ kiểm thử lỗi timeout, chưa phải kết nối IoT thực.
    trigger_timeout_error: bool = Field(
        default=False, strict=True, examples=[False]
    )


class SimulationValidationResult(BaseModel):
    """Kết quả kiểm tra hợp lệ kèm dữ liệu đã chuẩn hóa."""

    is_valid: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Dữ liệu đầu vào hợp lệ"])
    source: SimulationSourceState
    config: SimulationScenarioConfig


class SimulationErrorResponse(BaseModel):
    """Lỗi API mô phỏng, giữ mã nghiệp vụ EX-10-01 và EX-10-02."""

    status_code: str = Field(..., examples=["422"])
    error: int = Field(default=1, examples=[1])
    detail: str = Field(..., examples=["Thiếu cấu hình mô phỏng"])
    is_valid: bool = False
    error_code: str = Field(..., examples=["EX-10-01"])
    error_type: str = Field(..., examples=["INVALID_INPUT"])
    message: str = Field(..., examples=["Dữ liệu mô phỏng không hợp lệ"])


class HubLoadPoint(BaseModel):
    """Một điểm dữ liệu trên biểu đồ tải Hub."""

    time_label: str = Field(..., examples=["18:00"])
    metro_hub_load_pct: int = Field(..., examples=[81])
    bachkhoa_hub_load_pct: int = Field(..., examples=[51])
    warning_threshold_pct: int = Field(default=85, examples=[85])


class PowerLoadPoint(BaseModel):
    """Một điểm dữ liệu trên biểu đồ công suất."""

    time_label: str = Field(..., examples=["18:00"])
    power_kw: float = Field(..., examples=[160.0])
    station_limit_kw: float = Field(default=180.0, examples=[180.0])


class DispatchRecommendationItem(BaseModel):
    """Đề xuất được trình bày trong kết quả mô phỏng."""

    title: str = Field(..., examples=["Điều chuyển xe khẩn cấp"])
    source_hub: Optional[str] = None
    target_hub: Optional[str] = None
    bike_count: Optional[int] = None
    vehicle_type: Optional[str] = None
    details: List[str] = Field(default_factory=list)


class SimulationResultResponse(BaseModel):
    """Kết quả mô phỏng; đánh dấu rõ khi dùng dữ liệu mẫu."""

    simulation_id: str = Field(..., examples=["SIM-ABC123"])
    scenario_name: str = Field(..., examples=["Nhu cầu sạc tăng 50%"])
    status: str = Field(..., examples=["Hoàn thành (dữ liệu mẫu)"])
    executed_at: str = Field(
        ..., examples=["2026-11-03T10:00:00+00:00"]
    )
    is_mock: bool = Field(..., examples=[True])
    result_basis: str = Field(
        ..., examples=["Biểu đồ mẫu, chưa tính theo snapshot/config"]
    )

    load_chart_data: List[HubLoadPoint]
    power_chart_data: List[PowerLoadPoint]
    peak_power_kw: float
    peak_metro_load_pct: int
    overloaded_hubs: str
    overloaded_chargers: str
    metro_deficit_bikes: int
    recommendations: List[DispatchRecommendationItem]


class SimulationSaveRuleRequest(BaseModel):
    """Yêu cầu lưu quy tắc tham chiếu tới một phiên đã chạy."""

    model_config = ConfigDict(extra="forbid")

    simulation_id: str = Field(
        ..., min_length=1, pattern=r"\S", examples=["SIM-ABC123"]
    )
    rule_name: str = Field(
        ..., min_length=1, pattern=r"\S",
        examples=["Ứng phó cao điểm tại Ga Metro"]
    )
    operation_instructions: str = Field(
        ..., min_length=1, pattern=r"\S",
        examples=["Điều chuyển xe từ Hub KTX sang Hub Ga Metro."]
    )
    auto_match_on_high_load: bool = Field(
        default=True, strict=True, examples=[True]
    )


class SimulationSaveRuleResponse(BaseModel):
    """Kết quả lưu quy tắc vào store."""

    success: bool = Field(..., examples=[True])
    message: str = Field(..., examples=["Đã lưu quy tắc vào store"])
    rule_id: str = Field(..., examples=["RULE-ABC123"])
    simulation_id: str = Field(..., examples=["SIM-ABC123"])
    history_id: str = Field(..., examples=["SIM-ABC123"])


class SimulationHistoryItem(BaseModel):
    """Một phiên mô phỏng và dữ liệu phục vụ xem lại."""

    id: str = Field(..., examples=["SIM-ABC123"])
    title: str = Field(..., examples=["Nhu cầu sạc tăng 50%"])
    parameters_summary: str
    executed_at: str
    duration_str: str
    created_by: str
    status: str
    what_if_params: str
    recorded_result: str
    saved_rule: str = ""

    # Seed cũ chưa lưu đủ các trường này.
    source: Optional[SimulationSourceState] = None
    config: Optional[SimulationScenarioConfig] = None
    result: Optional[SimulationResultResponse] = None


class SimulationHistoryList(BaseModel):
    """Danh sách lịch sử với tổng số bản ghi thực tế."""

    total: int = Field(..., ge=0, examples=[1])
    items: List[SimulationHistoryItem]