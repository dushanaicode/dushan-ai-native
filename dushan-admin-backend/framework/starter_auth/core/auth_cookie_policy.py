from http.cookiejar import DefaultCookiePolicy


class AuthCookiePolicy(DefaultCookiePolicy):
    """Token API 不需要浏览器 Cookie，阻止共享传输在不同业务应用间携带 Cookie。"""

    def set_ok(self, cookie, request):
        return False

    def return_ok(self, cookie, request):
        return False
