"""Per-request adapter for the vendor's Databricks Responses gateway.

The browser backend supplies the forwarded user token. This adapter never looks
for alternate credentials or changes identity after an authorization failure.
Responses output, including reasoning items, stays private to this one run and
is replayed to the gateway when the existing agent returns MCP tool results.
"""

from __future__ import annotations

from copy import deepcopy

import httpx

from alz_compass.agent import ALLOWED_TOOLS, AgentError, ModelConfig, redact

DEFAULT_MODEL = "models.ai.gpt-5-6-luna"


def _invalid_response() -> AgentError:
    return AgentError(
        "model_response_invalid",
        "The model returned an unsupported or invalid response; "
        "no answer was accepted.",
    )


class ResponsesModel:
    """ChatModel interface backed by Responses; use a fresh instance per run.

    ``client`` is supplied and closed by the caller. Credentials are used only
    for this request's fixed workspace origin, never as model input or trace data.
    """

    def __init__(
        self,
        host: str,
        token: str,
        model: str = DEFAULT_MODEL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        try:
            origin = ModelConfig(host, token, model).workspace_origin()
        except (ValueError, TypeError, AttributeError):
            raise AgentError(
                "configuration_invalid", "Configure a valid Databricks workspace URL."
            ) from None
        if not isinstance(token, str) or not token.strip():
            raise AgentError(
                "model_authentication_missing",
                "Open the app through Databricks and enable its ai-gateway user scope.",
            )
        if "\r" in token or "\n" in token:
            raise AgentError(
                "model_authentication_invalid", "The app received an invalid sign-in."
            )
        if not isinstance(model, str) or not model.strip() or len(model) > 200:
            raise AgentError(
                "configuration_invalid", "Configure the vendor model service name."
            )
        if client is None:
            raise TypeError("ResponsesModel requires an HTTPX AsyncClient")
        self.model = model
        self.client = client
        self.endpoint = origin + "/ai-gateway/openai/v1/responses"
        self._token = token
        self._input: list[dict] = []
        self._previous_messages: list[dict] | None = None
        self._assistant: dict | None = None
        self._pending_calls: set[str] = set()
        self._finished = False

    @staticmethod
    def _tools(tools: list[dict]) -> list[dict]:
        converted = []
        names = set()
        for tool in tools:
            function = tool.get("function", {})
            name = function.get("name")
            parameters = function.get("parameters")
            if (
                tool.get("type") != "function"
                or name not in ALLOWED_TOOLS
                or name in names
                or not isinstance(parameters, dict)
            ):
                raise AgentError(
                    "tool_schema_invalid",
                    "The app supplied an invalid MCP tool schema.",
                )
            names.add(name)
            converted.append(
                {
                    "type": "function",
                    "name": name,
                    "description": function.get("description", ""),
                    "parameters": deepcopy(parameters),
                    # Preserve optional MCP arguments instead of normalizing the
                    # schema to Responses' stricter required-field convention.
                    "strict": False,
                }
            )
        return converted

    def _next_input(self, messages: list[dict]) -> list[dict]:
        invalid = AgentError(
            "model_conversation_invalid",
            "The model conversation could not be continued; start a new question.",
        )
        if self._finished or not isinstance(messages, list):
            raise invalid
        if self._previous_messages is None:
            if not messages or any(
                not isinstance(message, dict)
                or message.get("role") not in {"system", "user"}
                or not isinstance(message.get("content"), str)
                for message in messages
            ):
                raise invalid
            return [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ]
        prefix = self._previous_messages + [self._assistant]
        if messages[: len(prefix)] != prefix:
            raise invalid
        returned = set()
        results = []
        for message in messages[len(prefix) :]:
            if not isinstance(message, dict):
                raise invalid
            call_id = message.get("tool_call_id")
            if (
                message.get("role") != "tool"
                or call_id not in self._pending_calls
                or call_id in returned
                or not isinstance(message.get("content"), str)
            ):
                raise invalid
            returned.add(call_id)
            results.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": message["content"],
                }
            )
        if returned != self._pending_calls:
            raise invalid
        return deepcopy(self._input) + results

    @staticmethod
    def _message(payload: dict) -> tuple[dict, list[dict]]:
        if not isinstance(payload, dict):
            raise _invalid_response()
        if payload.get("status") == "incomplete":
            raise AgentError(
                "model_truncated",
                "The model response was incomplete; no final answer was accepted.",
            )
        if payload.get("status") != "completed" or payload.get("error"):
            raise _invalid_response()
        output = payload.get("output")
        if not isinstance(output, list) or not output:
            raise _invalid_response()
        text, calls = [], []
        call_ids = set()
        for item in output:
            if not isinstance(item, dict):
                raise _invalid_response()
            kind = item.get("type")
            if kind == "reasoning":
                continue
            if kind == "function_call":
                name, call_id = item.get("name"), item.get("call_id")
                if name not in ALLOWED_TOOLS:
                    raise AgentError(
                        "tool_not_allowed",
                        "The model requested a tool outside the T2D Compass tools.",
                    )
                if (
                    not isinstance(call_id, str)
                    or not call_id
                    or call_id in call_ids
                    or not isinstance(item.get("arguments"), str)
                ):
                    raise _invalid_response()
                call_ids.add(call_id)
                calls.append(
                    {
                        "type": "function",
                        "id": call_id,
                        "function": {"name": name, "arguments": item["arguments"]},
                    }
                )
            elif kind == "message":
                if item.get("role") != "assistant" or not isinstance(
                    item.get("content"), list
                ):
                    raise _invalid_response()
                for part in item["content"]:
                    if not isinstance(part, dict):
                        raise _invalid_response()
                    if part.get("type") == "refusal":
                        raise AgentError(
                            "model_refused", "The model declined this research request."
                        )
                    if part.get("type") != "output_text" or not isinstance(
                        part.get("text"), str
                    ):
                        raise _invalid_response()
                    text.append(part["text"])
            else:
                raise _invalid_response()
        content = "\n".join(text) or None
        if not calls and not (content and content.strip()):
            raise AgentError("empty_answer", "The model did not return an answer.")
        return {"role": "assistant", "content": content, "tool_calls": calls}, output

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        inputs = self._next_input(messages)
        request = {
            "model": self.model,
            "input": inputs,
            "tools": self._tools(tools),
            "tool_choice": "auto",
            "max_output_tokens": 4096,
            "include": ["reasoning.encrypted_content"],
        }
        try:
            response = await self.client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._token}"},
                json=request,
                timeout=45.0,
                follow_redirects=False,
            )
        except httpx.TimeoutException:
            raise AgentError(
                "model_timeout", "The model request timed out; try a smaller question."
            ) from None
        except httpx.RequestError:
            raise AgentError(
                "model_unavailable",
                "The Databricks model gateway could not be reached.",
            ) from None
        if response.status_code == 401:
            raise AgentError(
                "model_authentication_failed",
                "Databricks rejected the user sign-in. Reopen the app and consent "
                "to its ai-gateway scope.",
            )
        if response.status_code == 403:
            raise AgentError(
                "model_permission_denied",
                "Databricks denied model access. Check the app's ai-gateway user "
                "scope and your permission to use the configured model.",
            )
        if response.status_code == 429:
            raise AgentError(
                "model_rate_limited", "The model request limit was reached; try later."
            )
        if response.status_code != 200:
            raise AgentError(
                "model_http_error",
                f"The Databricks model gateway returned HTTP {response.status_code}; "
                "check model availability and configuration.",
            )
        try:
            payload = response.json()
        except ValueError:
            raise _invalid_response() from None
        message, output = self._message(payload)
        safe_message = redact(message, (self._token,))
        self._input = deepcopy(inputs) + deepcopy(output)
        self._previous_messages = deepcopy(messages)
        self._assistant = deepcopy(safe_message)
        self._pending_calls = {call["id"] for call in safe_message["tool_calls"]}
        self._finished = not self._pending_calls
        return safe_message
