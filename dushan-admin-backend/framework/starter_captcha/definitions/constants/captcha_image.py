class CaptchaImage:
    """本地验证码原图尺寸；坐标契约与绘制实现共用同一份声明。

    模型边界和 Provider 必须取同一个值：只改一处会让合法答案被坐标上界静默拒绝。
    改动同时影响前端 services/captcha/schema.ts 的原图换算与坐标上界，需一并调整。
    """

    WIDTH = 320
    HEIGHT = 160
