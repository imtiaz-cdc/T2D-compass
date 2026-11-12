"""Offline protocol and credential checks; no vendor model is invoked."""

import json
from copy import deepcopy
from types import SimpleNamespace

import httpx
import pytest

from alz_compass.agent import ALLOWED_TOOLS, AgentError, ToolCallingAgent
from alz_compass.gateway import DEFAULT_MODEL, ResponsesModel

HOST = "https://example.cloud.databricks.com"
TOKEN = "test-forwarded-user-token"
MESSAGES = [
    {"role": "system", "content": "Review sources."},
    {"role": "user", "content": "Find a trial."},
]
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_completed_trials",
            "description": "Find trials.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
        },
    }
]


def answer(text="Source-linked answer."):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "id": "msg_1",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
    }


def function_call(call_id="call_1", name="find_completed_trials"):
    return {
        "type": "function_call",
        "id": "fc_1",
        "call_id": call_id,
        "name": name,
        "arguments": '{"limit":1}',
        "status": "completed",
    }


@pytest.mark.asyncio
async def test_responses_shape_and_reasoning_preserved_across_tool_turns():
    requests = []
    reasoning = {
        "type": "reasoning",
        "id": "rs_1",
        "summary": [],
        "encrypted_content": "opaque-reasoning-state",
    }
    initial_output = [reasoning, function_call()]
    replies = iter([{"status": "completed", "output": initial_output}, answer()])

    def handler(request):
        assert request.url == HOST + "/ai-gateway/openai/v1/responses"
        assert request.headers["Authorization"] == "Bearer " + TOKEN
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=next(replies))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = ResponsesModel(HOST, TOKEN, client=client)
        messages = deepcopy(MESSAGES)
        first = await model.complete(messages, TOOLS)
        assert "opaque-reasoning-state" not in json.dumps(first)
        messages.extend(
            [
                first,
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "content": '{"status":"ok"}',
                },
            ]
        )
        final = await model.complete(messages, TOOLS)
    assert final["content"] == "Source-linked answer."
    assert requests[0]["model"] == DEFAULT_MODEL
    assert requests[0]["include"] == ["reasoning.encrypted_content"]
    assert requests[0]["tools"][0]["name"] == "find_completed_trials"
    assert requests[0]["tools"][0]["strict"] is False
    assert requests[0]["tools"][0]["parameters"] == TOOLS[0]["function"]["parameters"]
    assert requests[1]["input"][:2] == MESSAGES
    assert requests[1]["input"][2:4] == initial_output
    assert requests[1]["input"][4] == {
        "type": "function_call_output",
        "call_id": "call_1",
        "output": '{"status":"ok"}',
    }
    for request in requests:
        assert not {"store", "background", "previous_response_id"} & request.keys()
        assert TOKEN not in json.dumps(request)


@pytest.mark.asyncio
async def test_adapter_runs_existing_agent_and_multiple_tool_calls():
    requests = []
    replies = iter(
        [
            {"status": "completed", "output": [function_call("a"), function_call("b")]},
            answer(),
        ]
    )

    class FakeMCP:
        async def list_tools(self):
            return [
                SimpleNamespace(
                    name=name, description=name, inputSchema={"type": "object"}
                )
                for name in ALLOWED_TOOLS
            ]

        async def call_tool(self, name, arguments, raise_on_error=False):
            return SimpleNamespace(is_error=False, structured_content={"status": "ok"})

    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=next(replies))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        trace = await ToolCallingAgent(
            ResponsesModel(HOST, TOKEN, DEFAULT_MODEL, client),
            FakeMCP(),
            secrets=(TOKEN,),
        ).run("Find a trial")
    assert trace["status"] == "completed"
    assert len(trace["tool_calls"]) == 2
    outputs = [
        item
        for item in requests[1]["input"]
        if item.get("type") == "function_call_output"
    ]
    assert [item["call_id"] for item in outputs] == ["a", "b"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,code",
    [
        (401, "model_authentication_failed"),
        (403, "model_permission_denied"),
        (429, "model_rate_limited"),
        (400, "model_http_error"),
        (503, "model_http_error"),
        (302, "model_http_error"),
    ],
)
async def test_errors_never_expose_response_body_or_credentials(status, code):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            text="Private detail " + TOKEN,
            headers={"Location": "https://untrusted.example/"},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = ResponsesModel(HOST, TOKEN, client=client)
        with pytest.raises(AgentError) as error:
            await model.complete(MESSAGES, TOOLS)
    assert error.value.code == code
    assert TOKEN not in str(error.value) and "Private detail" not in str(error.value)
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload,code",
    [
        ({"status": "incomplete", "output": []}, "model_truncated"),
        ({"status": "failed", "error": {"message": TOKEN}}, "model_response_invalid"),
        ({"status": "completed", "output": "bad"}, "model_response_invalid"),
        (
            {"status": "completed", "output": [{"type": "web_search_call"}]},
            "model_response_invalid",
        ),
        (
            {"status": "completed", "output": [function_call(name="unsafe_tool")]},
            "tool_not_allowed",
        ),
        (
            {"status": "completed", "output": [function_call(), function_call()]},
            "model_response_invalid",
        ),
        (
            {"status": "completed", "output": [{"type": "reasoning", "summary": []}]},
            "empty_answer",
        ),
        ([], "model_response_invalid"),
    ],
)
async def test_unusable_model_output_stops_safely(payload, code):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    ) as client:
        with pytest.raises(AgentError) as error:
            await ResponsesModel(HOST, TOKEN, client=client).complete(MESSAGES, TOOLS)
    assert error.value.code == code
    assert TOKEN not in str(error.value)


@pytest.mark.asyncio
async def test_raw_gateway_json_error_is_safe():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text=TOKEN))
    ) as client:
        with pytest.raises(AgentError, match="invalid response"):
            await ResponsesModel(HOST, TOKEN, client=client).complete(MESSAGES, TOOLS)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure,code",
    [
        (httpx.ConnectError, "model_unavailable"),
        (httpx.ReadTimeout, "model_timeout"),
    ],
)
async def test_network_errors_are_safe(failure, code):
    def handler(request):
        raise failure("Private transport detail " + TOKEN, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(AgentError) as error:
            await ResponsesModel(HOST, TOKEN, client=client).complete(MESSAGES, TOOLS)
    assert error.value.code == code
    assert TOKEN not in str(error.value)
    assert error.value.__cause__ is None


@pytest.mark.parametrize(
    "host",
    [
        "https://untrusted.example",
        "http://example.cloud.databricks.com",
        "https://example.cloud.databricks.com/path",
        "https://user@example.cloud.databricks.com",
        "https://example.cloud.databricks.com/?token=private",
        "https://example.cloud.databricks.com:evil",
        "https://example.cloud.databricks.com:444",
    ],
)
def test_workspace_origin_validation(host):
    with pytest.raises(AgentError) as error:
        ResponsesModel(host, TOKEN)
    assert error.value.code == "configuration_invalid"


@pytest.mark.parametrize("token", ["", " ", "bad\ntoken", "bad\rtoken"])
def test_missing_or_invalid_forwarded_token_has_no_fallback(token, monkeypatch):
    monkeypatch.setenv("DATABRICKS_TOKEN", "must-not-be-used")
    with pytest.raises(AgentError) as error:
        ResponsesModel(HOST, token)
    assert error.value.code.startswith("model_authentication_")


@pytest.mark.asyncio
async def test_model_output_credential_echo_redacted():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=answer(TOKEN + " Bearer other-token")
            )
        )
    ) as client:
        result = await ResponsesModel(HOST, TOKEN, client=client).complete(
            MESSAGES, TOOLS
        )
    assert TOKEN not in json.dumps(result)
    assert "other-token" not in json.dumps(result)


@pytest.mark.asyncio
async def test_instance_rejects_unrelated_history_and_missing_tool_output():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            200, json={"status": "completed", "output": [function_call()]}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = ResponsesModel(HOST, TOKEN, client=client)
        first = await model.complete(MESSAGES, TOOLS)
        for history in [
            [{"role": "user", "content": "Another user's request"}],
            MESSAGES + [first],
        ]:
            with pytest.raises(AgentError) as error:
                await model.complete(history, TOOLS)
            assert error.value.code == "model_conversation_invalid"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_separate_users_do_not_share_credentials_or_conversations():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json=answer())

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        for token, question in [
            ("first-user", "First question"),
            ("second-user", "Second question"),
        ]:
            await ResponsesModel(HOST, token, client=client).complete(
                [{"role": "user", "content": question}], TOOLS
            )
    assert requests[0].headers["Authorization"] == "Bearer first-user"
    assert requests[1].headers["Authorization"] == "Bearer second-user"
    assert "First question" not in requests[1].content.decode()
