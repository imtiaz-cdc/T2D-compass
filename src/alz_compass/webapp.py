"""Browser routes use the same MCP contracts without a second network login.

Databricks authenticates incoming app traffic. Only its request-scoped forwarded
user token is used for optional model calls; no token is sent to the browser,
stored, shared between requests, or used to grant new permissions.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastmcp import Client
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.responses import FileResponse, JSONResponse

from alz_compass import __version__
from alz_compass.agent import ALLOWED_TOOLS, AgentError, ToolCallingAgent
from alz_compass.disease import APP_NAME, SEARCH_CONDITION
from alz_compass.gateway import ResponsesModel

WEB_ROOT = Path(__file__).with_name("web")
MAX_BODY_BYTES = 20_000
RESPONSE_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; connect-src 'self'; script-src 'self'; "
        "style-src 'self'; object-src 'none'; base-uri 'none'; "
        "frame-ancestors 'self'; form-action 'self'"
    ),
}


class SearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    intervention: str | None = Field(default=None, max_length=120)
    limit: int = Field(default=3, ge=1, le=5)


class CardInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    nct_id: str = Field(pattern=r"^NCT[0-9]{8}$")


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    question: str = Field(min_length=1, max_length=4000)


def reply(payload, status_code=200):
    return JSONResponse(payload, status_code=status_code, headers=RESPONSE_HEADERS)


def error(code, message, status_code=400):
    return reply(
        {"status": "error", "error": {"code": code, "message": message}},
        status_code,
    )


async def read_input(request, schema):
    """Reject cross-site browser requests and bound all incoming user input."""
    origin = request.headers.get("origin")
    expected_host = request.headers.get(
        "x-forwarded-host", request.headers.get("host", "")
    )
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise AgentError("invalid_origin", "Open this action from the app page.")
    if origin:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in ("http", "https")
            or parsed.netloc.lower() != expected_host.lower()
            or parsed.username
            or parsed.password
        ):
            raise AgentError("invalid_origin", "Open this action from the app page.")
    if request.headers.get("content-type", "").split(";")[0] != "application/json":
        raise AgentError("invalid_input", "This action requires JSON input.")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > MAX_BODY_BYTES:
            raise AgentError("invalid_input", "The request is too large.")
    try:
        return schema.model_validate(json.loads(body))
    except (ValueError, TypeError, ValidationError) as exc:
        raise AgentError(
            "invalid_input",
            "Check the input: use NCT plus eight digits, a limit of 1–5, "
            "or a question of 1–4000 characters, as appropriate.",
        ) from exc


def register_web_routes(server, config):
    @server.custom_route("/", methods=["GET"])
    async def index(request):
        return FileResponse(WEB_ROOT / "index.html", headers=RESPONSE_HEADERS)

    @server.custom_route("/static/{asset}", methods=["GET"])
    async def static_asset(request):
        asset = request.path_params["asset"]
        if asset not in {"app.js", "styles.css"}:
            return error("not_found", "This file is not available.", 404)
        media_type = "text/javascript" if asset.endswith(".js") else "text/css"
        return FileResponse(
            WEB_ROOT / asset, media_type=media_type, headers=RESPONSE_HEADERS
        )

    @server.custom_route("/api/status", methods=["GET"])
    async def status(request):
        try:
            async with Client(server) as client:
                names = sorted(tool.name for tool in await client.list_tools())
            token = request.headers.get("x-forwarded-access-token", "")
            available = bool(
                token and config.databricks_host and config.alz_compass_model
            )
            return reply(
                {
                    "version": __version__,
                    "application": APP_NAME,
                    "condition": SEARCH_CONDITION,
                    "data_mode": config.alz_compass_data_mode,
                    "tools": names,
                    "assistant": {
                        "available": available,
                        "model": config.alz_compass_model,
                        "message": (
                            "Ready to try with your model permissions. "
                            "Each question makes model requests."
                            if available
                            else "Search and evidence cards are ready. To use the AI "
                            "assistant, the app owner must enable user authorization "
                            "for AI Gateway and you must consent when opening the app."
                        ),
                    },
                }
            )
        except Exception:
            return error("tools_unavailable", "The trial tools could not start.", 503)

    async def invoke(request, schema, tool_name):
        try:
            args = await read_input(request, schema)
            async with Client(server) as client:
                result = await client.call_tool(
                    tool_name, args.model_dump(), raise_on_error=False
                )
            if result.is_error or not isinstance(result.structured_content, dict):
                return error("tool_error", "The trial tool could not complete.", 502)
            return reply(result.structured_content)
        except AgentError as exc:
            return error(exc.code, str(exc))
        except Exception:
            return error(
                "tool_unavailable", "The trial tool could not be reached.", 502
            )

    @server.custom_route("/api/search", methods=["POST"])
    async def search(request):
        return await invoke(request, SearchInput, "find_completed_trials")

    @server.custom_route("/api/card", methods=["POST"])
    async def card(request):
        return await invoke(request, CardInput, "get_trial_evidence_card")

    @server.custom_route("/api/ask", methods=["POST"])
    async def ask(request):
        try:
            args = await read_input(request, QuestionInput)
            if not args.question.strip():
                raise AgentError("invalid_input", "Enter a research question.")
            token = request.headers.get("x-forwarded-access-token", "")
            if not token or not config.databricks_host or not config.alz_compass_model:
                return error(
                    "assistant_not_configured",
                    "Enable the app's ai-gateway user authorization scope, then "
                    "reopen the app and consent. Search and evidence cards remain "
                    "available. Model access is checked when you ask a question.",
                    503,
                )
            async with httpx.AsyncClient() as http, Client(server) as client:
                model = ResponsesModel(
                    config.databricks_host, token, config.alz_compass_model, http
                )
                trace = await ToolCallingAgent(
                    model,
                    client,
                    secrets=(token,),
                    max_model_calls=6,
                    max_tool_calls=8,
                    timeout_seconds=150,
                ).run(args.question)
            trace["mcp_transport"] = "in_process"
            trace["data_mode"] = config.alz_compass_data_mode
            trace["allowed_tools"] = sorted(ALLOWED_TOOLS)
            return reply(trace)
        except AgentError as exc:
            return error(exc.code, str(exc))
        except Exception:
            return error(
                "assistant_unavailable", "The assistant could not complete.", 502
            )
