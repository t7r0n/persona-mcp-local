# Local Agent Identity Delegation

A local MCP-style reference implementation for delegating a verified human identity to an AI agent with scoped, expiring, revocable credentials.

The project simulates a verified identity provider locally. It never calls external APIs and does not require secrets. It is intended to demonstrate the protocol shape: register an agent, issue a signed presentation, verify it at a downstream service, revoke it, and reject failed liveness/deepfake checks with structured JSON an agent can read.

## Quick Start

```bash
uv sync
uv run persona-mcp-local init-demo
uv run persona-mcp-local run-suite --iterations 100
uv run persona-mcp-local verify
uv run persona-mcp-local dashboard
```

Single-flow examples:

```bash
uv run persona-mcp-local register --inquiry inq_verified_001 --scope payments:read --ttl-minutes 30
uv run persona-mcp-local run-suite
```

## Outputs

- `runs/latest/identity.duckdb` with registration, presentation, verification, and revocation rows
- `outputs/summary.json` with latency, throughput, rejection, revocation, and scope-escalation gates
- `outputs/event_stream.jsonl` with structured MCP-style results
- `outputs/dashboard.html` with delegation and verification analytics
- `outputs/demo_pack/` with portable evidence
