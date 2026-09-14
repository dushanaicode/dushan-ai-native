import base64
from contextlib import ExitStack
from io import BytesIO
from random import Random

from PIL import Image

from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.provider.local_captcha_provider import LocalCaptchaProvider


def lookup_original_background(data, references):
    """只用公开滑块及公开图库查表；不接收背景变换参数、所选图片或答案。"""
    with Image.open(BytesIO(base64.b64decode(data["piece"]))) as strip:
        pixels = strip.load()
        with strip.getchannel("A") as alpha:
            box = alpha.getbbox()
        samples = [
            (x, y, pixels[x, y][:3])
            for y in range(box[1] + 4, box[3] - 3, 5)
            for x in range(16, 39, 5)
            if pixels[x, y][3] == 255
        ]
    best_score, best_x = float("inf"), 0
    for reference in references:
        pixels = reference.load()
        for shift in range(reference.width - strip.width + 1):
            errors = sorted(
                sum(abs(a - b) for a, b in zip(colour, pixels[x + shift, y], strict=True))
                for x, y, colour in samples
            )
            # 忽略被少量干扰线覆盖的采样点，避免把干扰线误当成查表防护。
            score = sum(errors[: len(errors) * 3 // 4])
            if score < best_score:
                best_score, best_x = score, shift
    return best_x


async def test_public_originals_do_not_reveal_slider_position(settings, monkeypatch):
    """固定样本覆盖全部12张原图；阻止退回可直接查表的像素复用，不代表完整对抗评测。"""
    random = Random(20260912)
    monkeypatch.setattr(
        "framework.starter_captcha.provider.local_captcha_provider.SystemRandom", lambda: random
    )
    provider = LocalCaptchaProvider(settings(provider="block_puzzle"))
    backgrounds = provider.backgrounds
    assert len(backgrounds) == 12
    solved = 0
    with ExitStack() as stack:
        references = []
        for raw in backgrounds:
            source = stack.enter_context(Image.open(BytesIO(raw)))
            references.append(stack.enter_context(source.convert("RGB")))
        for raw in backgrounds:
            provider.backgrounds = (raw,)
            for _ in range(6):
                data, record = provider.create("login")
                guess = lookup_original_background(data, references)
                solved += await provider.verify(
                    record, CaptchaAnswer(points=[{"x": guess, "y": 0}]), None
                )
    # 在5像素容差下允许偶然猜中；旧实现的72/72应明确失败。
    assert solved <= 12, f"公开图库查表仍可恢复滑块位置：{solved}/72"
