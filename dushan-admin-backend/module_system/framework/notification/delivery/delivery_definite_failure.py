class DeliveryDefiniteFailure(Exception):
    """Provider 明确未接受发送，允许按策略重新尝试。"""
