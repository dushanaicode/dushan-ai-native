import base64
from io import BytesIO

import pytest
from PIL import Image
from pydantic import ValidationError

from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.provider.local_captcha_provider import LocalCaptchaProvider


@pytest.mark.parametrize("kind", ["block_puzzle", "click_word"])
async def test_real_generation_and_matching(settings, kind, tmp_path):
    provider = LocalCaptchaProvider(settings(provider=kind))
    data, record = provider.create("login")
    assert "points" not in data and "positions" not in data and "x" not in data
    raw = base64.b64decode(data["image"], validate=True)
    (tmp_path / f"{kind}.png").write_bytes(raw)
    with Image.open(BytesIO(raw)) as image:
        # 背景是照片，按 JPEG 返回；滑块条另行以 PNG 返回以保留透明通道。
        assert image.size == (320, 160) and image.format == "JPEG"
        assert len(image.convert("RGB").getcolors(100000)) > 200
    assert data["format"] == "jpeg" and len(raw) < 60000
    good = CaptchaAnswer(points=[point.model_copy() for point in record.points])
    assert await provider.verify(record, good, None)
    if kind == "block_puzzle":
        assert data["piece_format"] == "png"
        with Image.open(BytesIO(base64.b64decode(data["piece"]))) as piece:
            assert piece.format == "PNG" and piece.size == (48, 160) and piece.mode == "RGBA"
            assert piece.getchannel("A").getbbox() is not None
            assert piece.getextrema()[3] == (0, 255)
        good.points[0].x += 5
        assert await provider.verify(record, good, None)
        good.points[0].x += 0.01
        assert not await provider.verify(record, good, None)
        wrong = CaptchaAnswer(points=[{"x": 0, "y": 0}])
    else:
        assert len(set(data["words"])) == 3
        wrong = CaptchaAnswer(points=list(reversed(record.points)))
    assert not await provider.verify(record, wrong, None)
    second, _ = provider.create("login")
    assert data["image"] != second["image"]


@pytest.mark.parametrize(
    "point",
    [
        {"x": True, "y": 0},
        {"x": "4", "y": 0},
        {"x": float("nan"), "y": 0},
        {"x": float("inf"), "y": 0},
        {"x": -1, "y": 0},
        {"x": 320, "y": 0},
        {"x": 0, "y": 160},
        {"x": 0, "y": 0, "extra": 1},
    ],
)
def test_coordinate_input_limits(point):
    with pytest.raises(ValidationError):
        CaptchaAnswer.model_validate({"points": [point]})


async def test_click_circular_tolerance_and_order(settings):
    provider = LocalCaptchaProvider(settings(provider="click_word"))
    _, record = provider.create("login")
    answer = CaptchaAnswer(points=[point.model_copy() for point in record.points])
    answer.points[0].x += 6
    answer.points[0].y += 8
    assert await provider.verify(record, answer, None)
    answer.points[0].y += 0.01
    assert not await provider.verify(record, answer, None)


def test_resource_failure_is_explicit(settings):
    from framework.starter_captcha.exception.captcha_exception import CaptchaException

    with pytest.raises(CaptchaException):
        LocalCaptchaProvider(settings(watermark="😀"))


def _dark_pixels(image, threshold=70):
    """返回三通道都低于阈值的像素坐标。"""
    pixels = image.load()
    return {
        (x, y)
        for x in range(image.width)
        for y in range(image.height)
        if max(pixels[x, y]) < threshold
    }


@pytest.mark.parametrize("kind", ["block_puzzle", "click_word"])
def test_answer_ink_stays_inside_background_gamut(settings, kind):
    """缺口与字形不得使用背景里不存在的颜色。

    这是本组件最容易退化的地方：一旦改回固定深色填充，缺口/字形就整体落在
    背景色域之外，一次全局阈值即可直接筛出答案位置。断言的是"暗像素不集中"，
    而不是具体实现手法，因此不会锁死画法。
    """
    provider = LocalCaptchaProvider(settings(provider=kind))
    concentrated = 0
    for _ in range(12):
        data, record = provider.create("login")
        raw = base64.b64decode(data["image"])
        with Image.open(BytesIO(raw)) as image:
            dark = _dark_pixels(image.convert("RGB"))
        if not dark:
            continue
        if kind == "block_puzzle":
            target = record.points[0].x
            inside = sum(1 for x, _ in dark if target <= x < target + provider.GAP)
        else:
            inside = sum(
                1
                for x, y in dark
                if any((x - p.x) ** 2 + (y - p.y) ** 2 <= 32**2 for p in record.points)
            )
        # 暗像素若绝大多数落在答案区域内，说明答案被颜色直接标记了出来。
        if inside / len(dark) > 0.6:
            concentrated += 1
    assert concentrated <= 2, f"{kind} 的暗像素集中在答案位置，缺口/字形颜色脱离背景色域"


def test_slider_gap_is_not_locatable_by_global_threshold(settings):
    """朴素阈值攻击的成功率必须低于同容差下的随机猜测。"""
    provider = LocalCaptchaProvider(settings(provider="block_puzzle"))
    tolerance = provider.settings.slider_tolerance
    samples, solved = 40, 0
    for _ in range(samples):
        data, record = provider.create("login")
        with Image.open(BytesIO(base64.b64decode(data["image"]))) as image:
            columns = sorted({x for x, _ in _dark_pixels(image.convert("RGB"))})
        if columns and abs(columns[0] - record.points[0].x) <= tolerance:
            solved += 1
    baseline = (2 * tolerance + 1) / (provider.WIDTH - provider.GAP)
    assert solved / samples <= baseline * 2, "缺口可被全局阈值定位，滑块失去防护意义"


def test_backgrounds_are_bundled_and_span_the_tonal_range(settings):
    """随包背景必须存在且覆盖足够宽的亮度域，否则压暗的缺口会重新变得可分离。"""
    provider = LocalCaptchaProvider(settings(provider="block_puzzle"))
    assert len(provider.backgrounds) >= 8
    for raw in provider.backgrounds:
        with Image.open(BytesIO(raw)) as image:
            grey = image.convert("L")
            low, high = grey.getextrema()
        # 关心的是动态范围是否够宽：范围太窄时缺口变调会重新变成亮度离群点。
        assert high - low >= 150, f"背景动态范围过窄: {low}-{high}"


def test_background_directory_override_is_used_and_validated(settings, tmp_path):
    """部署可用自有图片替换随包背景；目录无效时明确失败。"""
    from framework.starter_captcha.exception.captcha_exception import CaptchaException

    custom = tmp_path / "backgrounds"
    custom.mkdir()
    Image.new("RGB", (320, 160), (11, 200, 90)).save(custom / "only.png")
    provider = LocalCaptchaProvider(settings(provider="block_puzzle", background_dir=str(custom)))
    assert len(provider.backgrounds) == 1
    data, _ = provider.create("login")
    with Image.open(BytesIO(base64.b64decode(data["image"]))) as image:
        assert image.size == (320, 160)

    with pytest.raises(CaptchaException):
        LocalCaptchaProvider(settings(provider="block_puzzle", background_dir=str(tmp_path / "无")))
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(CaptchaException):
        LocalCaptchaProvider(settings(provider="block_puzzle", background_dir=str(empty)))
