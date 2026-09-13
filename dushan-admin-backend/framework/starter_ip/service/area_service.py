import csv
import hashlib
import json
from pathlib import Path
from threading import RLock

from framework.starter_di.decorators.components import service
from framework.starter_di.enums.component_scope_enum import ComponentScopeEnum
from framework.starter_ip.enum.area_type_enum import AreaTypeEnum
from framework.starter_ip.exception.ip_error_code_constants import IpErrorCodeConstants
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.model.area import Area


@service(scope=ComponentScopeEnum.SINGLETON)
class AreaService:
    """应用独占的地区目录；先校验全部关系，再发布不可变节点。"""

    def __init__(self) -> None:
        self._areas: dict[int, Area] | None = None
        self._paths: dict[tuple[str, ...], Area] = {}
        self._lock = RLock()

    def initialize(self, csv_file_path: Path | None = None) -> None:
        with self._lock:
            if self._areas is not None:
                raise RuntimeError("地区目录已经初始化")
            resource_root = Path(__file__).resolve().parents[1] / "resources"
            path = resource_root / "area.csv" if csv_file_path is None else csv_file_path
            try:
                content = path.read_bytes()
                if csv_file_path is None:
                    manifest = json.loads((resource_root / "area-manifest.json").read_bytes())
                    if hashlib.sha256(content).hexdigest() != manifest["sha256"]:
                        raise ValueError("area.csv SHA-256 mismatch")
                areas = self._load(content.decode("utf-8-sig"))
            except (OSError, ValueError, KeyError, csv.Error) as error:
                raise IpException(
                    IpErrorCodeConstants.AREA_DATA_LOAD_ERROR,
                    cause=error,
                    context={"path": str(path)},
                ) from error
            self._paths = {self._path(area): area for area in areas.values()}
            self._areas = areas

    @staticmethod
    def _load(content: str) -> dict[int, Area]:
        reader = csv.DictReader(content.splitlines())
        if reader.fieldnames != ["id", "name", "type", "parentId"]:
            raise ValueError("地区 CSV 表头必须为 id,name,type,parentId")
        areas: dict[int, Area] = {}
        parents: dict[int, int] = {}
        siblings: set[tuple[int, str]] = set()
        for row in reader:
            try:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("列数与表头不一致")
                area_id, area_type, parent_id = (
                    int(row["id"]),
                    int(row["type"]),
                    int(row["parentId"]),
                )
                name = row["name"].strip()
                if area_id <= 0 or area_id in areas:
                    raise ValueError("地区 ID 必须为不重复的正整数")
                if not name or "/" in name or area_type not in (1, 2, 3, 4):
                    raise ValueError("地区名称或层级无效")
                if (parent_id, name) in siblings:
                    raise ValueError("同一父节点下的地区名称重复")
            except ValueError as error:
                raise ValueError(f"CSV 行 {reader.line_num}: {error}") from error
            areas[area_id] = Area(area_id, name, area_type)
            parents[area_id] = parent_id
            siblings.add((parent_id, name))
        if not areas:
            raise ValueError("地区 CSV 没有记录")
        children: dict[int, list[Area]] = {area_id: [] for area_id in areas}
        for area_id, parent_id in parents.items():
            area = areas[area_id]
            if parent_id == 0:
                if area.type != AreaTypeEnum.COUNTRY.code:
                    raise ValueError(f"地区 {area_id}: 根节点必须是国家")
                continue
            if parent_id not in areas or areas[parent_id].type + 1 != area.type:
                raise ValueError(f"地区 {area_id}: 父节点缺失或层级不连续")
            # 严格递增的层级同时排除了环；只在节点发布前建立关系。
            object.__setattr__(area, "parent", areas[parent_id])
            children[parent_id].append(area)
        for area_id, nodes in children.items():
            object.__setattr__(
                areas[area_id], "children", tuple(sorted(nodes, key=lambda node: node.id))
            )
        return areas

    def _require_areas(self) -> dict[int, Area]:
        if self._areas is None:
            raise IpException(IpErrorCodeConstants.NOT_INITIALIZED)
        return self._areas

    def get_area(self, area_id: int) -> Area | None:
        with self._lock:
            return self._require_areas().get(area_id)

    def get_areas_by_type(self, area_type: AreaTypeEnum) -> list[Area]:
        with self._lock:
            return [area for area in self._require_areas().values() if area.type == area_type.code]

    @staticmethod
    def _path(area: Area) -> tuple[str, ...]:
        names = []
        while area is not None:
            names.append(area.name)
            area = area.parent
        return tuple(reversed(names))

    def format_area_path(self, area_id: int, separator: str = "/") -> str | None:
        if not separator:
            raise ValueError("地区路径分隔符不能为空")
        area = self.get_area(area_id)
        return None if area is None else separator.join(self._path(area))

    def parse_area_path(self, path_str: str, separator: str = "/") -> Area | None:
        if not separator:
            raise ValueError("地区路径分隔符不能为空")
        with self._lock:
            self._require_areas()
            return self._paths.get(tuple(path_str.split(separator)))

    def get_parent_by_type(self, area_id: int, target_type: AreaTypeEnum) -> Area | None:
        area = self.get_area(area_id)
        while area is not None and area.type != target_type.code:
            area = area.parent
        return area

    def convert_to_dict(self, area: Area) -> dict:
        with self._lock:
            if self._require_areas().get(area.id) is not area:
                raise ValueError("地区节点不属于当前目录")
            return self._node_dict(area)

    @classmethod
    def _node_dict(cls, area: Area) -> dict:
        return {
            "id": area.id,
            "name": area.name,
            "children": [cls._node_dict(node) for node in area.children],
        }

    def close(self) -> None:
        with self._lock:
            self._areas = None
            self._paths.clear()
