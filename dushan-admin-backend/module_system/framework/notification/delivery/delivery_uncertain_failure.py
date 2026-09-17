class DeliveryUncertainFailure(Exception):
    """请求已发起但结果未知，禁止自动重复外发。"""
