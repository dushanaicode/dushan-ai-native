import yaml

from framework.starter_config.provider.bootstrap_config_error import BootstrapConfigError


class UniqueKeyLoader(yaml.SafeLoader):
    """读取 YAML 映射时拒绝重复键，避免后值悄悄覆盖前值。"""

    def construct_mapping(self, node, deep=False):
        """构造字符串键映射，错误消息不包含配置值。"""
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise BootstrapConfigError("配置键必须是字符串")
            if key in result:
                raise BootstrapConfigError(f"配置键重复：{key}")
            result[key] = self.construct_object(value_node, deep=deep)
        return result
