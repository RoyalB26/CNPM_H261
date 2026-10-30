"""
Operator What-if Simulation Schemas
Smart E-Mobility Hub - ĐHQG-HCM
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class ScenarioType(str, Enum):
    DEMAND_SURGE = "Nhu cầu sạc tăng đột biến"
    PARKING_FULL = "Bãi đỗ đầy"
    CHARGER_FAILURE = "Trạm sạc gặp sự cố"
    FLEET_CONCENTRATION = "Phương tiện tập trung tại một khu vực"
    HUB_EXPANSION = "Mở rộng Hub"


class SourceStateType(str, Enum):
    LIVE_STATE_A = "LIVE_A"
    MANUAL_STATE_A_PRIME = "MANUAL_A_PRIME"


class HubStateSnapshot(BaseModel):
    hub_id: str = Field(..., example="HUB-01")
    hub_code: str = Field(..., example="HUB-01")
    name: str = Field(..., example="Hub Ga Metro A")
    total_parking_capacity: int = Field(100, example=100)
    current_bikes: int = Field(65, example=65)
    free_parking_slots: int = Field(35, example=35)
    total_chargers: int = Field(20, example=20)
    active_chargers: int = Field(18, example=18)
    base_power_kw: float = Field(200.0, example=200.0)
    max_power_kw: float = Field(1000.0, example=1000.0)


class SimulationSourceState(BaseModel):
    source_type: SourceStateType = Field(default=SourceStateType.LIVE_STATE_A)
    source_label: str = Field("Trạng thái mạng lưới hiện tại (A)", example="Trạng thái mạng lưới hiện tại (A)")
    hub_snapshots: List[HubStateSnapshot]


class SimulationScenarioConfig(BaseModel):
    scenario_name: str = Field(..., example="Nhu cầu sạc tăng cao")
    scenario_type: ScenarioType = Field(default=ScenarioType.DEMAND_SURGE)
    demand_increase_pct: int = Field(50, ge=-50, le=300, example=50)
    duration_minutes: int = Field(60, ge=10, le=360, example=60)
    start_time: str = Field("18:00", example="18:00")
    affected_chargers_count: int = Field(2, ge=0, example=2)
    lost_power_kw: float = Field(50.0, ge=0.0, example=50.0)
    target_fill_rate_pct: int = Field(95, ge=0, le=100, example=95)
    additional_bikes_count: int = Field(30, ge=0, example=30)
    is_input_valid: bool = True
    is_grid_state_loaded: bool = True


class SimulationValidationResult(BaseModel):
    is_valid: bool
    error_code: Optional[str] = Field(None, example="EX-10-01")
    error_type: Optional[str] = Field(None, example="INVALID_INPUT")
    message: str = Field(..., example="Dữ liệu đầu vào hợp lệ")
    details: Optional[str] = None


class HubLoadPoint(BaseModel):
    time_label: str = Field(..., example="17:00")
    metro_hub_load_pct: int = Field(..., example=48)
    bachkhoa_hub_load_pct: int = Field(..., example=42)
    warning_threshold_pct: int = Field(85, example=85)


class PowerLoadPoint(BaseModel):
    time_label: str = Field(..., example="17:00")
    power_kw: float = Field(..., example=75.0)
    station_limit_kw: float = Field(180.0, example=180.0)


class DispatchRecommendationItem(BaseModel):
    title: str = Field(..., example="Điều chuyển xe khẩn cấp")
    source_hub: Optional[str] = Field("Hub KTX Khu A", example="Hub KTX Khu A")
    target_hub: Optional[str] = Field("Hub Ga Metro A", example="Hub Ga Metro A")
    bike_count: Optional[int] = Field(20, example=20)
    vehicle_type: Optional[str] = Field("Xe đạp điện", example="Xe đạp điện")
    details: List[str] = Field(default_factory=list)


class SimulationResultResponse(BaseModel):
    simulation_id: str = Field(..., example="SIM-109")
    scenario_name: str = Field(..., example="Nhu cầu sạc tăng 50%")
    status: str = Field("Hoàn thành", example="Hoàn thành")
    executed_at: str = Field(..., example="22/10/2026")
    load_chart_data: List[HubLoadPoint]
    power_chart_data: List[PowerLoadPoint]
    peak_power_kw: float = Field(185.0, example=185.0)
    peak_metro_load_pct: int = Field(92, example=92)
    overloaded_hubs: str = Field("2 / 12", example="2 / 12")
    overloaded_chargers: str = Field("15 / 60", example="15 / 60")
    metro_deficit_bikes: int = Field(35, example=35)
    recommendations: List[DispatchRecommendationItem]


class SimulationSaveRuleRequest(BaseModel):
    simulation_id: str = Field(..., example="SIM-109")
    rule_name: str = Field(..., example="Kịch bản ứng phó vỡ trận ga Metro giờ cao điểm")
    operation_instructions: str = Field(..., example="Điều chuyển xe từ Hub KTX Khu A sang Hub Ga Metro.")
    auto_match_on_high_load: bool = Field(True)


class SimulationHistoryItem(BaseModel):
    id: str = Field(..., example="SIM-108")
    title: str = Field(..., example="Tăng sinh viên giờ cao điểm Metro")
    parameters_summary: str = Field(..., example="Tham số: Nhu cầu +150%, Hub Metro A hỏng 3 cổng")
    executed_at: str = Field(..., example="10/10/2026 16:30")
    duration_str: str = Field("45s", example="45s")
    created_by: str = Field("Nguyen Van A", example="Nguyen Van A")
    status: str = Field("Thành công", example="Thành công")
    what_if_params: str = Field(..., example="Nhu cầu tăng +150%, 3 cổng sạc hỏng tại Hub Metro A, Thời gian giả định: 2 giờ.")
    recorded_result: str = Field(..., example="2 Hub vượt ngưỡng 85% tải, thiếu hụt 35 xe đạp điện tại các trạm kết nối.")
    saved_rule: str = Field(..., example="Tự động gửi lệnh điều chuyển 20 xe từ Hub KTX A sang Metro A khi nhu cầu > 80%.")


class SimulationHistoryList(BaseModel):
    total: int = 28
    items: List[SimulationHistoryItem]
