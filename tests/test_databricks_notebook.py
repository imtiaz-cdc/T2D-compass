"""Offline connector mechanics only; these are not real model-run evidence."""

import ast
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastmcp import Client
from mcp.types import CallToolResult, TextContent, Tool

from alz_compass.app import create_server
from alz_compass.config import Settings

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "deploy/databricks/ALZ_Compass_Connect.py").read_text("utf-8")
HELPERS = SOURCE.split("# BEGIN TESTED HELPERS\n")[1].split("# END TESTED HELPERS")[0]
NCT = "NCT02000583"


@pytest.fixture
def nb():
    namespace = {}
    exec(compile(HELPERS, "ALZ_Compass_Connect_helpers", "exec"), namespace)
    namespace.update(ThreadPoolExecutor=ThreadPoolExecutor, timedelta=timedelta)
    oauth_helpers = SOURCE.split("# BEGIN OAUTH HELPERS\n")[1].split(
        "# END OAUTH HELPERS"
    )[0]
    exec(compile(oauth_helpers, "ALZ_Compass_OAuth_helpers", "exec"), namespace)
    return SimpleNamespace(**namespace)


@pytest.fixture
def specs(nb):
    return nb.function_tools(
        [
            Tool(
                name="find_completed_trials",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                },
            ),
            Tool(
                name="get_trial_evidence_card",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "nct_id": {"type": "string", "pattern": "^NCT[0-9]{8}$"},
                    },
                    "required": ["nct_id"],
                },
            ),
        ]
    )


def synthetic_payload(mode="live", status="ok"):
    # Invented schema fixture for testing the verification gate, never saved as
    # a real retrieval or model evaluation. It contains no study findings.
    return {
        "status": status,
        "source_mode": mode,
        "card": {
            "source_mode": mode,
            "identity": {"nct_id": NCT},
            "provenance": {
                "source_url": f"https://clinicaltrials.gov/study/{NCT}",
                "retrieved_at": "2026-10-20T00:00:00+00:00",
            },
        },
    }


def call(name="get_trial_evidence_card", arguments=None, call_id="call_1"):
    return {
        "type": "function_call",
        "name": name,
        "call_id": call_id,
        "arguments": json.dumps({"nct_id": NCT} if arguments is None else arguments),
    }


def response(*items, status="completed"):
    return {"status": status, "id": "offline-test-response", "output": list(items)}


ANSWER = {
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "output_text",
            "text": "Synthetic test answer, not clinical evidence.",
        },
    ],
}


class FakeModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def __call__(self, **request):
        self.requests.append(copy.deepcopy(request))
        return next(self.responses)


class FakeMCP:
    def __init__(self, payload=None):
        self.payload = synthetic_payload() if payload is None else payload
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return CallToolResult(content=[], structuredContent=self.payload)


def run(nb, specs, model, mcp=None):
    return nb.run_lookup(
        model,
        mcp or FakeMCP(),
        specs,
        "TEST PROMPT",
        "TEST MODEL",
        "TEST QUESTION",
        NCT,
    )


def test_notebook_import_and_prompt_fidelity():
    assert SOURCE.startswith("# Databricks notebook source\n")
    tree = ast.parse(SOURCE)
    prompt = next(
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(t, ast.Name) and t.id == "SYSTEM_PROMPT" for t in node.targets
        )
    )
    # This notebook is the retained ALZ external-client example. It must not be
    # silently rewritten or presented as the current research browser workflow.
    assert prompt == (ROOT / "deploy/databricks/history/alz-compass-1.0.txt").read_text(
        "utf-8"
    )
    for cell in SOURCE.split("# COMMAND ----------"):
        compile(cell, "notebook_cell", "exec")


@pytest.mark.asyncio
async def test_actual_mcp_discovery_schemas_remain_optional(nb):
    async with Client(
        create_server(settings=Settings(alz_compass_data_mode="snapshot"))
    ) as c:
        discovered = await c.list_tools()
    converted = nb.function_tools(discovered)
    assert {t["name"] for t in converted} == set(nb.ALLOWED_TOOLS)
    for original, converted_tool in zip(discovered, converted, strict=True):
        assert converted_tool["parameters"] == nb.as_dict(original)["inputSchema"]
        assert converted_tool["strict"] is False
    search = next(t for t in converted if t["name"] == "find_completed_trials")
    nb.validate({}, search["parameters"])
    with pytest.raises(Exception):
        nb.validate({"limit": None}, search["parameters"])


def test_discovery_filters_extra_tools_and_requires_both(nb):
    tools = [Tool(name=name, inputSchema={}) for name in nb.ALLOWED_TOOLS]
    tools.append(Tool(name="unapproved", inputSchema={}))
    assert [s["name"] for s in nb.function_tools(tools)] == list(nb.ALLOWED_TOOLS)
    with pytest.raises(nb.CheckFailure):
        nb.function_tools(tools[1:])


def test_text_and_structured_mcp_results(nb):
    payload = synthetic_payload()
    result = CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload))]
    )
    assert nb.unpack_result(result) == payload
    assert nb.unpack_result(FakeMCP().call_tool("test", {})) == payload
    with pytest.raises(nb.CheckFailure):
        nb.unpack_result(CallToolResult(content=[], isError=True))


def test_round_trip_preserves_reasoning_and_records_actual_calls(nb, specs):
    reasoning = {"type": "reasoning", "id": "r1", "encrypted_content": "TEST ONLY"}
    model = FakeModel(response(reasoning, call()), response(ANSWER))
    mcp = FakeMCP()
    trace = run(nb, specs, model, mcp)
    assert trace["status"] == "completed" and trace["integration_verified"]
    assert trace["answer_review"] == "pending human review"
    assert mcp.calls == [("get_trial_evidence_card", {"nct_id": NCT})]
    history = model.requests[1]["input"]
    assert history[1] == reasoning
    assert history[2] == call()
    assert history[3]["type"] == "function_call_output"
    assert history[3]["call_id"] == "call_1"
    assert json.loads(history[3]["output"]) == synthetic_payload()
    assert trace["tool_calls"][0]["result"] == synthetic_payload()
    assert "encrypted_content" not in json.dumps(trace)


@pytest.mark.parametrize(
    "mode,status", [("snapshot", "ok"), ("live", "upstream_error")]
)
def test_snapshot_or_application_error_is_not_verified(nb, specs, mode, status):
    model = FakeModel(response(call()), response(ANSWER))
    trace = run(nb, specs, model, FakeMCP(synthetic_payload(mode, status)))
    assert trace["status"] == "unverified"
    assert not trace["integration_verified"]


def test_model_only_and_incomplete_answers_are_not_verified(nb, specs):
    model_only = run(nb, specs, FakeModel(response(ANSWER)))
    assert model_only["status"] == "unverified" and model_only["tool_calls"] == []
    mcp = FakeMCP()
    incomplete = run(nb, specs, FakeModel(response(call(), status="incomplete")), mcp)
    assert incomplete["status"] == "failed" and mcp.calls == []


@pytest.mark.parametrize(
    "bad_call",
    [
        call(name="unapproved"),
        call(arguments=[]),
        call(arguments={"nct_id": "bad"}),
        call(name="find_completed_trials", arguments={"limit": 6}),
        {**call(), "arguments": "not-json"},
    ],
)
def test_invalid_calls_never_reach_mcp(nb, specs, bad_call):
    mcp = FakeMCP()
    trace = run(nb, specs, FakeModel(response(bad_call)), mcp)
    assert trace["status"] == "failed" and mcp.calls == []


def test_call_limit_and_repeated_identifier(nb, specs):
    mcp = FakeMCP()
    calls = [call(call_id=f"call_{i}") for i in range(9)]
    trace = run(nb, specs, FakeModel(response(*calls)), mcp)
    assert trace["status"] == "failed" and len(mcp.calls) == 8
    mcp2 = FakeMCP()
    duplicate = run(nb, specs, FakeModel(response(call(), call())), mcp2)
    assert duplicate["status"] == "failed" and len(mcp2.calls) == 1


def test_sdk_exception_does_not_expose_request_credentials(nb, specs):
    class Unauthorized(Exception):
        status_code = 401

    def failed_request(**kwargs):
        raise Unauthorized("Authorization: Bearer SECRET-TEST-CREDENTIAL")

    trace = run(nb, specs, failed_request)
    assert trace["status"] == "failed"
    assert trace["error"] == {"type": "Unauthorized", "http_status": 401}
    assert "SECRET-TEST-CREDENTIAL" not in json.dumps(trace)


def test_safe_gateway_diagnostics(nb):
    class Unsupported(Exception):
        status_code = 400
        body = {
            "error": {
                "code": "unsupported_parameter",
                "param": "include",
                "message": "Authorization: Bearer SECRET-TEST-CREDENTIAL",
            }
        }

    diagnostic = nb.error_info(Unsupported())
    assert diagnostic["code"] == "unsupported_parameter"
    assert diagnostic["parameter"] == "include"
    assert "SECRET-TEST-CREDENTIAL" not in json.dumps(diagnostic)


@pytest.mark.parametrize(
    "message,expected",
    [
        (
            "OAuth authentication is required for MCP servers "
            "hosted on Databricks Apps.",
            "APP_OAUTH_REQUIRED",
        ),
        (
            "default auth: cannot configure default credentials",
            "WORKSPACE_AUTH_UNAVAILABLE",
        ),
        ("MCP Server not found at the provided server url", "MCP_ENDPOINT_NOT_FOUND"),
        (
            "asyncio.run() cannot be called from a running event loop",
            "NOTEBOOK_EVENT_LOOP",
        ),
    ],
)
def test_known_sdk_failure_is_classified_without_exposing_message(
    nb, message, expected
):
    result = nb.error_info(ValueError(message + " token=SECRET-TEST-CREDENTIAL"))
    assert result["diagnostic"] == expected
    assert "SECRET-TEST-CREDENTIAL" not in json.dumps(result)


class FakeOAuthToken:
    def __init__(self, **values):
        self.__dict__.update(values)

    @property
    def valid(self):
        return self.expiry > datetime.now(timezone.utc) + timedelta(seconds=40)


def oauth_source(nb, *, auth_type="runtime", status=200, body=None):
    calls = []
    workspace = SimpleNamespace(
        config=SimpleNamespace(
            auth_type=auth_type,
            host="https://assigned.cloud.databricks.com/",
            authenticate=lambda: {"Authorization": "Bearer NOTEBOOK-TEST-TOKEN"},
        )
    )
    body = (
        body
        if body is not None
        else {
            "access_token": "APP-TEST-TOKEN",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=status, json=lambda: body)

    return nb.AppOAuthTokens(
        workspace, "TEST-APP-AUDIENCE", post, FakeOAuthToken
    ), calls


def test_notebook_exchange_binds_audience_and_refreshes_expired_token(nb):
    source, calls = oauth_source(nb)
    source.refresh_if_needed()
    url, request = calls[0]
    assert url == "https://assigned.cloud.databricks.com/oidc/v1/token"
    assert request["allow_redirects"] is False and request["timeout"] == 30
    assert request["data"]["audience"] == "TEST-APP-AUDIENCE"
    assert request["data"]["subject_token"] == "NOTEBOOK-TEST-TOKEN"
    assert source.headers() == {"Authorization": "Bearer APP-TEST-TOKEN"}
    source.refresh_if_needed()
    assert len(calls) == 1
    source._token.expiry = datetime.now(timezone.utc) - timedelta(seconds=1)
    source.refresh_if_needed()
    assert len(calls) == 2


@pytest.mark.parametrize("auth_type", ["pat", "oauth-m2m", "unknown"])
def test_non_runtime_token_is_never_exchanged_as_notebook_pat(nb, auth_type):
    source, calls = oauth_source(nb, auth_type=auth_type)
    with pytest.raises(nb.CheckFailure):
        source.refresh_if_needed()
    assert calls == []


@pytest.mark.parametrize(
    "status,body",
    [
        (401, {"error": "SECRET-TOKEN-IN-ERROR"}),
        (302, {}),
        (
            200,
            {
                "access_token": "SECRET-TOKEN-IN-ERROR",
                "token_type": "Basic",
                "expires_in": 3600,
            },
        ),
        (
            200,
            {
                "access_token": "SECRET-TOKEN-IN-ERROR",
                "token_type": "Bearer",
                "expires_in": 0,
            },
        ),
        (200, {}),
    ],
)
def test_bad_exchange_cannot_produce_oauth_credentials(nb, status, body):
    source, _ = oauth_source(nb, status=status, body=body)
    with pytest.raises(nb.CheckFailure) as exc:
        source.refresh_if_needed()
    assert "SECRET-TOKEN" not in str(exc.value)
    with pytest.raises(nb.CheckFailure):
        source.headers()


@pytest.mark.asyncio
async def test_mcp_sdk_sync_calls_work_with_running_notebook_loop(nb):
    import asyncio
    import threading

    main_thread = threading.get_ident()
    prepared_on = []

    class ClientWithOwnLoop:
        def list_tools(self):
            async def fetch():
                assert threading.get_ident() != main_thread
                return ["tool"]

            return asyncio.run(fetch())

    client = nb.NotebookMCPClient(
        ClientWithOwnLoop(),
        lambda: prepared_on.append(threading.get_ident()),
    )
    assert client.list_tools() == ["tool"]
    assert prepared_on == [main_thread]
