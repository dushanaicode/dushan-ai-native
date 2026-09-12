FILES = {
    "__init__.py": "",
    "module.toml": 'name = "probe"\npackage = "foundation_probe"\nscan_roots = ["."]\ndefinitions = ["probe_settings:ProbeSettings", "probe_service:ProbeService"]\nrequires = ["framework"]\nrequired_message_keys = []\nresource_roots = []\n',
    "probe_settings.py": (
        "from framework.starter_config.config.config_model import ConfigModel\n"
        "from framework.starter_config.decorator.config_decorator import config_model\n"
        "@config_model('probe', env_prefix='PROBE_')\n"
        "class ProbeSettings(ConfigModel):\n    label: str\n    values: list[str]\n"
    ),
    "probe_interface.py": "class ProbeInterface:\n    pass\n",
    "probe_role.py": (
        "from framework.common.enums.base_enum import BaseEnum\n"
        "class ProbeRole(BaseEnum):\n    PLUGIN = ('probe_plugin', '安装验证插件')\n"
    ),
    "probe_service.py": (
        "from .probe_settings import ProbeSettings\n"
        "from .probe_interface import ProbeInterface\n"
        "from .probe_role import ProbeRole\n"
        "from framework.starter_di.decorators.components import component\n"
        "from framework.starter_di.decorators.inject import Inject\n"
        "plugin = component(ProbeRole.PLUGIN)\n"
        "@plugin(interface=ProbeInterface, providers=[ProbeInterface])\n"
        "class ProbeService(ProbeInterface):\n"
        "    settings: ProbeSettings = Inject()\n"
        "    async def post_construct(self):\n        self.started = True\n"
        "    async def pre_destroy(self):\n        self.started = False\n"
        "    def describe(self):\n        return self.settings.label + ':' + ','.join(self.settings.values)\n"
    ),
}
