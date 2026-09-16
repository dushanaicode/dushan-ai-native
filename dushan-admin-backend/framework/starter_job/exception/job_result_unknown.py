class JobResultUnknown(RuntimeError):
    """外部效果无法确认；记录未知终态，禁止自动重放整个业务。"""
