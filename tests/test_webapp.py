"""Browser requests exercise real in-process MCP, with public frozen records."""

import json
from types import SimpleNamespace

import httpx
import pytest
from starlette.testclient import TestClient

from alz_compass.app import create_server
from alz_compass.config import Settings


@pytest.fixture
def browser():
    server = create_server(
        settings=Settings(
            alz_compass_data_mode="snapshot",
            databricks_host="https://test.cloud.databricks.com",
        )
    )
    with TestClient(server.http_app(path="/mcp", stateless_http=True)) as client:
        yield client


def test_browser_loads_and_discovers_real_tools_without_credentials(browser):
    assert browser.get("/").status_code == 200
    assert "T2D Compass" in browser.get("/").text
    assert browser.get("/static/app.js").status_code == 200
    assert browser.get("/static/styles.css").status_code == 200
    assert browser.get("/static/secrets.env").status_code == 404
    response = browser.get("/api/status")
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["tools"] == [
        "find_completed_trials",
        "get_trial_evidence_card",
    ]
    assert response.json()["data_mode"] == "snapshot"
    assert response.json()["condition"] == "Type 2 Diabetes"
    assert response.json()["application"] == "T2D Compass"
    assert not response.json()["assistant"]["available"]
    assert browser.get("/health").json()["status"] == "healthy"


def test_browser_search_and_card_keep_source_provenance(browser):
    search = browser.post("/api/search", json={"limit": 1}).json()
    assert search["status"] == "ok"
    assert search["criteria"]["condition"] == "Type 2 Diabetes"
    assert search["source_mode"] == "snapshot"
    nct_id = search["studies"][0]["nct_id"]
    result = browser.post("/api/card", json={"nct_id": nct_id}).json()
    assert result["status"] == "ok"
    assert result["card"]["identity"]["nct_id"] == nct_id
    assert result["card"]["provenance"]["snapshot_sha256"]
    assert "clinicaltrials.gov" in json.dumps(result["card"]["provenance"])


@pytest.mark.parametrize(
    "route,payload",
    [
        ("search", {"limit": True}),
        ("search", {"limit": 6}),
        ("card", {"nct_id": "https://example.com"}),
        ("card", {"nct_id": "NCT03244800", "token": "should-not-be-accepted"}),
        ("ask", {"question": " "}),
        ("ask", {"question": "x" * 4001}),
    ],
)
def test_browser_rejects_invalid_inputs_without_echoing_values(browser, route, payload):
    result = browser.post(f"/api/{route}", json=payload)
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "invalid_input"
    assert "should-not-be-accepted" not in result.text


def test_browser_rejects_cross_origin_and_oversized_requests(browser):
    result = browser.post(
        "/api/search", json={}, headers={"Origin": "https://other.example"}
    )
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "invalid_origin"
    result = browser.post(
        "/api/search", json={}, headers={"Sec-Fetch-Site": "cross-site"}
    )
    assert result.status_code == 400
    assert browser.post("/api/search", data="{}").status_code == 400
    assert (
        browser.post(
            "/api/search",
            content=b" " * 20001,
            headers={"Content-Type": "application/json"},
        ).status_code
        == 400
    )


def test_missing_ai_authorization_does_not_break_core_tools(browser):
    result = browser.post("/api/ask", json={"question": "Get an evidence card"})
    assert result.status_code == 503
    assert result.json()["error"]["code"] == "assistant_not_configured"
    assert browser.post("/api/search", json={"limit": 1}).json()["status"] == "ok"


def test_forwarded_token_is_request_scoped_and_never_exported(browser, monkeypatch):
    from alz_compass import webapp

    tokens = []

    class FakeModel:
        def __init__(self, host, token, model, client):
            tokens.append(token)
            self.model = model
            self.token = token
            self.first = True

        async def complete(self, messages, tools):
            if self.first:
                self.first = False
                return {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "type": "function",
                            "id": "card-1",
                            "function": {
                                "name": "get_trial_evidence_card",
                                "arguments": '{"nct_id":"NCT03244800"}',
                            },
                        }
                    ],
                }
            return {"role": "assistant", "content": "Review pending " + self.token}

    monkeypatch.setattr(webapp, "ResponsesModel", FakeModel)
    for token in ("user-one-test-secret", "user-two-test-secret"):
        headers = {"X-Forwarded-Access-Token": token, "Origin": "http://testserver"}
        status = browser.get("/api/status", headers=headers)
        assert status.json()["assistant"]["available"]
        assert token not in status.text
        response = browser.post(
            "/api/ask", json={"question": "Get NCT03244800"}, headers=headers
        )
        assert response.json()["status"] == "completed"
        assert response.json()["mcp_transport"] == "in_process"
        assert response.json()["tool_calls"][0]["result"]["data"]["status"] == "ok"
        assert token not in response.text
    assert tokens == ["user-one-test-secret", "user-two-test-secret"]
    assert not browser.get("/api/status").json()["assistant"]["available"]


@pytest.mark.parametrize(
    "host", ["test.cloud.databricks.com", "https://test.cloud.databricks.com"]
)
def test_browser_assistant_normalizes_workspace_host_and_retrieves_card(
    host, monkeypatch
):
    from alz_compass import webapp

    token = "synthetic-forwarded-user-token"
    requests = []

    def handler(request):
        assert str(request.url) == (
            "https://test.cloud.databricks.com/ai-gateway/openai/v1/responses"
        )
        assert request.headers["Authorization"] == "Bearer " + token
        payload = json.loads(request.content)
        assert token not in json.dumps(payload)
        requests.append(payload)
        if len(requests) == 1:
            output = [
                {
                    "type": "function_call",
                    "id": "fc_card_1",
                    "call_id": "card_1",
                    "name": "get_trial_evidence_card",
                    "arguments": '{"nct_id":"NCT03244800"}',
                    "status": "completed",
                }
            ]
        else:
            assert len(requests) == 2
            tool_output = next(
                item
                for item in payload["input"]
                if item.get("type") == "function_call_output"
            )
            card = json.loads(tool_output["output"])["data"]
            assert card["status"] == "ok"
            assert card["card"]["identity"]["nct_id"] == "NCT03244800"
            assert card["card"]["provenance"]["snapshot_sha256"]
            output = [
                {
                    "type": "message",
                    "id": "msg_1",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Retrieved NCT03244800; review remains pending.",
                            "annotations": [],
                        }
                    ],
                }
            ]
        return httpx.Response(200, json={"status": "completed", "output": output})

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        webapp,
        "httpx",
        SimpleNamespace(AsyncClient=lambda: httpx.AsyncClient(transport=transport)),
    )
    server = create_server(
        settings=Settings(alz_compass_data_mode="snapshot", databricks_host=host)
    )
    with TestClient(server.http_app(path="/mcp", stateless_http=True)) as client:
        response = client.post(
            "/api/ask",
            json={"question": "Retrieve NCT03244800 and explain its review flags."},
            headers={"X-Forwarded-Access-Token": token},
        )
    assert response.status_code == 200
    trace = response.json()
    assert trace["status"] == "completed"
    assert trace["mcp_transport"] == "in_process"
    assert len(requests) == 2
    assert len(trace["tool_calls"]) == 1
    result = trace["tool_calls"][0]["result"]["data"]
    assert result["card"]["identity"]["nct_id"] == "NCT03244800"
    assert result["card"]["provenance"]["snapshot_sha256"]
    assert token not in response.text


def test_browser_live_outage_stays_an_error():
    server = create_server(
        settings=Settings(
            alz_compass_data_mode="snapshot", alz_compass_test_fault="upstream_error"
        )
    )
    with TestClient(server.http_app(path="/mcp", stateless_http=True)) as client:
        result = client.post("/api/search", json={}).json()
        assert result["status"] == "upstream_error"
        assert result["search_incomplete"] is True
        assert not result["studies"]
