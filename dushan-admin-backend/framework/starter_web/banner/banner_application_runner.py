import os
import sys
from collections.abc import Sequence
from importlib.resources import files

from framework.common.security.sanitizer import Sanitizer
from framework.starter_web.banner.banner_runtime_info import BannerRuntimeInfo
from framework.starter_web.banner.cat_mascot import CatMascotTUI
from framework.starter_web.config.banner_settings import BannerSettings

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_BLUE = "\033[34m"
_BRIGHT_CYAN = "\033[96m"
_BRIGHT_WHITE = "\033[97m"
_GRAY = "\033[90m"
_BG_BLUE = "\033[44;37m"


class BannerApplicationRunner:
    """按应用配置输出字符横幅、渡山喵和服务启动摘要。

    构造时注入 BannerSettings，展示内容通过 print 直接写入 stdout 并立即刷新。
    print_startup_banner 由启动器在创建引擎进程前调用；完成摘要由应用初始化末尾调用。
    类本身不启动服务、不发现模块，也不读取应用的完整配置。
    """

    def __init__(self, settings: BannerSettings) -> None:
        """保存明确传入的展示选项，不依赖日志初始化。"""
        self._settings = settings
        CatMascotTUI.setup_terminal()

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
        """按配置输出字符横幅与祈福图案（小猫伴侣仅在启动就绪末尾融合呈现）。"""
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

    async def print_startup_complete(self, info: BannerRuntimeInfo) -> None:
        """先刷新完整服务信息，再在可容纳整幅画面的终端播放猫咪动作。"""
        if not self._settings.enabled or not self._settings.show_startup_info:
            return
        if "PYTEST_CURRENT_TEST" in os.environ:
            self.print_module_status(info.enabled_modules, info.disabled_modules)
            self.print_doc(info)
            return

        await CatMascotTUI().play_and_render_completion(
            self._build_card_content(info), show_mascot=self._settings.show_mascot
        )

    def _build_card_content(self, info: BannerRuntimeInfo) -> list[str]:
        """只展示真实运行元数据、公开接口和调用方提供的模块状态。"""
        base_url = self._base_url(info)
        bind_host = f"[{info.host}]" if ":" in info.host else info.host
        app_title = f"[{info.app_name.upper()}] - 服务启动就绪"
        lines = [
            f"{_BOLD}{_BRIGHT_WHITE}{app_title}{_RESET}",
            f"{_DIM}版本：{info.version}  |  环境：{info.environment}  |  引擎：{info.engine}{_RESET}",
            "---",
            f"{_BOLD}服务公开接口清单:{_RESET}",
            f"  {_BLUE}•{_RESET} 网关入口:    {_BRIGHT_CYAN}{base_url}{_RESET}",
        ]
        if info.docs_url is not None:
            lines.append(
                f"  {_BLUE}•{_RESET} Swagger UI:  {_BRIGHT_CYAN}{base_url}{info.docs_url}{_RESET}"
            )
        if info.redoc_url is not None:
            lines.append(
                f"  {_BLUE}•{_RESET} ReDoc 文档:  {_BRIGHT_CYAN}{base_url}{info.redoc_url}{_RESET}"
            )
        if info.openapi_url is not None:
            lines.append(
                f"  {_BLUE}•{_RESET} OpenAPI:     {_BRIGHT_CYAN}{base_url}{info.openapi_url}{_RESET}"
            )
        if info.docs_url is None and info.redoc_url is None and info.openapi_url is None:
            lines.append("  接口文档：已关闭")
        if self._settings.documentation_url:
            lines.append(
                f"  {_BLUE}•{_RESET} 项目官方站:  {_BRIGHT_CYAN}{self._settings.documentation_url}{_RESET}"
            )
        lines.extend([f"{_DIM}监听地址：http://{bind_host}:{info.port}{_RESET}", "---"])
        if info.enabled_modules:
            mod_tags = " ".join(f"{_BG_BLUE} {name} {_RESET}" for name in info.enabled_modules)
            lines.append(f"{_BOLD}活动模块 ({len(info.enabled_modules)}):{_RESET} {mod_tags}")
        if info.disabled_modules:
            lines.append(f"{_GRAY}未启用模块：{'、'.join(info.disabled_modules)}{_RESET}")
        if self._settings.author:
            lines.append(f"{_DIM}工程维护作者: {self._settings.author}{_RESET}")
        return lines

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
        CatMascotTUI.setup_terminal()
        sanitized = Sanitizer.sanitize_text(message.rstrip())
        if not sys.stdout.isatty():
            sanitized = CatMascotTUI.strip_ansi(sanitized)
        try:
            print(sanitized, flush=True)
        except UnicodeEncodeError:
            encoding = sys.stdout.encoding or "utf-8"
            safe_text = sanitized.encode(encoding, errors="replace").decode(encoding)
            print(safe_text, flush=True)
