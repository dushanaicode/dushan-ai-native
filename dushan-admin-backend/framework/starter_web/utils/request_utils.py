from collections.abc import Mapping
from typing import TypeVar

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)
type QueryParams = dict[str, str | list[str]]


class RequestUtils:
    """读取多值查询参数并接入 FastAPI 字段错误，保持空串和重复项。"""

    @staticmethod
    def get_query_params(request: Request) -> QueryParams:
        """单值返回字符串，多值按出现顺序返回列表。"""
        return {
            name: values[0] if len(values := request.query_params.getlist(name)) == 1 else values
            for name in request.query_params
        }

    @staticmethod
    def process_multi_params(request: Request, param_mapping: Mapping[str, str]) -> QueryParams:
        """按显式格式将选中的参数展开，例如 {'tags': 'tags[%d]'}。"""
        values = RequestUtils.get_query_params(request)
        for name, template in param_mapping.items():
            if name not in values:
                continue
            entries = request.query_params.getlist(name)
            del values[name]
            for index, item in enumerate(entries):
                key = template % index
                if key in values:
                    raise RequestValidationError(
                        [
                            {
                                "type": "value_error",
                                "loc": ("query", name),
                                "msg": "查询参数映射后重名",
                                "input": None,
                            }
                        ]
                    )
                values[key] = item
        return values

    @staticmethod
    def validate_with_multi_params(
        request: Request, model_class: type[Model], param_mapping: Mapping[str, str]
    ) -> Model:
        """校验显式索引映射后的模型并保留查询参数位置。"""
        return RequestUtils._validate(
            RequestUtils.process_multi_params(request, param_mapping), model_class
        )

    @staticmethod
    def _validate(params: QueryParams, model_class: type[Model]) -> Model:
        """把 Pydantic 输入错误转为请求错误，避免错误进入通用 500 分类。"""
        try:
            return model_class.model_validate(params)
        except ValidationError as exc:
            errors = [
                {**error, "loc": ("query", *error["loc"])}
                for error in exc.errors(include_url=False, include_input=False)
            ]
            raise RequestValidationError(errors) from exc
