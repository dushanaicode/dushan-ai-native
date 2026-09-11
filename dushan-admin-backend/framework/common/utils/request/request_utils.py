from collections.abc import Mapping
from types import UnionType
from typing import TypeVar, Union, get_args, get_origin

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import AliasChoices, BaseModel, ValidationError

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

    @classmethod
    def validate_with_auto_list_params(cls, request: Request, model_class: type[Model]) -> Model:
        """将列表字段的单个查询值也包装成列表；字段别名以模型声明为准。"""
        params = cls.get_query_params(request)
        for name, field in model_class.model_fields.items():
            if not cls._annotation_contains_list(field.annotation):
                continue
            aliases = []
            alias = field.validation_alias
            if isinstance(alias, str):
                aliases.append(alias)
            elif isinstance(alias, AliasChoices):
                aliases.extend(choice for choice in alias.choices if isinstance(choice, str))
            if alias is None or model_class.model_config.get("validate_by_name", False):
                aliases.append(name)
            for accepted_name in aliases:
                if accepted_name in params and isinstance(params[accepted_name], str):
                    params[accepted_name] = [params[accepted_name]]
        return cls._validate(params, model_class)

    @staticmethod
    def _annotation_contains_list(annotation: object) -> bool:
        """识别直接列表以及显式联合类型中的列表成员。"""
        origin = get_origin(annotation)
        return (
            annotation is list
            or origin is list
            or origin in (UnionType, Union)
            and any(get_origin(member) is list or member is list for member in get_args(annotation))
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
