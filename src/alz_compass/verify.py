"""Record an actual MCP tool replay without claiming a model or clinical review."""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

from fastmcp import Client

from alz_compass.app import create_server
from alz_compass.config import Settings
from alz_compass.registry import utc_now


async def replay(live=False):
    settings = Settings(alz_compass_data_mode="live" if live else "snapshot")
    report = {
        "started_at": utc_now(),
        "verification_type": "actual_mcp_tool_replay",
        "source_mode": settings.alz_compass_data_mode,
        "model_used": False,
        "clinical_review": "pending Mohammad",
        "reference_review": "pending independent annotation",
        "heldout_evaluation": "not_run",
        "calls": [],
    }
    async with Client(create_server(settings=settings)) as client:
        names = [tool.name for tool in await client.list_tools()]
        report["discovered_tools"] = names
        if set(names) != {"find_completed_trials", "get_trial_evidence_card"}:
            raise RuntimeError("Unexpected MCP tool list")

        async def call(name, args):
            start = time.monotonic()
            response = await client.call_tool(name, args)
            result = response.structured_content
            if result is None:
                result = json.loads(response.content[0].text)
            report["calls"].append(
                {
                    "tool": name,
                    "arguments": args,
                    "duration_seconds": round(time.monotonic() - start, 3),
                    "result": result,
                }
            )
            return result

        search = await call("find_completed_trials", {"limit": 3})
        if search["status"] not in {"ok", "no_matches"}:
            report["status"] = "failed"
        else:
            for study in search["studies"]:
                await call("get_trial_evidence_card", {"nct_id": study["nct_id"]})
            report["status"] = (
                "passed"
                if all(item["result"]["status"] == "ok" for item in report["calls"])
                and search["returned_count"] > 0
                else "incomplete"
            )
    durations = [item["duration_seconds"] for item in report["calls"]]
    report["median_tool_seconds"] = statistics.median(durations)
    report["slowest_tool_seconds"] = max(durations)
    report["disclosure"] = (
        "Actual tool calls through MCP, not an LLM evaluation or physician-reviewed "
        "accuracy benchmark. Snapshot mode searches only the six development records."
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/type2diabetes/results/tool-replay.json"),
    )
    args = parser.parse_args()
    report = asyncio.run(replay(args.live))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in report.items() if k != "calls"}, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
