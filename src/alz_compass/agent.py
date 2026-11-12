"""Bounded single-agent workflow using discovered MCP tools and Databricks models.

No model credentials are passed to the local MCP subprocess. The server remains
responsible for validation and source retrieval; this module never calls its
Python functions directly.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx

from alz_compass.disease import APP_NAME, PROMPT_VERSION, SEARCH_CONDITION

ALLOWED_TOOLS = frozenset({"find_completed_trials", "get_trial_evidence_card"})
PROMPT_PATH = Path(__file__).with_name("agent_prompt.txt")
SECRET_KEYS = re.compile(
    r"authorization|api[_-]?key|access[_-]?token|password|secret|^token$", re.I
)


class AgentError(Exception):
    """A controlled error whose message is safe to put in a public run trace."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def redact(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    """Redact credential fields and configured credentials from saved artifacts."""
    if isinstance(value, dict):
        return {
            str(k): "[REDACTED]" if SECRET_KEYS.search(str(k)) else redact(v, secrets)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        return re.sub(r"(?i)Bearer\s+[^\s\"'<>]+", "Bearer [REDACTED]", value)
    return value


@dataclass(frozen=True)
class ModelConfig:
    host: str
    token: str = field(repr=False)
    model: str

    @classmethod
    def from_env(cls) -> ModelConfig:
        values = [
            os.environ.get(name, "").strip()
            for name in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "ALZ_COMPASS_MODEL")
        ]
        if not all(values):
            raise AgentError(
                "configuration_missing",
                "Set DATABRICKS_HOST, DATABRICKS_TOKEN, and ALZ_COMPASS_MODEL "
                "before running the agent. No model run was performed.",
            )
        return cls(*values)

    def workspace_origin(self) -> str:
        """Normalize a bare workspace hostname before attaching user credentials."""
        invalid = AgentError(
            "configuration_invalid",
            "DATABRICKS_HOST must be a Databricks workspace hostname or HTTPS "
            "origin, without a path, query, or credentials.",
        )
        if not isinstance(self.host, str):
            raise invalid
        host = self.host.strip()
        if re.fullmatch(r"[A-Za-z0-9.-]+", host):
            host = "https://" + host
        if any(char.isspace() or ord(char) < 32 for char in host):
            raise invalid
        try:
            parsed = urlparse(host)
        except ValueError:
            raise invalid from None
        hostname = parsed.hostname or ""
        domains = (
            ".cloud.databricks.com",
            ".azuredatabricks.net",
            ".gcp.databricks.com",
        )
        if (
            parsed.scheme != "https"
            or not hostname.endswith(domains)
            or not all(
                re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
                for label in hostname.split(".")
            )
            or parsed.netloc.lower() not in (hostname, hostname + ":443")
            or "?" in host
            or "#" in host
            or parsed.path not in ("", "/")
        ):
            raise invalid
        return "https://" + hostname

    def endpoint(self) -> str:
        return self.workspace_origin() + "/serving-endpoints/chat/completions"


class ChatModel(Protocol):
    model: str

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict: ...


class DatabricksChatModel:
    def __init__(self, config: ModelConfig, client: httpx.AsyncClient) -> None:
        self.config = config
        self.model = config.model
        self.client = client
        self.endpoint = config.endpoint()

    async def complete(self, messages: list[dict], tools: list[dict]) -> dict:
        try:
            response = await self.client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self.config.token}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "max_tokens": 4096,
                },
                timeout=45.0,
                follow_redirects=False,
            )
        except httpx.TimeoutException as exc:
            raise AgentError(
                "model_timeout",
                "The model request timed out; no final answer was accepted.",
            ) from exc
        except httpx.RequestError as exc:
            raise AgentError(
                "model_unavailable", "The model endpoint could not be reached."
            ) from exc
        if response.status_code != 200:
            raise AgentError(
                "model_http_error",
                f"The model endpoint returned HTTP {response.status_code}; "
                "check model access and tool-calling support.",
            )
        try:
            payload = response.json()
            choice = payload["choices"][0]
            message = choice["message"]
            if choice.get("finish_reason") == "length":
                raise AgentError(
                    "model_truncated",
                    "The model response was truncated and was not accepted "
                    "as a complete answer.",
                )
            if not isinstance(message, dict):
                raise TypeError
            return message
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AgentError(
                "model_response_invalid",
                "The model returned an invalid chat-completions response.",
            ) from exc


def _get(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        result = (
            value.get(name) if isinstance(value, dict) else getattr(value, name, None)
        )
        if result is not None:
            return result
    return default


def _structured_result(result: Any) -> dict:
    structured = _get(result, "structured_content", "structuredContent", "data")
    is_error = bool(_get(result, "is_error", "isError", default=False))
    if hasattr(structured, "model_dump"):
        structured = structured.model_dump(mode="json")
    if structured is not None:
        return {"is_error": is_error, "data": structured}
    texts = [
        _get(item, "text")
        for item in _get(result, "content", default=[])
        if _get(item, "type") == "text"
    ]
    for value in texts:
        try:
            return {"is_error": is_error, "data": json.loads(value)}
        except (ValueError, TypeError):
            pass
    return {"is_error": is_error, "text": texts}


class ToolCallingAgent:
    """Model-independent runner; inject model and MCP client for mechanical tests."""

    def __init__(
        self,
        model: ChatModel,
        mcp_client: Any,
        *,
        max_tool_calls: int = 8,
        max_model_calls: int = 10,
        timeout_seconds: float = 180,
        secrets: tuple[str, ...] = (),
    ) -> None:
        self.model = model
        self.mcp = mcp_client
        self.max_tool_calls = max_tool_calls
        self.max_model_calls = max_model_calls
        self.timeout_seconds = timeout_seconds
        self.secrets = secrets

    async def run(self, question: str) -> dict:
        prompt = PROMPT_PATH.read_text(encoding="utf-8")
        trace = {
            "application": APP_NAME,
            "condition": SEARCH_CONDITION,
            "schema_version": "1.0",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "model": self.model.model,
            "prompt_version": PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "status": "running",
            "manual_review": "pending",
            "tool_calls": [],
            "model_calls": [],
            "final_output": None,
            "limits": {
                "tool_calls": self.max_tool_calls,
                "model_calls": self.max_model_calls,
                "timeout_seconds": self.timeout_seconds,
            },
        }
        started = time.monotonic()
        try:
            if not question.strip() or len(question) > 16000:
                raise AgentError(
                    "invalid_question",
                    "Provide a nonempty research question of at most 16000 characters.",
                )
            await asyncio.wait_for(
                self._loop(question, prompt, trace), timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            trace.update(
                status="failed",
                error={
                    "code": "run_timeout",
                    "message": (
                        "The overall run time limit was reached; "
                        "no final answer was accepted."
                    ),
                },
            )
        except AgentError as exc:
            trace.update(status="failed", error={"code": exc.code, "message": str(exc)})
        except Exception:
            # MCP/HTTP exception strings can embed headers, URLs, or raw payloads.
            trace.update(
                status="failed",
                error={
                    "code": "connection_or_protocol_error",
                    "message": (
                        "The MCP connection or model protocol failed; "
                        "inspect access and service availability."
                    ),
                },
            )
        trace["duration_seconds"] = round(time.monotonic() - started, 3)
        return redact(trace, self.secrets)

    async def _loop(self, question: str, prompt: str, trace: dict) -> None:
        discovered = await self.mcp.list_tools()
        tool_definitions = []
        names = set()
        for tool in discovered:
            name = _get(tool, "name")
            if name not in ALLOWED_TOOLS:
                continue
            schema = _get(tool, "inputSchema", "input_schema")
            if not isinstance(schema, dict):
                raise AgentError(
                    "tool_schema_invalid",
                    "An allowed MCP tool did not provide a valid input schema.",
                )
            names.add(name)
            tool_definitions.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": _get(tool, "description", default=""),
                        "parameters": schema,
                    },
                }
            )
        if names != ALLOWED_TOOLS:
            raise AgentError(
                "tools_unavailable",
                f"The MCP server must expose both {APP_NAME} tools.",
            )
        trace["discovered_tools"] = sorted(names)
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ]
        seen_call_ids = set()
        for _ in range(self.max_model_calls):
            model_started = time.monotonic()
            message = await self.model.complete(messages, tool_definitions)
            trace["model_calls"].append(
                {
                    "duration_seconds": round(time.monotonic() - model_started, 3),
                    "message": message,
                }
            )
            if not isinstance(message, dict):
                raise AgentError(
                    "model_response_invalid", "The model returned an invalid message."
                )
            calls = message.get("tool_calls") or []
            if not isinstance(calls, list):
                raise AgentError(
                    "model_response_invalid",
                    "The model returned an invalid tool-call list.",
                )
            if not calls:
                output = message.get("content")
                if not isinstance(output, str) or not output.strip():
                    raise AgentError(
                        "empty_answer", "The model did not return an answer."
                    )
                trace.update(status="completed", final_output=output)
                return
            if len(trace["tool_calls"]) + len(calls) > self.max_tool_calls:
                raise AgentError(
                    "tool_budget_exceeded",
                    "The tool-call budget was reached; the request was not completed.",
                )
            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content"),
                    "tool_calls": calls,
                }
            )
            for call in calls:
                if not isinstance(call, dict) or call.get("type") != "function":
                    raise AgentError(
                        "model_response_invalid",
                        "The model returned an invalid function call.",
                    )
                fn = call.get("function")
                if not isinstance(fn, dict):
                    raise AgentError(
                        "model_response_invalid",
                        "The model returned an invalid function descriptor.",
                    )
                name, call_id = fn.get("name"), call.get("id")
                if name not in ALLOWED_TOOLS:
                    raise AgentError(
                        "tool_not_allowed",
                        "The model requested a tool outside the two-tool allowlist.",
                    )
                if (
                    not isinstance(call_id, str)
                    or not call_id
                    or call_id in seen_call_ids
                ):
                    raise AgentError(
                        "model_response_invalid",
                        "Tool calls require unique nonempty identifiers.",
                    )
                seen_call_ids.add(call_id)
                try:
                    arguments = json.loads(fn["arguments"])
                    if not isinstance(arguments, dict):
                        raise ValueError
                except (ValueError, KeyError, TypeError) as exc:
                    raise AgentError(
                        "invalid_tool_arguments",
                        "The model's tool arguments were not a JSON object.",
                    ) from exc
                event = {
                    "id": call_id,
                    "name": name,
                    "arguments": arguments,
                    "status": "started",
                }
                trace["tool_calls"].append(event)
                tool_started = time.monotonic()
                try:
                    result = await self.mcp.call_tool(
                        name, arguments, raise_on_error=False
                    )
                    normalized = _structured_result(result)
                    event.update(
                        status="error" if normalized["is_error"] else "returned",
                        result=normalized,
                    )
                    if isinstance(normalized.get("data"), dict):
                        event["domain_status"] = normalized["data"].get("status")
                except Exception:
                    normalized = {
                        "is_error": True,
                        "error": {
                            "code": "mcp_tool_failure",
                            "message": "MCP call failed; no result was retrieved.",
                        },
                    }
                    event.update(status="error", result=normalized)
                finally:
                    event["duration_seconds"] = round(
                        time.monotonic() - tool_started, 3
                    )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(normalized, ensure_ascii=False),
                    }
                )
        raise AgentError(
            "model_budget_exceeded",
            "The model-call budget was reached; the request was not completed.",
        )


def make_mcp_client(url: str | None = None, *, injected_failure: bool = False):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport, StreamableHttpTransport

    if url:
        if injected_failure:
            raise AgentError(
                "requires_fixture",
                "The failure scenario needs the local snapshot-only fault fixture; "
                "no remote service was changed.",
            )
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise AgentError(
                "configuration_invalid",
                "Remote MCP requires an HTTPS URL without embedded credentials "
                "or query parameters.",
            )
        token = os.environ.get("ALZ_COMPASS_MCP_TOKEN", "").strip()
        if not token:
            raise AgentError(
                "configuration_missing",
                "Set ALZ_COMPASS_MCP_TOKEN for the authenticated remote MCP endpoint.",
            )
        return Client(
            StreamableHttpTransport(
                url=url, headers={"Authorization": f"Bearer {token}"}
            ),
            timeout=135,
        )
    # Only task-specific source configuration reaches this subprocess.
    env = {
        name: os.environ[name]
        for name in ("ALZ_COMPASS_DATA_MODE", "ALZ_COMPASS_MANIFEST", "PYTHONPATH")
        if name in os.environ
    }
    env["MCP_TRANSPORT"] = "stdio"
    if injected_failure:
        env.update(
            ALZ_COMPASS_DATA_MODE="snapshot", ALZ_COMPASS_TEST_FAULT="upstream_error"
        )
    return Client(
        StdioTransport(
            command=sys.executable,
            args=["-m", "alz_compass.app"],
            env=env,
            keep_alive=False,
        ),
        timeout=135,
    )


def save_trace(path: Path, trace: dict, secrets: tuple[str, ...] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(redact(trace, secrets), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def export_mlflow(trace: dict) -> str:
    """Optional export of an already-saved trace; failures never erase local data."""
    if os.environ.get("ALZ_COMPASS_MLFLOW", "").lower() not in ("1", "true"):
        return "disabled"
    try:
        import mlflow

        with mlflow.start_span(name="alz_compass_run", span_type="AGENT") as span:
            span.set_inputs({"question": trace["question"]})
            span.set_attributes(
                {
                    "model": trace.get("model", "unconfigured"),
                    "prompt_version": PROMPT_VERSION,
                    "original_duration_seconds": trace.get("duration_seconds", 0),
                    "run_status": trace["status"],
                    "exported_after_run": True,
                }
            )
            span.set_outputs(trace)
        return "exported"
    except Exception:
        return "failed_local_trace_preserved"


async def _run_cli(args: argparse.Namespace) -> dict:
    config = ModelConfig.from_env()
    secrets = (config.token, os.environ.get("ALZ_COMPASS_MCP_TOKEN", ""))
    async with httpx.AsyncClient() as http_client:
        model = DatabricksChatModel(config, http_client)
        async with make_mcp_client(
            args.mcp_url, injected_failure=getattr(args, "injected_failure", False)
        ) as client:
            return await ToolCallingAgent(model, client, secrets=secrets).run(
                args.question
            )


async def run_scenarios(args: argparse.Namespace) -> dict:
    """Run fixed prompts; retain human quality scores as pending, never inferred."""
    config = ModelConfig.from_env()
    if not args.bindings:
        raise AgentError(
            "bindings_missing",
            "Scenario runs require --bindings pointing to reviewed "
            "development-record bindings as JSON.",
        )
    try:
        bindings = json.loads(args.bindings.read_text(encoding="utf-8"))
        suite_path = (
            Path(__file__).parents[2]
            / "eval"
            / "type2diabetes"
            / "agent_scenarios.json"
        )
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AgentError(
            "scenario_configuration_invalid",
            "The scenario suite or binding JSON could not be read.",
        ) from exc
    if not isinstance(bindings, dict) or not all(
        isinstance(bindings.get(key), str) and bindings[key].strip()
        for key in suite["bindings_required"]
    ):
        raise AgentError(
            "bindings_missing",
            "Provide every binding listed in eval/type2diabetes/agent_scenarios.json "
            "as a nonempty string; use reviewed development records.",
        )
    if args.repeats < 1 or args.repeats > 10:
        raise AgentError(
            "invalid_repeats",
            "Scenario repeats must be between 1 and 10; "
            "the acceptance plan calls for 2.",
        )
    secrets = (config.token, os.environ.get("ALZ_COMPASS_MCP_TOKEN", ""))
    trace_dir = args.output.parent / (args.output.stem + "-traces")
    summary = {
        "schema_version": "1.0",
        "status": "running",
        "question": "Fixed agent evaluation scenarios",
        "condition": SEARCH_CONDITION,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "model": config.model,
        "prompt_version": PROMPT_VERSION,
        "suite_sha256": hashlib.sha256(suite_path.read_bytes()).hexdigest(),
        "bindings": bindings,
        "repeats": args.repeats,
        "scenario_count": len(suite["scenarios"]),
        "manual_review": "pending",
        "quality_pass_count": None,
        "critical_failure_count": None,
        "quality_status": "pending independent review by Mohammad and Chinelo",
        "disclosure": (
            "completed means the model returned an answer, not that it passed "
            "clinical or factual review. Fault-injection cases are explicitly labeled."
        ),
        "runs": [],
    }
    started = time.monotonic()
    save_trace(trace_dir / "bindings.json", bindings, secrets)
    save_trace(args.output, summary, secrets)
    for repeat in range(1, args.repeats + 1):
        for scenario in suite["scenarios"]:
            scenario_id = scenario["id"]
            question = scenario["prompt"].format_map(bindings)
            injected_failure = scenario_id == "boundary_10"
            case_args = argparse.Namespace(
                question=question,
                mcp_url=args.mcp_url,
                injected_failure=injected_failure,
            )
            try:
                trace = await _run_cli(case_args)
            except AgentError as exc:
                trace = {
                    "status": "not_run_requires_fixture"
                    if exc.code == "requires_fixture"
                    else "not_run",
                    "question": question,
                    "model": config.model,
                    "manual_review": "pending",
                    "prompt_version": PROMPT_VERSION,
                    "final_output": None,
                    "error": {"code": exc.code, "message": str(exc)},
                }
            except Exception:
                trace = {
                    "status": "not_run",
                    "question": question,
                    "model": config.model,
                    "manual_review": "pending",
                    "prompt_version": PROMPT_VERSION,
                    "final_output": None,
                    "error": {
                        "code": "connection_error",
                        "message": (
                            "Scenario MCP initialization failed; "
                            "no quality score assigned."
                        ),
                    },
                }
            trace.update(
                scenario_id=scenario_id,
                repeat=repeat,
                expected_behavior=scenario["expected_behavior"],
                expected_tools=scenario["expected_tools"],
                critical=scenario["critical"],
                evaluation_setup="snapshot-only upstream-error injection"
                if injected_failure
                else "configured MCP data source",
                passed=None,
                reviewer=None,
            )
            if injected_failure:
                observed = any(
                    event.get("result", {}).get("data", {}).get("status")
                    == "upstream_error"
                    for event in trace.get("tool_calls", [])
                    if isinstance(event.get("result", {}).get("data"), dict)
                )
                trace["fault_observed_in_tool_trace"] = observed
                if trace["status"] == "completed" and not observed:
                    trace["original_execution_status"] = trace["status"]
                    trace["status"] = "invalid_fault_setup"
            trace_path = trace_dir / f"run-{repeat:02d}-{scenario_id}.json"
            save_trace(trace_path, trace, secrets)
            trace["mlflow_export"] = export_mlflow(redact(trace, secrets))
            save_trace(trace_path, trace, secrets)
            summary["runs"].append(
                {
                    "repeat": repeat,
                    "scenario_id": scenario_id,
                    "status": trace["status"],
                    "trace_path": str(trace_path.resolve()),
                    "passed": None,
                    "duration_seconds": trace.get("duration_seconds"),
                    "manual_review": "pending",
                }
            )
            save_trace(args.output, summary, secrets)
    durations = [
        item["duration_seconds"]
        for item in summary["runs"]
        if item["duration_seconds"] is not None
    ]
    summary.update(
        status="completed_pending_review"
        if all(r["status"] == "completed" for r in summary["runs"])
        else "incomplete_pending_review",
        executions_with_answer=sum(r["status"] == "completed" for r in summary["runs"]),
        executions_failed_or_not_run=sum(
            r["status"] != "completed" for r in summary["runs"]
        ),
        duration_seconds=round(time.monotonic() - started, 3),
        median_case_seconds=round(statistics.median(durations), 3)
        if durations
        else None,
        slowest_case_seconds=max(durations) if durations else None,
    )
    save_trace(args.output, summary, secrets)
    return redact(summary, secrets)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?")
    parser.add_argument("--run", choices=("question", "scenarios"), default="question")
    parser.add_argument(
        "--bindings", type=Path, help="JSON values for all scenario prompt placeholders"
    )
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mcp-url", default=os.environ.get("ALZ_COMPASS_MCP_URL"))
    args = parser.parse_args(argv)
    args.output = args.output or Path(
        "eval/type2diabetes/runs/scenarios-latest.json"
        if args.run == "scenarios"
        else "eval/type2diabetes/runs/agent-latest.json"
    )
    if args.run == "scenarios":
        args.question = "Fixed agent evaluation scenarios"
    try:
        if args.run == "question" and not args.question:
            raise AgentError(
                "invalid_question",
                "Provide a question, or use --run scenarios --bindings FILE.",
            )
        trace = asyncio.run(
            run_scenarios(args) if args.run == "scenarios" else _run_cli(args)
        )
    except AgentError as exc:
        trace = {
            "status": "not_run",
            "question": args.question,
            "prompt_version": PROMPT_VERSION,
            "manual_review": "pending",
            "error": {"code": exc.code, "message": str(exc)},
            "final_output": None,
        }
    except Exception:
        trace = {
            "status": "not_run",
            "question": args.question,
            "prompt_version": PROMPT_VERSION,
            "manual_review": "pending",
            "error": {
                "code": "connection_error",
                "message": (
                    "MCP initialization failed; check local dependencies "
                    "or remote endpoint access."
                ),
            },
            "final_output": None,
        }
    secrets = tuple(
        os.environ.get(name, "")
        for name in ("DATABRICKS_TOKEN", "ALZ_COMPASS_MCP_TOKEN")
    )
    trace = redact(trace, secrets)
    save_trace(args.output, trace, secrets)
    trace["mlflow_export"] = export_mlflow(trace)
    save_trace(args.output, trace, secrets)
    print(
        trace.get("final_output")
        or trace.get("error", {}).get("message")
        or f"Scenario execution status: {trace['status']}; "
        "quality review remains pending."
    )
    print(f"\nRun trace: {args.output.resolve()}")
    return 0 if trace["status"] in ("completed", "completed_pending_review") else 1


if __name__ == "__main__":
    raise SystemExit(main())
