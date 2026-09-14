import base64
import json
from contextlib import ExitStack
from importlib.resources import files
from io import BytesIO
from pathlib import Path
from secrets import SystemRandom

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageStat

from framework.starter_captcha.config.captcha_settings import CaptchaSettings
from framework.starter_captcha.core.captcha_provider import CaptchaProvider
from framework.starter_captcha.exception.captcha_error_codes import CaptchaErrorCodes as Codes
from framework.starter_captcha.exception.captcha_exception import CaptchaException
from framework.starter_captcha.model.captcha_answer import CaptchaAnswer
from framework.starter_captcha.model.captcha_point import CaptchaPoint
from framework.starter_captcha.model.captcha_record import CaptchaRecord


class LocalCaptchaProvider(CaptchaProvider):
    """固定 320×160 原图，滑块为 48×160 透明条；点选按提示顺序点击字形中心。

    背景取自随包照片，每次先随机裁切、镜像和重采样，再从本次背景裁出滑块，
    避免直接复用公开原图像素。缺口与字形需保持可辨认，不以固定图库保密作为防护。
    原图按 JPEG 返回，滑块条需要透明通道按 PNG 返回。
    """

    WIDTH = 320
    HEIGHT = 160
    GAP = 48
    PIECE_HEIGHT = 160

    def __init__(self, settings: CaptchaSettings) -> None:
        self.settings = settings
        resource = files("framework.starter_captcha").joinpath("resources")
        try:
            manifest = json.loads(resource.joinpath("provenance.json").read_text(encoding="utf-8"))
            self.characters = manifest["characters"]
            allowed = set(self.characters) | {chr(c) for c in range(32, 127)}
            if not set(settings.watermark) <= allowed:
                raise ValueError("水印含打包字体不支持的字符")
            self.font_bytes = resource.joinpath("DushanCaptcha.ttf").read_bytes()
            ImageFont.truetype(BytesIO(self.font_bytes), 28)
            self.backgrounds = self._load_backgrounds(resource)
        except (OSError, ValueError, KeyError) as error:
            raise CaptchaException(Codes.RESOURCE, cause=error) from error

    def _load_backgrounds(self, resource) -> tuple[bytes, ...]:
        """读取全部背景图并逐张校验；部署可用 background_dir 换成自有图片。"""
        override = self.settings.background_dir
        if override:
            directory = Path(override).resolve()
            if not directory.is_dir():
                raise ValueError(f"验证码背景目录不存在: {override}")
            sources = [
                path.read_bytes()
                for path in sorted(directory.iterdir())
                if path.suffix.lower() in (".jpg", ".jpeg", ".png")
            ]
        else:
            backgrounds = resource.joinpath("backgrounds")
            sources = [
                backgrounds.joinpath(name).read_bytes()
                for name in sorted(item.name for item in backgrounds.iterdir())
                if name.lower().endswith((".jpg", ".jpeg", ".png"))
            ]
        if not sources:
            raise ValueError("验证码背景图片为空")
        for raw in sources:
            with Image.open(BytesIO(raw)) as probe:
                probe.load()
        return tuple(sources)

    @staticmethod
    def _image(stack: ExitStack, image: Image.Image) -> Image.Image:
        stack.callback(image.close)
        return image

    @staticmethod
    def _encode_photo(image: Image.Image) -> str:
        """背景是照片，用 JPEG：同样画质下体积约为 PNG 的四分之一。"""
        with BytesIO() as stream:
            image.save(stream, format="JPEG", quality=84, optimize=True, subsampling=0)
            return base64.b64encode(stream.getvalue()).decode("ascii")

    @staticmethod
    def _encode_piece(image: Image.Image) -> str:
        """滑块条需要透明通道，只能用 PNG。"""
        with BytesIO() as stream:
            image.save(stream, format="PNG", optimize=True)
            return base64.b64encode(stream.getvalue()).decode("ascii")

    def _background(self, stack: ExitStack, random: SystemRandom) -> Image.Image:
        """保留原始背景素材，按本次随机视窗生成工作图，变换参数不进入响应。"""
        raw = random.choice(self.backgrounds)
        source = self._image(stack, Image.open(BytesIO(raw)))
        image = self._image(stack, source.convert("RGB"))
        scale = random.uniform(0.68, 0.86)
        width, height = image.width * scale, image.height * scale
        left = random.uniform(0, image.width - width)
        top = random.uniform(0, image.height - height)
        image = self._image(
            stack,
            image.resize(
                (self.WIDTH, self.HEIGHT),
                Image.Resampling.LANCZOS,
                box=(left, top, left + width, top + height),
            ),
        )
        if random.getrandbits(1):
            image = self._image(stack, image.transpose(Image.Transpose.FLIP_LEFT_RIGHT))
        return image

    def _puzzle_mask(self, stack: ExitStack) -> Image.Image:
        """经典拼图轮廓：方体 + 右侧凸耳 + 左侧凹口，便于用户辨认缺口形状。"""
        mask = self._image(stack, Image.new("L", (self.GAP, self.GAP), 0))
        shape = ImageDraw.Draw(mask)
        shape.rounded_rectangle((6, 6, 41, 41), radius=5, fill=255)
        shape.ellipse((34, 16, 48, 30), fill=255)
        shape.ellipse((-1, 16, 13, 30), fill=0)
        return mask

    def _apply_gap(
        self,
        stack: ExitStack,
        image: Image.Image,
        mask: Image.Image,
        x: int,
        y: int,
        random: SystemRandom,
    ) -> None:
        """用同图异地区块填充缺口，再按整图亮度分位变调并描边，帮助辨认轮廓。"""
        box = (x, y, x + self.GAP, y + self.GAP)
        local = self._image(stack, image.crop(box))
        filler = self._image(stack, self._displaced_patch(image, x, y, random))
        # 异地区块先去色，再统一到本地平均色调：结构来自别处（模板匹配对不上），
        # 观感却仍与周围同色，读起来是一处凹陷而不是贴上去的另一张图。
        grey = self._image(stack, filler.convert("L").convert("RGB"))
        tint = self._image(
            stack, Image.new("RGB", local.size, tuple(round(v) for v in ImageStat.Stat(local).mean))
        )
        blended = self._image(stack, Image.blend(grey, tint, 0.42))

        source = ImageStat.Stat(self._image(stack, blended.convert("L"))).mean[0]
        low, high = self._tone_targets(image)
        # 参照整图的亮度调整对比，避免所有照片都使用同一种缺口填充色。
        target = low if source > (low + high) / 2 else high
        factor = min(max(target / max(source, 1.0), 0.35), 2.6) * random.uniform(0.92, 1.08)
        shadow = self._image(stack, ImageEnhance.Brightness(blended).enhance(factor))
        shadow = self._image(stack, shadow.filter(ImageFilter.GaussianBlur(1.1)))
        image.paste(shadow, (x, y), mask)

        rim = self._image(stack, mask.filter(ImageFilter.FIND_EDGES))
        rim = self._image(stack, rim.point(lambda value: min(value, 120)))
        highlight = self._image(stack, Image.new("RGB", (self.GAP, self.GAP), (245, 247, 250)))
        image.paste(highlight, (x, y), rim)

    def _displaced_patch(
        self, image: Image.Image, x: int, y: int, random: SystemRandom
    ) -> Image.Image:
        """用同图异地镜像区块填充，避免缺口与滑块只相差一个亮度变换。"""
        span_x, span_y = self.WIDTH - self.GAP, self.HEIGHT - self.GAP
        for _ in range(16):
            source_x = random.randrange(span_x + 1)
            source_y = random.randrange(span_y + 1)
            if abs(source_x - x) >= self.GAP or abs(source_y - y) >= self.GAP:
                break
        else:
            source_x = (x + self.GAP) % (span_x + 1)
            source_y = (y + self.GAP) % (span_y + 1)
        patch = image.crop((source_x, source_y, source_x + self.GAP, source_y + self.GAP))
        return patch.transpose(Image.FLIP_LEFT_RIGHT)

    @staticmethod
    def _tone_targets(image: Image.Image) -> tuple[float, float]:
        """返回整图亮度的低位与高位分位，作为缺口变调的落点。

        用分位而不是纯黑纯白：深色照片里几乎没有亮像素，若把缺口提到纯白，
        缺口就成了全图唯一的亮区，一次亮端阈值即可定位。
        """
        histogram = image.convert("L").histogram()
        total = sum(histogram) or 1
        wanted = (0.15, 0.85)
        results = []
        for ratio in wanted:
            limit = total * ratio
            running = 0
            for value, count in enumerate(histogram):
                running += count
                if running >= limit:
                    results.append(float(value))
                    break
            else:
                results.append(255.0)
        low, high = results
        # 分位过近时强制拉开，保证缺口仍然可见。
        if high - low < 40:
            low, high = max(low - 20, 0.0), min(high + 20, 255.0)
        return low, high

    def _draw_watermark(self, image: Image.Image) -> None:
        if not self.settings.watermark:
            return
        font = ImageFont.truetype(BytesIO(self.font_bytes), 14)
        draw = ImageDraw.Draw(image)
        # 先画深色描边再画浅色字，任何底色上都能读清。
        draw.text(
            (self.WIDTH - 8, self.HEIGHT - 4),
            self.settings.watermark,
            font=font,
            fill=(250, 250, 250),
            anchor="rd",
            stroke_width=2,
            stroke_fill=(20, 20, 20),
        )

    def _interference(self, image: Image.Image, random: SystemRandom) -> None:
        """干扰线颜色取自背景采样，避免引入背景里不存在的色值。"""
        if self.settings.interference <= 0:
            return
        pixels = image.load()
        draw = ImageDraw.Draw(image)
        for _ in range(self.settings.interference * 8):
            start = (random.randrange(self.WIDTH), random.randrange(self.HEIGHT))
            # 用短线段而不是横贯全图的长线：既保留干扰，又不会盖住缺口和字形。
            end = (
                min(max(start[0] + random.randint(-46, 46), 0), self.WIDTH - 1),
                min(max(start[1] + random.randint(-30, 30), 0), self.HEIGHT - 1),
            )
            tone = pixels[random.randrange(self.WIDTH), random.randrange(self.HEIGHT)]
            draw.line((start, end), fill=tone, width=1)

    def create(self, purpose: str) -> tuple[dict, CaptchaRecord]:
        random = SystemRandom()
        with ExitStack() as stack:
            image = self._image(stack, self._background(stack, random).copy())
            self._interference(image, random)
            data = {
                "width": self.WIDTH,
                "height": self.HEIGHT,
                "format": "jpeg",
                "piece_format": "png",
                "coordinates": "original_pixels",
            }
            if self.settings.provider == "block_puzzle":
                points = self._compose_puzzle(stack, image, data, random)
            else:
                points = self._compose_words(stack, image, data, random)
            self._draw_watermark(image)
            data["image"] = self._encode_photo(image)
            return data, CaptchaRecord(
                provider=self.settings.provider, purpose=purpose, points=points
            )

    def _compose_puzzle(
        self, stack: ExitStack, image: Image.Image, data: dict, random: SystemRandom
    ) -> list[CaptchaPoint]:
        """抠出拼图块，再把缺口画回背景；答案只有横向位置。"""
        x = random.randint(self.GAP + 12, self.WIDTH - self.GAP - 12)
        y = random.randint(10, self.HEIGHT - self.GAP - 10)
        mask = self._puzzle_mask(stack)

        cropped = self._image(stack, image.crop((x, y, x + self.GAP, y + self.GAP)).convert("RGBA"))
        cropped.putalpha(mask)
        piece = self._image(stack, Image.new("RGBA", (self.GAP, self.PIECE_HEIGHT)))
        piece.paste(cropped, (0, y))

        self._apply_gap(stack, image, mask, x, y, random)
        data.update(piece=self._encode_piece(piece), piece_width=self.GAP, axis="x", origin_y=0)
        return [CaptchaPoint(x=x, y=0)]

    def _compose_words(
        self, stack: ExitStack, image: Image.Image, data: dict, random: SystemRandom
    ) -> list[CaptchaPoint]:
        """在背景上写 5 个字，提示其中 3 个的点击顺序。"""
        font = ImageFont.truetype(BytesIO(self.font_bytes), 28)
        words = random.sample(self.characters, 5)
        cells = random.sample([(x, y) for x in (53, 160, 267) for y in (42, 112)], 5)
        pixels = image.load()
        positions = []
        for word, (cx, cy) in zip(words, cells, strict=True):
            cx = min(max(cx + random.randint(-12, 12), 32), self.WIDTH - 32)
            cy = min(max(cy + random.randint(-8, 8), 32), self.HEIGHT - 32)
            fill, stroke = self._word_colours(pixels, cx, cy)
            layer = self._image(stack, Image.new("RGBA", (64, 64)))
            pen = ImageDraw.Draw(layer)
            left, top, right, bottom = pen.textbbox((0, 0), word, font=font, stroke_width=2)
            pen.text(
                (32 - (left + right) / 2, 32 - (top + bottom) / 2),
                word,
                font=font,
                fill=fill,
                stroke_width=2,
                stroke_fill=stroke,
            )
            rotated = self._image(
                stack, layer.rotate(random.randint(-25, 25), resample=Image.Resampling.BICUBIC)
            )
            image.paste(rotated, (cx - 32, cy - 32), rotated)
            positions.append(CaptchaPoint(x=cx, y=cy))
        selected = random.sample(range(5), 3)
        data["words"] = [words[index] for index in selected]
        return [positions[index] for index in selected]

    @staticmethod
    def _word_colours(
        pixels, cx: int, cy: int
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """按背景亮度选择深字浅边或浅字深边，保持字形可读。"""
        red, green, blue = pixels[cx, cy]
        luminance = 0.299 * red + 0.587 * green + 0.114 * blue
        if luminance >= 128:
            return (18, 20, 28), (238, 240, 245)
        return (240, 242, 246), (16, 18, 24)

    async def verify(
        self, record: CaptchaRecord, answer: CaptchaAnswer, client_ip: str | None
    ) -> bool:
        if self.settings.provider == "block_puzzle":
            return (
                answer.points[0].y == 0
                and abs(answer.points[0].x - record.points[0].x) <= self.settings.slider_tolerance
            )
        return all(
            (a.x - b.x) ** 2 + (a.y - b.y) ** 2 <= self.settings.click_tolerance**2
            for a, b in zip(answer.points, record.points, strict=True)
        )
