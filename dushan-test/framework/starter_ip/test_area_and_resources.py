import hashlib
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path
from threading import Event

import pytest

from framework.starter_ip.core.ip2region_database import Ip2RegionDatabase
from framework.starter_ip.enum.area_type_enum import AreaTypeEnum
from framework.starter_ip.exception.ip_exception import IpException
from framework.starter_ip.service.area_service import AreaService

RESOURCE_ROOT = (
    Path(__file__).resolve().parents[3] / "dushan-admin-backend/framework/starter_ip/resources"
)


def test_real_areas_are_immutable_reversible_and_isolated():
    first, second = AreaService(), AreaService()
    first.initialize()
    second.initialize()
    try:
        district = first.get_area(110101)
        assert str(district) == "东城区"
        assert first.format_area_path(110101) == "中国/北京市/北京市/东城区"
        assert first.parse_area_path(first.format_area_path(110101)) is district
        assert first.parse_area_path("东城区") is None
        assert first.get_area(987654321) is None
        assert first.format_area_path(987654321) is None
        assert first.get_parent_by_type(110101, AreaTypeEnum.COUNTRY).name == "中国"
        assert first.get_parent_by_type(1, AreaTypeEnum.DISTRICT) is None
        assert len(first.get_areas_by_type(AreaTypeEnum.COUNTRY)) > 190
        root = first.get_area(1)
        assert district.parent in root.children[0].children
        tree = first.convert_to_dict(root)
        assert tree["children"][0]["children"][0]["children"][0]["id"] == 110101
        assert len(first._areas) == 3661
        with pytest.raises(FrozenInstanceError):
            district.name = "被污染"
        with pytest.raises(ValueError, match="不属于"):
            second.convert_to_dict(district)
        first.close()
        with pytest.raises(IpException):
            first.get_area(1)
        assert second.get_area(110101).name == "东城区"
    finally:
        first.close()
        second.close()


@pytest.mark.parametrize(
    "rows, expected",
    [
        ("1,中国,1,0\n1,另一国家,1,0", "ID"),
        ("1,中国,1,0\n2,省,2,99", "父节点"),
        ("1,中国,1,0\n2,省,2,1\n3,省,2,1", "名称重复"),
        ("1,中国,1,0\n2,城市,3,1", "层级"),
        ("1,国家,1,2\n2,省,2,1", "层级"),
        ("2,省,2,0", "根节点"),
        ("1,中国,1,0,多列", "列数"),
        ("", "没有记录"),
        ("x,中国,1,0", "CSV 行 2"),
    ],
)
def test_area_data_rejects_invalid_tree_without_publication(tmp_path, rows, expected):
    path = tmp_path / "area.csv"
    path.write_text("id,name,type,parentId\n" + rows, encoding="utf-8")
    areas = AreaService()
    with pytest.raises(IpException) as failure:
        areas.initialize(path)
    assert expected in str(failure.value.__cause__)
    with pytest.raises(IpException):
        areas.get_area(1)


def test_pinned_resources_and_licenses_are_intact():
    area_manifest = json.loads((RESOURCE_ROOT / "area-manifest.json").read_bytes())
    assert (
        hashlib.sha256((RESOURCE_ROOT / "area.csv").read_bytes()).hexdigest()
        == area_manifest["sha256"]
    )
    assert (
        hashlib.sha256((RESOURCE_ROOT / area_manifest["license_file"]).read_bytes()).hexdigest()
        == area_manifest["license_sha256"]
    )
    assert area_manifest["source_commit"] == "088871d083cd03f25682e02cc2aedebefa0998d1"
    release = RESOURCE_ROOT / "ip2region/v3.17.0"
    manifest = json.loads((release / "manifest.json").read_bytes())
    for key in ("license", "ipv4", "ipv6"):
        artifact = manifest[key]
        content = (release / artifact["filename"]).read_bytes()
        assert len(content) == artifact["bytes"]
        assert hashlib.sha256(content).hexdigest() == artifact["sha256"]


def test_real_dual_stack_queries_concurrency_and_close():
    database, another = Ip2RegionDatabase(), Ip2RegionDatabase()
    database.initialize(("ipv4", "ipv6"))
    another.initialize(("ipv4", "ipv6"))
    expected = {
        "1.2.3.4": "Australia|Queensland|Brisbane|0|AU",
        "::ffff:1.2.3.4": "Australia|Queensland|Brisbane|0|AU",
        "114.114.114.114": "中国|江苏省|南京市|0|CN",
        "2604:a840:3::a04d": "United States|California|San Jose|xTom|US",
        "192.0.2.1": "Reserved|Reserved|Reserved|0|0",
        "2001:db8::1": "Reserved|Reserved|Reserved|0|0",
        "::": "",
    }
    try:
        queries = list(expected) * 80
        with ThreadPoolExecutor(max_workers=8) as executor:
            assert list(executor.map(database.search, queries)) == [expected[ip] for ip in queries]
        database.close()
        assert database._searchers is None
        with pytest.raises(IpException):
            database.search("1.2.3.4")
        assert another.search("1.2.3.4") == expected["1.2.3.4"]
        with pytest.raises(ValueError):
            another.search("not an ip")
    finally:
        database.close()
        another.close()


def test_close_waits_for_in_progress_local_search(monkeypatch):
    database = Ip2RegionDatabase()
    database.initialize(("ipv4", "ipv6"))
    started, finish, closing = Event(), Event(), Event()
    searcher = database._searchers[4]
    original = searcher.search

    def paused_search(address):
        started.set()
        assert finish.wait(2)
        return original(address)

    def close():
        closing.set()
        database.close()

    monkeypatch.setattr(searcher, "search", paused_search)
    with ThreadPoolExecutor(max_workers=2) as executor:
        query = executor.submit(database.search, "1.2.3.4")
        assert started.wait(2)
        shutdown = executor.submit(close)
        assert closing.wait(2)
        assert not shutdown.done()
        finish.set()
        assert query.result() == "Australia|Queensland|Brisbane|0|AU"
        shutdown.result()
    assert database._searchers is None


def test_corrupted_real_xdb_and_manifest_are_rejected(tmp_path):
    release = tmp_path / "release"
    shutil.copytree(RESOURCE_ROOT / "ip2region/v3.17.0", release)
    database = Ip2RegionDatabase()
    target = release / "ip2region_v4.xdb"
    with target.open("r+b") as stream:
        stream.seek(-1, 2)
        last = stream.read(1)
        stream.seek(-1, 2)
        stream.write(bytes([last[0] ^ 1]))
    with pytest.raises(IpException) as failure:
        database.initialize(("ipv4", "ipv6"), release)
    assert "SHA-256 mismatch" in str(failure.value.__cause__)
    assert database._searchers is None
    (release / "manifest.json").write_bytes(b"{}")
    with pytest.raises(IpException) as failure:
        database.initialize(("ipv4", "ipv6"), release)
    assert "manifest" in str(failure.value.__cause__)
