import configparser
import json
import tomllib
from pathlib import Path

import yaml

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError
from framework.starter_config.provider.unique_key_loader import UniqueKeyLoader


class ConfigFileReader:
    """读取附加结构化配置；不补缺省值、别名或静默跳过格式错误。"""

    @classmethod
    def read(cls, path: Path, *, required: bool, max_bytes: int) -> dict[str, object]:
        try:
            if not path.exists() and not required:
                return {}
            with path.open("rb") as stream:
                payload = stream.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise ValueError("配置文件超过大小上限")
            text = payload.decode("utf-8-sig")
            suffix = path.suffix.lower()
            if suffix in {".yaml", ".yml"}:
                values = yaml.load(text, Loader=UniqueKeyLoader)
            elif suffix == ".json":
                values = json.loads(text, object_pairs_hook=cls._unique_pairs)
            elif suffix == ".toml":
                values = tomllib.loads(text)
            elif suffix in {".ini", ".cfg"}:
                parser = configparser.ConfigParser(interpolation=None)
                parser.optionxform = str
                parser.read_string(text)
                if parser.defaults():
                    raise ValueError("INI 配置请显式声明 section，不接受 DEFAULT 隐式覆盖")
                values = {
                    f"{section}.{key}": value
                    for section in parser.sections()
                    for key, value in parser.items(section)
                }
            elif suffix == ".properties":
                pairs = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line or line.startswith(("#", "!")):
                        continue
                    key, separator, value = line.partition("=")
                    if not separator:
                        raise ValueError("properties 行必须为 key=value")
                    pairs.append((key.strip(), value.strip()))
                values = cls._unique_pairs(pairs)
            else:
                raise ValueError("不支持的配置文件格式")
            if not isinstance(values, dict):
                raise ValueError("配置文件顶层必须是映射")
            return values
        except (OSError, ValueError, yaml.YAMLError, configparser.Error) as error:
            # YAML/INI 解析错误会带出出错行的内容，不进入正常异常链；只保留错误类型名。
            raise BootstrapConfigError(
                f"配置文件读取失败：{path}（{type(error).__name__}）"
            ) from None

    @staticmethod
    def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        values = {}
        for key, value in pairs:
            if key in values:
                raise ValueError("配置文件存在重复键")
            values[key] = value
        return values
