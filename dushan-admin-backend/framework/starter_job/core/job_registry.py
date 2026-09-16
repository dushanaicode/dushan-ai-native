from pydantic import ValidationError

from framework.starter_job.cron.cron_schedule import CronSchedule
from framework.starter_job.exception.job_exception import JobException


class JobRegistry:
    def __init__(self, handlers, timezone):
        self.handlers = {}
        self.timezone = timezone
        for handler in handlers:
            declaration = vars(handler)["__job__"]
            if declaration.key in self.handlers:
                raise JobException("handler")
            self.handlers[declaration.key] = handler

    def require(self, key):
        if key not in self.handlers:
            raise JobException("handler")
        return self.handlers[key]

    def parameters(self, definition):
        handler = self.require(definition.handler_key)
        try:
            return handler.__job__.parameters.model_validate(
                definition.parameters, strict=True, extra="forbid"
            )
        except ValidationError as error:
            raise JobException("parameters", cause=error) from error

    def validate(self, definition):
        self.parameters(definition)
        return CronSchedule(definition.cron, self.timezone)
