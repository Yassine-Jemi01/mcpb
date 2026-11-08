# MCPB Examples

This directory contains example MCP Bundles that demonstrate the MCPB format and manifest structure. These are **reference implementations** designed to illustrate how to build MCPB extensions.

## ⚠️ Not Production Ready

**Important:** These examples are **NOT intended for production use**. They serve as:

- Demonstrations of the MCPB manifest format
- Templates for building your own extensions
- Simple MCP server implementations for testing

But, the MCP servers themselves are not robust secure production ready servers and should not be relied upon for production use.

## Examples Included

| Example               | Type    | Demonstrates                                |
| --------------------- | ------- | ------------------------------------------- |
| `hello-world-node`    | Node.js | Basic MCP server with simple time tool      |
| `chrome-applescript`  | Node.js | Browser automation via AppleScript          |
| `file-manager-python` | Python  | File system operations and path handling    |
| `calculator-rust`     | Binary  | Compiled Rust binary as MCP Bundle          |
| `linux-inspector-ylang` | Binary  | Native YLang 2.3 Linux diagnostics server   |

## Usage

Each example includes its own `manifest.json` and can be packed with:

```bash
mcpb pack examples/hello-world-node
```

Use these as starting points for your own extensions, but ensure you implement proper security measures before deploying to users.

### Linux Inspector (YLang)

`linux-inspector-ylang` is a read-only Linux diagnostics server implemented in YLang 2.3.0. It adds YLang 2.3.0 as a second compiled-language example alongside Rust, using MCPB's existing `binary` server type. It exposes 12 tools backed by `/etc` and `/proc` data and includes protocol smoke tests.

Build and test it from the repository root:

```sh
cd examples/linux-inspector-ylang
bash build.sh
python3 tests/protocol_smoke.py server/linux-inspector-ylang
mcpb pack .
```

See [`linux-inspector-ylang/README.md`](linux-inspector-ylang/README.md) for the supported MCP protocol versions, requirements, and limitations.
