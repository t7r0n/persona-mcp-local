# Security Review

## Scope

Local CLI, synthetic inquiry fixtures, credential issuer, presentation verifier, revocation registry, DuckDB event store, JSONL event stream, and generated static dashboard.

## Current Assessment

The application is offline and fixture-backed. It has no network clients, no external identity-provider calls, no subprocess execution, no shell execution, no credential handling, and no global configuration writes.

## Controls

- Inquiry and request data is parsed into Pydantic models.
- Credentials are HMAC-signed with a deterministic dev key stored in code for synthetic verification only, not a production secret.
- Verification enforces expiry, scope, audience, signature, and revocation.
- Dashboard rendering uses Jinja autoescaping.
- Runtime state, generated outputs, caches, and virtual environments are ignored by git.

## Focused Scan

Reviewed package code for command execution, network clients, unsafe deserialization, credential handling, and global configuration writes. The implementation contains no subprocess calls, shell execution, sockets, HTTP clients, pickle, dynamic evaluation, external identity-provider calls, or package-manager/config writes.

## Attack-Path Analysis

The realistic attacker-controlled surface is local inquiry fixture content or stdio JSON. Those values can affect structured MCP-style responses, the local event stream, and dashboard text. They are parsed into Pydantic models, rendered through Jinja autoescaping, and do not reach a shell, network client, credential store, or privileged write path. The deterministic dev signing key is explicitly synthetic and not a production credential. Runtime outputs are excluded from the public repo.

## Review Status

Passed focused local security review on 2026-05-17. No high-impact attacker-reachable path identified.
