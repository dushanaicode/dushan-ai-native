from dataclasses import dataclass

from framework.starter_data_permission.model.data_permission_frame import DataPermissionFrame


@dataclass(slots=True, repr=False)
class DataExemption:
    frame: DataPermissionFrame
    resource: str
    operation: str
    active: bool = True
