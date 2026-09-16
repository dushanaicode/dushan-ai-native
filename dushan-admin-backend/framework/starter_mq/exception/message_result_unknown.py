class MessageResultUnknown(Exception):
    """副作用可能已经提交，禁止自动重新执行业务。"""
