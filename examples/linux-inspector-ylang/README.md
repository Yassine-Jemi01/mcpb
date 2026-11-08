# Linux Inspector MCP Server (YLang)

A read-only Linux diagnostics server implemented in YLang 2.3.0. It is packaged as an MCPB binary extension and communicates over the MCP stdio transport.

## What it exposes

The server provides 12 read-only tools:

| Tool | Data source |
|---|---|
| `system_info` | `/etc/os-release` |
| `hostname_info` | `/etc/hostname` |
| `kernel_info` | `/proc/version` |
| `cpu_info` | `/proc/cpuinfo` |
| `memory_info` | `/proc/meminfo` |
| `uptime_info` | `/proc/uptime` |
| `load_average` | `/proc/loadavg` |
| `loaded_modules` | `/proc/modules` |
| `mounts_info` | `/proc/self/mounts` |
| `network_info` | `/proc/net/dev` |
| `disk_stats` | `/proc/diskstats` |
| `memory_pressure` | `/proc/pressure/memory` |

All tools are read-only. The server does not execute shell commands, invoke external programs, load/unload modules, or change system settings. It reads procfs through YLang's streaming Binary I/O API because procfs entries are not ordinary seekable files.

## Requirements

- Linux. The initial bundle targets the Linux platform and the architecture used to build the executable.
- YLang compiler 2.3.0 or newer.
- GCC or Clang for compiling the generated C program.
- Python 3.10+ to run the protocol smoke tests.
- MCPB CLI to package the extension.

The server implementation is in `server.yl`. Python is used only as a black-box test driver; it is not part of the server runtime.

## Build and test

From this directory:

```sh
bash build.sh
python3 tests/protocol_smoke.py server/linux-inspector-ylang
```

The smoke tests cover both protocol eras:

- Legacy MCP initialization at `2025-11-25`, `2025-06-18`, `2025-03-26`, and `2024-11-05`, plus tools/list, tools/call, legacy ping, and unknown-tool errors.
- Modern MCP discovery at `2026-07-28`, modern-only version advertisement, cache metadata, read-only annotations, tools/call, and rejection of the removed ping method.
- Unsupported protocol versions and malformed JSON-RPC input.

## Package as an MCP Bundle

After a successful build, run:

```sh
mcpb pack .
```

The manifest declares `server.type` as `binary` and points to the compiled executable through the bundle-relative directory variable. The binary is not checked into the repository; build it for the target Linux architecture before packing.

## Protocol compatibility

The server implements the modern MCP `2026-07-28` discovery flow and supports the handshake-based legacy revisions `2025-11-25`, `2025-06-18`, `2025-03-26`, and `2024-11-05`.

Modern requests carry the protocol version in `params._meta`. Modern responses include `resultType`; cacheable tool listings also include `ttlMs` and `cacheScope`. Legacy clients use initialize followed by the normal tools/list and tools/call methods.

## Text handling

Linux procfs output is normally ASCII. The server preserves printable ASCII, tabs, and line endings. Non-ASCII bytes are replaced with `?` so the JSON-RPC output remains valid UTF-8. Data is returned as text content rather than as a typed metrics schema.

## Limitations

- Linux only. Do not advertise this binary for macOS or Windows.
- The data is a direct snapshot of procfs/sysfs-style text, not a normalized monitoring database.
- `memory_pressure` may return an error on kernels that do not expose `/proc/pressure/memory`.
- The server currently exposes no write or administrative operations.

## License

Apache-2.0, matching the license used for new contributions in MCPB.