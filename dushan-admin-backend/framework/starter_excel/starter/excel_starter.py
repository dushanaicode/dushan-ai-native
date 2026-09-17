from loguru import logger

from framework.starter_excel.reader.excel_reader import ExcelReader
from framework.starter_excel.writer.excel_writer import ExcelWriter


class ExcelStarter:
    """构造本应用唯一的导入导出实例，交给 DI 作为预定义实例提供。"""

    @staticmethod
    def initialize(settings):
        logger.info("【ExcelStarter 】开始装配导入导出能力")
        reader, writer = ExcelReader(settings), ExcelWriter(settings)
        logger.debug(
            "【ExcelStarter 】导入行数={} 并发={} 文件上限={} bytes；导出行数={} 列数={} 单元格={}",
            settings.max_import_rows,
            settings.max_concurrent_imports,
            settings.max_upload_size_bytes,
            settings.max_export_rows,
            settings.max_columns,
            settings.max_cells,
        )
        logger.info("【ExcelStarter 】导入器、并发控制和导出器装配完成")
        return {ExcelReader: reader, ExcelWriter: writer}
