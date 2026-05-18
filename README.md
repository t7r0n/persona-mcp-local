# Local Agent Identity Delegation

A local MCP-style reference implementation for delegating a verified human identity to an AI agent with scoped, expiring, revocable credentials.

The project simulates a verified identity provider locally. It never calls external APIs and does not require secrets. It is intended to demonstrate the protocol shape: register an agent, issue a signed presentation, verify it at a downstream service, revoke it, and reject failed liveness/deepfake checks with structured JSON an agent can read.

## Intent

Local MCP-style agent identity delegation reference.

## What the code proves

- Builds a compact fixture set around local mcp-style agent identity delegation reference.
- Separates signal, failure, and reporting code so `Local Agent Identity Delegation` can be audited without a live integration.
- Writes `persona-mcp-local` structured outputs before rendering the dashboard, which keeps the UI honest.
- Uses the `persona-mcp-local` lockfile and local commands as the reproducibility contract.

## Local run

```bash
uv sync
uv run persona-mcp-local init-demo
uv run persona-mcp-local run-suite --iterations 100
uv run persona-mcp-local verify
uv run persona-mcp-local dashboard
```

```bash
uv run persona-mcp-local register --inquiry inq_verified_001 --scope payments:read --ttl-minutes 30
uv run persona-mcp-local run-suite
```

## Produced files

- `runs/latest/identity.duckdb` with registration, presentation, verification, and revocation rows
- `outputs/summary.json` with latency, throughput, rejection, revocation, and scope-escalation gates
- `outputs/event_stream.jsonl` with structured MCP-style results
- `outputs/dashboard.html` with delegation and verification analytics
- `outputs/demo_pack/` with portable evidence

## Gatekeeping

```bash
uv run ruff check .
uv run pytest -q
uv run persona-mcp-local verify
```

## Operational boundary

The `persona-mcp-local` public surface is source, tests, lockfile, and docs. It does not need credentials, browser state, customer records, or hosted services.
