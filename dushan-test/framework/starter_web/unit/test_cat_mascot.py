import asyncio
import io
import os
import re
from types import SimpleNamespace

import pytest
from loguru import logger

from framework.starter_web.banner import cat_mascot
from framework.starter_web.banner.cat_mascot import CatMascotTUI

pytestmark = pytest.mark.unit


class TerminalOutput(io.StringIO):
    def __init__(self):
        super().__init__()
        self.frames = []

    def isatty(self):
        return True

    def flush(self):
        self.frames.append(self.getvalue())


@pytest.fixture
def terminal(monkeypatch):
    output = TerminalOutput()
    monkeypatch.setattr(
        cat_mascot,
        "sys",
        SimpleNamespace(
            stdout=output, stdin=cat_mascot.sys.stdin, platform=cat_mascot.sys.platform
        ),
    )
    monkeypatch.setattr(cat_mascot.shutil, "get_terminal_size", lambda: os.terminal_size((100, 50)))
    for name in ("PYTEST_CURRENT_TEST", "CI", "NO_COLOR", "TERM"):
        monkeypatch.delenv(name, raising=False)
    return output


def test_round_cat_actions_share_a_canvas_and_keep_small_greeting():
    cat = CatMascotTUI()
    frames = [cat.render_header_frame(action) for action in cat_mascot._SPRITES]
    assert {len(frame.splitlines()) for frame in frames} == {12}
    assert {cat.visual_len(line) for frame in frames for line in frame.splitlines()} == {68}
    for frame in frames:
        plain = cat.strip_ansi(frame)
        assert "╭────╮" in plain and "╰────╯" in plain
        assert "█████" not in plain.split("╰────╯", 1)[0]
    wave = cat.strip_ansi(cat.render_header_frame("wave_paw"))
    assert "Hi!" in wave and "( ฅ )" in wave
    assert "Hi!" not in cat.strip_ansi(cat.render_header_frame("settled"))
    assert cat.render_header_frame("settled") != cat.render_header_frame("landing")
    with pytest.raises(KeyError):
        cat.render_header_frame("unknown")
    with pytest.raises(ValueError):
        cat.render_header_frame("wave_paw", cat_x=67)


def test_card_width_accounts_for_ansi_chinese_and_combining_marks():
    cat = CatMascotTUI()
    assert cat.visual_len("\033[38;2;45;155;240m渡山喵 e\u0301～\033[0m") == 10
    url = "https://example.com/" + "docs/" * 20
    rows = cat.build_card_rows(["测试服务", "---", url, "password=private-value"])
    assert {cat.visual_len(row) for row in rows} == {len(url) + 4}
    assert url in "\n".join(rows)
    assert "private-value" not in "\n".join(rows)


async def test_complete_card_is_flushed_before_wait_and_redraw_never_touches_it(
    terminal, monkeypatch
):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    content = [
        "测试服务",
        "---",
        "Swagger：http://localhost/docs",
        "OpenAPI：http://localhost/schema",
    ]
    cat = CatMascotTUI()
    card = cat.build_card_rows(content)
    height = len(cat.render_header_frame("settled").splitlines())
    waits = []
    clock = [0.0]
    real_sleep = asyncio.sleep
    monkeypatch.setattr(cat_mascot, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    async def wait(delay):
        assert all(value in terminal.frames[0] for value in content if value != "---")
        waits.append(delay)
        clock[0] += delay
        await real_sleep(0)

    monkeypatch.setattr(cat_mascot.asyncio, "sleep", wait)
    await cat.play_and_render_completion(content)
    output = terminal.getvalue()
    assert len(waits) == 100
    assert sum(waits) == pytest.approx(5.0)
    assert max(waits) <= 0.051
    assert all(output.count(row) == 1 for row in card)
    initial, animation = output.split(card[-1] + "\n", 1)
    assert len(CatMascotTUI.strip_ansi(initial).splitlines()) == height + len(card) - 1
    row = height + len(card)
    column = 0
    saved = None
    erased = []
    # 跟踪实际控制流，任何卡片行上的擦除/写字都会失败。
    tokens = re.split(r"(\x1b\[[0-?]*[ -/]*[@-~])", animation)
    for token in tokens:
        if token.startswith("\033["):
            argument, command = token[2:-1], token[-1]
            if command == "A":
                row -= int(argument)
            elif command == "B":
                row += int(argument)
            elif command == "s":
                saved = row, column
            elif command == "u":
                row, column = saved
            elif command == "K":
                erased.append(row)
                assert 0 <= row < height
        else:
            for char in token:
                if char == "\n":
                    row += 1
                elif char == "\r":
                    column = 0
                else:
                    assert row < height
                    column += CatMascotTUI.visual_len(char)
                    assert column <= 68
    assert erased and (row, column) == (height + len(card), 0)
    assert output.endswith("\033[u\033[?25h")


@pytest.mark.parametrize(
    "mode", ["redirect", "pytest", "ci", "dumb", "no_color", "narrow", "short", "hidden"]
)
async def test_static_modes_do_not_wait_or_move_cursor(terminal, monkeypatch, mode):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    if mode == "redirect":
        monkeypatch.setattr(terminal, "isatty", lambda: False)
    elif mode == "pytest":
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "banner")
    elif mode == "ci":
        monkeypatch.setenv("CI", "true")
    elif mode == "dumb":
        monkeypatch.setenv("TERM", "dumb")
    elif mode == "no_color":
        monkeypatch.setenv("NO_COLOR", "1")
    elif mode in ("narrow", "short"):
        size = (40, 50) if mode == "narrow" else (100, 15)
        monkeypatch.setattr(cat_mascot.shutil, "get_terminal_size", lambda: os.terminal_size(size))
    monkeypatch.setattr(cat_mascot.asyncio, "sleep", lambda _: pytest.fail("静态输出不应等待"))
    await CatMascotTUI().play_and_render_completion(
        ["Swagger：http://localhost/docs"], show_mascot=mode != "hidden"
    )
    output = terminal.getvalue()
    assert "Swagger：http://localhost/docs" in output
    assert "\033[" not in re.sub(r"\x1b\[[0-9;]*m", "", output)
    if mode in ("redirect", "no_color", "dumb", "ci", "pytest"):
        assert "\033" not in output


async def test_animation_restores_cursor_and_propagates_cancellation(terminal, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    async def cancel(_):
        raise asyncio.CancelledError

    monkeypatch.setattr(cat_mascot.asyncio, "sleep", cancel)
    with pytest.raises(asyncio.CancelledError):
        await CatMascotTUI().play_and_render_completion(["Swagger：http://localhost/docs"])
    assert terminal.getvalue().endswith("\033[u\033[?25h")


async def test_resize_stops_redrawing_without_losing_the_card(terminal, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    async def resize(_):
        monkeypatch.setattr(
            cat_mascot.shutil, "get_terminal_size", lambda: os.terminal_size((40, 12))
        )

    monkeypatch.setattr(cat_mascot.asyncio, "sleep", resize)
    await CatMascotTUI().play_and_render_completion(["Swagger：http://localhost/docs"])
    assert terminal.getvalue().count("Swagger：http://localhost/docs") == 1
    assert terminal.getvalue().count("\033[s") == 1


async def test_redirected_interactive_preview_does_not_read_keys(terminal, monkeypatch):
    monkeypatch.setattr(terminal, "isatty", lambda: False)
    monkeypatch.setattr(CatMascotTUI, "_check_key", lambda _: pytest.fail("管道不应进入键盘循环"))
    await CatMascotTUI().run_interactive()


def test_motion_has_small_position_steps_and_intermediate_poses():
    sequence = CatMascotTUI._animation_frames(15)
    assert len(sequence) == 100 and sequence[-1] == ("settled", 15)
    positions = [position for _, position in sequence]
    assert max(abs(right - left) for left, right in zip(positions, positions[1:])) <= 1
    assert {"leap_low", "crouch", "paw_lift", "wave_low", "glasses_reach", "settled_blink"} <= {
        name for name, _ in sequence
    }


async def test_animation_yields_to_other_tasks(terminal, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    real_sleep = asyncio.sleep
    clock = [0.0]
    heartbeat = []
    monkeypatch.setattr(cat_mascot, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    async def tick():
        for _ in range(100):
            heartbeat.append(True)
            await real_sleep(0)

    async def wait(delay):
        clock[0] += delay
        await real_sleep(0)

    monkeypatch.setattr(cat_mascot.asyncio, "sleep", wait)
    task = asyncio.create_task(tick())
    try:
        await CatMascotTUI().play_and_render_completion(["Swagger：http://localhost/docs"])
        assert len(heartbeat) == 100
    finally:
        await task


async def test_background_log_stops_animation_before_it_can_overwrite_output(terminal, monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

    async def wait(_):
        logger.info("后台任务状态更新")

    monkeypatch.setattr(cat_mascot.asyncio, "sleep", wait)
    await CatMascotTUI().play_and_render_completion(["Swagger：http://localhost/docs"])
    assert terminal.getvalue().count("\033[s") == 1
    assert terminal.getvalue().count("Swagger：http://localhost/docs") == 1
