from typing import Literal, Self

from pydantic import Field, model_validator

from framework.starter_config.config.config_model import ConfigModel
from framework.starter_config.decorator.config_decorator import config_model


@config_model("excel", env_prefix="EXCEL_")
class ExcelSettings(ConfigModel):
    """XLSX 资源上限和展示参数；默认值只由应用 YAML 提供。"""

    header_font_bold: bool
    header_font_size: int = Field(ge=1, le=72)
    auto_adjust_column_width: bool
    min_column_width: int = Field(ge=1, le=255)
    max_column_width: int = Field(ge=1, le=255)
    max_import_rows: int = Field(ge=1, le=1048575)
    max_concurrent_imports: int = Field(ge=1)
    max_export_rows: int = Field(ge=1, le=1048575)
    max_columns: int = Field(ge=1, le=16384)
    max_cells: int = Field(ge=1)
    max_upload_size_bytes: int = Field(ge=1)
    max_archive_entries: int = Field(ge=1)
    max_uncompressed_size_bytes: int = Field(ge=1)
    max_cell_text_length: int = Field(ge=1, le=32767)
    max_errors: int = Field(ge=1)
    max_dropdown_options: int = Field(ge=1, le=1048576)
    template_rows: int = Field(ge=1, le=1048575)
    money_decimal_places: int = Field(ge=2, le=8)
    formula_policy: Literal["reject", "literal"]
    unknown_columns: Literal["reject", "ignore"]

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        """保证列宽范围和模板行数可实现。"""
        if self.min_column_width > self.max_column_width:
            raise ValueError("min_column_width 不能大于 max_column_width")
        if self.template_rows > self.max_import_rows:
            raise ValueError("template_rows 不能大于 max_import_rows")
        return self
