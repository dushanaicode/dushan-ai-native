from collections.abc import Sequence
from importlib.resources import files

from framework.common.security.sanitizer import Sanitizer
from framework.starter_web.banner.banner_runtime_info import BannerRuntimeInfo
from framework.starter_web.config.banner_settings import BannerSettings


class BannerApplicationRunner:
    """按应用配置输出完整字符横幅、祈福图案和真实启动摘要。

    构造时注入 BannerSettings，展示内容通过 print 直接写入 stdout 并立即刷新。
    print_startup_banner 由启动器在创建引擎进程前调用；完成摘要由应用初始化末尾调用。
    类本身不启动服务、不发现模块，也不读取应用的完整配置。
    """

    def __init__(self, settings: BannerSettings) -> None:
        """保存明确传入的展示选项，不依赖日志初始化。"""
        self._settings = settings

    def print_banner(self) -> None:
        """启用时读取包内字符横幅，源码和 wheel 安装均使用相同资源。"""
        if self._settings.enabled and self._settings.show_logo:
            self._emit(
                files("framework.starter_web.banner")
                .joinpath("assets/logo.txt")
                .read_text(encoding="utf-8")
            )

    def worship(self) -> None:
        """仅在显式启用祈福图案时输出该资源。"""
        if self._settings.enabled and self._settings.show_worship:
            self._emit(
                files("framework.starter_web.banner")
                .joinpath("assets/worship.txt")
                .read_text(encoding="utf-8")
            )

    def print_startup_banner(self) -> None:
        """按各自开关输出字符横幅和祈福图案。"""
        self.print_banner()
        self.worship()

    def print_doc(self, info: BannerRuntimeInfo) -> None:
        """输出公开服务信息和实际配置的接口文档入口。"""
        if not self._settings.enabled or not self._settings.show_startup_info:
            return
        base_url = self._base_url(info)
        bind_host = f"[{info.host}]" if ":" in info.host else info.host
        lines = [
            f"应用初始化完成：{info.app_name}",
            f"版本：{info.version}",
        ]
        if self._settings.author != "":
            lines.append(f"作者：{self._settings.author}")
        paths = (
            ("Swagger", info.docs_url),
            ("ReDoc", info.redoc_url),
            ("OpenAPI", info.openapi_url),
        )
        for label, path in paths:
            if path is not None:
                lines.append(f"{label}：{base_url}{path}")
        if all(path is None for _, path in paths):
            lines.append("接口文档：已关闭")
        if self._settings.documentation_url != "":
            lines.append(f"项目文档：{self._settings.documentation_url}")
        lines.extend(
            [
                f"引擎：{info.engine}",
                f"环境：{info.environment}",
                f"监听地址：http://{bind_host}:{info.port}",
            ]
        )
        self._emit("\n".join(lines))

    def print_module_status(
        self, enabled_modules: Sequence[str], disabled_modules: Sequence[str]
    ) -> None:
        """只展示调用方给出的模块状态，不推测模块是否存在或加载成功。"""
        if not self._settings.enabled or not self._settings.show_startup_info:
            return
        lines = [f"[+] 已启用模块：{name}" for name in enabled_modules]
        lines.extend(f"[-] 未启用模块：{name}" for name in disabled_modules)
        if lines:
            self._emit("\n".join(lines))

    def print_startup_complete(self, info: BannerRuntimeInfo) -> None:
        """在初始化步骤完成后显示模块状态与公开服务信息。"""
        self.print_module_status(info.enabled_modules, info.disabled_modules)
        self.print_doc(info)

    @staticmethod
    def _base_url(info: BannerRuntimeInfo) -> str:
        """构造直连提示地址；通配监听地址映射为本机回环，IPv6 使用方括号。"""
        host = info.host
        if host == "0.0.0.0":
            host = "127.0.0.1"
        elif host == "::":
            host = "::1"
        authority = f"[{host}]" if ":" in host else host
        return f"http://{authority}:{info.port}{info.root_path.rstrip('/')}"

    @staticmethod
    def _emit(message: str) -> None:
        """直接打印并刷新 stdout，确保重定向时也先于随后启动的引擎输出。"""
        print(Sanitizer.sanitize_text(message.rstrip()), flush=True)
