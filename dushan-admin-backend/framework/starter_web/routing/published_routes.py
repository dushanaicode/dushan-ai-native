class PublishedRoutes(tuple):
    """保留原生路由集合的读取语义，启动后明确拒绝集合写入口。"""

    def _reject(self, *args, **kwargs):
        raise RuntimeError("Web 路由已经发布，不能在运行期修改路由集合")

    # 对原生路由器使用的 list 写操作统一拒绝，不改变任何匹配或分派逻辑。
    append = extend = insert = pop = remove = clear = sort = reverse = _reject
    __setitem__ = __delitem__ = __iadd__ = __imul__ = _reject
