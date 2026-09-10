import json
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from framework.common.i18n.core.i18n_locale_root import I18nLocaleRoot

LocaleTag = Annotated[str, Field(pattern=r"^[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*$")]


class I18nOptions(BaseModel):
    """配置语言、资源和失败策略，同一份模型用于 YAML 校验及组件运行。

    新增语言时将标签加入 supported_locales，并提供同名 JSON，无须修改枚举。
    default 是调用方完成的公开提示；格式参数只作用于命中的翻译模板。
    所有列表字段的环境变量采用 JSON 数组，required_message_keys 可声明业务必需文案。
    配置修改需重启；hot_reload 仅更新已配置目录中的文案内容。
    """

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)

    enabled: bool = True
    default_locale: LocaleTag = "zh-CN"
    supported_locales: tuple[LocaleTag, ...] = Field(default=("zh-CN", "en-US"), min_length=1)
    match_mode: Literal["exact", "primary"] = "primary"
    fallback_to_default: bool = True
    missing_policy: Literal["fallback", "key", "error"] = "fallback"
    format_error_policy: Literal["fallback", "error"] = "fallback"
    log_missing: bool = True
    cache_size: int = Field(default=4096, ge=0)
    missing_cache_size: int = Field(default=1024, ge=0)
    validate_translations: bool = True
    validation_policy: Literal["warning", "error"] = "error"
    hot_reload: bool = False
    reload_interval: float = Field(default=2.0, gt=0, allow_inf_nan=False)
    include_builtin: bool = True
    resource_roots: tuple[I18nLocaleRoot, ...] = ()
    scopes: tuple[str, ...] | None = None
    required_message_keys: tuple[Annotated[str, Field(min_length=1)], ...] = ()

    @field_validator(
        "supported_locales", "resource_roots", "scopes", "required_message_keys", mode="before"
    )
    @classmethod
    def parse_environment_array(cls, value: object) -> object:
        """将环境变量中的 JSON 数组交给相应字段校验，不接受逗号字符串。"""
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("i18n 列表配置必须是 JSON 数组") from None
            if not isinstance(value, list):
                raise ValueError("i18n 列表配置必须是 JSON 数组")
        return value

    @model_validator(mode="after")
    def validate_languages(self) -> Self:
        """保证默认语言可用、标签大小写不重复，筛选项不包含空 scope。"""
        tags = tuple(tag.casefold() for tag in self.supported_locales)
        if len(tags) != len(set(tags)):
            raise ValueError("supported_locales 不能包含重复语言")
        if self.default_locale not in self.supported_locales:
            raise ValueError("default_locale 必须与 supported_locales 中的一个标签一致")
        if self.scopes is not None and any(
            not scope or scope != scope.strip() for scope in self.scopes
        ):
            raise ValueError("scopes 不能包含空值或首尾空白")
        if any(key != key.strip() for key in self.required_message_keys):
            raise ValueError("required_message_keys 不能包含首尾空白")
        return self
