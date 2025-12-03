# OpenTargets MCP

[![Release](https://img.shields.io/github/v/release/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/releases)
[![Build status](https://img.shields.io/github/actions/workflow/status/opentargets/otar-mcp/main.yml?branch=main)](https://github.com/opentargets/otar-mcp/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/opentargets/otar-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/opentargets/otar-mcp)
[![Commit activity](https://img.shields.io/github/commit-activity/m/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/commits)
[![License](https://img.shields.io/github/license/opentargets/otar-mcp)](https://github.com/opentargets/otar-mcp/blob/main/LICENSE)

> **⚠️ DISCLAIMER: This project is currently experimental and under active development. Features, APIs, and documentation may change without notice ⚠️**

**Model Context Protocol (MCP) server for the [OpenTargets Platform API](https://platform.opentargets.org/)**

This package provides an MCP server that enables AI assistants like Claude to interact with the OpenTargets Platform, a comprehensive resource for target-disease associations and drug discovery data.

## Quick Navigation

- [Features](#features)
- [Available Tools](#available-tools)
- [Strategy](#strategy)
- [Installation](#installation)
- [Usage](#usage)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔍 **GraphQL Schema Access**: Fetch and explore the complete OpenTargets GraphQL schema with detailed documentation
- 📊 **Query Execution**: Execute custom GraphQL queries against the OpenTargets API
- ⚡ **Batch Query Processing**: Execute the same query multiple times with different parameters efficiently
- 🔎 **Entity Search**: Search for entities across multiple types (targets, diseases, drugs, variants, studies)
- 🚀 **Multiple Transports**: Support for both stdio (Claude Desktop) and HTTP transports
- 🛠️ **CLI Tools**: Easy-to-use command-line interface for server management
- 🎯 **JQ Filtering**: Server-side JSON filtering to reduce token consumption and improve performance

## Available Tools

The MCP server provides the following tools:

1. **get_open_targets_graphql_schema**: Fetch the complete GraphQL schema for the OpenTargets Platform API, including detailed documentation for all types and fields
2. **query_open_targets_graphql**: Execute GraphQL queries to retrieve data about targets, diseases, drugs, and their associations
3. **batch_query_open_targets_graphql**: Execute the same GraphQL query multiple times with different variable sets for efficient batch processing
4. **search_open_targets**: Search for entities across multiple types (targets, diseases, drugs, variants, studies) and retrieve their standardized IDs

## Strategy

The MCP server implements a 3-step workflow that guides the LLM to efficiently retrieve data from the OpenTargets Platform:

### Step 1: Learn Query Structure from Schema

The LLM calls `get_open_targets_graphql_schema` to understand the GraphQL API structure. The schema includes detailed documentation for all types and fields, enabling the LLM to construct valid queries. Key entity types include:

- **Targets/Genes**: Use ENSEMBL IDs (e.g., `ENSG00000139618` for BRCA2)
- **Diseases**: Use EFO/MONDO IDs (e.g., `MONDO_0007254` for breast cancer)
- **Drugs**: Use ChEMBL IDs (e.g., `CHEMBL1201583` for aspirin)
- **Variants**: Use "chr_pos_ref_alt" format or rsIDs

### Step 2: Resolve Identifiers (if needed)

When a user query contains common names (gene symbols, disease names, drug names), the LLM uses `search_open_targets` to convert them to standardized IDs required by the API.

### Step 3: Execute Query

The LLM constructs and executes GraphQL queries using:
- Standardized IDs from Step 2
- Query structure from the schema
- **jq filters** to extract only requested fields, minimizing token consumption

Tool selection:
- `query_open_targets_graphql` for single queries
- `batch_query_open_targets_graphql` for multiple identical queries with different parameters (reduces latency and tokens)

The jq filter is applied server-side before returning the response, ensuring only relevant data is transmitted.

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/opentargets/otar-mcp.git
cd otar-mcp
uv sync
```

### Using pip

```bash
pip install git+https://github.com/opentargets/otar-mcp.git
```

## Usage

### Claude Desktop Integration (Stdio Transport)

Add this configuration to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "otar-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "<your-path>/otar-mcp",
        "fastmcp",
        "run",
        "src/otar_mcp/server.py"
      ],
      "transport": "stdio",
    }
  }
}
```

### Command Line Usage

#### Start HTTP server (for testing/development)

```bash
# Using uv
uv run otar-mcp serve-http

# Using installed package
otar-mcp serve-http --host 127.0.0.1 --port 8000
```

#### Start stdio server

```bash
# Using uv
uv run otar-mcp serve-stdio

# Using installed package
otar-mcp serve-stdio
```

#### List available tools

```bash
uv run otar-mcp list-tools
```

#### Run as a Python module

```bash
python -m otar_mcp serve-http
```

### Environment Variables

Configure the server using environment variables:

- `OPENTARGETS_API_ENDPOINT`: OpenTargets API endpoint (default: https://api.platform.opentargets.org/api/v4/graphql)
- `MCP_SERVER_NAME`: Server name (default: "Open Targets MCP")
- `MCP_HTTP_HOST`: HTTP server host (default: "127.0.0.1")
- `MCP_HTTP_PORT`: HTTP server port (default: "8000")
- `OPENTARGETS_TIMEOUT`: Request timeout in seconds (default: "30")

## Development

### Setup development environment

```bash
make install
```

This will install the package with development dependencies and set up pre-commit hooks.

### Run tests

```bash
uv run pytest
```

### Run linting

```bash
uv run pre-commit run -a
```

### Project Structure

```
otar-mcp/
├── src/otar_mcp/
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point for python -m otar_mcp
│   ├── cli.py               # Command-line interface
│   ├── config.py            # Configuration management
│   ├── server.py            # MCP server setup
│   ├── mcp_instance.py      # MCP instance management
│   ├── client/              # GraphQL client utilities
│   │   ├── __init__.py
│   │   └── graphql.py
│   ├── tools/               # MCP tools
│   │   ├── __init__.py
│   │   ├── schema.py        # Schema fetching tool
│   │   ├── query.py         # Query execution tool
│   │   ├── batch_query.py   # Batch query tool
│   │   └── search.py        # Search tool
│   └── utils/               # Utility functions
│       └── __init__.py
├── tests/                   # Test suite
│   ├── conftest.py
│   ├── test_client/
│   └── test_tools/
└── utils_scripts/           # Utility scripts for maintenance
    └── annotate_schema_metadata.py
```


## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the terms of the license specified in [LICENSE](LICENSE).

## Acknowledgements

We would like to thank the developers from [@biocontext-ai](https://github.com/biocontext-ai) whose implementation of a GraphQL-based MCP server served as an inspiration for this project.

---

Repository initiated with [fpgmaas/cookiecutter-uv](https://github.com/fpgmaas/cookiecutter-uv).
