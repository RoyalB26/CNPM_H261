"""
Schemas for Operator Management & Control
Smart E-Mobility Hub - ĐHQG-HCM
"""

from .auth import (
    OperatorLoginRequest,
    OperatorLoginResponse,
    OperatorAuthErrorResponse,
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
    EmergencyHaltErrorResponse,
    EmergencyHaltResponse,
)
from .relocation import (
    RelocationStatus,
    RelocationPriority,
    RelocationCommandCreate,
    RelocationCommandItem,
    RelocationCommandList,

    RelocationResponse,
)
from .maintenance import (
    FaultSeverity,
    MaintenanceStatus,
    MaintenanceTicketItem,
    MaintenanceAssignRequest,
    MaintenanceCreateRequest,
    MaintenanceTicketList,
    MaintenanceAssignResponse,
    MaintenanceErrorResponse,
)


from .hub_manage import (
    HubOperationalStatus,
    HubConfig,
    HubConfigUpdate,
    HubDeactivateRequest,
    HubManageList,
    HubConfigUpdateResponse,
    HubDeactivateResponse,
    HubErrorResponse,
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
    SimulationRunRequest,
    SimulationErrorResponse,
    SimulationSaveRuleResponse,
)

__all__ = [
    "OperatorLoginRequest",
    "OperatorLoginResponse",
    "OperatorAuthErrorResponse",
    "Operator2FARequest",
    "OperatorProfile",
    "OperatorTokenResponse",
    "AlertLevel",
    "KPISummary",
    "TelemetryEvent",
    "HubLiveStatus",
    "EmergencyHaltRequest",
    "EmergencyHaltErrorResponse",
    "EmergencyHaltResponse",
    "RelocationStatus",
    "RelocationPriority",
    "RelocationCommandCreate",
    "RelocationCommandItem",
    "RelocationCommandList",
    "RelocationResponse",



    "FaultSeverity",
    "MaintenanceStatus",
    "MaintenanceTicketItem",
    "MaintenanceAssignRequest",
    "MaintenanceCreateRequest",
    "MaintenanceTicketList",
    "MaintenanceAssignResponse",
    "MaintenanceErrorResponse",

    "HubOperationalStatus",
    "HubConfig",
    "HubConfigUpdate",
    "HubDeactivateRequest",
    "HubManageList",
    "HubConfigUpdateResponse",
    "HubDeactivateResponse",
    "HubErrorResponse",




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

    "SimulationRunRequest",
    "SimulationErrorResponse",
    "SimulationSaveRuleResponse",
]
