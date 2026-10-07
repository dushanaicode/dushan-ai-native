class QrLoginScriptConstants:
    CREATE = "return redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2], 'NX')"
    READ = "return redis.call('GET', KEYS[1])"
    TRANSITION = """
local raw = redis.call('GET', KEYS[1])
if not raw then return 'expired' end
if raw ~= ARGV[1] then return 'changed' end
if ARGV[2] == 'consume' then
    redis.call('DEL', KEYS[1])
else
    redis.call('SET', KEYS[1], ARGV[2], 'KEEPTTL')
end
return 'ok'
"""
