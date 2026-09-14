from typing import Any, ClassVar

from fastapi import FastAPI

from framework.starter_web.response.result import Result


class BusinessOpenAPI:
    """让公共异常处理的接口文档与业务 HTTP 200 响应一致。

    在应用装配时将 app.openapi 指向本实例的 build；沿用 FastAPI 的生成与缓存失效。
    只移除框架自动声明的 422，保留成功模型、其他媒体类型和显式特殊状态。
    NativeResponse_ 前缀用于本适配器生成的错误 schema，避免覆盖业务同名模型。
    """

    methods: ClassVar[tuple[str, ...]] = (
        "get",
        "put",
        "post",
        "delete",
        "options",
        "head",
        "patch",
        "trace",
    )

    def __init__(self, app: FastAPI) -> None:
        """保留当前应用的原生生成入口，不共享其他应用的文档缓存。"""
        self._generate = app.openapi
        self._schema: dict[str, Any] | None = None

    def build(self) -> dict[str, Any]:
        """迁移默认校验响应到 200，成功与错误 schema 使用 anyOf 并列。"""
        schema = self._generate()
        if schema is self._schema:
            return schema
        changed = False
        error_ref = {"$ref": "#/components/schemas/NativeResponse_BusinessError"}
        for path in schema.get("paths", {}).values():
            for method in self.methods:
                if method not in path:
                    continue
                responses = path[method]["responses"]
                if responses.get("422") == {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/HTTPValidationError"}
                        }
                    },
                }:
                    del responses["422"]
                response = responses.setdefault("200", {"description": "业务响应"})
                if method == "head":
                    for item in responses.values():
                        item.pop("content", None)
                    response["description"] += "；HEAD 仅发送状态和响应头。"
                    continue
                response["description"] += (
                    "；业务异常也返回 HTTP 200，code 非 0，message 为整体提示，error.fields 为字段明细。"
                )
                content = response.setdefault("content", {}).setdefault("application/json", {})
                content["schema"] = (
                    {"anyOf": [content["schema"], error_ref]} if "schema" in content else error_ref
                )
                changed = True
        if changed:
            error_schema = Result[None].model_json_schema(
                mode="serialization", ref_template="#/components/schemas/NativeResponse_{model}"
            )
            definitions = error_schema.pop("$defs")
            error_schema["properties"]["code"]["not"] = {"const": 0}
            error_schema["required"] = ["code", "message", "data", "error"]
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            components.update(
                {f"NativeResponse_{name}": value for name, value in definitions.items()}
            )
            components["NativeResponse_BusinessError"] = error_schema
        self._schema = schema
        return schema
