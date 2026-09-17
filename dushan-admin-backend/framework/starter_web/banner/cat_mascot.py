import asyncio
import os
import re
import shutil
import sys
import time
import unicodedata
from threading import Event

from loguru import logger

from framework.common.security.sanitizer import Sanitizer

_RESET = "\033[0m"
_C_FUR = "\033[38;2;180;170;160m"
_C_STRIP = "\033[38;2;115;105;95m"
_C_PINK = "\033[38;2;255;165;180m"
_C_WHITE = "\033[38;2;255;255;255m"
_C_BLUE = "\033[38;2;45;155;240m"
_C_GLASS = "\033[38;2;158;151;139m"
_C_GOLD = "\033[38;2;255;215;0m"
_C_BORDER = "\033[94m"
# 透明镜片、灰色镜框与蓝眼睛；六列三行的镜框在终端约为正方形。
_B_LENS = ""

_FACE_ROWS = (
    f"      {_C_FUR}/\\_______/\\{_RESET}",
    f"     {_C_FUR}/{_C_PINK}░{_C_FUR}   ░{_C_STRIP}≡{_C_FUR}░   "
    f"{_C_PINK}░{_RESET}{_C_FUR}\\{_RESET}",
    f"   {_C_FUR}╭╯░           ░╰╮{_RESET}",
    f"  {_C_FUR}╭╯░{_B_LENS}{_C_GLASS}╭────╮{_RESET} {_B_LENS}{_C_GLASS}╭────╮"
    f"{_RESET}{_C_FUR}░╰╮{_RESET}",
    f" {_C_FUR}(░  {_B_LENS}{_C_GLASS}│ {_C_BLUE}◕  {_C_GLASS}│{_RESET}{_C_GLASS}═"
    f"{_B_LENS}│  {_C_BLUE}◕ {_C_GLASS}│{_RESET}{_C_FUR}  ░){_RESET}",
    f"{_C_STRIP}≡{_C_FUR}(░  {_B_LENS}{_C_GLASS}╰────╯{_RESET}{_C_PINK}ᴥ"
    f"{_B_LENS}{_C_GLASS}╰────╯{_RESET}{_C_FUR}  ░){_C_STRIP}≡{_RESET}",
    f"  {_C_FUR}╰╮░   {_C_STRIP}╰━━━━━╯{_C_FUR}   ░╭╯{_RESET}",
)
_BODY_ROWS = (
    f"   {_C_FUR}(░    {_C_WHITE}░░░░░{_C_FUR}    ░){_RESET}",
    f"   {_C_FUR}(░    {_C_WHITE}█████{_C_FUR}    ░){_C_STRIP}～(≡){_RESET}",
    f"    {_C_FUR}╰─{_C_WHITE}( ฅ ){_C_FUR}_{_C_WHITE}( ฅ ){_C_FUR}─╯{_RESET}",
)

# 共用圆脸骨架；空行也属于固定的 12 行动画区域。
_SPRITES: dict[str, list[str]] = {
    "leap": [
        *_FACE_ROWS,
        f"   {_C_FUR}╰╮░   {_C_WHITE}░░░░░{_C_FUR}   ░╭╯{_C_STRIP}～(≡){_RESET}",
        f"  {_C_WHITE}( ฅ ){_C_FUR}╰─{_C_WHITE}█████{_C_FUR}─╯{_C_WHITE}( ฅ ){_RESET}",
        "",
        "",
        "",
    ],
    "landing": ["", *_FACE_ROWS, *_BODY_ROWS, ""],
    "lick_paw": [
        "",
        *_FACE_ROWS[:4],
        f" {_C_FUR}(░  {_B_LENS}{_C_GLASS}│ {_C_BLUE}⌒  {_C_GLASS}│{_RESET}{_C_GLASS}═"
        f"{_B_LENS}│  {_C_BLUE}⌒ {_C_GLASS}│{_RESET}{_C_FUR}  ░){_RESET}",
        _FACE_ROWS[5],
        f"  {_C_FUR}╰╮░  {_C_STRIP}╰━{_C_PINK}ᴗ{_C_STRIP}╯{_C_WHITE}( ฅ )"
        f"{_C_FUR}  ░{_RESET}{_C_FUR}╭╯{_RESET}",
        *_BODY_ROWS,
        "",
    ],
    "wave_paw": [
        "",
        *_FACE_ROWS[:2],
        f"{_FACE_ROWS[2]}     {_C_GOLD}╭──────╮{_RESET}",
        f"{_FACE_ROWS[3]}    {_C_GOLD}│ Hi!  │{_RESET}",
        f"{_FACE_ROWS[4]}   {_C_GOLD}╰╮╭────╯{_RESET}",
        f"{_FACE_ROWS[5]}   {_C_GOLD}╰╯{_RESET}",
        f"{_FACE_ROWS[6]}  {_C_FUR}╱{_C_WHITE}( ฅ ){_RESET}",
        *_BODY_ROWS,
        "",
    ],
    "glasses_push": [
        "",
        *_FACE_ROWS[:5],
        f"{_C_STRIP}≡{_C_FUR}(░  {_B_LENS}{_C_GLASS}╰────╯{_RESET}{_C_PINK}ᴥ"
        f"{_B_LENS}{_C_GLASS}╰────╯{_RESET}{_C_WHITE}(ฅ){_C_FUR}░){_C_STRIP}≡{_RESET}",
        f"  {_C_FUR}╰╮░   {_C_STRIP}╰━━━━━╯{_C_FUR} ╱ ░╭╯ {_C_GOLD}✧{_RESET}",
        *_BODY_ROWS,
        "",
    ],
    "settled": [
        "",
        "",
        "",
        *_FACE_ROWS,
        f"  {_C_WHITE}( ฅ ){_C_FUR}╰─{_C_WHITE}█████{_C_FUR}─╯{_C_WHITE}( ฅ )"
        f"{_C_STRIP}～(≡){_RESET}",
        "",
    ],
}


_SPRITES["leap_low"] = ["", *_SPRITES["leap"][:9], "", ""]
_SPRITES["crouch"] = [
    "",
    "",
    *_FACE_ROWS,
    _BODY_ROWS[0],
    f"  {_C_WHITE}( ฅ ){_C_FUR}╰─{_C_WHITE}█████{_C_FUR}─╯{_C_WHITE}( ฅ ){_C_STRIP}～(≡){_RESET}",
    "",
]
_SPRITES["paw_lift"] = [
    "",
    *_FACE_ROWS[:-1],
    f"  {_C_FUR}╰╮░ {_C_WHITE}( ฅ ){_C_STRIP}╰━━━╯{_C_FUR}  ░╭╯{_RESET}",
    *_BODY_ROWS,
    "",
]
_SPRITES["lick_paw_alt"] = [
    *_SPRITES["lick_paw"][:7],
    f"  {_C_FUR}╰╮░  {_C_STRIP}╰━{_C_PINK}▽{_C_STRIP}╯{_C_WHITE}( ฅ ){_C_FUR}  ░╭╯{_RESET}",
    *_BODY_ROWS,
    "",
]
_SPRITES["wave_low"] = [
    *_SPRITES["wave_paw"][:7],
    _FACE_ROWS[6],
    f"{_BODY_ROWS[0]} {_C_WHITE}( ฅ ){_RESET}",
    *_BODY_ROWS[1:],
    "",
]
_SPRITES["glasses_reach"] = [
    "",
    *_FACE_ROWS[:-1],
    f"{_FACE_ROWS[6]} {_C_WHITE}(ฅ){_RESET}",
    *_BODY_ROWS,
    "",
]
_SPRITES["settled_blink"] = [
    *_SPRITES["settled"][:7],
    _SPRITES["lick_paw"][5],
    *_SPRITES["settled"][8:],
]


class CatMascotTUI:
    """绘制圆脸眼镜猫和固定服务卡片，所有动画等待都在完整刷新信息之后。"""

    def __init__(self, cat_name: str = "渡山喵 (Dushan Meow)") -> None:
        self.cat_name = cat_name
        self.setup_terminal()

    @staticmethod
    def setup_terminal() -> None:
        """为支持重编码的 stdout 设置 UTF-8；捕获流可能不允许重配置。"""
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

    @staticmethod
    def strip_ansi(text: str) -> str:
        """移除 CSI 转义序列，供纯文本输出和列宽计算使用。"""
        return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)

    @staticmethod
    def visual_len(text: str) -> int:
        """中文、全角字符占两列，组合附加符不额外占列。"""
        return sum(
            2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
            for char in CatMascotTUI.strip_ansi(text)
            if not unicodedata.combining(char)
        )

    def render_header_frame(
        self, action_name: str, cat_x: int | None = None, card_w: int = 68
    ) -> str:
        """按终端列宽居中，或在指定左起列绘制动作；越界时明确报错。"""
        sprite = _SPRITES[action_name]
        sprite_w = max(self.visual_len(line) for line in sprite)
        if cat_x is None:
            cat_x = (card_w - sprite_w) // 2
        if cat_x < 0 or cat_x + sprite_w > card_w:
            raise ValueError(f"猫咪帧超出 {card_w} 列区域：位置 {cat_x}，宽度 {sprite_w}")
        return "\n".join(
            " " * cat_x + line + " " * (card_w - cat_x - self.visual_len(line)) for line in sprite
        )

    def build_card_rows(self, info_lines: list[str], card_w: int = 68) -> list[str]:
        """默认 68 列，长地址扩宽整张卡片，保持链接完整和边框对齐。"""
        lines = [Sanitizer.sanitize_text(line) for line in info_lines]
        card_w = max(card_w, max((self.visual_len(line) + 4 for line in lines), default=4))
        top_border = f"{_C_BORDER}┌" + ("─" * (card_w - 2)) + f"┐{_RESET}"
        bot_border = f"{_C_BORDER}└" + ("─" * (card_w - 2)) + f"┘{_RESET}"
        div_border = f"{_C_BORDER}├" + ("─" * (card_w - 2)) + f"┤{_RESET}"

        card_rows: list[str] = [top_border]
        for line in lines:
            if line == "---":
                card_rows.append(div_border)
            else:
                pad = " " * (card_w - 4 - self.visual_len(line))
                card_rows.append(f"{_C_BORDER}│{_RESET} {line}{pad} {_C_BORDER}│{_RESET}")
        card_rows.append(bot_border)
        return card_rows

    @staticmethod
    def _uses_ansi() -> bool:
        """只在可交互且未明确禁用控制码的终端输出 ANSI。"""
        return (
            sys.stdout.isatty()
            and os.environ.get("TERM") != "dumb"
            and not any(name in os.environ for name in ("PYTEST_CURRENT_TEST", "CI", "NO_COLOR"))
        )

    @staticmethod
    def _draw_header(lines: list[str], card_height: int) -> None:
        """每帧独立保存和恢复底部光标，等待期间不占用猫咪区域。"""
        try:
            sys.stdout.write(
                f"\033[s\033[?25l\033[{len(lines) + card_height}A\r"
                + "".join(f"\033[2K{line}\r\n" for line in lines)
            )
        finally:
            sys.stdout.write("\033[u\033[?25h")
            sys.stdout.flush()

    @staticmethod
    def _animation_frames(center_x: int) -> list[tuple[str, int]]:
        """以 20 帧/秒细分五秒动作；跳跃位移使用缓入缓出，姿态共用固定画布。"""
        frames = []
        for index in range(28):
            progress = index / 27
            position = round(2 + (center_x - 2) * progress * progress * (3 - 2 * progress))
            action = "crouch" if index < 3 else "leap_low" if index < 8 or index >= 23 else "leap"
            frames.append((action, position))
        for action, count in (
            ("crouch", 4),
            ("landing", 6),
            ("paw_lift", 4),
            ("lick_paw", 5),
            ("lick_paw_alt", 4),
            ("lick_paw", 3),
            ("paw_lift", 2),
            ("wave_low", 4),
            ("wave_paw", 4),
            ("wave_low", 3),
            ("wave_paw", 4),
            ("wave_low", 3),
            ("wave_paw", 2),
            ("paw_lift", 2),
            ("glasses_reach", 4),
            ("glasses_push", 5),
            ("glasses_reach", 3),
            ("landing", 2),
            ("crouch", 3),
            ("settled_blink", 2),
            ("settled", 3),
        ):
            frames.extend([(action, center_x)] * count)
        return frames

    async def play_and_render_completion(
        self, card_content_lines: list[str], *, show_mascot: bool = True
    ) -> None:
        """一次刷新全部内容，随后仅在完整画面可见时原位播放一次动作。"""
        card_rows = self.build_card_rows(card_content_lines)
        card_w = self.visual_len(card_rows[0])
        size = shutil.get_terminal_size()
        use_ansi = self._uses_ansi()
        center_x = (
            card_w - max(self.visual_len(line) for sprite in _SPRITES.values() for line in sprite)
        ) // 2
        animate = (
            use_ansi
            and show_mascot
            and size.columns > card_w
            and size.lines > len(card_rows) + len(_SPRITES["settled"])
        )
        header = (
            self.render_header_frame(
                "crouch" if animate else "settled", cat_x=2 if animate else center_x, card_w=card_w
            ).splitlines()
            if show_mascot
            else []
        )
        rows = [*header, *card_rows]
        # 自动折行或画面滚出视口后，按旧行数回移会擦到服务链接。
        if sys.stdout.isatty() and size.columns <= card_w:
            rows = [
                Sanitizer.sanitize_text(line) if line != "---" else ""
                for line in card_content_lines
            ]
            show_mascot = False
        message = "\n".join(rows)
        print(message if use_ansi else self.strip_ansi(message), file=sys.stdout, flush=True)
        if not animate:
            return

        # 后台日志会移动终端光标；有新输出时停止回绘，避免擦到卡片或日志。
        interrupted = Event()
        observer = logger.add(lambda _: interrupted.set(), level="TRACE", format="{message}")
        deadline = time.monotonic()
        try:
            for action, x in self._animation_frames(center_x):
                if interrupted.is_set() or shutil.get_terminal_size() != size:
                    return
                self._draw_header(
                    self.render_header_frame(action, cat_x=x, card_w=card_w).splitlines(),
                    len(card_rows),
                )
                deadline += 0.05
                await asyncio.sleep(max(0, deadline - time.monotonic()))
        finally:
            logger.remove(observer)

    async def run_interactive(self) -> None:
        """独立预览动作；重定向输出时打印静态画面并立即退出。"""
        content = [self.cat_name, "1 跳跃  2 舔爪  3 招手  4 推眼镜  5 趴伏  Q 退出"]
        await self.play_and_render_completion(content)
        if not self._uses_ansi() or not sys.stdin.isatty():
            return
        size = shutil.get_terminal_size()
        card_rows = self.build_card_rows(content)
        card_w = self.visual_len(card_rows[0])
        header_height = len(_SPRITES["settled"])
        if size.columns <= card_w or size.lines <= len(card_rows) + header_height:
            return
        center_x = (
            card_w - max(self.visual_len(line) for sprite in _SPRITES.values() for line in sprite)
        ) // 2
        actions = {
            "1": "leap",
            "2": "lick_paw",
            "3": "wave_paw",
            "4": "glasses_push",
            "5": "settled",
        }
        try:
            while shutil.get_terminal_size() == size:
                key = self._check_key()
                if key in ("q", "Q", "\x1b"):
                    break
                if key in actions:
                    self._draw_header(
                        self.render_header_frame(
                            actions[key], cat_x=center_x, card_w=card_w
                        ).splitlines(),
                        len(card_rows),
                    )
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            pass

    @staticmethod
    def _check_key() -> str | None:
        """非阻塞按键读取。"""
        if sys.platform == "win32":
            import msvcrt

            return msvcrt.getwch() if msvcrt.kbhit() else None
        else:
            import select

            r, _, _ = select.select([sys.stdin], [], [], 0)
            if r:
                return sys.stdin.read(1)
            return None


if __name__ == "__main__":
    asyncio.run(CatMascotTUI().run_interactive())
