import importlib
import inspect
import pkgutil
from typing import Annotated, get_args, get_origin, get_type_hints

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.params import Depends
from fastapi.routing import APIRoute, _iter_routes_with_context

from framework.common.schemas.base_vo import BaseVO
from framework.common.schemas.request.id_list_req_vo import IdListReqVO
from framework.starter_web.response.result import Result
from module_system.controller.admin.announcement.vo.announcement_save_req_vo import (
    AnnouncementSaveReqVO,
)
from module_system.controller.admin.mail.vo.template.template_send_req_vo import (
    MailTemplateSendReqVO,
)
from module_system.controller.admin.notification.vo.notice.notice_send_req_vo import NoticeSendReqVO
from module_system.controller.admin.sms.vo.channel.channel_save_req_vo import SmsChannelSaveReqVO
from module_system.router import admin_router_main
from module_system.service.mail.bo.mail_batch_send_bo import MailBatchSendBO


@pytest.mark.parametrize("model", [AnnouncementSaveReqVO, SmsChannelSaveReqVO])
def test_updated_request_examples_are_valid(model):
    for example in model.model_config["json_schema_extra"]["examples"]:
        model.model_validate(example)


def test_http_business_inputs_are_vo_models():
    for route, _ in _iter_routes_with_context(admin_router_main.routes):
        if not isinstance(route, APIRoute):
            continue
        hints = get_type_hints(route.endpoint, include_extras=True)
        for name, parameter in inspect.signature(route.endpoint).parameters.items():
            annotation = hints[name]
            if get_origin(annotation) is Annotated:
                annotation = get_args(annotation)[0]
            if annotation in (Request, Response) or isinstance(parameter.default, Depends):
                continue
            assert isinstance(annotation, type) and issubclass(annotation, BaseVO), (
                route.path,
                name,
                annotation,
            )


@pytest.mark.parametrize("module_name,expected_count", [("module_system", 19), ("module_infra", 6)])
def test_batch_id_routes_share_array_request_and_openapi(module_name, expected_count):
    router = importlib.import_module(f"{module_name}.router").admin_router_main
    app = FastAPI()
    app.include_router(router)
    document = app.openapi()
    checked = 0
    for route, context in _iter_routes_with_context(router.routes):
        if not isinstance(route, APIRoute):
            continue
        path = context.path if context else route.path
        if not path.endswith("/delete-list") and not path.endswith(
            "/notification/message/update-read"
        ):
            continue
        assert get_type_hints(route.endpoint)["req_vo"] is IdListReqVO, path
        method = next(iter(route.methods)).lower()
        operation = document["paths"][path][method]
        if method == "delete":
            parameter = next(item for item in operation["parameters"] if item["name"] == "ids")
            assert parameter["in"] == "query" and parameter["required"]
            assert parameter.get("style", "form") == "form"
            assert parameter.get("explode", True)
            schema = parameter["schema"]
        else:
            body = operation["requestBody"]["content"]["application/json"]["schema"]
            schema = document["components"]["schemas"][body["$ref"].rsplit("/", 1)[1]][
                "properties"
            ]["ids"]
        assert schema["type"] == "array" and schema["minItems"] == 1, path
        assert schema["items"]["type"] == "string", path
        assert schema["items"]["pattern"] == r"^[1-9][0-9]{0,18}$", path
        checked += 1
    assert checked == expected_count


def test_business_service_names_are_interfaces():
    package = importlib.import_module("module_system.service")
    for info in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not info.name.endswith("_service"):
            continue
        module = importlib.import_module(info.name)
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and value.__module__ == info.name
                and value.__name__.endswith("Service")
            ):
                assert getattr(value, "_is_protocol", False), value


def test_aliases_belong_to_web_models_and_leave_dynamic_dictionary_keys_alone():
    request = MailTemplateSendReqVO.model_validate(
        {
            "toMails": ["recipient@example.com"],
            "templateCode": "welcome",
            "templateParams": {"user_name": "Tester"},
        }
    )
    assert request.to_mails == ["recipient@example.com"]
    command = MailBatchSendBO(**request.model_dump(by_alias=False), user_id=42)
    assert command.template_params == {"user_name": "Tester"}
    assert "to_mails" in command.model_dump() and "toMails" not in command.model_dump()
    response = Result.success(data=request).to_response()["data"]
    assert response["toMails"] == ["recipient@example.com"]
    assert response["templateParams"] == {"user_name": "Tester"}
    notification = NoticeSendReqVO.model_validate({"id": "42", "userIds": ["43"], "deptIds": []})
    assert notification.user_ids == [43]
