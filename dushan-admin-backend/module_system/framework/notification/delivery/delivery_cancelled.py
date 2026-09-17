class DeliveryCancelled(Exception):
    """外发策略在 Provider 请求前明确取消，消费者应正常 ACK。"""
