from __future__ import annotations

import json
import sys

import typer
from rich.console import Console

from persona_mcp_local.dashboard import benchmark_summary, build_dashboard
from persona_mcp_local.issuer import register_agent
from persona_mcp_local.runner import export_demo_pack, init_demo, run_suite, verify_outputs

app = typer.Typer(help="Local MCP-style agent identity delegation.")
console = Console()


@app.command("init-demo")
def init_demo_command(force: bool = typer.Option(False, "--force")) -> None:
    console.print_json(data=init_demo(force=force))


@app.command("register")
def register_command(
    inquiry: str = typer.Option(..., "--inquiry"),
    scope: list[str] = typer.Option(..., "--scope"),
    ttl_minutes: int = typer.Option(30, "--ttl-minutes"),
) -> None:
    console.print_json(register_agent(inquiry, scope, ttl_minutes).model_dump_json(indent=2))


@app.command("run-suite")
def run_suite_command(iterations: int = typer.Option(100, min=1, max=5000)) -> None:
    console.print_json(run_suite(iterations=iterations).model_dump_json(indent=2))


@app.command("verify")
def verify_command() -> None:
    report = verify_outputs()
    console.print_json(data=report)
    if not report["passed"]:
        raise typer.Exit(1)


@app.command("dashboard")
def dashboard_command() -> None:
    console.print(str(build_dashboard()))


@app.command("benchmark")
def benchmark_command() -> None:
    console.print_json(data=benchmark_summary())


@app.command("export-demo-pack")
def export_demo_pack_command() -> None:
    console.print(str(export_demo_pack()))


@app.command("stdio")
def stdio_command() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        if request.get("tool") == "agent.register":
            try:
                result = register_agent(request["inquiry_id"], request["scopes"], int(request.get("ttl_minutes", 30)))
                sys.stdout.write(result.model_dump_json() + "\n")
            except Exception as exc:
                sys.stdout.write(json.dumps({"ok": False, "reason": str(exc)}) + "\n")
            sys.stdout.flush()


def main() -> None:
    app()


if __name__ == "__main__":
    main()
