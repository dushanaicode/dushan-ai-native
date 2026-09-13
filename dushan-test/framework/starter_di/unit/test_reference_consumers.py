import ast
import functools
import json
from collections.abc import Callable
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from fixtures.di_reference_cases import SOURCES
from framework.starter_di.context.application_context import ApplicationContext
from framework.starter_di.context.get_bean import get_bean
from framework.starter_di.decorators.components import service

pytestmark = pytest.mark.unit


def load_case(name, tmp_path, **values):
    path = tmp_path / f"reference_{name}.py"
    path.write_text(SOURCES[name], encoding="utf-8")
    namespace = {
        "Any": Any,
        "Callable": Callable,
        "functools": functools,
        "ApplicationContext": ApplicationContext,
        "get_bean": get_bean,
        "json": json,
        **values,
    }
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


async def test_reference_transaction_decorators_resolve_the_current_app(contexts, tmp_path):
    @service
    class SessionProvider:
        def __init__(self):
            self.events = []

        @asynccontextmanager
        async def transactional_session(self):
            self.events.append("begin")
            try:
                yield
            except ValueError:
                self.events.append("rollback")
                raise
            else:
                self.events.append("commit")

        @asynccontextmanager
        async def requires_new_transactional_session(self):
            self.events.append("requires_new")
            yield

    case = load_case("transaction", tmp_path, SessionProvider=SessionProvider)

    @case["transactional"]
    async def operation(*, fail=False):
        provider = get_bean(SessionProvider)
        if fail:
            raise ValueError("business failure")
        return provider

    @case["transactional_requires_new"]
    async def independent():
        return get_bean(SessionProvider)

    first, second = contexts([SessionProvider]), contexts([SessionProvider])
    await first.startup()
    await second.startup()
    first.mark_ready()
    second.mark_ready()
    a = await first.tasks.run(operation)
    b = await second.tasks.run(operation)
    assert a is not b and a.events == b.events == ["begin", "commit"]
    assert await first.tasks.run(independent) is a
    with pytest.raises(ValueError):
        await first.tasks.run(operation, fail=True)
    assert a.events[-2:] == ["begin", "rollback"] and b.events == ["begin", "commit"]
    await first.shutdown()
    await second.shutdown()


async def test_reference_job_and_ai_tool_use_real_task_context(contexts, tmp_path):
    @service
    class JobOrchestratorService:
        def __init__(self):
            self.calls = []

        async def orchestrate(self, **kwargs):
            self.calls.append(kwargs)

    @service
    class SmsTemplateService:
        async def get_sms_template_list(self):
            return [{"name": "real DI lookup"}]

    class SmsTemplateToolRespVO(BaseModel):
        name: str

    logger = SimpleNamespace(debug=lambda *args: None, error=lambda *args: None)
    job = load_case("job", tmp_path, logger=logger, JobOrchestratorService=JobOrchestratorService)
    tool = load_case(
        "ai_tool",
        tmp_path,
        SmsTemplateService=SmsTemplateService,
        SmsTemplateToolRespVO=SmsTemplateToolRespVO,
        SystemModuleTool=object,
        PermissionTypeEnum=SimpleNamespace(LIST=SimpleNamespace(code="list")),
    )
    current = contexts([JobOrchestratorService, SmsTemplateService])
    await current.startup()
    current.mark_ready()
    await current.tasks.run(job["orchestrated_job_entry"], 7, "handler", None)
    assert json.loads(await current.tasks.run(tool["ListSmsTemplatesTool"]().execute)) == [
        {"name": "real DI lookup"}
    ]
    with current.execution():
        assert get_bean(JobOrchestratorService).calls == [
            {"job_id": 7, "handler_name": "handler", "handler_param": None}
        ]
    await current.shutdown()


async def test_reference_cache_requires_removing_class_level_service_cache(contexts, tmp_path):
    @service
    class CacheHandler:
        pass

    case = load_case("cache", tmp_path, CacheHandler=CacheHandler)
    legacy = case["Cacheable"]
    first, second = contexts([CacheHandler]), contexts([CacheHandler])
    await first.startup()
    await second.startup()
    first.mark_ready()
    second.mark_ready()
    with first.execution():
        original = legacy._get_cache_handler()
    with second.execution():
        # 原类级缓存跨应用复用了 A；仅改 get_bean 的导入不能修复这个旧用法。
        assert legacy._get_cache_handler() is original
        assert get_bean(CacheHandler) is not original

    tree = ast.parse(SOURCES["cache"])
    owner = tree.body[0]
    method = next(node for node in owner.body if isinstance(node, ast.FunctionDef))
    method.body = ast.parse("return get_bean(bean_type=CacheHandler)").body
    owner.body = [method]
    migrated_path = tmp_path / "migrated_cache_access.py"
    migrated_path.write_text(ast.unparse(ast.fix_missing_locations(tree)), encoding="utf-8")
    namespace = {"CacheHandler": CacheHandler, "get_bean": get_bean}
    exec(compile(migrated_path.read_text(encoding="utf-8"), str(migrated_path), "exec"), namespace)
    migrated = namespace["Cacheable"]
    with first.execution():
        a = migrated._get_cache_handler()
        assert migrated._get_cache_handler() is a
    await first.shutdown()
    with second.execution():
        assert migrated._get_cache_handler() is not a
    await second.shutdown()
