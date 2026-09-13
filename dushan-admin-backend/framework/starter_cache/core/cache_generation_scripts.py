from framework.starter_cache.constants.cache_constants import CacheConstants


class CacheGenerationScripts:
    """generation 栅栏键的单键 Lua 协议。

    栅栏键的值固定是 "<epoch>:<version>:<state>"：epoch 在键首次创建时随机生成，
    用来识别 Redis 被清空后重建的同名键；version 每次开始失效自增；state 表示
    这轮失效是否已经结束。三个脚本都只操作一个键，因此在单实例上天然原子。
    """

    # 读取栅栏；键不存在时原子写入初始值，避免并发读各自初始化出不同 epoch。
    READ_OR_INITIALIZE = f"""
-- cache_generation_read_or_initialize
local current = redis.call('GET', KEYS[1])
if current then
    return current
end
local initial = ARGV[1] .. ':{CacheConstants.INITIAL_GENERATION_VERSION}:' .. ARGV[2]
redis.call('SET', KEYS[1], initial)
redis.call('PERSIST', KEYS[1])
return initial
"""

    # 开始一轮失效：版本自增并进入 ACTIVE，期间任何回源发布都会被拒绝。
    BEGIN = f"""
-- cache_generation_begin
local current = redis.call('GET', KEYS[1])
local version = {CacheConstants.INITIAL_GENERATION_VERSION}
local epoch = ARGV[3]
if current then
    local first = string.find(current, ':')
    local second = first and string.find(current, ':', first + 1)
    if not first or not second then
        return redis.error_reply('invalid cache generation payload')
    end
    epoch = string.sub(current, 1, first - 1)
    version = tonumber(string.sub(current, first + 1, second - 1))
    local state = string.sub(current, second + 1)
    if epoch == '' then
        return redis.error_reply('invalid cache generation epoch')
    end
    if not version or version < {CacheConstants.INITIAL_GENERATION_VERSION} or version % 1 ~= 0 then
        return redis.error_reply('invalid cache generation version')
    end
    if state ~= ARGV[1] and state ~= ARGV[2] then
        return redis.error_reply('invalid cache generation state')
    end
end
version = version + 1
local next_value = epoch .. ':' .. tostring(version) .. ':' .. ARGV[1]
redis.call('SET', KEYS[1], next_value)
redis.call('PERSIST', KEYS[1])
return next_value
"""

    # 结束本轮失效：只有 epoch 与 version 都对得上才允许改成 FINALIZED。
    # 版本更高说明已经有新的失效开始，本轮直接放弃；版本更低说明数据被回退，必须报错。
    FINALIZE = """
-- cache_generation_finalize
local current = redis.call('GET', KEYS[1])
if not current then
    return redis.error_reply('missing cache generation payload')
end
local first = string.find(current, ':')
local second = first and string.find(current, ':', first + 1)
if not first or not second then
    return redis.error_reply('invalid cache generation payload')
end
local current_epoch = string.sub(current, 1, first - 1)
local current_version = tonumber(string.sub(current, first + 1, second - 1))
local current_state = string.sub(current, second + 1)
local expected_version = tonumber(ARGV[2])
if current_epoch == '' or not current_version or current_version % 1 ~= 0 then
    return redis.error_reply('invalid cache generation state')
end
if current_epoch ~= ARGV[1] then
    return 0
end
if current_version > expected_version then
    return 0
end
if current_version < expected_version then
    return redis.error_reply('cache generation moved backwards')
end
if current_state == ARGV[4] then
    return 1
end
if current_state ~= ARGV[3] then
    return redis.error_reply('invalid cache generation state')
end
redis.call('SET', KEYS[1], ARGV[1] .. ':' .. tostring(expected_version) .. ':' .. ARGV[4])
redis.call('PERSIST', KEYS[1])
return 1
"""
