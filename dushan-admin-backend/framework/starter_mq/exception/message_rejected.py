class MessageRejected(Exception):
    """业务明确拒绝此消息，不再重试；异常文本不写入消费日志。"""
