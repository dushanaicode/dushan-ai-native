from aiokafka.abc import ConsumerRebalanceListener


class KafkaAssignments(ConsumerRebalanceListener):
    """分配代次阻止旧在途回调提交新代次的 offset。"""

    def __init__(self, maximum):
        self.version = 0
        self.maximum = maximum
        self.exceeded = False

    async def on_partitions_revoked(self, revoked):
        self.version += 1

    async def on_partitions_assigned(self, assigned):
        self.version += 1
        self.exceeded = len(assigned) > self.maximum
