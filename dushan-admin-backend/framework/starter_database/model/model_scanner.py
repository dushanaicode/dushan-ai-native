from framework.common.component.component_metadata import ComponentMetadata
from framework.common.enums.component_type_enum import ComponentTypeEnum
from framework.starter_scanner.annotation.scanner_decorator import scanner


class ModelScanner:
    """多个独立模型声明共用一个发现标记，各声明仍自行拒绝重复装饰。"""

    @staticmethod
    def mark(model):
        metadata = vars(model).get(ComponentMetadata.ATTRIBUTE)
        if metadata is None:
            return scanner(model)
        if metadata != ComponentMetadata(ComponentTypeEnum.COMPONENT):
            raise ValueError("模型与已有扫描类别冲突")
        return model
