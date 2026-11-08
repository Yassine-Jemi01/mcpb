#!/usr/bin/env python3
"""Black-box JSON-RPC tests for the compiled YLang MCP server."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_server(binary: Path, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wire = "".join(
        json.dumps(message, separators=(",", ":")) + "\n"
        for message in messages
    )
    completed = subprocess.run(
        [str(binary)],
        input=wire,
        text=True,
        capture_output=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"server exited with {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )

    output_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    try:
        return [json.loads(line) for line in output_lines]
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"server wrote non-JSON data to stdout: {exc}\n{completed.stdout}"
        ) from exc


def result_text(response: dict[str, Any]) -> str:
    result = response.get("result", {})
    blocks = result.get("content", [])
    return "\n".join(
        block.get("text", "")
        for block in blocks
        if block.get("type") == "text"
    )


def legacy_protocol_test(binary: Path) -> None:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "linux-inspector-smoke-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "system_info", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "memory_info", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "unknown_tool", "arguments": {}},
        },
    ]

    requests.append({"jsonrpc": "2.0", "id": 6, "method": "ping"})
    responses = run_server(binary, requests)
    assert [item.get("id") for item in responses] == [1, 2, 3, 4, 5, 6], responses

    initialize = responses[0]["result"]
    assert initialize["protocolVersion"] == "2025-11-25", initialize
    assert "tools" in initialize["capabilities"], initialize

    tools = responses[1]["result"]["tools"]
    names = {tool["name"] for tool in tools}
    expected = {
        "system_info",
        "hostname_info",
        "kernel_info",
        "cpu_info",
        "memory_info",
        "uptime_info",
        "load_average",
        "loaded_modules",
        "mounts_info",
        "network_info",
        "disk_stats",
        "memory_pressure",
    }
    assert names == expected, names

    system_text = result_text(responses[2])
    assert "Source: /etc/os-release" in system_text, system_text
    assert "ID=" in system_text, system_text

    memory_text = result_text(responses[3])
    assert "Source: /proc/meminfo" in memory_text, memory_text
    assert "MemTotal:" in memory_text, memory_text

    assert responses[4].get("error", {}).get("code") == -32602, responses[4]
    assert responses[5].get("result") == {}, responses[5]


def oldest_legacy_protocol_test(binary: Path) -> None:
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "linux-inspector-smoke-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    responses = run_server(binary, requests)
    assert len(responses) == 2, responses
    assert responses[0]["result"]["protocolVersion"] == "2024-11-05", responses[0]
    tools = responses[1]["result"]["tools"]
    assert len(tools) == 12, tools
    assert all("annotations" not in tool for tool in tools), tools


def modern_protocol_test(binary: Path) -> None:
    metadata = {
        "io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientInfo": {
            "name": "linux-inspector-smoke-test",
            "version": "1.0",
        },
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    requests = [
        {
            "jsonrpc": "2.0",
            "id": "discover-1",
            "method": "server/discover",
            "params": {"_meta": metadata},
        },
        {
            "jsonrpc": "2.0",
            "id": "tools-1",
            "method": "tools/list",
            "params": {"_meta": metadata},
        },
        {
            "jsonrpc": "2.0",
            "id": "call-1",
            "method": "tools/call",
            "params": {
                "_meta": metadata,
                "name": "uptime_info",
                "arguments": {},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": "ping-1",
            "method": "ping",
            "params": {"_meta": metadata},
        },
    ]

    responses = run_server(binary, requests)
    assert [item.get("id") for item in responses] == [
        "discover-1",
        "tools-1",
        "call-1",
        "ping-1",
    ], responses

    discovery = responses[0]["result"]
    assert discovery["resultType"] == "complete", discovery
    assert discovery["supportedVersions"] == ["2026-07-28"], discovery
    assert discovery["capabilities"].get("tools") == {}, discovery

    listing = responses[1]["result"]
    assert listing["resultType"] == "complete", listing
    assert listing["cacheScope"] == "private", listing
    assert listing["ttlMs"] == 30000, listing
    assert len(listing["tools"]) == 12, listing
    assert all(tool.get("annotations", {}).get("readOnlyHint") is True for tool in listing["tools"]), listing

    call = responses[2]["result"]
    assert call["resultType"] == "complete", call
    assert call["isError"] is False, call
    assert "Source: /proc/uptime" in result_text(responses[2]), call
    assert responses[3].get("error", {}).get("code") == -32601, responses[3]


def intermediate_legacy_protocol_test(binary: Path) -> None:
    for version in ("2025-06-18", "2025-03-26"):
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": version,
                    "capabilities": {},
                    "clientInfo": {"name": "linux-inspector-smoke-test", "version": "1.0"},
                },
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        responses = run_server(binary, requests)
        assert len(responses) == 2, (version, responses)
        assert responses[0]["result"]["protocolVersion"] == version, (version, responses)
        assert len(responses[1]["result"]["tools"]) == 12, (version, responses)


def all_tools_test(binary: Path) -> None:
    sources = {
        "system_info": "/etc/os-release",
        "hostname_info": "/etc/hostname",
        "kernel_info": "/proc/version",
        "cpu_info": "/proc/cpuinfo",
        "memory_info": "/proc/meminfo",
        "uptime_info": "/proc/uptime",
        "load_average": "/proc/loadavg",
        "loaded_modules": "/proc/modules",
        "mounts_info": "/proc/self/mounts",
        "network_info": "/proc/net/dev",
        "disk_stats": "/proc/diskstats",
        "memory_pressure": "/proc/pressure/memory",
    }
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "linux-inspector-smoke-test", "version": "1.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]
    requests.extend(
        {
            "jsonrpc": "2.0",
            "id": index + 2,
            "method": "tools/call",
            "params": {"name": name, "arguments": {}},
        }
        for index, name in enumerate(sources)
    )

    responses = run_server(binary, requests)
    assert len(responses) == len(sources) + 1, responses
    by_id = {item["id"]: item for item in responses}
    for index, (name, source) in enumerate(sources.items(), start=2):
        response = by_id[index]
        text = result_text(response)
        result = response.get("result", {})
        assert text, (name, response)
        if name == "memory_pressure" and text.startswith("Unable to open "):
            assert result.get("isError") is True, response
            continue
        assert f"Source: {source}" in text, (name, text)
        assert result.get("isError") is False, response


def unsupported_version_test(binary: Path) -> None:
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2099-01-01",
                "io.modelcontextprotocol/clientInfo": {
                    "name": "linux-inspector-smoke-test",
                    "version": "1.0",
                },
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        },
    }
    responses = run_server(binary, [request])
    assert len(responses) == 1, responses
    error = responses[0].get("error", {})
    assert error.get("code") == -32022, responses[0]
    assert error.get("message") == "Unsupported protocol version", responses[0]
    assert error.get("data", {}).get("supported") == [
        "2026-07-28",
        "2025-11-25",
        "2025-06-18",
        "2025-03-26",
        "2024-11-05",
    ], responses[0]
    assert error.get("data", {}).get("requested") == "2099-01-01", responses[0]


def parse_error_test(binary: Path) -> None:
    completed = subprocess.run(
        [str(binary)],
        input="{not-json}\n",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    response = json.loads(completed.stdout.strip())
    assert response.get("id") is None, response
    assert response.get("error", {}).get("code") == -32700, response


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: protocol_smoke.py PATH_TO_SERVER", file=sys.stderr)
        return 64

    binary = Path(sys.argv[1]).resolve()
    if not binary.is_file():
        print(f"server binary not found: {binary}", file=sys.stderr)
        return 66

    legacy_protocol_test(binary)
    print("PASS: legacy MCP initialization, tools/list, tools/call, and unknown-tool error")
    oldest_legacy_protocol_test(binary)
    print("PASS: MCP 2024-11-05 legacy tool schema without annotations")
    intermediate_legacy_protocol_test(binary)
    print("PASS: MCP 2025-06-18 and 2025-03-26 legacy initialization")
    modern_protocol_test(binary)
    print("PASS: MCP 2026-07-28 discovery, cache metadata, and read-only annotations")
    all_tools_test(binary)
    print("PASS: all 12 read-only Linux diagnostic tools")
    unsupported_version_test(binary)
    print("PASS: unsupported MCP protocol versions are rejected")
    parse_error_test(binary)
    print("PASS: malformed JSON returns a JSON-RPC parse error")
    print("All Linux Inspector protocol smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
