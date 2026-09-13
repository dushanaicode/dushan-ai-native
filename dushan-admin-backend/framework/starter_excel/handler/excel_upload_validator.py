import io
import struct
from pathlib import Path
from typing import BinaryIO
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile, ZipFile

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import iterparse
from openpyxl.utils.cell import coordinate_to_tuple

from framework.starter_excel.config.excel_settings import ExcelSettings
from framework.starter_excel.exception.excel_error import ExcelError
from framework.starter_excel.exception.excel_error_codes import ExcelErrorCodes
from framework.starter_excel.model.excel_upload import ExcelUpload


class ExcelUploadValidator:
    """先限制 ZIP 中央目录，再逐个验证解压量、CRC、XML 与真实单元格坐标。"""

    _MIME_TYPES = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
        "application/zip",
        "application/x-zip-compressed",
        "",
    }

    def __init__(self, settings: ExcelSettings) -> None:
        self.settings = settings

    def validate(self, upload: ExcelUpload) -> None:
        """借用上传流并恢复位置；不关闭调用方的流，也不解压到文件系统。"""
        if not upload.filename or Path(upload.filename).suffix.lower() != ".xlsx":
            raise ExcelError(ExcelErrorCodes.VALIDATION, "仅支持有效的 .xlsx 文件")
        mime = (upload.content_type or "").split(";", 1)[0].strip().lower()
        if mime not in self._MIME_TYPES:
            raise ExcelError(ExcelErrorCodes.VALIDATION, "XLSX 媒体类型无效")
        stream = upload.file
        if not stream.seekable():
            raise ExcelError(ExcelErrorCodes.VALIDATION, "XLSX 上传流必须支持定位")
        original = stream.tell()
        try:
            stream.seek(0, io.SEEK_END)
            size = stream.tell()
            if size > self.settings.max_upload_size_bytes:
                raise ExcelError(ExcelErrorCodes.LIMIT, "上传文件字节数超过限制")
            self._directory(stream, size)
            stream.seek(0)
            with ZipFile(stream) as archive:
                self._archive(archive)
        except (
            BadZipFile,
            ParseError,
            DefusedXmlException,
            OSError,
            ValueError,
            KeyError,
            struct.error,
        ) as exc:
            raise ExcelError(
                ExcelErrorCodes.VALIDATION, "XLSX 压缩结构或 XML 无效", cause=exc
            ) from exc
        finally:
            stream.seek(original)

    def _directory(self, stream: BinaryIO, size: int) -> None:
        """在 ZipFile 物化条目对象前扫描目录，包含 ZIP64 和伪造条目数校验。"""
        tail_size = min(size, 22 + 65535)
        stream.seek(size - tail_size)
        tail = stream.read(tail_size)
        offset = tail.rfind(b"PK\x05\x06")
        while offset >= 0:
            if offset + 22 <= len(tail):
                values = struct.unpack_from("<4s4H2LH", tail, offset)
                if offset + 22 + values[7] == len(tail):
                    break
            offset = tail.rfind(b"PK\x05\x06", 0, offset)
        if offset < 0:
            raise ValueError("缺少 ZIP 结束记录")
        if values[1] or values[2] or values[3] != values[4]:
            raise ValueError("不支持分卷 ZIP")
        count, directory_size, position = values[4:7]
        end = size - tail_size + offset
        if count == 0xFFFF or directory_size == 0xFFFFFFFF or position == 0xFFFFFFFF:
            stream.seek(end - 20)
            signature, disk, zip64_offset, disks = struct.unpack("<4sLQL", stream.read(20))
            if signature != b"PK\x06\x07" or disk or disks != 1:
                raise ValueError("ZIP64 定位记录无效")
            stream.seek(zip64_offset)
            record = struct.unpack("<4sQ2H2L4Q", stream.read(56))
            if record[0] != b"PK\x06\x06" or record[4] or record[5] or record[6] != record[7]:
                raise ValueError("ZIP64 结束记录无效")
            count, directory_size, position = record[7:10]
            end = zip64_offset
        if position + directory_size != end or end > size:
            raise ValueError("中央目录范围无效")
        actual = 0
        while position < end:
            stream.seek(position)
            header = stream.read(46)
            if len(header) != 46 or header[:4] != b"PK\x01\x02":
                raise ValueError("中央目录条目无效")
            position += 46 + sum(struct.unpack_from("<3H", header, 28))
            actual += 1
            if actual > self.settings.max_archive_entries:
                raise ExcelError(ExcelErrorCodes.LIMIT, "压缩条目数超过限制")
        if position != end or actual != count:
            raise ValueError("中央目录条目数或范围不一致")

    def _archive(self, archive: ZipFile) -> None:
        entries = archive.infolist()
        names = {entry.filename for entry in entries}
        if len(names) != len(entries):
            raise ValueError("ZIP 不允许重名条目")
        if not {"[Content_Types].xml", "xl/workbook.xml"}.issubset(names):
            raise ValueError("缺少 XLSX 工作簿结构")
        if sum(entry.file_size for entry in entries) > self.settings.max_uncompressed_size_bytes:
            raise ExcelError(ExcelErrorCodes.LIMIT, "解压总字节数超过限制")
        cells = 0
        for entry in entries:
            if entry.flag_bits & 1:
                raise ValueError("不支持加密 ZIP")
            if entry.filename.lower().endswith("vbaproject.bin"):
                raise ValueError("XLSX 不允许 VBA 资源")
            with archive.open(entry) as source:
                if entry.filename.endswith((".xml", ".rels")):
                    cells += self._xml(source, entry.filename)
                    if cells > self.settings.max_cells:
                        raise ExcelError(ExcelErrorCodes.LIMIT, "工作簿单元格总数超过限制")
                else:
                    while source.read(65536):
                        pass

    def _xml(self, source: BinaryIO, filename: str) -> int:
        cells = 0
        coordinates: set[str] = set()
        worksheet = filename.startswith("xl/worksheets/")
        for _, element in iterparse(source, events=("end",), forbid_dtd=True):
            if worksheet and element.tag.endswith("}row"):
                if not 1 <= int(element.attrib["r"]) <= self.settings.max_import_rows + 1:
                    raise ExcelError(ExcelErrorCodes.LIMIT, "工作表实际行坐标超过限制")
            if worksheet and element.tag.endswith("}c"):
                cells += 1
                if cells > self.settings.max_cells:
                    raise ExcelError(ExcelErrorCodes.LIMIT, "工作表单元格数超过限制")
                coordinate = element.attrib["r"]
                if coordinate in coordinates:
                    raise ValueError("工作表含重复单元格坐标")
                coordinates.add(coordinate)
                row, column = coordinate_to_tuple(coordinate)
                if (
                    not 1 <= row <= self.settings.max_import_rows + 1
                    or not 1 <= column <= self.settings.max_columns
                ):
                    raise ExcelError(ExcelErrorCodes.LIMIT, "工作表实际行列坐标超过限制")
            if (
                element.tag.endswith("}t")
                and len(element.text or "") > self.settings.max_cell_text_length
            ):
                raise ExcelError(ExcelErrorCodes.LIMIT, "单元格文本长度超过限制")
            element.clear()
        return cells
