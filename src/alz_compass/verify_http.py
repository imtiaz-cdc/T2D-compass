"""Check the packaged entry point over loopback HTTP using public snapshots."""

import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

import httpx
from fastmcp import Client

from alz_compass.registry import utc_now


async def verify():
    root = Path(__file__).resolve().parents[2]
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = {
        name: value
        for name, value in os.environ.items()
        if name.upper()
        in {"PATH", "SYSTEMROOT", "WINDIR", "USERPROFILE", "TEMP", "TMP"}
    }
    env.update(
        MCP_TRANSPORT="streamable-http",
        MCP_HOST="127.0.0.1",
        MCP_PORT=str(port),
        ALZ_COMPASS_DATA_MODE="snapshot",
        ALZ_COMPASS_TEST_FAULT="",
    )
    url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [sys.executable, str(root / "main.py")],
        cwd=root,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    try:
        async with httpx.AsyncClient(timeout=1, trust_env=False) as http:
            health = None
            for _ in range(150):
                if process.poll() is not None:
                    raise RuntimeError("Local HTTP server exited before readiness")
                try:
                    response = await http.get(url + "/health")
                    if response.status_code == 200:
                        health = response.json()
                        break
                except httpx.RequestError:
                    pass
                await asyncio.sleep(0.1)
            if health is None or health.get("data_mode") != "snapshot":
                raise RuntimeError(
                    "Local HTTP server did not become ready in snapshot mode"
                )
        async with Client(url + "/mcp") as client:
            names = [tool.name for tool in await client.list_tools()]
            assert set(names) == {"find_completed_trials", "get_trial_evidence_card"}
            search = (
                await client.call_tool("find_completed_trials", {"limit": 1})
            ).structured_content
            assert search["status"] == "ok" and search["source_mode"] == "snapshot"
            nct_id = search["studies"][0]["nct_id"]
            card = (
                await client.call_tool("get_trial_evidence_card", {"nct_id": nct_id})
            ).structured_content
            assert (
                card["status"] == "ok" and card["card"]["identity"]["nct_id"] == nct_id
            )
        return {
            "created_at": utc_now(),
            "status": "passed",
            "source_mode": "snapshot",
            "transport": "streamable-http",
            "entry_point": "python main.py",
            "health": health,
            "tools": names,
            "retrieved_nct_id": nct_id,
            "disclosure": (
                "Actual local loopback HTTP MCP check. No Databricks deployment, "
                "platform authentication, model run, or clinical validation is claimed."
            ),
        }
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/type2diabetes/results/http-transport.json"),
    )
    args = parser.parse_args()
    report = asyncio.run(verify())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
