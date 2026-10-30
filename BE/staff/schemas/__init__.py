"""
Schemas for Staff Workflows (Relocation, Maintenance, Security Guard)
Smart E-Mobility Hub - ĐHQG-HCM
"""

from .auth import (
    StaffRole,
    StaffLoginRequest,
    StaffProfile,
    StaffTokenResponse,
)
from .relocation import (
    BikeChecklistStatus,
    BikeChecklistItem,
    RelocationTaskDetail,
    BikeScanRequest,
    RelocationHandoverRequest,
    RelocationIncidentRequest,
)
from .maintenance import (
    MaintenancePriority,
    ResolutionOutcome,
    MaintenanceTaskSummary,
    MaintenanceTaskDetail,
    DeviceVerifyRequest,
    MaintenanceResolveRequest,
    MaintenanceIncidentRequest,
)
from .parking import (
    VehicleCheckInRequest,
    VehicleCheckInResponse,
    VehicleCheckOutLookup,
    VehicleCheckOutResponse,
    ParkingTransactionItem,
    ShiftReconciliationSummary,
    ShiftCloseRequest,
)

__all__ = [
    "StaffRole",
    "StaffLoginRequest",
    "StaffProfile",
    "StaffTokenResponse",
    "BikeChecklistStatus",
    "BikeChecklistItem",
    "RelocationTaskDetail",
    "BikeScanRequest",
    "RelocationHandoverRequest",
    "RelocationIncidentRequest",
    "MaintenancePriority",
    "ResolutionOutcome",
    "MaintenanceTaskSummary",
    "MaintenanceTaskDetail",
    "DeviceVerifyRequest",
    "MaintenanceResolveRequest",
    "MaintenanceIncidentRequest",
    "VehicleCheckInRequest",
    "VehicleCheckInResponse",
    "VehicleCheckOutLookup",
    "VehicleCheckOutResponse",
    "ParkingTransactionItem",
    "ShiftReconciliationSummary",
    "ShiftCloseRequest",
]
