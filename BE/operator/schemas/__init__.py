"""
Schemas for Operator Management & Control
Smart E-Mobility Hub - ĐHQG-HCM
"""

from .auth import (
    OperatorLoginRequest,
    Operator2FARequest,
    OperatorProfile,
    OperatorTokenResponse,
)
from .dashboard import (
    AlertLevel,
    KPISummary,
    TelemetryEvent,
    HubLiveStatus,
    EmergencyHaltRequest,
    EmergencyHaltResponse,
)
from .relocation import (
    RelocationStatus,
    RelocationPriority,
    RelocationCommandCreate,
    RelocationCommandItem,
    RelocationCommandList,
)
from .maintenance import (
    FaultSeverity,
    MaintenanceStatus,
    MaintenanceTicketItem,
    MaintenanceAssignRequest,
    MaintenanceCreateRequest,
    MaintenanceTicketList,
)
from .hub_manage import (
    HubOperationalStatus,
    HubConfig,
    HubConfigUpdate,
    HubDeactivateRequest,
    HubManageList,
)
from .simulation import (
    ScenarioType,
    SourceStateType,
    HubStateSnapshot,
    SimulationSourceState,
    SimulationScenarioConfig,
    SimulationValidationResult,
    HubLoadPoint,
    PowerLoadPoint,
    DispatchRecommendationItem,
    SimulationResultResponse,
    SimulationSaveRuleRequest,
    SimulationHistoryItem,
    SimulationHistoryList,
)

__all__ = [
    "OperatorLoginRequest",
    "Operator2FARequest",
    "OperatorProfile",
    "OperatorTokenResponse",
    "AlertLevel",
    "KPISummary",
    "TelemetryEvent",
    "HubLiveStatus",
    "EmergencyHaltRequest",
    "EmergencyHaltResponse",
    "RelocationStatus",
    "RelocationPriority",
    "RelocationCommandCreate",
    "RelocationCommandItem",
    "RelocationCommandList",
    "FaultSeverity",
    "MaintenanceStatus",
    "MaintenanceTicketItem",
    "MaintenanceAssignRequest",
    "MaintenanceCreateRequest",
    "MaintenanceTicketList",
    "HubOperationalStatus",
    "HubConfig",
    "HubConfigUpdate",
    "HubDeactivateRequest",
    "HubManageList",
    "ScenarioType",
    "SourceStateType",
    "HubStateSnapshot",
    "SimulationSourceState",
    "SimulationScenarioConfig",
    "SimulationValidationResult",
    "HubLoadPoint",
    "PowerLoadPoint",
    "DispatchRecommendationItem",
    "SimulationResultResponse",
    "SimulationSaveRuleRequest",
    "SimulationHistoryItem",
    "SimulationHistoryList",
]
