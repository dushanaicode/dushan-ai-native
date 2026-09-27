class SmsCodeConstants:
    DEBUG_CODE = "8888"
    # 原子递增单条验证码的校验次数；首次计数时设置过期，避免并发请求读到同一旧值。
    ATTEMPT_SCRIPT = """
local attempts = redis.call('INCR', KEYS[1])
if attempts == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return attempts
"""
