import json
from typing import Protocol

from openai import APITimeoutError, OpenAI, OpenAIError
from pydantic import ValidationError

from ..config import Settings
from ..schemas import AgentIntent


class ModelUnavailable(Exception):
    pass


class ModelOutputError(Exception):
    pass


class ModelClient(Protocol):
    def parse_request(self, text: str) -> AgentIntent | dict: ...


class UnavailableModelClient:
    def parse_request(self, text: str) -> AgentIntent:
        raise ModelUnavailable("尚未配置托管模型 API")


class OpenAICompatibleClient:
    def __init__(self, settings: Settings):
        kwargs = {
            "api_key": settings.model_api_key,
            "timeout": settings.model_timeout_seconds,
            "max_retries": 1,
        }
        if settings.model_base_url:
            kwargs["base_url"] = settings.model_base_url
        self.client = OpenAI(**kwargs)
        self.model_name = settings.model_name

    def parse_request(self, text: str) -> AgentIntent:
        system_prompt = (
            "你是中文族谱请求解析器。只返回 JSON，不回答问题。"
            "kind 只能是 relationship_query、create_person、create_child。"
            "关系查询填写 source_name、target_name；新增人物填写 person_name、gender；"
            "新增子女还要填写 parent_name。gender 只能是 male、female、unknown。"
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
            )
        except APITimeoutError as error:
            raise ModelUnavailable("模型响应超时，请稍后重试") from error
        except OpenAIError as error:
            raise ModelUnavailable("模型服务暂时不可用") from error

        content = response.choices[0].message.content
        try:
            return AgentIntent.model_validate(json.loads(content or ""))
        except (json.JSONDecodeError, ValidationError) as error:
            raise ModelOutputError("模型返回的结构化结果无效") from error
